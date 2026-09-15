import unicodedata

MIN_LENGTH = 2


def normalize_word(word) -> str:
    """Forme normalisée d'un mot, identique à celle des grilles.

    Doit rester strictement équivalente à `DictionnaireTrie._normalize` (backend/trie_engine.py) :
    majuscules, sans accents, caractères alphanumériques uniquement.
    """
    if not isinstance(word, str):
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", word.upper())
        if unicodedata.category(c) != "Mn" and c.isalnum()
    ).strip()


def is_usable(normalized: str) -> bool:
    """Un mot n'entre dans une grille qu'à partir de 2 lettres (comme le Trie du backend)."""
    return len(normalized) >= MIN_LENGTH
