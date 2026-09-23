# DANS backend/engine/word_repository.py

import logging
from dataclasses import dataclass

from trie_engine import DictionnaireTrie # On importe la classe Trie

from .pattern_index import PatternIndex

# Pools d'un mot, du plus prioritaire au moins prioritaire ([ADR 0007](../../docs/adr/0007-contrat-de-generation.md)).
# Le solveur essaie les candidats dans cet ordre : un mot souhaité passe avant un mot du lexique commun.
POOL_PRIORITY = {"must": 0, "wish": 1, "common": 2}
DEFAULT_POOL = "common"


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


def prepare_lexicon(trie: DictionnaireTrie, max_length: int, min_length: int = 2) -> None:
    """Construit d'avance les index partagés des longueurs qu'une grille peut demander.

    Sans cela, la première génération de chaque longueur paie la construction de son index (plusieurs
    secondes sur le lexique complet), et l'API la paie à nouveau après chaque rechargement du lexique.
    """
    for length in range(min_length, max_length + 1):
        _shared_index(trie, length)


@dataclass(frozen=True)
class WholeLexicon:
    """Pool commun fait de **tous** les mots du Trie dont la longueur va de `min_length` à `max_length`.

    C'est le pool de toute génération de l'API. Passé en liste, il obligeait à recopier, trier puis
    répartir 700 000 mots à chaque requête — jusqu'à 0,7 s avant le premier appel du solveur
    ([ADR 0013](../../docs/adr/0013-cible-hebergement-production.md)). Désigné ainsi, il se lit
    directement dans les index partagés : les mots disponibles sont ceux de l'index entier.
    Les grilles produites sont identiques à celles de la liste équivalente.
    """
    max_length: int
    min_length: int = 2


class WordRepository:
    """
    Mots valides, mots encore disponibles et candidats d'un motif pour une grille.

    Les candidats sont calculés par ET binaire sur l'index (position, lettre) du Trie (#20) : pas de parcours
    du Trie ni de cache à invalider. Les mots consommés sont retirés de l'ensemble des disponibles.

    Les mots viennent de trois pools (#17) : obligatoires, souhaités (dictionnaires personnels et
    thématiques) et communs (lexique curé). Les mots des pools qui ne sont pas dans le lexique sont
    ajoutés à l'index de leur longueur et acceptés aux croisements : sans cela ils étaient simplement
    ignorés, et le dictionnaire personnel n'influençait jamais la grille.
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
        return cls.from_pools(trie, valid_words)

    @classmethod
    def from_pools(cls, trie: DictionnaireTrie, common_words=(), wish_words=(), must_words=()) -> "WordRepository":
        """Dépôt d'une grille à partir des trois pools. Un mot cité plusieurs fois garde le pool le plus prioritaire.

        `common_words` : une liste de mots, ou `WholeLexicon` pour tout le lexique d'une plage de longueurs.
        """
        repository = object.__new__(cls)
        repository._setup(trie, common_words, wish_words, must_words)
        return repository

    def _setup(self, trie: DictionnaireTrie, common_words, wish_words=(), must_words=()) -> None:
        self.trie = trie
        # Longueurs où tout le lexique est disponible : ses mots ne sont pas recopiés un à un
        whole = common_words if isinstance(common_words, WholeLexicon) else None
        whole_lengths = range(whole.min_length, whole.max_length + 1) if whole else range(0)
        # Pool de chaque mot cité ; les pools prioritaires écrasent les autres, donc un mot obligatoire
        # reste obligatoire même s'il figure aussi dans un dictionnaire thématique. Un mot absent vaut
        # « common » (DEFAULT_POOL), ce qu'est tout mot du lexique entier.
        self.pools: dict[str, str] = {}
        for pool, words in (("common", () if whole else common_words), ("wish", wish_words), ("must", must_words)):
            for word in words:
                self.pools[word] = pool
        words_by_len: dict[int, set[str]] = {}
        for word in self.pools:
            words_by_len.setdefault(len(word), set()).add(word)
        # Mots absents du lexique : ils viennent des pools de l'auteur, donc ils sont valides aux croisements
        self.extra_words: set[str] = {word for word in self.pools if word not in trie.words}
        # Mots disponibles par longueur, en ensembles de bits sur l'index (retirer ou remettre un mot : O(1))
        self.indexes: dict[int, PatternIndex] = {}
        self.available: dict[int, int] = {}
        for length in sorted(words_by_len.keys() | set(whole_lengths)):
            words = words_by_len.get(length, set())
            everything = _shared_index(trie, length).full_mask if length in whole_lengths else 0
            if not (words or everything):
                continue
            self.indexes[length] = index = self._index_for(length, words & self.extra_words)
            # L'index étendu garde les positions de l'index partagé : son ensemble complet reste valide
            self.available[length] = everything | index.mask_of(words)

    def _index_for(self, length: int, extras: set[str]) -> PatternIndex:
        """Index du lexique pour cette longueur, étendu aux mots des pools qui n'y sont pas (ordre alphabétique)."""
        index = _shared_index(self.trie, length)
        return index.extended(sorted(extras)) if extras else index

    def get_all_words(self) -> list[str]:
        """Récupère tous les mots valides depuis le Trie."""
        return self.trie.get_all_words()

    def get_words_by_length(self, length: int) -> list[str]:
        """Mots encore disponibles d'une longueur donnée, dans l'ordre de l'index."""
        index = self.indexes.get(length)
        return index.words_in(self.available[length]) if index else []

    def available_count(self) -> int:
        """Nombre de mots encore disponibles, toutes longueurs confondues."""
        return sum(mask.bit_count() for mask in self.available.values())

    def is_word_valid(self, word: str) -> bool:
        """Vérifie si un mot existe dans notre dictionnaire (lexique commun ou pools de l'auteur)."""
        return word in self.trie.words or word in self.extra_words

    def source_of(self, word: str) -> str:
        """Pool d'origine du mot : « must », « wish » ou « common »."""
        return self.pools.get(word, DEFAULT_POOL)

    def priority_of(self, word: str) -> int:
        """Rang du pool du mot, pour trier les candidats (0 = essayé en premier)."""
        return POOL_PRIORITY[self.source_of(word)]

    def frequency_of(self, word: str) -> float:
        """Fréquence zipf du mot, 0 si le lexique chargé n'en donne pas (DELA brut).

        Toutes les fréquences à 0 ⇒ le tri des candidats retombe exactement sur le score de
        lettres, c'est-à-dire l'ordre d'avant cette mesure.
        """
        return self.trie.frequency(word)

    def _candidate_mask(self, pattern: str) -> tuple[PatternIndex | None, int]:
        index = self.indexes.get(len(pattern))
        if index is None:
            return None, 0
        return index, index.mask(pattern) & self.available[len(pattern)]

    def get_candidates(self, pattern: str) -> list[str]:
        """Mots encore disponibles qui correspondent au motif, dans l'ordre de l'index."""
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
        if length in self.available:
            self.available[length] &= ~self.indexes[length].bit(word)

    def add_word_to_available(self, word: str, length: int):
        """Remet un mot dans les disponibles (retour arrière)."""
        if length not in self.available:
            self.indexes[length] = self._index_for(length, {word} & self.extra_words)
            self.available[length] = 0
        self.available[length] |= self.indexes[length].bit(word)
