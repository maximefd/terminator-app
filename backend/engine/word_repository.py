# DANS backend/engine/word_repository.py

import logging
from trie_engine import DictionnaireTrie # On importe la classe Trie

class WordRepository:
    """
    Charge et indexe tous les mots du dictionnaire pour une recherche efficace.
    """
    def __init__(self, dela_file_path: str):
        self.trie = DictionnaireTrie()
        self._load_and_index(dela_file_path)
        
        # OPTIMISATION : Indexer par longueur avec des SETS pour O(1) add/remove
        self.words_by_len = {}
        for word in self.get_all_words():
            length = len(word)
            if length not in self.words_by_len:
                self.words_by_len[length] = set()
            self.words_by_len[length].add(word)
        
        # OPTIMISATION : Cache pour get_candidates
        self._candidate_cache = {}  # pattern -> list[str]
            
        logging.info(f"{len(self.get_all_words())} mots uniques indexés par longueur.")

    def _load_and_index(self, file_path):
        """Charge les mots en utilisant le Trie."""
        logging.info(f"Chargement et indexation du dictionnaire depuis : {file_path}")
        try:
            self.trie.load_dela_csv(file_path)
        except Exception as e:
            logging.error(f"Échec du chargement du dictionnaire pour le WordRepository: {e}")
            raise

    def get_all_words(self) -> list[str]:
        """Récupère tous les mots valides depuis le Trie."""
        return self.trie.get_all_words()

    def get_words_by_length(self, length: int) -> list[str]:
        """Retourne une liste de tous les mots d'une longueur donnée."""
        return list(self.words_by_len.get(length, set()))

    def is_word_valid(self, word: str) -> bool:
        """Vérifie si un mot existe dans notre dictionnaire."""
        return word in self.trie.words
    
    def get_candidates(self, pattern: str) -> list[str]:
        """
        Trouve tous les mots qui correspondent au motif ET qui sont disponibles.
        Utilise un cache pour éviter les recherches redondantes.
        """
        # OPTIMISATION : Vérifier le cache d'abord
        cache_key = (pattern, tuple(sorted(self.words_by_len.get(len(pattern), []))))
        # Note: On ne peut pas utiliser la liste directement comme clé, on utilise le pattern
        # et on vérifie si la disponibilité a changé en comptant les mots disponibles
        
        # Version simplifiée : cache basé uniquement sur le pattern + longueur de words_by_len
        simple_cache_key = (pattern, len(self.words_by_len.get(len(pattern), [])))
        
        if simple_cache_key in self._candidate_cache:
            return self._candidate_cache[simple_cache_key]
        
        # 1. Utilise le Trie pour la recherche par motif (rapide)
        all_matching_words = self.trie.search_pattern(pattern)
        
        # 2. Utilise la longueur du pattern pour trouver le SET des mots disponibles
        length = len(pattern)
        available_set = self.words_by_len.get(length, set())
        
        # 3. Intersection: retourne uniquement les mots correspondants ET disponibles
        
        candidates = [word for word in all_matching_words if word in available_set]
        
        # OPTIMISATION : Mettre en cache le résultat
        self._candidate_cache[simple_cache_key] = candidates
        
        return candidates
        
    # ------------------------------------------------------------------
    # NOUVELLES MÉTHODES POUR LA CONSOMMATION DE MOTS (Backtracking)
    # ------------------------------------------------------------------

    def remove_word_from_available(self, word: str, length: int):
        """
        Retire un mot du pool disponible pour la longueur spécifiée.
        Utilisé pour simuler la 'consommation' du mot dans la branche de l'arbre.
        OPTIMISATION : O(1) grâce aux sets.
        """
        if length in self.words_by_len:
            self.words_by_len[length].discard(word)  # discard ne lève pas d'erreur si absent
            # OPTIMISATION : Invalider le cache quand la disponibilité change
            self._invalidate_cache_for_length(length)
            
    def add_word_to_available(self, word: str, length: int):
        """
        Remet un mot dans le pool disponible. Utilisé lors du backtrack.
        OPTIMISATION : O(1) grâce aux sets.
        """
        if length in self.words_by_len:
            self.words_by_len[length].add(word)
        else:
            # Cas rare si la longueur n'existait pas, mais on la crée par précaution.
            self.words_by_len[length] = {word}
        
        # OPTIMISATION : Invalider le cache quand la disponibilité change
        self._invalidate_cache_for_length(length)
    
    def _invalidate_cache_for_length(self, length: int):
        """
        Invalide les entrées du cache pour un pattern de longueur donnée.
        """
        keys_to_remove = [key for key in self._candidate_cache.keys() if len(key[0]) == length]
        for key in keys_to_remove:
            del self._candidate_cache[key]