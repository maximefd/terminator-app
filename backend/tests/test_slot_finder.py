from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder


def find_slots(rows):
    finder = SlotFinder(GridTemplate.from_rows(rows))
    return finder.find_all_slots()


def test_finds_across_and_down_slots_of_two_letters_or_more():
    slots = find_slots([
        "#.#",
        "...",
        "#..",
    ])
    found = {(s["x"], s["y"], s["direction"], s["length"]) for s in slots}
    assert found == {
        (1, 0, "down", 3),
        (2, 1, "down", 2),
        (0, 1, "across", 3),
        (1, 2, "across", 2),
    }


def test_single_letter_runs_are_not_slots():
    assert find_slots([".#.", "#.#"]) == []


def test_slot_ids_are_unique():
    slots = find_slots(["...", "...", "..."])
    assert len(slots) == 6
    assert sorted(s["id"] for s in slots) == list(range(6))
