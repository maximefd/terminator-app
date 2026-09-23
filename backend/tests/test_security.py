"""Mesures de sécurité transverses : erreurs, en-têtes, jetons, limites, suppression de compte."""

from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from models import Dictionary, PersonalWord, User, db
from routes import escape_like
from tests.helpers import TEST_PASSWORD, auth_headers, default_dictionary_id, register, send, unique_email
from trie_engine import DictionnaireTrie

TEST_SETTINGS = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "JWT_SECRET_KEY": "test-secret-key-long-enough-for-hs256-signing",
    "RATELIMIT_ENABLED": False,
}


def make_app(**overrides):
    return create_app({**TEST_SETTINGS, **overrides})


# --- En-têtes et erreurs ---

def test_api_responses_carry_security_headers(client):
    response = client.get("/api/status")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert response.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_is_sent_in_production():
    response = make_app(APP_ENV="production").test_client().get("/api/status")

    assert response.headers["Strict-Transport-Security"].startswith("max-age=")


def test_unknown_route_returns_french_json_404(client):
    response = client.get("/api/inexistant")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Ressource introuvable."}


def test_wrong_method_returns_json_405_with_allow_header(client):
    response = client.put("/api/status")

    assert response.status_code == 405
    assert response.get_json() == {"error": "Méthode non autorisée."}
    assert "GET" in response.headers["Allow"]


def test_unexpected_errors_do_not_leak_details():
    app = make_app()

    @app.route("/api/boom")
    def boom():
        raise RuntimeError("détail interne confidentiel")

    response = app.test_client().get("/api/boom")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Erreur interne du serveur."}
    assert "confidentiel" not in response.get_data(as_text=True)


def test_oversized_body_is_rejected(client):
    response = client.post("/api/auth/login", data="x" * (70 * 1024), content_type="application/json")

    assert response.status_code == 413


def test_cors_only_allows_configured_origins(client):
    def preflight(origin):
        return client.options("/api/search", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        })

    assert preflight("http://localhost:3000").headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert "Access-Control-Allow-Origin" not in preflight("https://site-malveillant.example").headers


def test_production_refuses_wildcard_cors(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "flask-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/terminator")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        _load_config_from_env()


# --- Injection et coût des recherches ---

def test_escape_like_neutralizes_sql_wildcards():
    assert escape_like("A%B_C\\") == "A\\%B\\_C\\\\"


def test_trie_search_stops_at_limit():
    trie = DictionnaireTrie()
    for word in ["ABCD", "ABCE", "ABCF", "ABCG"]:
        trie.insert(word)

    assert len(trie.search_pattern("????", limit=2)) == 2
    assert len(trie.search_pattern("????")) == 4


# --- Jetons ---

def test_refresh_token_issues_a_working_access_token(client):
    _, tokens = register(client)

    response = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})

    assert response.status_code == 200
    new_access = response.get_json()["access_token"]
    assert client.get("/api/dictionaries", headers={"Authorization": f"Bearer {new_access}"}).status_code == 200


def test_access_token_cannot_be_used_to_refresh(client):
    _, tokens = register(client)

    response = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {tokens['access_token']}"})

    assert response.status_code == 401
    assert response.get_json()["error"]


def test_refresh_token_cannot_be_used_on_the_api(client):
    _, tokens = register(client)

    response = client.get("/api/dictionaries", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})

    assert response.status_code == 401


