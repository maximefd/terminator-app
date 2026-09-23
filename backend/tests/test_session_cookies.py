"""Session en cookies httpOnly, protection CSRF et révocation (ADR 0015)."""

from datetime import timedelta

import pytest

import auth
from tests.helpers import TEST_PASSWORD, send, unique_email


def set_cookies(response) -> dict[str, str]:
    """Les en-têtes Set-Cookie de la réponse, par nom de cookie."""
    cookies = {}
    for header in response.headers.getlist("Set-Cookie"):
        cookies[header.split("=", 1)[0]] = header
    return cookies


def sign_up(client) -> str:
    """Inscription par le navigateur : la session reste dans les cookies du client de test."""
    email = unique_email()
    assert send(client, "post", "/api/auth/register", {"email": email, "password": TEST_PASSWORD}).status_code == 201
    return email


def csrf(client, kind="access") -> dict:
    """L'en-tête que le frontend recopie depuis le cookie lisible (double soumission)."""
    return {"X-CSRF-TOKEN": client.get_cookie(f"csrf_{kind}_token").value}


def test_the_session_is_in_httponly_cookies_and_never_in_the_body(client):
    response = send(client, "post", "/api/auth/register", {"email": unique_email(), "password": TEST_PASSWORD})
    cookies = set_cookies(response)

    assert response.get_json() == {"message": "Compte créé."}
    for name, path in (("access_token_cookie", "/api/"), ("refresh_token_cookie", "/api/auth/")):
        assert "HttpOnly" in cookies[name] and "SameSite=Lax" in cookies[name]
        assert f"Path={path}" in cookies[name]
    # Les jetons CSRF, eux, doivent être lus par le frontend
    for name in ("csrf_access_token", "csrf_refresh_token"):
        assert "HttpOnly" not in cookies[name]


def test_the_browser_session_works_with_cookies_alone(client):
    email = sign_up(client)

    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.get_json()["email"] == email


def test_a_cookie_session_cannot_write_without_the_csrf_token(client):
    """Un autre site peut faire envoyer les cookies ; il ne peut pas lire le jeton CSRF pour le recopier."""
    sign_up(client)

    forged = send(client, "post", "/api/dictionaries", {"name": "Piège"})
    legitimate = send(client, "post", "/api/dictionaries", {"name": "Thème"}, csrf(client))

    assert forged.status_code == 401
    assert legitimate.status_code == 201


def test_the_refresh_cookie_renews_the_access_cookie(client):
    sign_up(client)
    client.delete_cookie("access_token_cookie", path="/api/")  # expiré au bout de 15 minutes

    assert client.get("/api/users/me").status_code == 401
    assert send(client, "post", "/api/auth/refresh", None, csrf(client, "refresh")).status_code == 200
    assert client.get("/api/users/me").status_code == 200


def test_logging_out_revokes_the_tokens_not_just_the_cookies(client):
    """Un refresh token copié avant la déconnexion ne doit plus rien ouvrir pendant ses 7 jours."""
    sign_up(client)
    stolen_refresh = client.get_cookie("refresh_token_cookie", path="/api/auth/").value
    stolen_access = client.get_cookie("access_token_cookie", path="/api/").value
    refresh_csrf = csrf(client, "refresh")

    response = send(client, "post", "/api/auth/logout", None, refresh_csrf)

    assert response.status_code == 200
    assert client.get("/api/users/me").status_code == 401  # cookies effacés
    replayed_refresh = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {stolen_refresh}"})
    replayed_access = client.get("/api/users/me", headers={"Authorization": f"Bearer {stolen_access}"})
    assert replayed_refresh.status_code == replayed_access.status_code == 401
    assert replayed_access.get_json() == {"error": "Session fermée. Veuillez vous reconnecter."}


def test_logging_out_always_succeeds(client):
    """Sans session, ou avec une session déjà fermée : on doit toujours pouvoir se déconnecter."""
    assert send(client, "post", "/api/auth/logout").status_code == 200


def test_changing_the_password_closes_every_open_session(client, test_app, monkeypatch):
    email = sign_up(client)
    old_access = client.get_cookie("access_token_cookie", path="/api/").value
    test_app.config["MAIL_BACKEND"] = "memory"
    test_app.extensions["sent_emails"] = []
    send(client, "post", "/api/auth/password/forgot", {"email": email})
    token = test_app.extensions["sent_emails"][-1].get_content().split("token=")[1].split()[0]
    test_app.config["MAIL_BACKEND"] = "console"
    # Le changement est daté une seconde plus tard : un jeton émis dans la même seconde resterait valable
    now = auth._utcnow()
    monkeypatch.setattr(auth, "_utcnow", lambda: now + timedelta(seconds=1))

    send(client, "post", "/api/auth/password/reset", {"token": token, "password": "NouveauSecret42"})

    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {old_access}"})
    assert response.status_code == 401


def test_deleting_the_account_clears_the_session_cookies(client):
    sign_up(client)

    response = send(client, "delete", "/api/users/me", {"password": TEST_PASSWORD}, csrf(client))

    assert response.status_code == 200
    cookies = set_cookies(response)
    assert "access_token_cookie=;" in cookies["access_token_cookie"]


def test_cors_allows_credentials_for_the_frontend_only(client):
    def preflight(origin):
        return client.options("/api/dictionaries", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-CSRF-TOKEN, Content-Type",
        })

    allowed = preflight("http://localhost:3000")
    assert allowed.headers["Access-Control-Allow-Credentials"] == "true"
    assert "x-csrf-token" in allowed.headers["Access-Control-Allow-Headers"].lower()
    assert "Access-Control-Allow-Origin" not in preflight("https://site-malveillant.example").headers


@pytest.mark.parametrize("app_env, secure", [("production", True), ("development", False)])
def test_cookies_are_secure_in_production(monkeypatch, app_env, secure):
    from app import _load_config_from_env

    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("SECRET_KEY", "une-cle-de-production-suffisamment-longue")
    monkeypatch.setenv("JWT_SECRET_KEY", "une-autre-cle-de-production-suffisamment-longue")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/terminator")
    monkeypatch.setenv("COOKIE_DOMAIN", "terminator.fr")

    config = _load_config_from_env()

    assert config["JWT_COOKIE_SECURE"] is secure
    assert config["JWT_COOKIE_DOMAIN"] == "terminator.fr"
