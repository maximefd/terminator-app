import pytest

from convert_layouts import convert_file
from engine.layout_format import LayoutFormatError, format_layout, layout_size, parse_layout


def test_parse_v1_layout():
    rows = parse_layout("x-x\n---\n")
    assert rows == ["x-x", "---"]
    assert layout_size(rows) == (3, 2)


def test_legacy_layout_is_read_as_v1():
    assert parse_layout("#.#\n...") == ["x-x", "---"]


def test_trailing_spaces_and_blank_lines_are_ignored():
    assert parse_layout("x-  \n--\n\n\n") == ["x-", "--"]


@pytest.mark.parametrize("text, message", [
    ("", "vide"),
    ("x-\n\n--\n", "Ligne 2 : ligne vide"),
    ("x-\n-o\n", "Ligne 2, colonne 2 : caractère « o »"),
    ("X-\n--\n", "caractère « X »"),
    ("x-x\n--\n", "Ligne 2 : 2 cases au lieu de 3"),
    ("x-\n#.\n", "mélange"),
])
def test_invalid_layouts_explain_the_problem(text, message):
    with pytest.raises(LayoutFormatError, match=message):
        parse_layout(text)


def test_format_layout_round_trip():
    rows = ["x-x", "---"]
    assert parse_layout(format_layout(rows)) == rows


def test_convert_file_rewrites_legacy_layout_once(tmp_path):
    layout = tmp_path / "001.txt"
    layout.write_text("#.#\n...")

    assert convert_file(str(layout))
    assert layout.read_text() == "x-x\n---\n"
    assert not convert_file(str(layout))
