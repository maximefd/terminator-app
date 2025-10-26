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
        """
        Trouve tous les mots qui correspondent au motif ET qui sont disponibles.
        """
        # 1. Utilise le Trie pour la recherche par motif (rapide)
        all_matching_words = self.trie.search_pattern(pattern)
        
        # 2. Utilise la longueur du pattern pour trouver la liste des mots disponibles
        length = len(pattern)
        available_words = self.words_by_len.get(length, [])
        
        # 3. Intersection: retourne uniquement les mots correspondants ET disponibles
        # On utilise un set pour la rapidité de la vérification.
        available_set = set(available_words)
        
        candidates = [word for word in all_matching_words if word in available_set]
        
        # OPTIMISATION : Si le Trie peut retourner un générateur et qu'on utilise des sets, ce serait plus propre.
        # Pour l'instant, on se base sur la liste, en assumant que le Trie renvoie des mots globaux.
        return candidates
        
    # ------------------------------------------------------------------
    # NOUVELLES MÉTHODES POUR LA CONSOMMATION DE MOTS (Backtracking)
    # ------------------------------------------------------------------

    def remove_word_from_available(self, word: str, length: int):
        """
        Retire un mot du pool disponible pour la longueur spécifiée.
        Utilisé pour simuler la 'consommation' du mot dans la branche de l'arbre.
        """
        if length in self.words_by_len:
            try:
                self.words_by_len[length].remove(word)
                # NOTE : l'utilisation de list.remove est O(n), ce qui peut impacter
                # la performance. Si la grille est très grande, passer à des sets
                # pour self.words_by_len serait O(1), mais nécessite une adaptation
                # dans la classe si l'ordre est important ailleurs.
            except ValueError:
                # Le mot n'est plus dans la liste (déjà consommé ou retiré).
                pass
            
    def add_word_to_available(self, word: str, length: int):
        """
        Remet un mot dans le pool disponible. Utilisé lors du backtrack.
        """
        if length in self.words_by_len:
            self.words_by_len[length].append(word)
        else:
            # Cas rare si la longueur n'existait pas, mais on la crée par précaution.
            self.words_by_len[length] = [word]