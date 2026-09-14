import pytest

from engine.word_repository import WordRepository


@pytest.fixture
def repo(tmp_path):
    csv_file = tmp_path / "dela.csv"
    words = ["POLE", "PALE", "PILE", "CHAT", "OU"]
    csv_file.write_text("".join(f"{w};{w.lower()};Forme\n" for w in words), encoding="utf-8")
    return WordRepository(str(csv_file))


def test_get_candidates_matches_pattern(repo):
    assert sorted(repo.get_candidates("P?LE")) == ["PALE", "PILE", "POLE"]


def test_is_word_valid(repo):
    assert repo.is_word_valid("CHAT")
    assert not repo.is_word_valid("CHIEN")


def test_removed_word_is_not_a_candidate_until_restored(repo):
    repo.remove_word_from_available("PALE", 4)
    assert "PALE" not in repo.get_candidates("P?LE")

    repo.add_word_to_available("PALE", 4)
    assert "PALE" in repo.get_candidates("P?LE")


def test_candidate_cache_is_used_for_repeated_patterns(repo):
    repo.get_candidates("P?LE")
    repo.get_candidates("P?LE")
    assert repo._cache_stats == {"hits": 1, "misses": 1}


def test_get_words_by_length(repo):
    assert repo.get_words_by_length(2) == ["OU"]
