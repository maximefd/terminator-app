import csv
import unicodedata
import logging

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False

class DictionnaireTrie:
    def __init__(self):
        self.root = TrieNode()
        self.words = set()
        logging.info("Initialisation du DictionnaireTrie.")

    @staticmethod
    def _normalize(word):
        """Normalise un mot : majuscules, pas d'accents, sans espaces."""
        if not isinstance(word, str): return ""
        # On supprime les espaces, ce qui était la cause de nos bugs précédents
        s = ''.join(c for c in unicodedata.normalize('NFD', word.upper()) 
                    if unicodedata.category(c) != 'Mn' and c.isalnum())
        return s.strip()

    def insert(self, mot_affiche):
        """Insère un mot dans le Trie, en ignorant les expressions composées."""
        mot_normalise = self._normalize(mot_affiche)
        
        if not mot_normalise or len(mot_normalise) < 2:
            return

        node = self.root
        for char in mot_normalise:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        
        if not node.is_end_of_word:
            node.is_end_of_word = True
            self.words.add(mot_normalise)

    def load_dela_csv(self, file_path):
        """Charge le CSV directement dans le set et le Trie."""
        logging.info(f"Chargement du DELA à partir de {file_path}...")
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                count = 0
                for row in reader:
                    if row:
                        self.insert(row[0]) # On n'insère que la première colonne
                        count += 1
                logging.info(f"DELA CSV chargé. {count} lignes lues. {len(self.words)} mots valides (sans espaces) stockés.")
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du CSV: {e}")
            raise

    def search_pattern(self, pattern) -> list[str]:
        """Recherche les mots (strings) correspondant à un motif (ex: 'P?LE')."""
        results = []
        # Le motif est déjà normalisé par le repository
        self._search_recursive(self.root, pattern, "", results)
        return results

    def _search_recursive(self, node, pattern, current_word, results):
        if len(current_word) == len(pattern):
            if node.is_end_of_word:
                results.append(current_word)
            return

        char_pattern = pattern[len(current_word)]

        if char_pattern == '?':
            for char, child_node in node.children.items():
                self._search_recursive(child_node, pattern, current_word + char, results)
        elif char_pattern in node.children:
            child_node = node.children[char_pattern]
            self._search_recursive(child_node, pattern, current_word + char_pattern, results)

    def get_all_words(self) -> list[str]:
        """Retourne une liste de tous les mots du set."""
        return list(self.words)

class Mot:
    # Cette classe n'est plus utilisée par le Trie, mais on la garde au cas où
    def __init__(self, texte, texte_normalise, definition=None):
        self.texte = texte
        self.texte_normalise = texte_normalise
        self.definition = definition