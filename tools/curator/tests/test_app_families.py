import pytest

from tools.curator.app import CSRF_HEADER, create_app
from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import DELETE, KEEP, effective_decisions, read_decisions

PIN = "246810"
API = {CSRF_HEADER: "1"}


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


def families(client, **params):
    response = client.get("/api/families", query_string=params)
    assert response.status_code == 200, response.get_json()
    return {card["family"]: card for card in response.get_json()["families"]}


def decisions(paths):
    return effective_decisions(read_decisions(paths[1]))


def test_a_family_gathers_the_lemma_and_its_forms(logged):
    cards = families(logged)

    ouvrager = cards["OUVRAGER"]
    assert ouvrager["lemma"] == "ouvrager"
    assert {form["norm"] for form in ouvrager["forms"]} == {"OUVRAGER", "OUVRAGEAMES"}
    assert ouvrager["pending_count"] == 2
    assert ouvrager["definition"] == "Travailler avec soin."


def test_common_words_never_appear_in_the_family_queue(logged):
    # PORTE et ETE sont « keep » : jamais proposés au tri
    assert {"PORTE", "ETRE"}.isdisjoint(families(logged))


def test_the_length_filter_selects_the_families_to_work_on(logged):
    assert "OUVRAGER" not in families(logged, min_length=2, max_length=5)
    assert "AABAM" in families(logged, min_length=2, max_length=5)


def test_keeping_a_family_records_every_pending_form(logged, paths):
    response = logged.post("/api/decisions/family", json={"word": "OUVRAGER", "decision": KEEP}, headers=API)

    assert response.status_code == 200
    assert set(response.get_json()["words"]) == {"OUVRAGER", "OUVRAGEAMES"}
    assert decisions(paths) == {"OUVRAGER": KEEP, "OUVRAGEAMES": KEEP}


def test_deleting_stays_the_default_decision(logged, paths):
    logged.post("/api/decisions/family", json={"word": "OUVRAGER"}, headers=API)

    assert decisions(paths)["OUVRAGEAMES"] == DELETE


def test_a_decided_family_leaves_the_queue(logged):
    logged.post("/api/decisions/family", json={"word": "OUVRAGER", "decision": DELETE}, headers=API)

    assert "OUVRAGER" not in families(logged)


def test_an_invalid_decision_is_refused(logged, paths):
    response = logged.post("/api/decisions/family", json={"word": "OUVRAGER", "decision": "peut-être"}, headers=API)

    assert response.status_code == 400
    assert decisions(paths) == {}


def test_a_family_without_anything_left_to_sort_is_refused(logged):
    logged.post("/api/decisions/family", json={"word": "OUVRAGER", "decision": DELETE}, headers=API)

    response = logged.post("/api/decisions/family", json={"word": "OUVRAGER", "decision": DELETE}, headers=API)

    assert response.status_code == 400
    assert "Aucun mot" in response.get_json()["error"]


def test_writing_still_requires_the_csrf_header(logged, paths):
    assert logged.post("/api/decisions/family", json={"word": "OUVRAGER"}).status_code == 403
    assert decisions(paths) == {}


# --- Règles automatiques ---

def test_words_covered_by_a_rule_are_not_proposed_anymore(paths):
    client = create_app(*paths, pin=PIN, secret_key="test-secret", testing=True,
                        auto_rules=["formes-composees"]).test_client()
    client.post("/login", json={"pin": PIN})

    queued = client.get("/api/queue").get_json()["cards"]

    assert "APRIORI" not in {card["norm"] for card in queued}   # « a priori »
    assert "APRIORI" not in families(client)


def test_the_page_says_how_many_words_the_rules_handle(paths):
    client = create_app(*paths, pin=PIN, secret_key="test-secret", testing=True,
                        auto_rules=["formes-composees"]).test_client()
    client.post("/login", json={"pin": PIN})

    assert client.get("/api/stats").get_json()["handled_by_rules"] == 1
