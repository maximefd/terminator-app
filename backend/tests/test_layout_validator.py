import pytest

from engine.layout_validator import find_words, validate_rows, validate_text


def messages(report, kind="errors"):
    return [item["message"] for item in report[kind]]


def test_valid_layout_comes_with_its_statistics():
    report = validate_rows(["x-x-x-", "------", "x-----", "------", "x----x", "--x---", "x-----"])

    assert report["valid"], report["errors"]
    assert report["warnings"] == []
    stats = report["stats"]
    assert (stats["width"], stats["height"], stats["definition_cells"]) == (6, 7, 8)
    assert stats["words"] == stats["across"] + stats["down"] == sum(stats["lengths"].values())


def test_find_words_across_then_down():
    assert find_words(["x--", "-x-"]) == [
        {"x": 1, "y": 0, "direction": "across", "length": 2},
        {"x": 2, "y": 0, "direction": "down", "length": 2},
    ]


def test_a_word_may_start_at_the_edge():
    assert validate_rows(["---", "---"])["valid"]


def test_isolated_letter_is_an_error_that_points_to_its_cell():
    report = validate_rows(["x--", "-x-"])

    assert not report["valid"]
    assert report["errors"] == [{
        "message": "Ligne 2, colonne 1 : case lettre isolée, elle n'appartient à aucun mot de 2 lettres ou plus.",
        "cells": [[0, 1]],
    }]


def test_grid_without_words_is_an_error():
    assert "aucun mot" in messages(validate_rows(["xx", "xx"]))[0]


@pytest.mark.parametrize("rows", [["-" * 31, "-" * 31], ["--"]])
def test_unsupported_sizes_are_errors(rows):
    assert "non pris en charge" in messages(validate_rows(rows))[0]


def test_unusual_definition_ratio_is_only_a_warning():
    report = validate_rows(["------"] * 6)

    assert report["valid"]
    assert messages(report, "warnings")[0].startswith("0 % de cases définitions")


def test_format_errors_are_reported_instead_of_raised():
    report = validate_text("x-o\n---\n")

    assert not report["valid"]
    assert report["rows"] is None
    assert "colonne 3" in messages(report)[0]
