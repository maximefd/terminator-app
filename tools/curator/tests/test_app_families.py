import gzip
import json

import pytest

from tools.conftest import DELA_LINES, WIKTIONARY_RECORDS
from tools.curator.app import CSRF_HEADER, create_app
from tools.curator.repository import MIN_FAMILY_FORMS
from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import DELETE, KEEP, effective_decisions, read_decisions

PIN = "246810"
API = {CSRF_HEADER: "1"}

# La famille « ouvrager » doit dépasser le minimum de formes : on lui en ajoute deux.
EXTRA_DELA = [
    "OUVRAGEA;ouragea;Forme fléchie de 'ouvragea'",
    "OUVRAGERA;ouvragera;Forme fléchie de 'ouvragera'",
]
EXTRA_WIKTIONARY = [
    {"word": "ouvragea", "lang_code": "fr", "pos": "verb",
     "senses": [{"glosses": ["Troisième personne du singulier du passé simple de ouvrager."],
                 "tags": ["form-of"], "form_of": [{"word": "ouvrager"}]}]},
    {"word": "ouvragera", "lang_code": "fr", "pos": "verb",
     "senses": [{"glosses": ["Troisième personne du singulier du futur de ouvrager."],
                 "tags": ["form-of"], "form_of": [{"word": "ouvrager"}]}]},
    # Deuxième graphie en deux mots : le mot n'est pas une famille et ne doit jamais l'être
    {"word": "cava", "lang_code": "fr", "pos": "noun", "senses": [{"glosses": ["Vin espagnol."]}]},
]


@pytest.fixture
def paths(lexique_file, tmp_path):
    dela = tmp_path / "dela.csv"
    dela.write_text("\n".join(DELA_LINES + EXTRA_DELA + [
        "CAVA;cava;Forme fléchie de 'cava'",
        "CAVA;ça va;Forme fléchie de 'ça va'",
    ]) + "\n", encoding="utf-8")
    wiktionary = tmp_path / "wiktionary.jsonl.gz"
    with gzip.open(wiktionary, "wt", encoding="utf-8") as f:
        for record in WIKTIONARY_RECORDS + EXTRA_WIKTIONARY:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    db_path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela, lexique_file, db_path, wiktionary, log=lambda _: None)
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
    ouvrager = families(logged)["OUVRAGER"]

    assert ouvrager["lemma"] == "ouvrager"
    assert {form["norm"] for form in ouvrager["forms"]} == {
        "OUVRAGER", "OUVRAGEAMES", "OUVRAGEA", "OUVRAGERA"}
    assert ouvrager["pending_count"] == 4
    assert ouvrager["definition"] == "Travailler avec soin."


def test_each_form_carries_its_own_definition(logged):
    # Une famille peut mélanger deux mots : c'est la définition de chaque forme qui le montre
    forms = {form["norm"]: form for form in families(logged)["OUVRAGER"]["forms"]}

    assert "passé simple" in forms["OUVRAGEA"]["definition"]
    assert forms["OUVRAGER"]["definition"] == "Travailler avec soin."
    assert forms["OUVRAGER"]["protected"] is False


def test_a_group_of_less_than_three_forms_is_not_a_family(logged, paths):
    # PORTE / PORTES : un mot et son pluriel se jugent aussi vite mot à mot
    assert MIN_FAMILY_FORMS == 3
    assert "PORTE" not in families(logged)
    assert "AABAM" not in families(logged)


def test_a_family_shrinking_below_the_minimum_leaves_the_queue(logged, paths):
    logged.post("/api/decisions", json={"words": ["OUVRAGEA", "OUVRAGERA"], "decision": DELETE}, headers=API)

    assert "OUVRAGER" not in families(logged)


def test_composed_forms_never_make_a_family(logged):
    # « cava » a une graphie en deux mots (« ça va ») : deuxième graphie, donc invisible avant
    assert "CAVA" not in families(logged)


def test_common_words_never_appear_in_the_family_queue(logged):
    assert {"PORTE", "ETRE"}.isdisjoint(families(logged))


def test_the_length_filter_selects_the_families_to_work_on(logged):
    assert "OUVRAGER" not in families(logged, min_length=2, max_length=5)
    assert "OUVRAGER" in families(logged, min_length=6, max_length=11)


def test_keeping_a_family_records_every_pending_form(logged, paths):
    response = logged.post("/api/decisions/family", json={"word": "OUVRAGER", "decision": KEEP}, headers=API)

    assert response.status_code == 200
    assert set(response.get_json()["words"]) == {"OUVRAGER", "OUVRAGEAMES", "OUVRAGEA", "OUVRAGERA"}
    assert set(decisions(paths).values()) == {KEEP}


def test_deleting_stays_the_default_decision(logged, paths):
    logged.post("/api/decisions/family", json={"word": "OUVRAGER"}, headers=API)

    assert decisions(paths)["OUVRAGEAMES"] == DELETE


def test_a_single_form_can_be_sorted_apart_from_its_family(logged, paths):
    # Le cas « hier » : garder le mot courant, supprimer les formes du verbe homonyme
    logged.post("/api/decisions", json={"words": ["OUVRAGER"], "decision": KEEP}, headers=API)

    assert decisions(paths) == {"OUVRAGER": KEEP}
    assert families(logged)["OUVRAGER"]["pending_count"] == 3


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

    queued = {card["norm"] for card in client.get("/api/queue").get_json()["cards"]}

    assert {"APRIORI", "CAVA"}.isdisjoint(queued)


def test_the_page_says_how_many_words_the_rules_handle(paths):
    client = create_app(*paths, pin=PIN, secret_key="test-secret", testing=True,
                        auto_rules=["formes-composees"]).test_client()
    client.post("/login", json={"pin": PIN})

    assert client.get("/api/stats").get_json()["handled_by_rules"] == 2  # APRIORI et CAVA
