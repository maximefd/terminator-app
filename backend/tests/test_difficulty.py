"""Estimation de la difficulté d'une demande de mots imposés, calibrée sur les mesures (#73)."""

from engine.difficulty import (
    MEASURED_SUCCESS,
    length_band,
    level_of,
    rare_letters,
    request_difficulty,
    success_rate,
    word_difficulty,
)


def test_length_bands_follow_the_measurements():
    assert [length_band(n) for n in (2, 5, 6, 7, 8, 9, 10, 13)] == [
        "2-5", "2-5", "6-7", "6-7", "8-9", "8-9", "10+", "10+"]


def test_rare_letters_are_listed_once_in_order():
    assert rare_letters("BIBLIOTHEQUES") == ["Q"]
    assert rare_letters("ZAZOU") == ["Z"]
    assert rare_letters("PORTE") == []


def test_a_short_common_word_is_easy():
    facile = word_difficulty("RUE")

    assert facile["level"] == "facile"
    assert facile["success_rate"] == MEASURED_SUCCESS[(1, "2-5", False)]
    assert facile["reasons"] == []


def test_a_long_word_with_a_rare_letter_says_why():
    dur = word_difficulty("BIBLIOTHEQUES")

    assert dur["level"] == "difficile"
    assert dur["rare_letters"] == ["Q"]
    assert any("13 lettres" in raison for raison in dur["reasons"])
    assert any("Q" in raison for raison in dur["reasons"])


def test_adding_words_lowers_the_estimate():
    """C'est ce que l'auteur doit voir se dégrader au fur et à mesure qu'il ajoute des mots."""
    un = request_difficulty(["ROUTE"])
    deux = request_difficulty(["ROUTE", "PORTE"])
    trois = request_difficulty(["ROUTE", "PORTE", "TABLE"])

    assert un["success_rate"] > deux["success_rate"] > trois["success_rate"]
    assert un["level"] == "facile"


def test_the_hardest_word_is_named_and_a_way_out_is_offered():
    demande = request_difficulty(["RUE", "BIBLIOTHEQUES", "PORTE"])

    assert demande["hardest"] == "BIBLIOTHEQUES"
    assert demande["level"] in ("difficile", "très difficile")
    assert "souhaité" in demande["advice"]


def test_an_easy_request_offers_no_advice():
    assert request_difficulty(["RUE"])["advice"] is None


def test_beyond_three_words_the_estimate_is_flagged_as_unmeasured():
    """Rien n'a été mesuré au-delà de trois mots : le taux à trois est alors une borne haute."""
    trois = request_difficulty(["RUE", "PORTE", "TABLE"])
    quatre = request_difficulty(["RUE", "PORTE", "TABLE", "ROUTE"])

    assert trois["measured"] and not quatre["measured"]
    assert quatre["success_rate"] == trois["success_rate"]


def test_an_unmeasured_rare_cell_is_penalised_not_invented():
    mesure, _ = success_rate(2, "8-9", False)
    estime, measured = success_rate(2, "8-9", True)

    assert not measured and estime < mesure


def test_no_words_is_no_constraint():
    assert request_difficulty([]) == {"words": [], "success_rate": 1.0, "level": "facile",
                                      "measured": True, "hardest": None, "advice": None}


def test_levels_follow_the_thresholds():
    assert [level_of(r) for r in (1.0, 0.9, 0.75, 0.5, 0.2)] == [
        "facile", "facile", "moyen", "difficile", "très difficile"]
