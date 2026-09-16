import os

import pytest

from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from grid_generator import GridGenerator, LayoutNotFoundError, luby
from layout_catalog import DEFAULT_LAYOUTS_DIR, available_formats, layout_id
from tests.paths import FIXTURE_LAYOUTS_DIR


def test_available_formats_lists_only_formats_with_layouts(tmp_path):
    (tmp_path / "6x7").mkdir()
    (tmp_path / "6x7" / "a.txt").write_text("..")
    (tmp_path / "11x6").mkdir()
    (tmp_path / "11x6" / "a.txt").write_text("..")
    (tmp_path / "11x6" / "b.txt").write_text("..")
    (tmp_path / "9x9").mkdir()  # dossier vide : ignoré
    (tmp_path / "notes").mkdir()  # nom invalide : ignoré
    (tmp_path / "notes" / "a.txt").write_text("")

    assert available_formats(str(tmp_path)) == [
        {"width": 6, "height": 7, "layouts": 1},
        {"width": 11, "height": 6, "layouts": 2},
    ]


def test_available_formats_on_missing_directory(tmp_path):
    assert available_formats(str(tmp_path / "absent")) == []


def test_missing_layout_raises(small_words, small_trie):
    with pytest.raises(LayoutNotFoundError):
        GridGenerator(9, 9, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR)


def test_layout_id_is_derived_from_the_path():
    assert layout_id(os.path.join("layouts", "11x6", "007.txt")) == "11x6-007"


def test_shipped_layouts_load_regardless_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    formats = available_formats()

    assert {(6, 7), (11, 6)} <= {(f["width"], f["height"]) for f in formats}
    for fmt in formats:
        format_dir = os.path.join(DEFAULT_LAYOUTS_DIR, f"{fmt['width']}x{fmt['height']}")
        for name in os.listdir(format_dir):
            template = GridTemplate(fmt["width"], fmt["height"], os.path.join(format_dir, name))
            assert SlotFinder(template).find_all_slots(), f"{name} ne contient aucun slot"


def test_luby_sequence():
    assert [luby(i) for i in range(1, 16)] == [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]


def make_generator(small_words, small_trie, **kwargs):
    return GridGenerator(5, 5, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR, **kwargs)


def test_restarts_find_a_grid_and_stay_deterministic(small_words, small_trie):
    results = []
    for _ in range(2):
        generator = make_generator(small_words, small_trie, seed=3, restart_unit_calls=1)
        assert generator.generate()
        results.append(generator.get_grid_data())

    assert results[0]["cells"] == results[1]["cells"]
    assert results[0]["statistics"]["attempts"] > 1


def test_interrupted_attempt_gives_back_the_words_it_used(small_words, small_trie):
    generator = make_generator(small_words, small_trie, seed=3, restart_unit_calls=None)
    sizes = {length: len(words) for length, words in generator.repository.words_by_len.items()}
    # Un seul appel : le premier mot est placé, puis l'essai s'arrête (le 5×5 se remplit en quelques appels)
    generator.solver.max_recursive_calls = 1

    assert not generator.generate()
    assert generator.solver.stop_reason == "calls"
    assert not generator.budget_exceeded  # seuil d'appels, pas le budget temps
    assert {length: len(words) for length, words in generator.repository.words_by_len.items()} == sizes


def test_time_budget_stops_the_restarts(small_words, small_trie):
    generator = make_generator(small_words, small_trie, seed=3, time_budget_s=-1, restart_unit_calls=1)

    assert not generator.generate()
    assert generator.budget_exceeded
    assert len(generator.attempts) == 1


def test_grid_data_shape(small_words, small_trie):
    generator = GridGenerator(5, 5, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR, seed=3)
    assert generator.generate()

    data = generator.get_grid_data()

    assert (data["width"], data["height"], data["seed"]) == (5, 5, 3)
    assert data["layout"] == "5x5-001"
    assert len(data["cells"]) == 25
    assert {"metrics", "cache_stats", "placement_history"} <= data["statistics"].keys()


def test_each_placed_word_reports_its_pool(small_words, small_trie):
    generator = GridGenerator(5, 5, small_words, prebuilt_trie=small_trie,
                              layouts_dir=FIXTURE_LAYOUTS_DIR, seed=3)
    assert generator.generate()

    data = generator.get_grid_data()

    # Sans mots de l'auteur, tout vient du lexique commun : la part souhaitée est nulle
    assert {word["source"] for word in data["words"]} == {"common"}
    assert data["wish_ratio"] == 0.0
