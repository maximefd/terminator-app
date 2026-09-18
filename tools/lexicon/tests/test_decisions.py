from datetime import datetime, timezone

import pytest

from tools.lexicon.decisions import (
    DELETE,
    KEEP,
    REVISION,
    TRI,
    append_decisions,
    batch_kind,
    batch_sizes,
    effective_decisions,
    effective_rows,
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


# --- Origine des lots : tri courant ou deuxième regard ---

def test_a_revision_batch_says_where_it_comes_from(tmp_path):
    path = tmp_path / "decisions.csv"

    tri = append_decisions(path, ["PORTE"], DELETE, now=NOW)
    revision = append_decisions(path, ["PORTE"], KEEP, now=NOW, kind=REVISION)

    assert batch_kind(tri) == TRI
    assert batch_kind(revision) == REVISION
    assert ".revision." not in revision and "-revision." in revision
    assert state(path) == {"PORTE": KEEP}


def test_batches_written_before_this_feature_are_read_as_tri():
    assert batch_kind("20260915083000-3f9a1c") == TRI
    assert batch_kind("20260915083000-inconnu.3f9a1c") == TRI


def test_an_unknown_batch_kind_is_refused(tmp_path):
    with pytest.raises(ValueError, match="origine de lot"):
        append_decisions(tmp_path / "decisions.csv", ["PORTE"], DELETE, kind="automatique")


def test_effective_rows_keep_the_date_and_the_batch(tmp_path):
    path = tmp_path / "decisions.csv"
    batch = append_decisions(path, ["PORTE"], DELETE, now=NOW)

    row = effective_rows(read_decisions(path))["PORTE"]

    assert (row.decision, row.batch) == (DELETE, batch)
    assert row.date == "2026-09-15T08:30:00+00:00"


def test_batch_sizes_tell_family_batches_from_single_decisions(tmp_path):
    path = tmp_path / "decisions.csv"
    solo = append_decisions(path, ["PORTE"], KEEP, now=NOW)
    family = append_decisions(path, ["OUVRAGE", "OUVRAGER", "OUVRAGEAMES"], DELETE, now=NOW)

    sizes = batch_sizes(read_decisions(path))

    assert sizes == {solo: 1, family: 3}


def test_undone_batches_are_not_counted(tmp_path):
    path = tmp_path / "decisions.csv"
    append_decisions(path, ["PORTE"], KEEP, now=NOW)
    undo_last_batch(path, now=NOW)

    assert batch_sizes(read_decisions(path)) == {}
    assert effective_rows(read_decisions(path)) == {}
