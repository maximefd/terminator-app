import pytest

from engine.word_repository import WordRepository


@pytest.fixture
def repo(tmp_path):
    csv_file = tmp_path / "dela.csv"
    words = ["POLE", "PALE", "PILE", "CHAT", "OU"]
    csv_file.write_text("".join(f"{w};{w.lower()};Forme\n" for w in words), encoding="utf-8")
    return WordRepository(str(csv_file))


def test_get_candidates_matches_pattern_in_alphabetical_order(repo):
    assert repo.get_candidates("P?LE") == ["PALE", "PILE", "POLE"]
    assert repo.get_candidates("ZZZZZZZZ") == []


def test_is_word_valid(repo):
    assert repo.is_word_valid("CHAT")
    assert not repo.is_word_valid("CHIEN")


def test_removed_word_is_not_a_candidate_until_restored(repo):
    repo.remove_word_from_available("PALE", 4)
    assert "PALE" not in repo.get_candidates("P?LE")

    repo.add_word_to_available("PALE", 4)
    assert "PALE" in repo.get_candidates("P?LE")


def test_count_candidates_follows_the_available_words(repo):
    assert repo.count_candidates("P?LE") == 3

    repo.remove_word_from_available("PILE", 4)

    assert repo.count_candidates("P?LE") == 2
    assert repo.count_candidates("????????") == 0


def test_from_words_limits_candidates_but_not_validity(repo):
    grid_repo = WordRepository.from_words(repo.trie, ["PALE", "CHAT"])

    assert grid_repo.get_candidates("P?LE") == ["PALE"]
    assert grid_repo.is_word_valid("POLE")  # un croisement reste valide s'il est dans le lexique


def test_get_words_by_length(repo):
    assert repo.get_words_by_length(2) == ["OU"]


def test_pool_words_absent_from_the_lexicon_are_placeable_and_valid(repo):
    """#17 : un mot personnel était simplement ignoré à l'indexation, donc jamais placé."""
    grid_repo = WordRepository.from_pools(repo.trie, common_words=["CHAT"], wish_words=["ZORG"])

    assert grid_repo.get_candidates("Z???") == ["ZORG"]
    assert grid_repo.is_word_valid("ZORG")  # accepté aussi comme mot croisé
    assert (grid_repo.source_of("ZORG"), grid_repo.source_of("CHAT")) == ("wish", "common")


def test_a_word_cited_twice_keeps_its_most_prioritary_pool(repo):
    grid_repo = WordRepository.from_pools(repo.trie, common_words=["PILE", "PALE", "POLE"],
                                          wish_words=["PILE"], must_words=["PALE"])

    assert (grid_repo.source_of("PALE"), grid_repo.source_of("PILE")) == ("must", "wish")
    assert grid_repo.priority_of("PALE") < grid_repo.priority_of("PILE") < grid_repo.priority_of("POLE")


def test_a_pool_word_is_consumed_and_restored_like_the_others(repo):
    grid_repo = WordRepository.from_pools(repo.trie, wish_words=["ZORG"])

    grid_repo.remove_word_from_available("ZORG", 4)
    assert grid_repo.get_candidates("????") == []

    grid_repo.add_word_to_available("ZORG", 4)
    assert grid_repo.get_candidates("????") == ["ZORG"]
