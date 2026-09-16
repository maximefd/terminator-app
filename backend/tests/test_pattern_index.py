import random

from engine.pattern_index import PatternIndex
from trie_engine import DictionnaireTrie


def test_mask_and_words_follow_the_index_order():
    index = PatternIndex(["PALE", "PILE", "POLE", "PORT"])

    assert index.words_in(index.mask("P?LE")) == ["PALE", "PILE", "POLE"]
    assert index.words_in(index.mask("????")) == ["PALE", "PILE", "POLE", "PORT"]
    assert index.mask("Z???") == 0
    assert index.words_in(0) == []


def test_bit_selects_a_single_word():
    index = PatternIndex(["PALE", "PILE"])

    assert index.words_in(index.bit("PILE")) == ["PILE"]
    assert index.bit("INCONNU") == 0
    assert (index.mask("P?LE") & ~index.bit("PALE")).bit_count() == 1


def test_mask_of_ignores_unknown_words():
    index = PatternIndex(["PALE", "PILE", "POLE"])

    assert index.words_in(index.mask_of(["POLE", "INCONNU", "PALE"])) == ["PALE", "POLE"]


def test_empty_index():
    index = PatternIndex([])

    assert index.mask("") == 0
    assert index.words_in(index.full_mask) == []


def test_same_candidates_as_the_trie_in_the_same_order(small_words):
    # Trie construit dans l'ordre alphabétique, comme le benchmark : son parcours rend les mots dans cet ordre
    ordered = sorted(small_words)
    trie = DictionnaireTrie()
    for word in ordered:
        trie.insert(word)
    rng = random.Random(0)

    for length in range(2, 6):
        words = [word for word in ordered if len(word) == length]
        index = PatternIndex(words)
        for _ in range(150):
            source = rng.choice(words)
            pattern = "".join("?" if rng.random() < 0.6 else char for char in source)
            assert index.words_in(index.mask(pattern)) == trie.search_pattern(pattern), pattern
