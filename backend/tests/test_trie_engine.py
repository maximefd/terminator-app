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


# --- Fréquences (Phase 3 : tri des candidats par fréquence) ---

def test_the_frequency_column_of_the_curated_lexicon_is_read(tmp_path):
    lexique = tmp_path / "lexique_cure.csv"
    lexique.write_text("PORTE;porte;Ouverture;4.2\n"
                       "ZORGL;zorgl;;\n"
                       "AABAM;aabam;Plomb (métal).;0.0\n", encoding="utf-8")
    trie = DictionnaireTrie()

    trie.load_dela_csv(str(lexique))

    assert trie.frequency("PORTE") == 4.2
    assert trie.frequency("ZORGL") == 0.0  # colonne vide
    assert trie.frequency("AABAM") == 0.0
    assert trie.frequency("INCONNU") == 0.0


def test_a_lexicon_without_the_column_leaves_every_frequency_at_zero(tmp_path):
    """Le DELA brut n'a que trois colonnes : le solveur doit retomber sur le score de lettres."""
    dela = tmp_path / "dela.csv"
    dela.write_text("PORTE;porte;Forme fléchie\n", encoding="utf-8")
    trie = DictionnaireTrie()

    trie.load_dela_csv(str(dela))

    assert trie.words == {"PORTE"}
    assert trie.frequencies == {}


def test_two_spellings_of_a_word_keep_the_highest_frequency(tmp_path):
    lexique = tmp_path / "lexique.csv"
    lexique.write_text("CAVA;cava;Vin;1.0\nCAVA;ça va;;3.0\n", encoding="utf-8")
    trie = DictionnaireTrie()

    trie.load_dela_csv(str(lexique))

    assert trie.frequency("CAVA") == 3.0


def test_insert_returns_the_normalized_word_or_none():
    trie = DictionnaireTrie()

    assert trie.insert("Éléphant") == "ELEPHANT"
    assert trie.insert("a") is None  # moins de deux lettres : ignoré
