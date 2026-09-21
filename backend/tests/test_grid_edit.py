"""Correction manuelle d'une grille conservée (#27, ADR 0012) : les lettres font foi."""

import pytest

from engine.grid_edit import (
    allowed_letters,
    apply_letters,
    cells_of_slot,
    fill_ratio,
    letters_of,
    slot_at,
    slots_of,
    text_of,
    words_from_cells,
)


def grid(rows: list[str]) -> list[dict]:
    """Une grille depuis ses rangées : « # » est une case définition, une lettre est une lettre."""
    return [
        {"x": x, "y": y, "char": "" if char == "#" else char, "is_black": char == "#"}
        for y, row in enumerate(rows)
        for x, char in enumerate(row)
    ]


PETITE = grid([
    "#AS",
    "ILE",
])


def test_slots_come_from_the_definition_cells():
    """Les emplacements ne dépendent pas des lettres : c'est ce qui rend l'édition sûre."""
    slots = slots_of(PETITE)

    assert sorted((s["x"], s["y"], s["direction"], s["length"]) for s in slots) == [
        (0, 1, "across", 3),
        (1, 0, "across", 2),
        (1, 0, "down", 2),
        (2, 0, "down", 2),
    ]


def test_a_letter_change_renames_two_words_and_only_them():
    """Changer une lettre touche son mot horizontal et son mot vertical, jamais les autres."""
    # AS / ILE : on remplace le A de (1,0) par un O
    edited, problems = apply_letters(PETITE, [{"x": 1, "y": 0, "char": "O"}])

    assert problems == []
    words = {(w["x"], w["y"], w["direction"]): w["text"] for w in words_from_cells(edited, words_from_cells(PETITE))}
    assert words[(1, 0, "across")] == "OS"
    assert words[(1, 0, "down")] == "OL"
    assert words[(0, 1, "across")] == "ILE"
    assert words[(2, 0, "down")] == "SE"


def test_a_changed_word_is_no_longer_the_engine_s():
    """La provenance dit d'où vient un mot : celui que l'auteur a corrigé devient « manuel »."""
    before = [
        {"id": 0, "text": "AS", "x": 1, "y": 0, "direction": "across", "source": "must"},
        {"id": 1, "text": "ILE", "x": 0, "y": 1, "direction": "across", "source": "common"},
    ]
    edited, _ = apply_letters(PETITE, [{"x": 1, "y": 0, "char": "O"}])

    words = {(w["x"], w["y"], w["direction"]): w["source"] for w in words_from_cells(edited, before)}

    assert words[(1, 0, "across")] == "manuel"
    assert words[(0, 1, "across")] == "common"


def test_a_definition_cell_refuses_a_letter():
    """Une lettre posée sur une case définition ne s'afficherait nulle part : on la refuse."""
    edited, problems = apply_letters(PETITE, [{"x": 0, "y": 0, "char": "Z"}])

    assert problems == ["la case (0, 0) est une case définition"]
    assert edited == PETITE


def test_a_cell_outside_the_grid_is_refused():
    _, problems = apply_letters(PETITE, [{"x": 9, "y": 9, "char": "Z"}])

    assert problems == ["la case (9, 9) n'existe pas dans cette grille"]


def test_slot_at_finds_the_word_running_through_a_cell():
    slot = slot_at(PETITE, 2, 1, "across")

    assert (slot["x"], slot["y"], slot["length"]) == (0, 1, 3)
    assert cells_of_slot(slot) == [(0, 1), (1, 1), (2, 1)]
    assert slot_at(PETITE, 0, 0, "across") is None


def test_only_letters_keeping_the_crossing_a_word_are_allowed():
    """Cohérence d'arc : une lettre n'est proposée que si le mot perpendiculaire reste un mot."""
    lexique = {"AS", "OS", "AL", "OL", "ILE", "SE"}

    allowed = allowed_letters(PETITE, slot_at(PETITE, 1, 0, "across"), lambda word: word in lexique)

    # En (1,0), le croisement vertical est « AL » : seuls A et O gardent un mot (AL, OL)
    assert allowed[0] == {"A", "O"}
    # En (2,0), le croisement est « SE » : seul S convient
    assert allowed[1] == {"S"}


def test_a_cell_without_a_crossing_constrains_nothing():
    sans_croisement = grid([
        "#AB",
        "###",
    ])

    allowed = allowed_letters(sans_croisement, slot_at(sans_croisement, 1, 0, "across"), lambda word: False)

    assert allowed == [set(), set()]


@pytest.mark.parametrize("char", ["", " "])
def test_an_erased_cell_leaves_a_hole_and_keeps_the_length(char):
    """Effacer une lettre ne raccourcit pas le mot : « ?S » et non « S ».

    Sans cette marque, toute la géométrie qui s'appuie sur la longueur du mot — surbrillance,
    remplacement, croisements — se décalerait d'une case.
    """
    troue = grid(["#AS", "ILE"])
    troue[1]["char"] = char

    mots = {(w["x"], w["y"], w["direction"]): w for w in words_from_cells(troue)}

    assert mots[(1, 0, "across")]["text"] == "?S"
    assert mots[(1, 0, "across")]["length"] == 2
    assert mots[(1, 0, "across")]["complete"] is False
    assert mots[(0, 1, "across")]["complete"] is True


def test_erasing_is_a_letter_edit_like_any_other():
    """Une case se vide en écrivant « rien » : c'est le même chemin que poser une lettre."""
    efface, problems = apply_letters(PETITE, [{"x": 1, "y": 0, "char": ""}])

    assert problems == []
    assert fill_ratio(efface) == round(4 / 5, 3)
    assert text_of(slot_at(efface, 1, 0, "across"), letters_of(efface)) == "?S"


def test_an_unfinished_crossing_does_not_constrain_yet():
    """Un croisement troué se remplira plus tard : le refuser viderait la liste sans raison."""
    lexique = {"AS", "OS", "AL", "OL", "ILE", "SE"}
    troue, _ = apply_letters(PETITE, [{"x": 1, "y": 1, "char": ""}])

    allowed = allowed_letters(troue, slot_at(troue, 1, 0, "across"), lambda word: word in lexique)

    # Le vertical en (1,0) est « A? » : inachevé, donc aucune contrainte sur cette case
    assert allowed[0] == set()
    # Le vertical en (2,0) reste « SE », entier : il contraint toujours
    assert allowed[1] == {"S"}
