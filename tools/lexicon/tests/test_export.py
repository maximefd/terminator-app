import csv

import pytest

from tools.lexicon.build import build_lexicon
from tools.lexicon.decisions import DELETE, KEEP, append_decisions
from tools.lexicon.export import export_curated, lexicon_stats


@pytest.fixture
def db_path(dela_file, lexique_file, wiktionary_file, tmp_path):
    path = tmp_path / "lexicon.sqlite"
    build_lexicon(dela_file, lexique_file, path, wiktionary_file, log=lambda _: None)
    return path


def exported_words(path):
    with open(path, encoding="utf-8", newline="") as f:
        return {row[0]: row for row in csv.reader(f, delimiter=";")}


def test_export_removes_only_author_deletions_by_default(db_path, tmp_path):
    decisions = tmp_path / "decisions.csv"
    append_decisions(decisions, ["OUVRAGEAMES"], DELETE)
    out = tmp_path / "lexique_cure.csv"

    counts = export_curated(db_path, decisions, out)

    words = exported_words(out)
    assert "OUVRAGEAMES" not in words
    assert "AABAM" in words  # suggéré à supprimer, mais pas encore décidé
    assert words["PORTE"] == ["PORTE", "porte", "Ouverture permettant le passage.", "5.7"]
    assert counts == {"exported": 6, "deleted_by_author": 1}


def test_export_can_also_remove_suggested_deletions(db_path, tmp_path):
    decisions = tmp_path / "decisions.csv"
    out = tmp_path / "lexique_cure.csv"

    counts = export_curated(db_path, decisions, out, exclude_suggested_deletes=True)

    assert "AABAM" not in exported_words(out)
    assert counts["deleted_by_suggestion"] == 1


def test_explicit_keep_overrides_the_suggestion(db_path, tmp_path):
    decisions = tmp_path / "decisions.csv"
    append_decisions(decisions, ["AABAM"], KEEP)
    out = tmp_path / "lexique_cure.csv"

    export_curated(db_path, decisions, out, exclude_suggested_deletes=True)

    assert "AABAM" in exported_words(out)


def test_export_is_readable_by_the_backend_trie(db_path, tmp_path):
    from trie_engine import DictionnaireTrie

    out = tmp_path / "lexique_cure.csv"
    export_curated(db_path, tmp_path / "decisions.csv", out)

    trie = DictionnaireTrie()
    trie.load_dela_csv(str(out))
    assert trie.search_pattern("P?RTE") == ["PORTE"]


def test_stats_count_remaining_words_to_review(db_path, tmp_path):
    decisions = tmp_path / "decisions.csv"
    append_decisions(decisions, ["AABAM"], DELETE)

    stats = lexicon_stats(db_path, decisions)

    assert stats["words"] == 7
    assert stats["decisions"] == {"delete": 1}
    # Restent à trier (hors « keep » et hors décidés) : OUVRAGE, APRIORI, OUVRAGEAMES
    assert stats["to_review_by_length"] == {"2-5": 0, "6-8": 2, "9-11": 1, "12+": 0}
