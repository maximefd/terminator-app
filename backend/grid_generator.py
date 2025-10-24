# DANS backend/grid_generator.py

import logging
import os
import random

from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from engine.word_repository import WordRepository
from engine.grid_solver import GridSolver
from trie_engine import DictionnaireTrie # NÉCESSAIRE pour votre correction

logger = logging.getLogger(__name__)

class GridGenerator:
    """
    Chef d'orchestre qui pilote la création d'une grille de A à Z.
    """
    def __init__(self, width: int, height: int, all_words: list[str], seed: int = None):
        self.width = width
        self.height = height
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        # 1. Charger le template
        template_path = self._find_template_path(width, height)
        if not template_path:
            raise RuntimeError(f"Aucun template trouvé pour la taille {width}x{height}.")
        self.template = GridTemplate(width, height, template_path)

        # 2. Préparer le dictionnaire (avec votre correction)
        self.repository = self._create_repository(all_words)

        # 3. Trouver les slots
        finder = SlotFinder(self.template)
        finder.find_all_slots()

        # 4. Initialiser le solveur
        self.solver = GridSolver(self.template, self.repository, finder)
        
        self.placed_words = []

    def _find_template_path(self, width: int, height: int) -> str | None:
        """Trouve un fichier template au hasard pour la taille donnée."""
        template_dir = f"templates/{width}x{height}"
        if not os.path.isdir(template_dir):
            return None
        templates = [f for f in os.listdir(template_dir) if f.endswith('.txt')]
        return os.path.join(template_dir, random.choice(templates)) if templates else None

    # VOTRE FONCTION CORRIGÉE :
    def _create_repository(self, all_words: list[str]) -> WordRepository:
        """Crée un repository avec un Trie construit à partir des mots filtrés."""
        repo = object.__new__(WordRepository)
        repo.trie = DictionnaireTrie()

        valid_words = [w for w in all_words if len(w) <= max(self.width, self.height)]
        repo.word_set = set(valid_words)

        repo.words_by_len = {}
        for word in valid_words:
            length = len(word)
            if length not in repo.words_by_len:
                repo.words_by_len[length] = []
            repo.words_by_len[length].append(word)
            repo.trie.insert(word) # On peuple le Trie

        logging.info(f"{len(valid_words)} mots pertinents indexés pour cette grille.")
        return repo

    def generate(self) -> bool:
        """Lance le solveur et récupère les résultats."""
        success = self.solver.solve()
        if success:
            # On trie les mots dans l'ordre de leur slot pour un affichage cohérent
            self.placed_words = sorted(self.solver.placed_words, key=lambda p: p['id'])
        return success


    # ---------------------------------------------------------
    # 2. Données de sortie
    # ---------------------------------------------------------
    def get_grid_data(self) -> dict:
        """
        Formate la grille finale en dictionnaire pour export (API ou rapport HTML).
        Inclut le seed pour traçabilité.
        """
        final_grid = self.solver.grid
        filled_cells = 0
        cells = []

        for y in range(self.height):
            for x in range(self.width):
                char = final_grid[y][x]
                is_black = (self.template.grid[y][x] == self.template.BLACK_SQUARE)

                if char and not is_black and char != self.template.EMPTY_CELL:
                    filled_cells += 1

                display_char = char if not is_black and char != self.template.EMPTY_CELL else ""
                cells.append({
                    "x": x,
                    "y": y,
                    "char": display_char,
                    "is_black": is_black
                })

        total_cells = self.width * self.height
        non_black_cells = total_cells - sum(
            row.count(self.template.BLACK_SQUARE) for row in self.template.grid
        )
        fill_ratio = filled_cells / non_black_cells if non_black_cells > 0 else 0

        return {
            "seed": getattr(self, "seed", None),  # ✅ empêche KeyError dans test_harness
            "width": self.width,
            "height": self.height,
            "fill_ratio": round(fill_ratio, 3),
            "cells": cells,
            "words": self.placed_words,
        }