"""Tirage des mots imposés du benchmark : il doit être reproductible et mesurer le solveur.

Un tirage qui ne choisirait rien, ou des longueurs que le layout n'a pas, ferait croire à un
benchmark vert alors qu'il ne mesurerait rien.
"""

import random

from test_harness import MUST_WORD_MIN_ZIPF, common_words_by_length, pick_must_words
from trie_engine import DictionnaireTrie


def trie_with(frequencies):
    trie = DictionnaireTrie()
    for word in frequencies:
        trie.insert(word)
    trie.frequencies = dict(frequencies)
    return trie


def test_only_common_words_are_eligible():
    words = ["PORTE", "ROUTE", "ZORGL"]
    pool = common_words_by_length(words, trie_with({"PORTE": 4.5, "ROUTE": 3.0, "ZORGL": 0.0}))

    assert pool[5] == ["PORTE", "ROUTE"]
    assert MUST_WORD_MIN_ZIPF == 3.0


def test_a_lexicon_without_frequencies_keeps_every_word():
    """DELA brut : toutes les fréquences valent 0, on garde tout plutôt que de ne rien pouvoir imposer."""
    words = ["PORTE", "ZORGL"]

    pool = common_words_by_length(words, trie_with({}))

    assert pool[5] == ["PORTE", "ZORGL"]


def test_the_draw_uses_distinct_lengths_of_the_layout():
    pool = {3: ["OUI"], 5: ["PORTE"], 7: ["ROUTIER"]}

    chosen = pick_must_words([3, 3, 5, 5, 7], pool, 3, random.Random("x"))

    assert sorted(len(word) for word in chosen) == [3, 5, 7]
    assert all(word in pool[len(word)] for word in chosen)


def test_a_length_absent_from_the_layout_is_never_drawn():
    pool = {3: ["OUI"], 9: ["IMPOSSIBLE"]}

    chosen = pick_must_words([3, 3], pool, 2, random.Random("x"))

    assert chosen == ["OUI"]  # une seule longueur disponible : un seul mot, pas d'invention


def test_the_draw_is_reproducible():
    pool = {3: ["OUI", "NON", "BAS"], 5: ["PORTE", "ROUTE"]}

    first = pick_must_words([3, 5], pool, 2, random.Random("11x6-001:7"))
    second = pick_must_words([3, 5], pool, 2, random.Random("11x6-001:7"))
    other = pick_must_words([3, 5], pool, 2, random.Random("11x6-001:8"))

    assert first == second
    assert first != other or len(set(pool[3])) == 1  # une autre seed doit pouvoir tirer autre chose


def test_the_length_cap_makes_formats_comparable():
    """Sans plafond, un grand format reçoit des mots plus longs, donc plus durs : comparaison faussée."""
    pool = {3: ["OUI"], 5: ["PORTE"], 10: ["IMPOSSIBLE"]}

    sans = pick_must_words([3, 5, 10], pool, 3, random.Random("x"))
    avec = pick_must_words([3, 5, 10], pool, 3, random.Random("x"), max_length=5)

    assert sorted(len(m) for m in sans) == [3, 5, 10]
    assert sorted(len(m) for m in avec) == [3, 5]