def test_invalid_token_returns_french_401(client):
    response = client.get("/api/dictionaries", headers={"Authorization": "Bearer pas-un-jeton"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Jeton d'authentification invalide."}


def test_expired_token_is_flagged_for_refresh(client, test_app):
    email, _ = register(client)
    user = User.query.filter_by(email=email).first()
    expired = create_access_token(identity=str(user.id), expires_delta=timedelta(seconds=-1))

    response = client.get("/api/dictionaries", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "token_expired"


def test_login_with_unreadable_legacy_hash_fails_cleanly(client, test_app):
    email = unique_email()
    db.session.add(User(email=email, password="deleted"))
    db.session.commit()

    response = send(client, "post", "/api/auth/login", {"email": email, "password": "deleted"})

    assert response.status_code == 401


def test_login_error_is_identical_for_unknown_email_and_wrong_password(client):
    email, _ = register(client)

    unknown = send(client, "post", "/api/auth/login", {"email": unique_email(), "password": TEST_PASSWORD})
    wrong = send(client, "post", "/api/auth/login", {"email": email, "password": "mauvais-mot-de-passe"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json() == wrong.get_json()


# --- Limites ---

def test_login_is_rate_limited():
    app = make_app(RATELIMIT_ENABLED=True, RATELIMIT_LOGIN="3 per minute")
    client = app.test_client()
    body = {"email": unique_email(), "password": "mauvais-mot-de-passe"}

    statuses = [send(client, "post", "/api/auth/login", body).status_code for _ in range(4)]

    assert statuses == [401, 401, 401, 429]
    blocked = send(client, "post", "/api/auth/login", body)
    assert blocked.get_json() == {"error": "Trop de requêtes. Réessayez dans quelques instants."}


def login_statuses(client, visitors):
    """Une tentative de connexion par visiteur (valeur de CF-Connecting-IP, None : sans l'en-tête)."""
    body = {"email": unique_email(), "password": "mauvais-mot-de-passe"}
    return [send(client, "post", "/api/auth/login", body,
                 {"CF-Connecting-IP": ip} if ip else None).status_code for ip in visitors]


def test_behind_cloudflare_each_visitor_has_its_own_limit():
    """ADR 0013 : derrière le tunnel, toutes les requêtes arrivent de cloudflared, à la même adresse."""
    app = make_app(RATELIMIT_ENABLED=True, RATELIMIT_LOGIN="2 per minute", CLIENT_IP_HEADER="CF-Connecting-IP")

    statuses = login_statuses(app.test_client(), ["203.0.113.1", "203.0.113.1", "203.0.113.1", "198.51.100.7"])

    assert statuses == [401, 401, 429, 401]  # le second visiteur n'est pas bloqué par le premier


def test_the_visitor_header_is_ignored_unless_configured():
    """Sans tunnel devant l'API, l'en-tête s'invente : il ne doit pas permettre d'échapper à la limite."""
    app = make_app(RATELIMIT_ENABLED=True, RATELIMIT_LOGIN="2 per minute")

    statuses = login_statuses(app.test_client(), ["203.0.113.1", "203.0.113.2", "203.0.113.3"])

    assert statuses == [401, 401, 429]


def test_a_malformed_visitor_header_falls_back_to_the_connection_address():
    app = make_app(RATELIMIT_ENABLED=True, RATELIMIT_LOGIN="2 per minute", CLIENT_IP_HEADER="CF-Connecting-IP")

    statuses = login_statuses(app.test_client(), ["pas-une-adresse", None, "999.1.1.1"])

    assert statuses == [401, 401, 429]  # trois fois l'adresse de la connexion


def test_dictionary_count_is_capped(client, test_app, monkeypatch):
    monkeypatch.setitem(test_app.config, "MAX_DICTIONARIES_PER_USER", 2)
    headers = auth_headers(client)
    default_dictionary_id(client, headers)  # 1er dictionnaire (par défaut)

    assert send(client, "post", "/api/dictionaries", {"name": "Deuxième"}, headers).status_code == 201
    capped = send(client, "post", "/api/dictionaries", {"name": "Troisième"}, headers)
    assert capped.status_code == 400
    assert "Limite" in capped.get_json()["error"]


def test_word_count_is_capped(client, test_app, monkeypatch):
    monkeypatch.setitem(test_app.config, "MAX_WORDS_PER_DICTIONARY", 1)
    headers = auth_headers(client)
    dict_id = default_dictionary_id(client, headers)

    assert send(client, "post", f"/api/dictionaries/{dict_id}/words", {"mot": "premier"}, headers).status_code == 201
    assert send(client, "post", f"/api/dictionaries/{dict_id}/words", {"mot": "second"}, headers).status_code == 400


def test_renaming_to_an_existing_name_is_a_conflict(client):
    headers = auth_headers(client)
    default_dictionary_id(client, headers)
    other = send(client, "post", "/api/dictionaries", {"name": "Autre"}, headers).get_json()

    response = send(client, "patch", f"/api/dictionaries/{other['id']}", {"name": "Dictionnaire par défaut"}, headers)

    assert response.status_code == 409


# --- Suppression de compte (RGPD) ---

def test_account_deletion_removes_all_user_data(client, test_app):
    email, tokens = register(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    dict_id = default_dictionary_id(client, headers)
    send(client, "post", f"/api/dictionaries/{dict_id}/words", {"mot": "confidentiel"}, headers)

    response = client.delete("/api/users/me", headers=headers)

    assert response.status_code == 200
    assert User.query.filter_by(email=email).count() == 0
    assert db.session.get(Dictionary, dict_id) is None
    assert PersonalWord.query.filter_by(dictionary_id=dict_id).count() == 0
    # Les jetons du compte supprimé ne donnent plus accès à rien
    assert client.get("/api/dictionaries", headers=headers).status_code == 401
    refresh = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert refresh.status_code == 401
    assert send(client, "post", "/api/auth/login", {"email": email, "password": TEST_PASSWORD}).status_code == 401
