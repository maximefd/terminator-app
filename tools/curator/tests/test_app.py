import sqlite3
from datetime import date

import pytest

from tools.curator.app import CSRF_HEADER, MAX_PIN_FAILURES, create_app
from tools.curator.repository import LexiconRepository
from tools.curator.stats import streak_days
from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import effective_decisions, read_decisions

PIN = "246810"
API = {CSRF_HEADER: "1"}


@pytest.fixture
def paths(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)
    return db_path, tmp_path / "decisions.csv"


@pytest.fixture
def client(paths):
    db_path, decisions_path = paths
    return create_app(db_path, decisions_path, PIN, secret_key="test-secret", testing=True).test_client()


@pytest.fixture
def logged(client):
    assert client.post("/login", json={"pin": PIN}).status_code == 200
    return client


def queue_words(client, **params):
    response = client.get("/api/queue", query_string=params)
    assert response.status_code == 200, response.get_json()
    return [card["norm"] for card in response.get_json()["cards"]]


def decisions(paths):
    return effective_decisions(read_decisions(paths[1]))


# --- Démarrage ---

def test_refuses_to_start_with_a_short_pin(paths):
    with pytest.raises(ValueError, match="CURATOR_PIN"):
        create_app(*paths, pin="1234")


# --- Authentification et sécurité ---

def test_pages_redirect_to_login_and_api_requires_the_pin(client):
    assert client.get("/").headers["Location"].endswith("/login")
    assert client.get("/api/queue").status_code == 401
    assert client.get("/login").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_app_script_is_not_public(client):
    assert client.get("/static/app.js").status_code == 302


def test_wrong_pin_is_refused_then_locked(client):
    for _ in range(MAX_PIN_FAILURES):
        assert client.post("/login", json={"pin": "000000"}).status_code == 401

    locked = client.post("/login", json={"pin": PIN})

    assert locked.status_code == 429


def test_session_cookie_is_http_only_and_same_site_strict(client):
    cookie = client.post("/login", json={"pin": PIN}).headers["Set-Cookie"]

    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie


def test_writes_require_the_csrf_header(logged):
    assert logged.post("/api/undo").status_code == 403
    assert logged.post("/api/undo", headers=API).status_code == 200


def test_security_headers(logged):
    response = logged.get("/")

    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Frame-Options"] == "DENY"


def test_logout_ends_the_session(logged):
    logged.post("/logout")

    assert logged.get("/api/queue").status_code == 401


def test_database_is_opened_read_only(paths):
    repository = LexiconRepository(paths[0])

    with pytest.raises(sqlite3.OperationalError):
        repository.connection().execute("DELETE FROM words")


# --- File de mots ---

def test_queue_skips_common_words_and_puts_short_rare_words_first(logged):
    assert queue_words(logged) == ["AABAM", "OUVRAGE", "APRIORI", "OUVRAGER", "OUVRAGEAMES"]


def test_queue_filters(logged):
    assert queue_words(logged, suggestion="likely_delete") == ["AABAM", "OUVRAGEAMES"]
    assert queue_words(logged, min_length=6, max_length=8) == ["OUVRAGE", "APRIORI", "OUVRAGER"]
    assert logged.get("/api/queue", query_string={"suggestion": "keep"}).status_code == 400


def test_queue_pagination(logged):
    first = logged.get("/api/queue", query_string={"limit": 2}).get_json()
    second = logged.get("/api/queue", query_string={"limit": 2, "after": first["next_after"]}).get_json()

    assert [c["norm"] for c in first["cards"]] == ["AABAM", "OUVRAGE"]
    assert [c["norm"] for c in second["cards"]] == ["APRIORI", "OUVRAGER"]


def test_cards_carry_what_the_author_needs_to_decide(logged):
    card = logged.get("/api/queue", query_string={"min_length": 11}).get_json()["cards"][0]

    assert card["norm"] == "OUVRAGEAMES"
    assert card["forms"] == ["ouvrageâmes"]
    assert card["definition_kind"] == "inflection"
    assert card["lemma"] == "ouvrager"
    assert card["family_size"] == 2


# --- Décisions ---

def test_decision_is_recorded_and_leaves_the_queue(logged, paths):
    response = logged.post("/api/decisions", json={"words": ["AABAM"], "decision": "delete"}, headers=API)

    assert response.status_code == 200
    assert decisions(paths) == {"AABAM": "delete"}
    assert "AABAM" not in queue_words(logged)


