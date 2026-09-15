import os

import pytest

from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from grid_generator import DEFAULT_LAYOUTS_DIR, GridGenerator, LayoutNotFoundError, available_formats, layout_id
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


def test_grid_data_shape(small_words, small_trie):
    generator = GridGenerator(5, 5, small_words, prebuilt_trie=small_trie, layouts_dir=FIXTURE_LAYOUTS_DIR, seed=3)
    assert generator.generate()

    data = generator.get_grid_data()

    assert (data["width"], data["height"], data["seed"]) == (5, 5, 3)
    assert data["layout"] == "5x5-001"
    assert len(data["cells"]) == 25
    assert {"metrics", "cache_stats", "placement_history"} <= data["statistics"].keys()
