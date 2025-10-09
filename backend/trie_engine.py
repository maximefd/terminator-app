import os
# import xml.etree.ElementTree as ET est retiré car il n'est plus utilisé nulle part
import sys # Ajouté pour un meilleur débogage si besoin

class MotLexical:
    """Représente un mot unique avec ses métadonnées."""
    def __init__(self, texte_normalise, texte_original, definition, source):
        # Le mot sans accent pour la recherche (ex: ABATEE)
        self.texte_normalise = texte_normalise
        # Le mot original avec accent pour l'affichage (ex: abatée)
        self.texte_original = texte_original
        
        self.longueur = len(texte_normalise) # La longueur reste celle du mot
        self.definition = definition
        self.source = source
    
    def to_json(self):
        """Utile pour envoyer le résultat au Front-end Flask."""
        return {
            "mot": self.texte_normalise,
            "mot_affiche": self.texte_original,
            "longueur": self.longueur,
            "definition": self.definition,
            "source": self.source
        }

class TrieNode:
    """Représente un nœud dans l'arbre préfixe."""
    def __init__(self):
        self.children = {}
        self.end_of_word = [] # Contient une liste d'objets MotLexical

class DictionnaireTrie:
    def __init__(self):
        self.root = TrieNode()
        self.inserted_words = set() # Ajouté pour le filtre anti-doublon

    @property
    def words(self):
        """Fournit le nombre de mots insérés, utilisé par /api/status."""
        return self.inserted_words

    def insert(self, mot_obj):
        """Insère un objet MotLexical dans le Trie."""
        node = self.root
        
        # Utiliser 'texte_normalise' comme clé de recherche dans le Trie
        text = mot_obj.texte_normalise 
        
        # Logique du filtre anti-doublon
        if text in self.inserted_words:
            return
        self.inserted_words.add(text)
        
        # Parcours du Trie
        for char in text:
            if char not in node.children:
                node.children[char] = TrieNode()
                node = node.children[char]
            else:
                node = node.children[char]
        
        node.end_of_word.append(mot_obj)

    def load_dela_csv(self, filepath):
        """Charge les données du fichier CSV propre dans le Trie."""
        print(f"Chargement du DELA à partir de {filepath}...")
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # La ligne de DELA est : NORMALISE;ORIGINAL;DEFINITION
                    # On utilise split(';', 2) pour s'assurer que seuls les deux premiers ; sont utilisés comme séparateurs,
                    # le reste de la ligne devenant la 'DEFINITION'.
                    parts = line.split(';', 2)
                    
                    if len(parts) >= 2:
                        mot_normalise = parts[0].strip().upper()
                        mot_original = parts[1].strip()
                        definition = parts[2].strip() if len(parts) == 3 else f"Définition manquante pour {mot_original}"

                        # Vérification de base pour éviter d'insérer des lignes vides
                        if mot_normalise:
                            mot_obj = MotLexical(mot_normalise, mot_original, definition, "DELA")
                            self.insert(mot_obj)
                            count += 1
                        #else:
                            #print(f"DEBUG: Ligne ignorée (mot normalisé vide): {line}")

            print(f"DELA CSV chargé. {count} entrées insérées.")
        except FileNotFoundError:
            print(f"Erreur : Fichier {filepath} non trouvé. Vérifiez le chemin.")
        except Exception as e:
            # Afficher l'erreur détaillée
            print(f"Erreur de chargement CSV : {e}", file=sys.stderr)


    def load_user_list(self, filepath):
        """Charge une liste de mots personnelle (format : mot;definition)"""
        print(f"Chargement de la liste personnelle à partir de {filepath}...")
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    parts = line.split(';', 1)
                    mot_texte = parts[0].strip().upper() # CORRECTION: Assurer UPPERCASE pour la recherche
                    definition = parts[1].strip() if len(parts) > 1 else f"Liste personnelle - {mot_texte}"
                    
                    if mot_texte:
                        # mot_texte est utilisé pour les deux (car la liste perso n'a pas besoin de normalisation)
                        mot_obj = MotLexical(mot_texte, mot_texte, definition, "PERSONNEL")
                        self.insert(mot_obj)
                        count += 1
        except FileNotFoundError:
            print(f"Avertissement : Fichier personnel {filepath} non trouvé. C'est normal si vous n'avez pas encore de liste.")
        except Exception as e:
            print(f"Erreur de chargement de la liste personnelle : {e}", file=sys.stderr)
            
        print(f"Liste personnelle chargée. {count} entrées insérées.")

    # ... (le reste du code reste inchangé) ...
    def _recursive_search(self, current_node, pattern_index, normalized_pattern, results):
        """Fonction récursive pour parcourir le Trie (le moteur)"""
        if pattern_index == len(normalized_pattern):
            if current_node.end_of_word:
                results.extend(current_node.end_of_word)
            return
        
        char = normalized_pattern[pattern_index]
        
        if char == '?':
            for child_char, child_node in current_node.children.items():
                self._recursive_search(child_node, pattern_index + 1, normalized_pattern, results)
                
        else:
            if char in current_node.children:
                child_node = current_node.children[char]
                self._recursive_search(child_node, pattern_index + 1, normalized_pattern, results)

    def search_pattern(self, pattern):
        """Méthode principale pour démarrer la recherche."""
        results = []
        normalized_pattern = pattern.upper()
        
        if not normalized_pattern:
            return results

        self._recursive_search(
            current_node=self.root,
            pattern_index=0,
            normalized_pattern=normalized_pattern,
            results=results
        )
        
        # Triez les résultats pour mettre en avant les listes personnelles
        # Mots PERSONNELS en premier, puis DELA.
        results.sort(key=lambda x: x.source, reverse=True) 

        return results

    def add_user_word(self, mot_texte, definition, filepath):
        """Ajoute un mot au fichier de l'utilisateur et au Trie en mémoire."""
        
        mot_texte = mot_texte.strip().upper()
        
        # 1. Ajout au fichier physique (pour la persistance)
        try:
            # 'a' pour append (ajouter à la fin du fichier)
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(f"\n{mot_texte};{definition}")
        except Exception as e:
            print(f"Erreur d'écriture dans le fichier personnel: {e}")
            return False

        # 2. Ajout au Trie en mémoire (pour que la recherche soit immédiate)
        # CORRECTION: mot_texte est utilisé pour les deux
        mot_obj = MotLexical(mot_texte, mot_texte, definition, "PERSONNEL")
        self.insert(mot_obj)
        
        print(f"Mot personnel ajouté et inséré dans le Trie : {mot_texte}")
        return True

    def is_match(self, pattern, word):
        """
        Vérifie si un mot donné correspond au motif (incluant le joker '?').
        
        Args:
            pattern (str): Le motif de recherche (en majuscules, sans accents, ex: 'A???I').
            word (str): Le mot personnel à vérifier (en majuscules, sans accents, ex: 'ALIBI').
            
        Returns:
            bool: True si le mot correspond au motif, False sinon.
        """
        if len(pattern) != len(word):
            return False
        
        for p_char, w_char in zip(pattern, word):
            # Le point d'interrogation ('?') correspond à tout caractère.
            # Sinon, les caractères doivent être identiques.
            if p_char != '?' and p_char != w_char:
                return False
                
        return True