@pytest.mark.parametrize("body", [
    {"words": ["AABAM"], "decision": "maybe"},
    {"words": ["INCONNU"], "decision": "delete"},
    {"words": "AABAM", "decision": "delete"},
    {"words": [], "decision": "delete"},
    {"words": ["aabam"], "decision": "delete"},
])
def test_invalid_decisions_are_rejected(logged, paths, body):
    assert logged.post("/api/decisions", json=body, headers=API).status_code == 400
    assert decisions(paths) == {}


def test_undo_returns_the_card(logged, paths):
    logged.post("/api/decisions", json={"words": ["OUVRAGE"], "decision": "keep"}, headers=API)

    response = logged.post("/api/undo", headers=API).get_json()

    assert response["words"] == ["OUVRAGE"]
    assert response["cards"][0]["norm"] == "OUVRAGE"
    assert decisions(paths) == {}
    assert "OUVRAGE" in queue_words(logged)


def test_family_deletion_removes_the_lemma_and_its_forms(logged, paths):
    response = logged.post("/api/decisions/family", json={"word": "OUVRAGEAMES"}, headers=API)

    assert sorted(response.get_json()["words"]) == ["OUVRAGEAMES", "OUVRAGER"]
    assert decisions(paths) == {"OUVRAGER": "delete", "OUVRAGEAMES": "delete"}

    undone = logged.post("/api/undo", headers=API).get_json()
    assert sorted(undone["words"]) == ["OUVRAGEAMES", "OUVRAGER"]


def test_family_deletion_spares_kept_and_common_words(logged, paths):
    logged.post("/api/decisions", json={"words": ["OUVRAGER"], "decision": "keep"}, headers=API)

    response = logged.post("/api/decisions/family", json={"word": "OUVRAGEAMES"}, headers=API)

    assert response.get_json()["words"] == ["OUVRAGEAMES"]

    # PORTE et PORTES sont très courants (keep) : jamais supprimés par famille. Il n'y a donc rien
    # à trier, ce qui n'est pas une erreur — simplement une décision qui n'écrit rien.
    spared = logged.post("/api/decisions/family", json={"word": "PORTES"}, headers=API)

    assert spared.status_code == 200
    assert spared.get_json()["words"] == [] and spared.get_json()["already_sorted"] is True
    assert "PORTE" not in decisions(paths) and "PORTES" not in decisions(paths)


# --- Statistiques ---

def test_stats_count_today_and_remaining_words(logged):
    logged.post("/api/decisions", json={"words": ["AABAM"], "decision": "delete"}, headers=API)
    logged.post("/api/decisions", json={"words": ["OUVRAGE"], "decision": "keep"}, headers=API)

    stats = logged.get("/api/stats").get_json()

    assert stats["today"] == 2
    assert stats["streak_days"] == 1
    assert stats["decisions"] == {"delete": 1, "keep": 1}
    assert stats["remaining_by_length"] == {"2-5": 0, "6-8": 2, "9-11": 1, "12+": 0}


def test_stats_include_progression(logged, paths):
    logged.post("/api/decisions", json={"words": ["OUVRAGE"], "decision": "keep"}, headers=API)
    logged.post("/api/decisions", json={"words": ["OUVRAGE"], "decision": "delete"}, headers=API)
    logged.post("/api/decisions/family", json={"word": "OUVRAGEAMES"}, headers=API)
    logged.post("/api/decisions", json={"words": ["AABAM"], "decision": "delete"}, headers=API)

    stats = logged.get("/api/stats").get_json()

    assert stats["daily_goal"] == 100
    assert stats["today"] == 4  # OUVRAGE ne compte qu'une fois malgré le changement d'avis
    assert stats["total_decided"] == 4
    assert (stats["level"]["number"], stats["level"]["title"]) == (1, "Apprenti")
    assert len(stats["week"]) == 7
    assert stats["week"][-1]["count"] == 4
    badges = {a["id"] for a in stats["achievements"] if a["unlocked"]}
    # AABAM était le seul mot de 2 à 5 lettres à trier
    assert {"first_word", "family", "band_2_5"} <= badges
    assert "hundred_day" not in badges


def test_daily_goal_is_configurable(paths):
    client = create_app(*paths, pin=PIN, secret_key="x", testing=True, daily_goal=30).test_client()
    client.post("/login", json={"pin": PIN})

    assert client.get("/api/stats").get_json()["daily_goal"] == 30
    with pytest.raises(ValueError, match="CURATOR_DAILY_GOAL"):
        create_app(*paths, pin=PIN, daily_goal=0)


def test_streak_days():
    today = date(2026, 9, 15)
    days = {date(2026, 9, 13), date(2026, 9, 14)}

    assert streak_days(days, today) == 2           # série toujours en cours aujourd'hui
    assert streak_days(days | {today}, today) == 3
    assert streak_days({date(2026, 9, 10)}, today) == 0
