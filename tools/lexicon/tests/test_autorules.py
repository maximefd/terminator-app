import pytest

from tools.lexicon.autorules import (
    DEFAULT_RULES,
    UnknownRuleError,
    condition,
    load_enabled,
    matches,
    preview,
    save_enabled,
)
from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import KEEP, append_decisions

# « aabamesque » : 10 lettres, absent de Lexique, sans définition ni lemme — le mot type des règles
EXTRA_DELA = [
    "AABAMESQUE;aabamesque;Forme fléchie de 'aabamesque'",
    "ZORFLIQUE;zorflique;Forme fléchie de 'zorflique'",
]


@pytest.fixture
def db_path(dela_file, lexique_file, wiktionary_file, tmp_path):
    dela = tmp_path / "dela_plus.csv"
    dela.write_text(dela_file.read_text(encoding="utf-8") + "\n".join(EXTRA_DELA) + "\n", encoding="utf-8")
    path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela, lexique_file, path, wiktionary_file, log=lambda _: None)
    return path


def test_composed_forms_are_matched_by_their_displayed_form(db_path):
    assert "APRIORI" in matches(db_path, ["formes-composees"])  # « a priori »
    assert "PORTE" not in matches(db_path, ["formes-composees"])


def test_unknown_words_without_definition_are_matched_from_six_letters(db_path):
    matched = matches(db_path, ["inconnues-sans-definition"])

    assert {"AABAMESQUE", "ZORFLIQUE"} <= matched
    assert "AABAM" not in matched  # 5 lettres : trop court pour la règle
    assert "OUVRAGEAMES" not in matched  # forme fléchie : elle a un lemme


def test_long_rare_inflections_rule_covers_inflected_forms(db_path):
    matched = matches(db_path, ["flexions-rares-longues"])

    assert "OUVRAGEAMES" in matched  # 11 lettres, lemme « ouvrager » absent de Lexique
    assert "PORTE" not in matched


def test_no_rule_means_no_word_and_no_condition():
    assert condition([]) == ""
    assert matches("base-inexistante.sqlite", []) == set()


def test_rules_are_saved_and_read_back_in_a_stable_order(tmp_path):
    path = tmp_path / "auto_rules.json"

    saved = save_enabled(path, ["inconnues-sans-definition", "formes-composees", "formes-composees"])

    assert saved == ("formes-composees", "inconnues-sans-definition")
    assert load_enabled(path) == saved
    assert load_enabled(tmp_path / "absent.json") == ()


def test_unknown_rule_is_refused(tmp_path):
    with pytest.raises(UnknownRuleError, match="règle inconnue"):
        save_enabled(tmp_path / "auto_rules.json", ["regle-imaginaire"])


def test_preview_counts_words_and_shows_examples_without_writing(db_path, tmp_path):
    decisions = tmp_path / "decisions.csv"
    append_decisions(decisions, ["APRIORI"], KEEP)

    report = preview(db_path, decisions, sample=5)

    composed = report["formes-composees"]
    assert composed["words"] == 0  # le seul mot visé est gardé explicitement
    assert composed["kept_by_author"] == 1
    unknown = report["inconnues-sans-definition"]
    assert unknown["words"] == 2
    assert set(unknown["sample"]) == {"aabamesque", "zorflique"}
    assert unknown["words_up_to_11"] == 2


def test_recommended_rules_are_the_two_measured_ones():
    assert DEFAULT_RULES == ("formes-composees", "inconnues-sans-definition")
