from datetime import datetime, timezone

import pytest

from tools.lexicon.decisions import (
    DELETE,
    KEEP,
    append_decisions,
    effective_decisions,
    read_decisions,
    undo_last_batch,
)

NOW = datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc)


def state(path):
    return effective_decisions(read_decisions(path))


def test_file_is_created_with_a_header(tmp_path):
    path = tmp_path / "decisions.csv"

    append_decisions(path, ["AABAM"], DELETE, now=NOW)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "mot;decision;date;lot"
    assert lines[1].startswith("AABAM;delete;2026-09-15T08:30:00+00:00;20260915083000-")


def test_last_decision_wins(tmp_path):
    path = tmp_path / "decisions.csv"
    append_decisions(path, ["ETE"], DELETE, now=NOW)
    append_decisions(path, ["ETE"], KEEP, now=NOW)

    assert state(path) == {"ETE": KEEP}


def test_undo_cancels_the_whole_last_batch(tmp_path):
    path = tmp_path / "decisions.csv"
    append_decisions(path, ["PORTE"], KEEP, now=NOW)
    append_decisions(path, ["OUVRAGE", "OUVRAGEAMES"], DELETE, now=NOW)

    assert undo_last_batch(path, now=NOW) == ["OUVRAGE", "OUVRAGEAMES"]
    assert state(path) == {"PORTE": KEEP}


def test_undo_restores_an_earlier_decision(tmp_path):
    path = tmp_path / "decisions.csv"
    append_decisions(path, ["ETE"], DELETE, now=NOW)
    append_decisions(path, ["ETE"], KEEP, now=NOW)

    undo_last_batch(path, now=NOW)

    assert state(path) == {"ETE": DELETE}


def test_successive_undos_walk_back_in_time(tmp_path):
    path = tmp_path / "decisions.csv"
    append_decisions(path, ["PORTE"], KEEP, now=NOW)
    append_decisions(path, ["AABAM"], DELETE, now=NOW)

    assert undo_last_batch(path, now=NOW) == ["AABAM"]
    assert undo_last_batch(path, now=NOW) == ["PORTE"]
    assert undo_last_batch(path, now=NOW) == []
    assert state(path) == {}


def test_missing_file_means_no_decision(tmp_path):
    assert read_decisions(tmp_path / "absent.csv") == []
    assert undo_last_batch(tmp_path / "absent.csv") == []


@pytest.mark.parametrize("words, decision", [
    (["été"], DELETE),        # non normalisé
    (["A"], DELETE),          # trop court
    ([], DELETE),
    (["PORTE"], "undo"),      # l'annulation passe par undo_last_batch
    (["PORTE"], "maybe"),
])
def test_invalid_input_is_rejected(tmp_path, words, decision):
    with pytest.raises(ValueError):
        append_decisions(tmp_path / "decisions.csv", words, decision)


def test_corrupted_decision_is_reported_with_its_line(tmp_path):
    path = tmp_path / "decisions.csv"
    path.write_text("mot;decision;date;lot\nPORTE;peut-être;2026-09-15;x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="decisions.csv:2"):
        read_decisions(path)
