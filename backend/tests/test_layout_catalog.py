import os
from unittest.mock import ANY

import pytest

from layout_catalog import LayoutSaveError, catalog, list_layouts, next_layout_id, save_layout

GRID = ["x-x", "---", "---"]
GRID_TEXT = "x-x\n---\n---\n"


def write(root, folder, name, text):
    (root / folder).mkdir(exist_ok=True)
    (root / folder / name).write_text(text)


def test_shipped_catalog_is_valid():
    entries = list_layouts()

    assert entries
    for entry in entries:
        assert entry["report"]["valid"], (entry["id"], entry["report"]["errors"])


def test_badly_named_file_or_wrong_folder_is_invalid(tmp_path):
    write(tmp_path, "3x3", "grille.txt", GRID_TEXT)
    write(tmp_path, "4x3", "001.txt", GRID_TEXT)

    reports = {entry["id"]: entry["report"] for entry in list_layouts(str(tmp_path))}

    assert "Nom de fichier « grille.txt »" in reports["3x3-grille"]["errors"][0]["message"]
    assert "dans le dossier « 4x3 »" in reports["4x3-001"]["errors"][0]["message"]


def test_identical_grids_are_flagged(tmp_path):
    write(tmp_path, "3x3", "001.txt", GRID_TEXT)
    write(tmp_path, "3x3", "002.txt", "#.#\n...\n...\n")  # même grille, ancien format

    first, second = list_layouts(str(tmp_path))

    assert first["report"]["warnings"] == []
    assert second["report"]["warnings"][0]["message"] == "Grille identique à 3x3-001."
    assert second["report"]["valid"]


def test_catalog_groups_valid_layouts_by_format(tmp_path):
    write(tmp_path, "3x3", "001.txt", GRID_TEXT)
    write(tmp_path, "3x3", "002.txt", "x-o\n---\n---\n")

    assert catalog(str(tmp_path)) == [
        {"width": 3, "height": 3, "layouts": [{"id": "3x3-001", "rows": GRID, "stats": ANY}]},
    ]


def test_save_creates_the_format_folder_and_numbers_the_files(tmp_path):
    first = save_layout(GRID, str(tmp_path))

    assert first["id"] == "3x3-001"
    assert (tmp_path / "3x3" / "001.txt").read_text() == GRID_TEXT
    assert next_layout_id(3, 3, str(tmp_path)) == "3x3-002"
    assert save_layout(["xx-", "---", "---"], str(tmp_path))["id"] == "3x3-002"


def test_save_never_overwrites_and_takes_the_next_free_number(tmp_path):
    write(tmp_path, "3x3", "001.txt", GRID_TEXT)
    write(tmp_path, "3x3", "005.txt", "xx-\n---\n---\n")

    assert save_layout(["x--", "---", "---"], str(tmp_path))["id"] == "3x3-006"
    assert (tmp_path / "3x3" / "001.txt").read_text() == GRID_TEXT


def test_save_refuses_duplicates_and_invalid_grids(tmp_path):
    save_layout(GRID, str(tmp_path))

    with pytest.raises(LayoutSaveError, match="existe déjà : 3x3-001") as duplicate:
        save_layout(GRID, str(tmp_path))
    assert duplicate.value.duplicate_of == "3x3-001"

    with pytest.raises(LayoutSaveError, match="pas valide") as invalid:
        save_layout(["x-", "-x"], str(tmp_path))
    assert invalid.value.report["errors"]

    assert sorted(os.listdir(tmp_path)) == ["3x3"]
    assert os.listdir(tmp_path / "3x3") == ["001.txt"]


def test_save_refuses_a_symlinked_format_folder(tmp_path):
    elsewhere = tmp_path / "ailleurs"
    elsewhere.mkdir()
    root = tmp_path / "layouts"
    root.mkdir()
    (root / "3x3").symlink_to(elsewhere)

    with pytest.raises(LayoutSaveError, match="lien symbolique"):
        save_layout(GRID, str(root))
    assert os.listdir(elsewhere) == []
