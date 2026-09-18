from datetime import datetime, timedelta, timezone

import pytest

from tools.curator.app import CSRF_HEADER, create_app
from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import DELETE, KEEP, append_decisions, effective_decisions, read_decisions

PIN = "246810"
API = {CSRF_HEADER: "1"}
NOW = datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc)


@pytest.fixture
def paths(dela_file, lexique_file, wiktionary_file, tmp_path):
    db_path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, db_path, wiktionary_file, log=lambda _: None)
    return db_path, tmp_path / "decisions.csv"


@pytest.fixture
def logged(paths):
    client = create_app(*paths, pin=PIN, secret_key="test-secret", testing=True, auto_rules=()).test_client()
    assert client.post("/login", json={"pin": PIN}).status_code == 200
    return client


def to_review(client):
    response = client.get("/api/revisions")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def decisions(paths):
    return effective_decisions(read_decisions(paths[1]))


def test_a_family_judged_both_ways_comes_back_for_a_second_look(logged, paths):
    append_decisions(paths[1], ["OUVRAGEAMES"], DELETE)
    append_decisions(paths[1], ["OUVRAGER"], KEEP)

    body = to_review(logged)

    assert {item["norm"] for item in body["items"]} == {"OUVRAGEAMES", "OUVRAGER"}
    assert body["counts"]["famille-incoherente"] == 2
    assert body["items"][0]["explanation"].startswith("Dans la famille")


def test_the_count_covers_everything_even_when_the_page_is_short(logged, paths):
    # Dates fixées : trois décisions dans la même seconde font une rafale, quelle que soit la machine
    for word in ("OUVRAGEAMES", "AABAM", "OUVRAGE"):
        append_decisions(paths[1], [word], DELETE, now=NOW)
    append_decisions(paths[1], ["OUVRAGER"], KEEP, now=NOW + timedelta(minutes=1))

    body = logged.get("/api/revisions", query_string={"limit": 1}).get_json()

    # Une seule carte renvoyée, mais le compte annoncé reste celui de toutes les décisions à revoir
    assert len(body["items"]) == 1
    assert body["total"] == 4
    assert body["counts"] == {"famille-incoherente": 2, "mot-courant-supprime": 0, "decision-eclair": 2}


def test_a_common_word_deleted_comes_back_with_its_frequency(logged, paths):
    append_decisions(paths[1], ["PORTE"], DELETE)

    item = to_review(logged)["items"][0]

    assert (item["norm"], item["decision"], item["reason"]) == ("PORTE", DELETE, "mot-courant-supprime")
    assert item["form"] == "porte"
    assert item["zipf"] > 2.5


def test_confirming_leaves_the_decision_and_closes_the_case(logged, paths):
    append_decisions(paths[1], ["PORTE"], DELETE)

    response = logged.post("/api/revisions", json={"words": ["PORTE"], "decision": DELETE}, headers=API)

    assert response.status_code == 200
    assert decisions(paths)["PORTE"] == DELETE
    assert to_review(logged)["items"] == []


def test_inverting_changes_the_decision_and_closes_the_case(logged, paths):
    append_decisions(paths[1], ["PORTE"], DELETE)

    logged.post("/api/revisions", json={"words": ["PORTE"], "decision": KEEP}, headers=API)

    assert decisions(paths)["PORTE"] == KEEP
    assert to_review(logged)["items"] == []


def test_a_revision_is_written_in_its_own_batch(logged, paths):
    append_decisions(paths[1], ["PORTE"], DELETE)

    logged.post("/api/revisions", json={"words": ["PORTE"], "decision": KEEP}, headers=API)

    assert read_decisions(paths[1])[-1].batch.split("-")[1].startswith("revision.")


def test_an_unknown_word_or_decision_is_refused(logged, paths):
    append_decisions(paths[1], ["PORTE"], DELETE)

    assert logged.post("/api/revisions", json={"words": ["ZZZZZ"], "decision": KEEP}, headers=API).status_code == 400
    assert logged.post("/api/revisions", json={"words": ["PORTE"], "decision": "bof"}, headers=API).status_code == 400
    assert logged.post("/api/revisions", json={"words": "PORTE", "decision": KEEP}, headers=API).status_code == 400
    assert decisions(paths)["PORTE"] == DELETE


def test_writing_still_requires_the_csrf_header(logged, paths):
    append_decisions(paths[1], ["PORTE"], DELETE)

    assert logged.post("/api/revisions", json={"words": ["PORTE"], "decision": KEEP}).status_code == 403
    assert decisions(paths)["PORTE"] == DELETE


def test_the_pages_are_served_and_need_the_pin(paths):
    client = create_app(*paths, pin=PIN, secret_key="test-secret", testing=True, auto_rules=()).test_client()

    assert client.get("/revision").headers["Location"].endswith("/login")
    assert client.get("/familles").headers["Location"].endswith("/login")
    client.post("/login", json={"pin": PIN})
    assert client.get("/revision").status_code == 200
    assert client.get("/familles").status_code == 200
