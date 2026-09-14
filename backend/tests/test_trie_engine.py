from trie_engine import DictionnaireTrie


def make_trie(*words):
    trie = DictionnaireTrie()
    for word in words:
        trie.insert(word)
    return trie


def test_normalize_removes_accents_spaces_and_punctuation():
    assert DictionnaireTrie._normalize("à l'été") == "ALETE"


def test_normalize_non_string_returns_empty():
    assert DictionnaireTrie._normalize(None) == ""


def test_insert_ignores_words_shorter_than_two_letters():
    assert make_trie("a", "", "ou").words == {"OU"}


def test_insert_deduplicates_normalized_forms():
    assert make_trie("pôle", "POLE").get_all_words() == ["POLE"]


def test_search_pattern_with_wildcards():
    trie = make_trie("pole", "pale", "pile", "poli", "poles")
    assert sorted(trie.search_pattern("P?LE")) == ["PALE", "PILE", "POLE"]


def test_search_pattern_respects_exact_length():
    trie = make_trie("pole", "poles")
    assert trie.search_pattern("POLE") == ["POLE"]
    assert trie.search_pattern("?????") == ["POLES"]


def test_search_pattern_without_match():
    assert make_trie("pole").search_pattern("X???") == []


def test_load_dela_csv_reads_first_column(tmp_path):
    csv_file = tmp_path / "dela.csv"
    csv_file.write_text("ÉTÉ;été;Forme\nA;a;Forme\nCHAT;chat;Forme\n", encoding="utf-8")
    trie = DictionnaireTrie()
    trie.load_dela_csv(str(csv_file))
    assert trie.words == {"ETE", "CHAT"}
