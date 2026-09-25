"""Mesure d'usage côté serveur (ADR 0016) : ce qui est écrit, ce qui ne l'est jamais, ce qui s'efface."""

import json
from datetime import date, datetime, timedelta

import pytest

import stats
import usage
from extensions import db
from generation_slots import generation_slot
from models import UsageEvent, User, VisitorSalt

from tests.helpers import TEST_PASSWORD, auth_headers, register, send, unique_email
from tests.paths import FIXTURE_LAYOUTS_DIR

BROWSER = {"User-Agent": "Mozilla/5.0 (test)", "CF-IPCountry": "fr"}


@pytest.fixture(autouse=True)
def clean_usage(test_app):
    UsageEvent.query.delete()
    VisitorSalt.query.delete()
    db.session.commit()
    test_app.extensions.pop("usage_salt", None)
    yield


@pytest.fixture
def grid_app(test_app, small_trie, monkeypatch):
    monkeypatch.setattr(test_app, "dela_trie", small_trie)
    monkeypatch.setitem(test_app.config, "LAYOUTS_DIR", FIXTURE_LAYOUTS_DIR)
    return test_app


def events(kind=None):
    query = UsageEvent.query.order_by(UsageEvent.id)
    return (query.filter_by(kind=kind) if kind else query).all()


def generate(client, body, headers=None):
    return client.post("/api/grids/generate", data=json.dumps(body), content_type="application/json",
                       headers={**BROWSER, **(headers or {})})


# --- Générations ---

def test_a_generation_is_recorded_with_its_format_outcome_and_cost(grid_app, client):
    response = generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})

    assert response.status_code == 200, response.get_json()
    [event] = events("generation")
    assert (event.outcome, event.status, event.site, event.lang, event.country) == ("grid", 200, "fr", "fr", "FR")
    assert event.data["format"] == "5x5"
    assert event.data["layout"] == "5x5-001"
    assert event.data["attempts"] >= 1
    assert event.data["must"] == []
    assert event.words is None
    assert event.duration_ms is not None and event.cpu_ms is not None
    assert event.user_id is None  # une génération n'a pas besoin du compte


def test_imposed_words_are_kept_as_text_and_as_shape(grid_app, client, small_words):
    known = next(word for word in small_words if len(word) == 4).upper()
    generate(client, {"size": {"width": 5, "height": 5}, "seed": 42, "must_words": [known.lower()],
                      "wish_words": ["zzqxw"]})

    [event] = events("generation")
    assert event.data["must"] == [{"length": 4, "known": True}]
    assert event.data["wish_count"] == 1
    assert event.words == {"must": [known], "wish": ["ZZQXW"]}


def test_a_failed_generation_keeps_its_reason(grid_app, client, monkeypatch):
    monkeypatch.setitem(grid_app.config, "GENERATION_TIME_BUDGET_S", -1)

    generate(client, {"size": {"width": 5, "height": 5}, "seed": 1})

    assert [(e.outcome, e.status) for e in events("generation")] == [("timeout", 422)]


def test_an_unknown_must_word_is_flagged_for_curation(grid_app, client):
    generate(client, {"size": {"width": 5, "height": 5}, "seed": 1, "must_words": ["zzqxw"]})

    [event] = events("generation")
    assert event.data["must"] == [{"length": 5, "known": False}]
    assert stats.compute()["unknown_words"] == {"ZZQXW": 1}


def test_busy_refusals_are_told_apart(grid_app, client, tmp_path, monkeypatch):
    monkeypatch.setitem(grid_app.config, "GENERATION_LOCK_DIR", str(tmp_path))
    monkeypatch.setitem(grid_app.config, "GENERATION_MAX_CONCURRENT", 1)

    with generation_slot(str(tmp_path), "compte:un-autre-auteur", max_concurrent=1):
        generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})

    assert [(e.outcome, e.status) for e in events("generation")] == [("busy_server", 429)]


def test_an_invalid_generation_request_is_still_counted(grid_app, client):
    generate(client, {"size": {"width": "abc", "height": 5}})

    assert [(e.outcome, e.status) for e in events("generation")] == [("invalid_request", 400)]


def test_a_rate_limited_generation_is_counted_as_such(grid_app, client, monkeypatch):
    # Flask-Limiter refuse avant la vue, par une TooManyRequests : on la lève au même endroit
    from werkzeug.exceptions import TooManyRequests

    def refuse():
        raise TooManyRequests()

    grid_app.before_request_funcs.setdefault(None, []).insert(0, refuse)
    try:
        generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})
    finally:
        grid_app.before_request_funcs[None].remove(refuse)

    assert [(e.outcome, e.status) for e in events("generation")] == [("rate_limited", 429)]


# --- Recherches ---

def test_a_search_is_recorded_with_its_pattern_shape_not_its_text(grid_app, client):
    client.post("/api/search", data=json.dumps({"mask": "p??le"}), content_type="application/json",
                headers=BROWSER)

    [event] = events("search")
    assert event.outcome == "results"
    assert event.data == {"pattern_length": 5, "wildcards": 2, "results": event.data["results"],
                          "logged_in": False}
    assert event.words is None


# --- Visiteurs ---

