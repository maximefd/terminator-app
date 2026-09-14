import pytest

from engine.grid_template import GridTemplate


def test_from_rows_marks_black_squares_and_empty_cells():
    template = GridTemplate.from_rows(["#.", ".x"])
    assert (template.width, template.height) == (2, 2)
    assert template.grid == [["#", "."], [".", "."]]


def test_load_from_file_matches_from_rows(tmp_path):
    layout = tmp_path / "layout.txt"
    layout.write_text("#.#\n...\n")
    assert GridTemplate(3, 2, str(layout)).grid == GridTemplate.from_rows(["#.#", "..."]).grid


def test_file_larger_than_requested_size_is_truncated(tmp_path):
    layout = tmp_path / "layout.txt"
    layout.write_text("#.#.#\n.....\n.....\n")
    assert GridTemplate(3, 2, str(layout)).grid == [["#", ".", "#"], [".", ".", "."]]


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        GridTemplate(3, 3, str(tmp_path / "absent.txt"))


def test_cell_accessors():
    template = GridTemplate.from_rows(["#."])
    assert template.is_black_square(0, 0)
    assert not template.is_black_square(1, 0)
    assert template.get_cell(5, 0) is None
