from datetime import datetime, timedelta, timezone

import pytest

from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import (
    DELETE,
    KEEP,
    append_decisions,
    effective_decisions,
    read_decisions,
    undo_last_batch,
)
from tools.lexicon.review import (
    FLASH_DECISION,
    FREQUENT_DELETED,
    MIXED_FAMILY,
    counts_by_reason,
    family_of,
    revise,
    suspicious,
)

NOW = datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc)


@pytest.fixture
def db_path(dela_file, lexique_file, wiktionary_file, tmp_path):
    path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, path, wiktionary_file, log=lambda _: None)
    return path


@pytest.fixture
def decisions_path(tmp_path):
    return tmp_path / "decisions.csv"


def reasons(items):
    return {item["norm"]: item["reason"] for item in items}


def test_opposite_decisions_in_the_same_family_are_flagged(db_path, decisions_path):
    # « ouvrager » est absent de Lexique : il se regroupe avec sa forme fléchie par son propre nom
    append_decisions(decisions_path, ["OUVRAGEAMES"], DELETE, now=NOW)
    append_decisions(decisions_path, ["OUVRAGER"], KEEP, now=NOW + timedelta(minutes=1))

    found = suspicious(db_path, decisions_path)

    assert reasons(found) == {"OUVRAGEAMES": MIXED_FAMILY, "OUVRAGER": MIXED_FAMILY}
    assert "gardé 1 forme(s) et supprimé 1 forme(s)" in found[0]["explanation"]


def test_a_common_word_deleted_is_flagged(db_path, decisions_path):
    append_decisions(decisions_path, ["PORTE"], DELETE, now=NOW)

    found = suspicious(db_path, decisions_path)

    assert reasons(found) == {"PORTE": FREQUENT_DELETED}
    assert "courant" in found[0]["explanation"]


def test_a_burst_of_decisions_in_one_second_is_flagged(db_path, decisions_path):
    # Trois mots peu fréquents, décidés dans la même seconde : rien d'autre ne les signale
    for word in ("AABAM", "OUVRAGE", "OUVRAGER"):
        append_decisions(decisions_path, [word], DELETE, now=NOW)

    found = suspicious(db_path, decisions_path)

    assert reasons(found) == {word: FLASH_DECISION for word in ("AABAM", "OUVRAGE", "OUVRAGER")}
    assert counts_by_reason(found)[FLASH_DECISION] == 3


def test_two_decisions_in_one_second_are_not_enough(db_path, decisions_path):
    for word in ("AABAM", "OUVRAGE"):
        append_decisions(decisions_path, [word], DELETE, now=NOW)

    assert suspicious(db_path, decisions_path) == []


def test_family_deletions_are_not_second_guessed(db_path, decisions_path):
    append_decisions(decisions_path, ["OUVRAGEAMES", "OUVRAGER", "OUVRAGE"], DELETE, now=NOW)

    assert suspicious(db_path, decisions_path) == []


def test_undone_decisions_are_not_flagged(db_path, decisions_path):
    append_decisions(decisions_path, ["PORTE"], DELETE, now=NOW)
    undo_last_batch(decisions_path, now=NOW)

    assert suspicious(db_path, decisions_path) == []


def test_a_revised_word_never_comes_back(db_path, decisions_path):
    append_decisions(decisions_path, ["PORTE"], DELETE, now=NOW)
    assert len(suspicious(db_path, decisions_path)) == 1

    revise(decisions_path, ["PORTE"], DELETE, now=NOW + timedelta(minutes=5))

    assert suspicious(db_path, decisions_path) == []
    assert effective_decisions(read_decisions(decisions_path))["PORTE"] == DELETE


def test_revising_can_also_change_the_decision(db_path, decisions_path):
    append_decisions(decisions_path, ["PORTE"], DELETE, now=NOW)

    revise(decisions_path, ["PORTE"], KEEP, now=NOW + timedelta(minutes=5))

    assert effective_decisions(read_decisions(decisions_path))["PORTE"] == KEEP
    assert suspicious(db_path, decisions_path) == []


def test_family_shows_every_form_with_its_decision(db_path, decisions_path):
    append_decisions(decisions_path, ["OUVRAGEAMES"], DELETE, now=NOW)
    decisions = effective_decisions(read_decisions(decisions_path))

    family = family_of(db_path, "OUVRAGEAMES", decisions)

    by_word = {item["norm"]: item["decision"] for item in family}
    assert by_word["OUVRAGEAMES"] == DELETE
    assert by_word["OUVRAGER"] is None
