import pytest

from engine.grid_solver import GridSolver
from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from grid_generator import GridGenerator
from tests.paths import FIXTURE_LAYOUTS_DIR
from trie_engine import DictionnaireTrie


def make_generator(words, trie, layouts_dir=FIXTURE_LAYOUTS_DIR, width=5, height=5, **kwargs):
    return GridGenerator(width, height, words, prebuilt_trie=trie, layouts_dir=layouts_dir, **kwargs)


def test_generates_a_complete_and_consistent_grid(small_words, small_trie):
    generator = make_generator(small_words, small_trie, seed=42)

    assert generator.generate()
    data = generator.get_grid_data()

    assert data["fill_ratio"] == 1.0
    placed = [w["text"] for w in data["words"]]
    # Chaque slot reçoit exactement un mot, sans doublon, issu du dictionnaire
    assert len(placed) == len(generator.solver.slots)
    assert len(placed) == len(set(placed))
    assert set(placed) <= set(small_words)
    # Les lettres de la grille épellent bien chaque mot placé
    letters = {(c["x"], c["y"]): c["char"] for c in data["cells"]}
    for word in data["words"]:
        for i, char in enumerate(word["text"]):
            x = word["x"] + (i if word["direction"] == "across" else 0)
            y = word["y"] + (i if word["direction"] == "down" else 0)
            assert letters[(x, y)] == char


def test_same_seed_gives_same_grid(small_words, small_trie):
    first = make_generator(small_words, small_trie, seed=7)
    second = make_generator(small_words, small_trie, seed=7)

    assert first.generate() and second.generate()
    assert first.get_grid_data()["cells"] == second.get_grid_data()["cells"]


def test_exceeded_time_budget_is_reported(small_words, small_trie):
    generator = make_generator(small_words, small_trie, seed=1, time_budget_s=-1)

    assert not generator.generate()
    assert generator.budget_exceeded
    assert generator.solver.placed_words == []


def test_unsolvable_grid_returns_false_without_budget_flag(tmp_path):
    (tmp_path / "3x2").mkdir()
    (tmp_path / "3x2" / "001.txt").write_text("---\n---\n")
    trie = DictionnaireTrie()
    for word in ["ABC", "DEF"]:
        trie.insert(word)

    generator = make_generator(["ABC", "DEF"], trie, layouts_dir=str(tmp_path), width=3, height=2, seed=1)

    assert not generator.generate()
    assert not generator.budget_exceeded


def test_forward_checking_threshold_below_two_is_rejected():
    template = GridTemplate.from_rows(["..", ".."])
    finder = SlotFinder(template)
    finder.find_all_slots()

    with pytest.raises(ValueError):
        GridSolver(template, repository=None, finder=finder, min_safe_candidates=1)
