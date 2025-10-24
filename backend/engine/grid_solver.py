import logging
logging.basicConfig(level=logging.DEBUG)
import random

from .grid_template import GridTemplate
from .slot_finder import SlotFinder
from .word_repository import WordRepository

logger = logging.getLogger(__name__)

class GridSolver:
    """
    Le "cerveau". Utilise le backtracking et des heuristiques pour remplir
    un template de grille avec des mots d'un dictionnaire.
    """
    
    LETTER_SCORES = {
        'A': 9, 'B': 2, 'C': 2, 'D': 3, 'E': 15, 'F': 1, 'G': 1, 'H': 1,
        'I': 8, 'J': 1, 'K': 0, 'L': 6, 'M': 3, 'N': 7, 'O': 6, 'P': 3,
        'Q': 1, 'R': 8, 'S': 9, 'T': 7, 'U': 6, 'V': 2, 'W': 0, 'X': 0,
        'Y': 0, 'Z': 0
    }

    def __init__(self, template: GridTemplate, repository: WordRepository, finder: SlotFinder):
        self.template = template
        self.repository = repository
        self.slots = finder.slots
        self.grid = [row[:] for row in template.grid]
        self.height = template.height
        self.width = template.width
        self.placed_words = []

    def solve(self) -> bool:
        """Point d'entrée principal pour lancer la résolution."""
        logging.info("Début de la résolution de la grille...")
        return self._solve_recursive(0)

    def _solve_recursive(self, slot_index: int) -> bool:
        if slot_index == len(self.slots):
            logging.info("SUCCÈS : Tous les slots ont été remplis.")
            return True

        slot = self.slots[slot_index]
        
        # --- NOTRE NOUVEL INDICE ---
        # On génère le motif
        pattern = self._get_slot_pattern(slot)
        # On le montre AVANT de chercher les candidats
        logging.info(f"[Slot {slot_index+1}/{len(self.slots)}] (Dir: {slot['direction']}, L: {slot['length']}) - Génération du motif : '{pattern}'")
        
        candidates = self.repository.get_candidates(pattern)
        
        if not candidates:
            logging.info(f"  Aucun candidat pour le slot {slot_index+1}, backtrack !")
            return False
        
        logging.info(f"  {len(candidates)} candidats trouvés. Tri en cours...")
        
        scored_candidates = [(self._score_word(w), w) for w in candidates]
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        for i, (score, word) in enumerate(scored_candidates):
            logging.debug(f"    Tentative {i+1}/{len(scored_candidates)} : mot '{word}' (Score: {score})")
            
            original_state = self._place_word_on_grid(word, slot)
            
            if self._is_placement_valid(word, slot):
                logging.debug(f"      -> Mot '{word}' est valide. Passage au slot suivant...")
                if self._solve_recursive(slot_index + 1):
                    self.placed_words.insert(0, {"text": word, "x": slot['x'], "y": slot['y'], "direction": slot['direction'], "id": slot['id']})
                    return True
                else:
                    logging.debug(f"      <- Retour arrière (Backtrack). Le placement de '{word}' n'a pas abouti.")

            self._revert_grid_state(original_state, slot)

        logging.debug(f"  ÉCHEC FINAL : Aucun des {len(scored_candidates)} candidats n'a fonctionné pour le slot {slot_index+1}.")
        return False

    def _get_slot_pattern(self, slot: dict) -> str:
        pattern = []
        placeholder = '?'
        if slot['direction'] == 'across':
            for i in range(slot['length']):
                char = self.grid[slot['y']][slot['x'] + i]
                logging.debug(f"    Case ({slot['x']+i},{slot['y']}) = '{char}'")
                pattern.append(char if char not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL) else placeholder)
        else:
            for i in range(slot['length']):
                char = self.grid[slot['y'] + i][slot['x']]
                logging.debug(f"    Case ({slot['x']},{slot['y']+i}) = '{char}'")
                pattern.append(char if char not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL) else placeholder)
        result = "".join(pattern)
        logging.debug(f"    Motif généré : '{result}'")
        return result

    def _place_word_on_grid(self, word: str, slot: dict) -> list[str]:
        original_state = []
        x, y, length, direction = slot['x'], slot['y'], slot['length'], slot['direction']
        for i, char in enumerate(word):
            px = x + i if direction == 'across' else x
            py = y if direction == 'across' else y + i
            original_state.append(self.grid[py][px])
            self.grid[py][px] = char
        return original_state

    def _revert_grid_state(self, original_state: list[str], slot: dict):
        x, y, length, direction = slot['x'], slot['y'], slot['length'], slot['direction']
        for i in range(length):
            px = x + i if direction == 'across' else x
            py = y if direction == 'across' else y + i
            self.grid[py][px] = original_state[i]

    def _is_placement_valid(self, word: str, slot: dict) -> bool:
        """Vérifie si le mot crée des fragments valides dans l'autre sens."""
        x, y, direction = slot['x'], slot['y'], slot['direction']
        
        for i, char in enumerate(word):
            px = x + i if direction == 'across' else x
            py = y if direction == 'across' else y + i
            
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