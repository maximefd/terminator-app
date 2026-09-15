# DANS backend/engine/word_repository.py

import logging

from trie_engine import DictionnaireTrie # On importe la classe Trie

from .pattern_index import PatternIndex


def _shared_index(trie: DictionnaireTrie, length: int) -> PatternIndex:
    """Index (position, lettre) des mots du Trie de cette longueur, construit une seule fois par Trie.

    Un Trie n'est plus modifié après son chargement (l'API en charge un nouveau quand le lexique change) :
    l'index est donc partagé par toutes les générations qui l'utilisent. Ordre alphabétique, comme le
    parcours d'un Trie construit dans l'ordre.
    """
    cache = trie.__dict__.setdefault("_pattern_indexes", {})
    index = cache.get(length)
    if index is None:
        by_length = trie.__dict__.get("_words_by_length")
        if by_length is None:
            by_length = {}
            for word in trie.words:
                by_length.setdefault(len(word), []).append(word)
            for words in by_length.values():
                words.sort()
            trie._words_by_length = by_length
        index = cache[length] = PatternIndex(by_length.get(length, []))
    return index


class WordRepository:
    """
    Mots valides, mots encore disponibles et candidats d'un motif pour une grille.

    Les candidats sont calculés par ET binaire sur l'index (position, lettre) du Trie (#20) : pas de parcours
    du Trie ni de cache à invalider. Les mots consommés sont retirés de l'ensemble des disponibles.
    """
    def __init__(self, dela_file_path: str):
        trie = DictionnaireTrie()
        logging.info(f"Chargement et indexation du dictionnaire depuis : {dela_file_path}")
        try:
            trie.load_dela_csv(dela_file_path)
        except Exception as e:
            logging.error(f"Échec du chargement du dictionnaire pour le WordRepository: {e}")
            raise
        self._setup(trie, trie.get_all_words())
        logging.info(f"{len(trie.words)} mots uniques indexés par longueur.")

    @classmethod
    def from_words(cls, trie: DictionnaireTrie, valid_words: list[str]) -> "WordRepository":
        """Dépôt d'une grille : réutilise un Trie déjà chargé (et ses index) avec les mots autorisés."""
        repository = object.__new__(cls)
        repository._setup(trie, valid_words)
        return repository

    def _setup(self, trie: DictionnaireTrie, valid_words: list[str]) -> None:
        self.trie = trie
        # Mots disponibles par longueur (sets : O(1) pour retirer ou remettre un mot)
        self.words_by_len: dict[int, set[str]] = {}
        for word in valid_words:
            self.words_by_len.setdefault(len(word), set()).add(word)
        # Même information sous forme d'ensembles de bits, pour l'index
        self.indexes: dict[int, PatternIndex] = {}
        self.available: dict[int, int] = {}
        for length, words in self.words_by_len.items():
            index = self.indexes[length] = _shared_index(trie, length)
            self.available[length] = index.mask_of(words)

    def get_all_words(self) -> list[str]:
        """Récupère tous les mots valides depuis le Trie."""
        return self.trie.get_all_words()

    def get_words_by_length(self, length: int) -> list[str]:
        """Retourne une liste de tous les mots d'une longueur donnée."""
        return list(self.words_by_len.get(length, set()))

    def is_word_valid(self, word: str) -> bool:
        """Vérifie si un mot existe dans notre dictionnaire."""
        return word in self.trie.words

    def _candidate_mask(self, pattern: str) -> tuple[PatternIndex | None, int]:
        index = self.indexes.get(len(pattern))
        if index is None:
            return None, 0
        return index, index.mask(pattern) & self.available[len(pattern)]

    def get_candidates(self, pattern: str) -> list[str]:
        """Mots encore disponibles qui correspondent au motif, dans l'ordre alphabétique."""
        index, mask = self._candidate_mask(pattern)
        return index.words_in(mask) if index else []

    def count_candidates(self, pattern: str) -> int:
        """Nombre de candidats du motif, sans construire la liste (choix du slot, forward checking)."""
        return self._candidate_mask(pattern)[1].bit_count()

    # ------------------------------------------------------------------
    # CONSOMMATION DES MOTS (Backtracking)
    # ------------------------------------------------------------------

    def remove_word_from_available(self, word: str, length: int):
        """Retire un mot des disponibles (mot placé dans la branche en cours)."""
        if length in self.words_by_len:
            self.words_by_len[length].discard(word)  # discard ne lève pas d'erreur si absent
        if length in self.available:
            self.available[length] &= ~self.indexes[length].bit(word)

    def add_word_to_available(self, word: str, length: int):
        """Remet un mot dans les disponibles (retour arrière)."""
        self.words_by_len.setdefault(length, set()).add(word)
        if length not in self.available:
            self.indexes[length] = _shared_index(self.trie, length)
            self.available[length] = 0
        self.available[length] |= self.indexes[length].bit(word)