def test_the_ip_address_is_never_stored(grid_app, client):
    client.post("/api/search", data=json.dumps({"mask": "p??le"}), content_type="application/json",
                headers={**BROWSER, "X-Forwarded-For": "203.0.113.77"}, environ_base={"REMOTE_ADDR": "203.0.113.77"})

    [event] = events("search")
    stored = json.dumps({column.name: str(getattr(event, column.name)) for column in UsageEvent.__table__.columns})
    assert "203.0.113.77" not in stored
    assert len(event.visitor) == 32


def test_the_same_visitor_keeps_one_fingerprint_for_the_day_only(grid_app, client, monkeypatch):
    def search(ip):
        client.post("/api/search", data=json.dumps({"mask": "p??le"}), content_type="application/json",
                    headers=BROWSER, environ_base={"REMOTE_ADDR": ip})
        return events("search")[-1].visitor

    first, again, other = search("198.51.100.1"), search("198.51.100.1"), search("198.51.100.2")
    assert first == again != other

    tomorrow = datetime.utcnow() + timedelta(days=1)
    monkeypatch.setattr(usage, "_utcnow", lambda: tomorrow)
    assert search("198.51.100.1") != first
    # Le sel d'hier est détruit : plus rien ne relie l'empreinte d'hier à une adresse
    assert [salt.day for salt in VisitorSalt.query.all()] == [tomorrow.date()]


# --- Comptes, grilles, erreurs ---

def test_account_steps_are_recorded_and_disappear_with_the_account(client):
    email, tokens = register(client)
    send(client, "post", "/api/auth/login", {"email": email, "password": TEST_PASSWORD})
    user = User.query.filter_by(email=email).one()
    assert [e.outcome for e in events("account")] == ["register", "login"]
    assert all(e.user_id == user.id for e in events("account"))
    assert user.created_at is not None and user.last_login_at is not None

    response = send(client, "delete", "/api/users/me", {"password": TEST_PASSWORD},
                    {"Authorization": f"Bearer {tokens['access_token']}"})

    assert response.status_code == 200
    assert UsageEvent.query.filter_by(user_id=user.id).count() == 0
    # Reste la trace anonyme de la suppression : un compte de moins, sans dire lequel
    assert [(e.outcome, e.user_id) for e in events("account")] == [("delete", None)]


def test_a_failed_login_is_an_error_not_a_login(client):
    send(client, "post", "/api/auth/login", {"email": unique_email(), "password": "mauvais-mot-de-passe"})

    assert events("account") == []
    assert [(e.route, e.status) for e in events("error")] == [("/api/auth/login", 401)]


def test_errors_are_counted_by_route_and_status(client):
    client.get("/api/grids/999999", headers=auth_headers(client))

    assert [(e.route, e.status) for e in events("error")] == [("/api/grids/<int:grid_id>", 404)]


def test_an_unknown_address_is_not_counted(client):
    # Les robots qui sondent /wp-admin rempliraient la table sans rien apprendre à personne
    client.get("/wp-admin/setup.php")

    assert events() == []


def test_measuring_never_breaks_a_request(grid_app, client, monkeypatch):
    def broken(_today):
        raise RuntimeError("base indisponible")

    monkeypatch.setattr(usage, "visitor_fingerprint", broken)
    response = client.post("/api/search", data=json.dumps({"mask": "p??le"}), content_type="application/json")

    assert response.status_code == 200
    assert events() == []


# --- Conservation ---

def test_old_imposed_words_and_old_events_are_purged(test_app):
    now = datetime.utcnow()

    def event(age_days, words):
        return UsageEvent(created_at=now - timedelta(days=age_days), kind="generation", outcome="grid",
                          status=200, site="fr", lang="fr", data={}, words=words)

    db.session.add_all([event(10, {"must": ["ANNIVERSAIRE"]}), event(100, {"must": ["CAMILLE"]}),
                        event(400, None)])
    db.session.add(VisitorSalt(day=date.today() - timedelta(days=2), salt="ancien"))
    db.session.commit()

    usage.purge()

    assert [e.words for e in events()] == [{"must": ["ANNIVERSAIRE"]}, None]
    assert VisitorSalt.query.count() == 0


# --- flask stats ---

def test_stats_answer_the_questions_of_the_adr(grid_app, client, runner):
    generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})
    client.post("/api/search", data=json.dumps({"mask": "p??le"}), content_type="application/json",
                headers=BROWSER)
    register(client)

    result = runner.invoke(args=["stats"])

    assert result.exit_code == 0, result.output
    for expected in ("Visiteurs", "Recherches", "Générations demandées", "taux de réussite", "refus « occupé »",
                     "temps CPU", "Inscriptions", "Grilles conservées", "Erreurs", "Seuils de l'ADR 0013",
                     "Formats", "Mots imposés absents du lexique", "Dernières générations", "5x5"):
        assert expected in result.output


def test_stats_figures(grid_app, client):
    generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})
    generate(client, {"size": {"width": "abc", "height": 5}})

    today = stats.compute()["periods"]["Aujourd'hui"]

    assert (today["generations"], today["grids"], today["errors"], today["visitors"]) == (2, 1, 1, 1)
