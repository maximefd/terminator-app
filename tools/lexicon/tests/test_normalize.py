import pytest
from trie_engine import DictionnaireTrie

from tools.lexicon.normalize import is_usable, normalize_word


@pytest.mark.parametrize("word", ["été", "à l'été", "Œuvre", "porte-clé", "100-mètres", "  ça  ", "", "ÀÉÎÕÜ"])
def test_normalization_matches_the_backend_trie(word):
    assert normalize_word(word) == DictionnaireTrie._normalize(word)


def test_non_string_is_empty():
    assert normalize_word(None) == ""


def test_words_need_two_characters():
    assert not is_usable("A")
    assert is_usable("OU")
