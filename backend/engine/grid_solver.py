import logging
import random

from .grid_template import GridTemplate
from .slot_finder import SlotFinder
from .word_repository import WordRepository

logger = logging.getLogger(__name__)

class GridSolver:
    
    # --- NOUVELLE CONSTANTE POUR LA PERFORMANCE ---
    MAX_CANDIDATES_PER_SLOT = 100 
    # ---------------------------------------------

    LETTER_SCORES = {
        # ... (scores inchangés)
        'A': 9, 'B': 2, 'C': 2, 'D': 3, 'E': 15, 'F': 1, 'G': 1, 'H': 1,
        'I': 8, 'J': 1, 'K': 0, 'L': 6, 'M': 3, 'N': 7, 'O': 6, 'P': 3,
        'Q': 1, 'R': 8, 'S': 9, 'T': 7, 'U': 6, 'V': 2, 'W': 0, 'X': 0,
        'Y': 0, 'Z': 0
    }

    def __init__(self, template: GridTemplate, repository: WordRepository, finder: SlotFinder):
        self.template = template
        self.repository = repository
        
        # IMPORTANT: Initialisation des slots avec 'is_filled' pour l'heuristique MRV
        self.slots = []
        for slot in finder.slots:
            new_slot = slot.copy()
            new_slot['is_filled'] = False 
            self.slots.append(new_slot)
            
        self.grid = [row[:] for row in template.grid]
        self.height = template.height
        self.width = template.width
        self.placed_words = []

    def solve(self) -> bool:
        """Point d'entrée principal pour lancer la résolution (démarre la récursion MRV)."""
        logging.info("Début de la résolution de la grille (Heuristique MRV)...")
        return self._solve_recursive() # <-- SANS INDEX
    
    def _choose_next_slot(self) -> dict | None:
        """
        Choisit dynamiquement le prochain slot à traiter (le plus contraint)
        par l'heuristique MRV, basé sur le nombre minimal de cases vides ('?')
        dans son motif actuel.
        """
        best_slot = None
        min_unknowns = float('inf')
        
        for slot in self.slots:
            # On ignore les slots qui sont déjà remplis
            if slot.get('is_filled', False):
                continue
                
            pattern = self._get_slot_pattern(slot)
            nb_unknowns = pattern.count('?')
            
            # Si nb_unknowns est 0, c'est que le slot est rempli par des croisements
            # mais n'est pas marqué 'is_filled'. On l'ignore également, sauf
            # si on veut s'assurer qu'il est marqué avant d'être ignoré.
            if nb_unknowns == 0:
                continue

            # On cherche le minimum d'inconnues (la contrainte la plus forte)
            if nb_unknowns < min_unknowns:
                min_unknowns = nb_unknowns
                best_slot = slot
                
        return best_slot
        
    def _solve_recursive(self) -> bool:
        """
        Implémente l'algorithme de backtracking. Utilise _choose_next_slot() (MRV).
        """
        # 1. Choix dynamique du slot le plus contraint
        slot = self._choose_next_slot()
        
        # 2. Condition d'arrêt (Succès : tous les slots sont remplis)
        if not slot:
            logging.info("SUCCÈS : Tous les slots ont été remplis.")
            return True

        pattern = self._get_slot_pattern(slot)
        
        logging.info(f"[Slot {slot.get('id', 'MRV')}] (Dir: {slot['direction']}, L: {slot['length']}) - Motif : '{pattern}' (Inconnues: {pattern.count('?')})")

        # 3. Récupération des candidats possibles
        candidates = self.repository.get_candidates(pattern)
        if not candidates:
            logging.info(f"  Aucun candidat pour ce slot, backtrack !")
            return False
        
        # Tri des candidats par score (heuristique)
        scored_candidates = [(self._score_word(w), w) for w in candidates]
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 💥 APPLICATION DE LA LIMITE (EPIC A2)
        scored_candidates = scored_candidates[:self.MAX_CANDIDATES_PER_SLOT]
        
        logging.debug(f"  {len(scored_candidates)} candidats trouvés (limité à {self.MAX_CANDIDATES_PER_SLOT}). Trié.")        
        # 4. Boucle de test des candidats
        for i, (score, word) in enumerate(scored_candidates):
            
            logging.debug(f"    Tentative {i+1}/{len(scored_candidates)} : mot '{word}' (Score: {score})")

            # Place le mot temporairement et sauvegarde l'état pour le revert
            original_state = self._place_word_on_grid(word, slot)

            if self._is_placement_valid(word, slot):
                
                # --- CONSOMMATION ---
                slot['is_filled'] = True # Marque le slot comme rempli
                self.repository.remove_word_from_available(word, slot['length']) 
                logging.debug(f"      -> Mot '{word}' est valide. Passage au slot suivant...")

                if self._solve_recursive(): # Appel récursif SANS INDEX
                    # SUCCES
                    self.placed_words.insert(0, {
                        "text": word, "x": slot['x'], "y": slot['y'],
                        "direction": slot['direction'], "id": slot['id']
                    })
                    return True
                else:
                    # ÉCHEC RÉCURSIF (Backtrack)
                    # Annule la consommation du mot et marque le slot comme vide
                    self.repository.add_word_to_available(word, slot['length']) 
                    slot['is_filled'] = False 
                    logging.debug(f"      <- Retour arrière (Backtrack) pour '{word}'.")
            
            # --- REVERT DE LA GRILLE ---
            self._revert_grid_state(original_state)
            # self._check_grid_integrity() # ATTENTION : Décommenter ceci rend le code TRÈS LENT !

        # 5. Échec de tous les candidats (aligné avec la boucle for)
        logging.debug(f"  ÉCHEC FINAL : Aucun candidat n'a abouti pour le slot.")
        return False

    def _check_grid_integrity(self):
        """
        Vérifie si des lettres orphelines (non associées à un slot non rempli) existent.
        ATTENTION : Très coûteux en performance, à utiliser pour le débogage seulement.
        """
        
        # Logique non implémentée, mais correction de la structure pour éviter l'erreur d'indentation
        
        active_slots_indices = set()
        for slot in self.slots:
            if not slot.get('is_filled', False):
                # Utiliser l'ID unique du slot si disponible, sinon l'index
                active_slots_indices.add(slot.get('id', self.slots.index(slot))) 

        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                
                # On ne vérifie que les cellules non noires et non vides
                if cell not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, '', ' '):
                    # ICI TU DOIS METTRE LA LOGIQUE DE VÉRIFICATION
                    # Exemple: if not is_cell_in_any_active_slot(x, y, active_slots_indices):
                    # logging.warning(f"⚠️ Lettre orpheline '{cell}' détectée en ({x},{y})")
                    pass
        
    # --- METHODES INCHANGEES (DOIVENT ETRE PLACEES SOUS CETTE LIGNE DANS VOTRE FICHIER) ---

    def _get_slot_pattern(self, slot: dict) -> str:
        """
        Génère le motif du slot (ex : 'A??E?').
        '?' représente une case vide.
        """
        pattern = []
        placeholder = '?'

        logging.debug(f"   Génération du motif pour slot {slot.get('id', 'N/A')} ({slot['direction']}, L={slot['length']})")

        for i in range(slot['length']):
            # Détermination des coordonnées selon la direction
            if slot['direction'] == 'across':
                x = slot['x'] + i
                y = slot['y']
            else:  # down
                x = slot['x']
                y = slot['y'] + i

            # Lecture sécurisée
            if y >= self.height or x >= self.width:
                logging.warning(f"    Coordonnées invalides ({x},{y}) hors grille (max {self.width-1},{self.height-1})")
                continue
                
            char = self.grid[y][x]

            # Nettoyage du caractère lu
            if char in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL,'', ' ', None):
                pattern.append(placeholder)
            else:
                pattern.append(char)

        result = ''.join(pattern)
        logging.debug(f"   → Motif généré : '{result}'")
        return result

    def _place_word_on_grid(self, word: str, slot: dict) -> list[tuple[int, int, str]]:
        """
        Place un mot dans la grille et renvoie la liste des états précédents
        pour chaque case modifiée (coordonnées + ancienne valeur).
        """
        original_state = []
        x, y, length, direction = slot['x'], slot['y'], slot['length'], slot['direction']

        for i, char in enumerate(word):
            px = x + i if direction == 'across' else x
            py = y if direction == 'across' else y + i
            original_state.append((px, py, self.grid[py][px]))
            self.grid[py][px] = char
        return original_state

    def _revert_grid_state(self, original_state: list[tuple[int, int, str]], slot=None):
        """
        Restaure l’état précédent de la grille à partir de la liste d’états sauvegardés.
        """
        for (x, y, old_char) in original_state:
            self.grid[y][x] = old_char

    def _is_placement_valid(self, word: str, slot: dict) -> bool:
        """Vérifie si le mot crée des fragments valides dans l'autre sens."""
        x, y, direction = slot['x'], slot['y'], slot['direction']
        
        for i, char in enumerate(word):
            px = x + i if direction == 'across' else x
            py = y if direction == 'across' else y + i
            
            # Note: Si le mot est bien placé, il aura remplacé temporairement l'ancienne valeur
            current_char_before_placement = self.grid[py][px]
            if current_char_before_placement == char:
                continue

            fragment = ""
            if direction == 'across':
                fragment = self._get_vertical_fragment(px, py)
            else:
                fragment = self._get_horizontal_fragment(px, py)

            if len(fragment) > 1 and not self.repository.is_word_valid(fragment):
                logging.debug(f"      -> REJETÉ : Le mot '{word}' crée un fragment invalide : '{fragment}'")
                return False
        return True

    def _get_vertical_fragment(self, x: int, y: int) -> str:
        """Construit le mot vertical complet passant par (x,y)."""
        fragment = ""
        cy = y
        while cy >= 0 and self.grid[cy][x] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL):
            fragment = self.grid[cy][x] + fragment; cy -= 1
        cy = y + 1
        while cy < self.height and self.grid[cy][x] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL):
            fragment = fragment + self.grid[cy][x]; cy += 1
        return fragment

    def _get_horizontal_fragment(self, x: int, y: int) -> str:
        """Construit le mot horizontal complet passant par (x,y)."""
        fragment = ""
        cx = x
        while cx >= 0 and self.grid[y][cx] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL):
            fragment = self.grid[y][cx] + fragment; cx -= 1
        cx = x + 1
        while cx < self.width and self.grid[y][cx] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL):
            fragment = fragment + self.grid[y][cx]; cx += 1
        return fragment
    
    def _score_word(self, word: str) -> int:
        """Calcule le 'score d'utilité' d'un mot."""
        return sum(self.LETTER_SCORES.get(char, 0) for char in word)