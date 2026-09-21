"""Déduction des flèches (#26), y compris les invariants vérifiés sur tout le catalogue."""

from collections import Counter

import pytest

from engine.arrows import BENT_DOWN_RIGHT, BENT_RIGHT_DOWN, DOWN, RIGHT, clues_for_slots, clues_for_words
from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from layout_catalog import catalog


def all_layouts():
    """(identifiant, rangées) de chaque layout valide du catalogue."""
    return [(layout["id"], layout["rows"]) for fmt in catalog() for layout in fmt["layouts"]]


def template_of(rows):
    return GridTemplate.from_rows(rows)


def clue_of(rows, x, y, direction):
    template = template_of(rows)
    slots = [{"id": 0, "x": x, "y": y, "direction": direction, "length": 2}]
    return clues_for_slots(template, slots)[0]


def test_a_horizontal_word_is_defined_from_its_left():
    # x - -
    # La définition tient dans la case noire, la flèche part vers la droite
    clue = clue_of(["x--", "---"], 1, 0, "across")

    assert (clue["cell_x"], clue["cell_y"]) == (0, 0)
    assert clue["arrow"] == RIGHT
    assert clue["exit"] == "right"


def test_a_vertical_word_is_defined_from_above():
    clue = clue_of(["x--", "---"], 0, 1, "down")

    assert (clue["cell_x"], clue["cell_y"]) == (0, 0)
    assert clue["arrow"] == DOWN
    assert clue["exit"] == "bottom"


def test_a_word_against_the_left_edge_is_defined_from_above_with_a_bend():
    # Le mot commence en colonne 0 : rien à sa gauche, la définition passe au-dessus
    clue = clue_of(["x--", "---"], 0, 1, "across")

    assert (clue["cell_x"], clue["cell_y"]) == (0, 0)
    assert clue["arrow"] == BENT_DOWN_RIGHT
    assert clue["exit"] == "bottom"


def test_a_word_against_the_top_edge_is_defined_from_its_left_with_a_bend():
    clue = clue_of(["x--", "---"], 1, 0, "down")

    assert (clue["cell_x"], clue["cell_y"]) == (0, 0)
    assert clue["arrow"] == BENT_RIGHT_DOWN
    assert clue["exit"] == "right"


def test_a_word_in_a_corner_without_any_definition_cell_is_reported_not_dropped():
    # Grille sans aucune case définition : le mot du coin n'a nulle part où se définir
    clue = clue_of(["--", "--"], 0, 0, "across")

    assert (clue["cell_x"], clue["cell_y"]) == (None, None)
    assert clue["arrow"] is None


def test_placed_words_keep_their_text():
    words = [{"text": "AS", "x": 1, "y": 0, "direction": "across", "source": "common"}]

    clues = clues_for_words(template_of(["x--", "---"]), words)

    assert clues[0]["text"] == "AS"
    assert clues[0]["arrow"] == RIGHT


@pytest.mark.parametrize("layout_id, rows", all_layouts(), ids=[layout[0] for layout in all_layouts()])
def test_every_word_of_the_catalogue_has_somewhere_to_be_defined(layout_id, rows):
    """L'invariant qui rend les flèches déductibles : aucun mot orphelin, deux définitions par case au plus,
    et dans une case qui en porte deux, l'une sort par la droite et l'autre par le bas."""
    template = GridTemplate.from_rows(rows)
    slots = SlotFinder(template).find_all_slots()

    clues = clues_for_slots(template, slots)

    assert [c for c in clues if c["arrow"] is None] == []

    by_cell: dict[tuple[int, int], list[str]] = {}
    for clue in clues:
        by_cell.setdefault((clue["cell_x"], clue["cell_y"]), []).append(clue["exit"])
    overloaded = {cell: exits for cell, exits in by_cell.items() if len(exits) > 2}
    assert overloaded == {}
    collisions = {cell: exits for cell, exits in by_cell.items() if len(exits) != len(set(exits))}
    assert collisions == {}


def test_the_catalogue_uses_the_four_arrows():
    """Si une forme disparaissait du catalogue, le rendu pourrait l'oublier sans que rien ne le dise."""
    seen: Counter = Counter()
    for _, rows in all_layouts():
        template = GridTemplate.from_rows(rows)
        slots = SlotFinder(template).find_all_slots()
        seen.update(clue["arrow"] for clue in clues_for_slots(template, slots))

    assert set(seen) == {RIGHT, DOWN, BENT_DOWN_RIGHT, BENT_RIGHT_DOWN}
    assert all(count > 0 for count in seen.values())
