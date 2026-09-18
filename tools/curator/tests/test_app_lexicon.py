"""Curateur : recherche d'un mot et mise à jour du lexique tous les N mots triés."""

import pytest

from tools.curator.app import CSRF_HEADER, create_app
from tools.curator.exporter import LexiconExporter
from tools.lexicon.build import build_lexicon

PIN = "246810"
API = {CSRF_HEADER: "1"}


class FakeLookup:
    def __init__(self):
        self.words = []

    def lookup(self, word):
        self.words.append(word)
        return {"provider": "libre", "answer": None, "results": [], "links": {"Google": "https://www.google.com"},
                "cached": False}


class FakeExport:
    def __init__(self):
        self.calls = 0

    def __call__(self, db_path, decisions_path, out_path, auto_rules=(), filter_level="aucun"):
        self.calls += 1
        return {"exported": 7, "deleted_by_author": 1}


@pytest.fixture
def setup(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)
    decisions_path = tmp_path / "decisions.csv"
    lookup, export = FakeLookup(), FakeExport()
    exporter = LexiconExporter(db_path, decisions_path, tmp_path / "out.csv", every=2, export=export, background=False)
    app = create_app(db_path, decisions_path, PIN, secret_key="test", testing=True, lookup=lookup,
                     exporter=exporter, terminator_url="http://mac.local:3000/grid")
    client = app.test_client()
    assert client.post("/login", json={"pin": PIN}).status_code == 200
    return client, lookup, export


def test_lookup_searches_the_display_form(setup):
    client, lookup, _ = setup

    response = client.get("/api/lookup?word=OUVRAGEAMES")

    assert response.status_code == 200
    assert lookup.words == ["ouvrageâmes"]  # la forme avec accents, pas la forme normalisée
    assert response.get_json()["word"] == "ouvrageâmes"


@pytest.mark.parametrize("word, status", [("inconnu", 400), ("ZZZZZZ", 404), ("<script>", 400)])
def test_lookup_rejects_invalid_or_unknown_words(setup, word, status):
    client, lookup, _ = setup

    assert client.get("/api/lookup", query_string={"word": word}).status_code == status
    assert lookup.words == []


def test_lookup_requires_the_pin(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)
    client = create_app(db_path, tmp_path / "d.csv", PIN, testing=True, lookup=FakeLookup()).test_client()

    assert client.get("/api/lookup?word=AABAM").status_code == 401


def test_lexicon_is_exported_when_a_milestone_is_reached(setup):
    client, _, export = setup

    first = client.post("/api/decisions", json={"words": ["AABAM"], "decision": "delete"}, headers=API).get_json()
    second = client.post("/api/decisions", json={"words": ["OUVRAGE"], "decision": "keep"}, headers=API).get_json()

    assert first["lexicon_export"] is None
    assert second["lexicon_export"]["state"] == "done"
    assert export.calls == 1


def test_family_deletion_can_trigger_the_export(setup):
    client, _, export = setup

    response = client.post("/api/decisions/family", json={"word": "OUVRAGEAMES"}, headers=API).get_json()

    assert len(response["words"]) == 2
    assert response["lexicon_export"] is not None
    assert export.calls == 1


def test_lexicon_status_and_manual_export(setup):
    client, _, export = setup

    status = client.get("/api/lexicon").get_json()
    assert (status["state"], status["every"], status["next_at"]) == ("idle", 2, 2)
    assert status["terminator_url"] == "http://mac.local:3000/grid"

    assert client.post("/api/lexicon/export").status_code == 403  # en-tête CSRF obligatoire
    response = client.post("/api/lexicon/export", headers=API)

    assert response.status_code == 202
    assert response.get_json()["started"] is True
    assert export.calls == 1
