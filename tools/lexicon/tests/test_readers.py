import pytest

from tools.lexicon.readers import (
    MAX_DEFINITION_LENGTH,
    WiktionaryEntry,
    read_dela,
    read_lexique,
    read_wiktionary,
    resolve_definition,
    wiktionary_pos,
)


def test_read_dela_groups_display_forms_and_skips_short_words(dela_file):
    dela = read_dela(dela_file)

    assert dela["ETE"] == ["été", "étê"]
    assert dela["APRIORI"] == ["a priori"]
    assert "X" not in dela
    assert len(dela) == 8


def test_read_lexique_sums_homographs_and_keeps_the_most_frequent_lemma(lexique_file):
    lexique = read_lexique(lexique_file)

    porte = lexique["PORTE"]
    assert porte.frequency == pytest.approx((288.39 + 536.96) / 2 + (93.05 + 79.05) / 2)
    assert (porte.lemma, porte.pos) == ("porte", "NOM")
    assert (lexique["ETE"].lemma, lexique["ETE"].pos) == ("être", "AUX")


@pytest.mark.parametrize("lexique_pos, expected", [("NOM", "noun"), ("AUX", "verb"), ("ADJ:num", "adj"), ("PRO:per", "pron"), (None, None), ("???", None)])
def test_lexique_categories_map_to_wiktionary(lexique_pos, expected):
    assert wiktionary_pos(lexique_pos) == expected


def test_read_wiktionary_keeps_french_common_word_definitions(wiktionary_file):
    wiktionary = read_wiktionary(wiktionary_file, wanted={"PORTE", "OUVRAGE", "OUVRAGEAMES"})

    assert wiktionary["PORTE"].definition == "Ouverture permettant le passage."
    assert wiktionary["PORTE"].forms == ["porte"]  # « Porte » (nom propre) et « porte- » (préfixe) ignorés
    assert wiktionary["OUVRAGEAMES"].form_lemma == "ouvrager"
    assert "DOOR" not in wiktionary
    assert "VIDE" not in wiktionary


def test_acronyms_are_ignored(wiktionary_file):
    wiktionary = read_wiktionary(wiktionary_file, wanted={"ETE"})

    assert wiktionary["ETE"].forms == ["été"]
    assert wiktionary["ETE"].definition == "La plus chaude des saisons."


def test_lemma_definitions_are_kept_even_for_unwanted_words(wiktionary_file):
    wiktionary = read_wiktionary(wiktionary_file, wanted={"OUVRAGEAMES"})

    assert wiktionary["OUVRAGER"].definition == "Travailler avec soin."
    assert wiktionary["OUVRAGER"].forms == []  # formes affichées seulement pour les mots voulus


def test_inflected_form_is_explained_by_its_lemma(wiktionary_file):
    wiktionary = read_wiktionary(wiktionary_file, wanted={"OUVRAGEAMES"})

    definition = resolve_definition("OUVRAGEAMES", wiktionary)

    assert definition.text == "Première personne du pluriel du passé simple de ouvrager. — Travailler avec soin."
    assert definition.own is False
    assert resolve_definition("AABAM", wiktionary) is None


def test_own_definition_prefers_the_lexique_category():
    entry = WiktionaryEntry(definitions={"noun": "Vase conique.", "adj": "Sans importance."})

    assert resolve_definition("FUTILE", {"FUTILE": entry}, preferred_pos="adj").text == "Sans importance."
    assert resolve_definition("FUTILE", {"FUTILE": entry}).text == "Vase conique."


def test_inflection_uses_the_lemma_sense_of_the_same_category():
    wiktionary = {
        "FUTILES": WiktionaryEntry(form_gloss="Pluriel de futile.", form_lemma="futile", form_pos="adj"),
        "FUTILE": WiktionaryEntry(definitions={"noun": "Vase conique.", "adj": "Sans importance."}),
    }

    assert resolve_definition("FUTILES", wiktionary).text == "Pluriel de futile. — Sans importance."


def test_long_definitions_are_shortened():
    definition = resolve_definition("LONG", {"LONG": WiktionaryEntry(definitions={"noun": "mot " * 200})})

    assert len(definition.text) <= MAX_DEFINITION_LENGTH + 1
    assert definition.text.endswith("…")
