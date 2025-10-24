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
        
        # On indexe par longueur pour la recherche de candidats
        self.words_by_len = {}
        for word in self.get_all_words():
            length = len(word)
            if length not in self.words_by_len:
                self.words_by_len[length] = []
            self.words_by_len[length].append(word)
            
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
        return self.words_by_len.get(length, [])

    def is_word_valid(self, word: str) -> bool:
        """Vérifie si un mot existe dans notre dictionnaire."""
        return word in self.trie.words
    
    def get_candidates(self, pattern: str) -> list[str]:
        return self.trie.search_pattern(pattern)