import pytest

from engine.grid_solver import GridSolver
from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from engine.word_repository import WordRepository
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


def make_solver(rows, words):
    """Solveur sur une petite grille et un dictionnaire minimal, pour tester une règle isolée."""
    template = GridTemplate.from_rows(rows)
    finder = SlotFinder(template)
    finder.find_all_slots()
    trie = DictionnaireTrie()
    for word in words:
        trie.insert(word)
    return GridSolver(template, WordRepository.from_words(trie, words), finder)


def across_slot(solver, y):
    return next(slot for slot in solver.slots if slot["direction"] == "across" and slot["y"] == y)


def test_a_word_still_being_written_is_not_required_to_exist():
    # Colonnes de 4 cases : après deux rangées, « AB » n'est qu'un début de mot vertical
    solver = make_solver(["---", "---", "---", "---"], ["BOA", "ABLE"])
    solver.grid[0][0] = "A"
    slot = across_slot(solver, 1)

    state = solver._place_word_on_grid("BOA", slot)

    assert not solver.repository.is_word_valid("AB")
    assert solver._is_placement_valid("BOA", slot, state)


def test_a_finished_crossing_word_must_exist():
    # Colonnes de 2 cases (la 3e rangée est en cases définitions) : le mot vertical est terminé
    solver = make_solver(["---", "---", "xxx"], ["BOA", "ABC"])
    solver.grid[0][0] = "A"
    slot = across_slot(solver, 1)

    state = solver._place_word_on_grid("BOA", slot)

    assert not solver._is_placement_valid("BOA", slot, state)


def test_a_wish_word_absent_from_the_lexicon_is_placed_before_the_common_ones():
    """#17 : un mot personnel n'entrait jamais dans la grille (ignoré à l'indexation)."""
    template = GridTemplate.from_rows(["---"])  # une seule rangée : un unique emplacement
    finder = SlotFinder(template)
    finder.find_all_slots()
    trie = DictionnaireTrie()
    trie.insert("ABC")
    repository = WordRepository.from_pools(trie, common_words=["ABC"], wish_words=["ZUT"])

    solver = GridSolver(template, repository, finder)

    assert solver.solve()
    assert [(word["text"], word["source"]) for word in solver.placed_words] == [("ZUT", "wish")]


def test_the_most_frequent_candidate_is_tried_first():
    """Mode « exact » : à pool égal, la fréquence l'emporte sur le score de lettres."""
    template = GridTemplate.from_rows(["---"])  # une seule rangée : un unique emplacement
    finder = SlotFinder(template)
    finder.find_all_slots()
    trie = DictionnaireTrie()
    for word in ("ASE", "ZUT"):
        trie.insert(word)
    # ASE a un bien meilleur score de lettres (A+S+E = 30 contre Z+U+T = 14), mais reste rare
    trie.frequencies = {"ZUT": 4.0}
    repository = WordRepository.from_words(trie, ["ASE", "ZUT"])

    solver = GridSolver(template, repository, finder, frequency_mode="exact")

    assert solver.solve()
    assert [word["text"] for word in solver.placed_words] == ["ZUT"]


def test_frequency_ordering_is_off_by_default():
    """Mesuré : trier par fréquence fait tomber sept layouts sous 20/20 (benchmarks/README.md)."""
    template = GridTemplate.from_rows(["---"])
    finder = SlotFinder(template)
    finder.find_all_slots()
    trie = DictionnaireTrie()
    for word in ("ASE", "ZUT"):
        trie.insert(word)
    trie.frequencies = {"ZUT": 4.0}
    repository = WordRepository.from_words(trie, ["ASE", "ZUT"])

    solver = GridSolver(template, repository, finder)

    assert solver.frequency_mode == "none"
    assert solver.solve()
    assert [word["text"] for word in solver.placed_words] == ["ASE"]


def test_an_unknown_frequency_mode_is_refused():
    template = GridTemplate.from_rows(["---"])
    finder = SlotFinder(template)
    finder.find_all_slots()

    with pytest.raises(ValueError, match="mode de fréquence"):
        GridSolver(template, repository=None, finder=finder, frequency_mode="zorglub")


def test_the_measured_candidate_cap_is_the_default():
    """300 : mesuré 420/420 comme 100, mais plus rapide (médiane 0,91 s → 0,71 s)."""
    assert GridSolver.MAX_CANDIDATES_PER_SLOT == 300


def test_without_frequencies_the_letter_score_still_decides():
    """Un lexique sans fréquence (DELA brut) doit rendre exactement l'ordre d'avant la mesure."""
    template = GridTemplate.from_rows(["---"])
    finder = SlotFinder(template)
    finder.find_all_slots()
    trie = DictionnaireTrie()
    for word in ("ASE", "ZUT"):
        trie.insert(word)
    repository = WordRepository.from_words(trie, ["ASE", "ZUT"])

    solver = GridSolver(template, repository, finder)

    assert solver.solve()
    assert [word["text"] for word in solver.placed_words] == ["ASE"]


def test_forward_checking_threshold_below_two_is_rejected():
    template = GridTemplate.from_rows(["..", ".."])
    finder = SlotFinder(template)
    finder.find_all_slots()

    with pytest.raises(ValueError):
        GridSolver(template, repository=None, finder=finder, min_safe_candidates=1)
