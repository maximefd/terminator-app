import pytest

from engine.grid_template import GridTemplate
from engine.layout_format import LayoutFormatError


def test_from_rows_marks_black_squares_and_empty_cells():
    template = GridTemplate.from_rows(["x-", "--"])
    assert (template.width, template.height) == (2, 2)
    assert template.grid == [["#", "."], [".", "."]]


def test_from_rows_accepts_legacy_format():
    assert GridTemplate.from_rows(["#.", ".."]).grid == GridTemplate.from_rows(["x-", "--"]).grid


def test_load_from_file_matches_from_rows(tmp_path):
    layout = tmp_path / "001.txt"
    layout.write_text("x-x\n---\n")
    assert GridTemplate(3, 2, str(layout)).grid == GridTemplate.from_rows(["x-x", "---"]).grid


def test_file_with_another_size_is_rejected(tmp_path):
    layout = tmp_path / "001.txt"
    layout.write_text("x-x-x\n-----\n-----\n")
    with pytest.raises(LayoutFormatError, match="5x3 alors que le format attendu est 3x2"):
        GridTemplate(3, 2, str(layout))


def test_unknown_character_is_rejected_instead_of_read_as_a_letter(tmp_path):
    layout = tmp_path / "001.txt"
    layout.write_text("x-o\n---\n")
    with pytest.raises(LayoutFormatError, match="001.txt : Ligne 1, colonne 3"):
        GridTemplate(3, 2, str(layout))


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        GridTemplate(3, 3, str(tmp_path / "absent.txt"))


def test_cell_accessors():
    template = GridTemplate.from_rows(["x-"])
    assert template.is_black_square(0, 0)
    assert not template.is_black_square(1, 0)
    assert template.get_cell(5, 0) is None
