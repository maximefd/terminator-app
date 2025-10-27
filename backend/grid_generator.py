# DANS backend/grid_generator.py

import logging
import os
import random

from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from engine.word_repository import WordRepository
from engine.grid_solver import GridSolver
from trie_engine import DictionnaireTrie # NÉCESSAIRE

logger = logging.getLogger(__name__)

class GridGenerator:
    """
    Chef d'orchestre qui pilote la création d'une grille de A à Z.
    """
    
    # 1. MODIFICATION DE LA SIGNATURE DE __init__
    def __init__(self, width: int, height: int, valid_words: list[str], prebuilt_trie: DictionnaireTrie, seed: int = None):
        """
        Initialise le générateur.
        
        Args:
            width (int): Largeur de la grille.
            height (int): Hauteur de la grille.
            valid_words (list[str]): Liste de mots DÉJÀ FILTRÉS pour la taille de la grille.
            prebuilt_trie (DictionnaireTrie): Un Trie DÉJÀ CONSTRUIT avec les valid_words.
            seed (int, optional): Seed pour la reproductibilité.
        """
        self.width = width
        self.height = height
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            
        # NOUVELLE LIGNE : On stocke le Trie pré-construit
        self.prebuilt_trie = prebuilt_trie

        # 1. Charger le template
        template_path = self._find_template_path(width, height)
        if not template_path:
            raise RuntimeError(f"Aucun template trouvé pour la taille {width}x{height}.")
        self.template = GridTemplate(width, height, template_path)

        # 2. Préparer le dictionnaire (utilise maintenant le Trie et les mots pré-filtrés)
        self.repository = self._create_repository(valid_words)

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

    # 2. FONCTION _create_repository ENTIÈREMENT REMPLACÉE
    def _create_repository(self, valid_words: list[str]) -> WordRepository:
        """
        Crée un repository en RÉUTILISANT le Trie pré-construit
        et une liste de mots DÉJÀ FILTRÉS.
        """
        repo = object.__new__(WordRepository)

        # Réutilise le Trie au lieu d'en créer un
        repo.trie = self.prebuilt_trie 

        # 'valid_words' est maintenant la liste passée à __init__
        repo.word_set = set(valid_words) 

        # Ce dictionnaire est spécifique à cette grille (pour la consommation)
        # OPTIMISATION : Utiliser des sets pour O(1) add/remove
        repo.words_by_len = {}
        for word in valid_words:
            length = len(word)
            if length not in repo.words_by_len:
                repo.words_by_len[length] = set()
            repo.words_by_len[length].add(word)
            # PAS BESOIN DE repo.trie.insert(word), c'est déjà fait !
        
        # Initialiser le cache vide pour get_candidates
        repo._candidate_cache = {}
        repo._cache_stats = {'hits': 0, 'misses': 0}

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
    # 2. Données de sortie (INCHANGÉ)
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

        # Récupérer les statistiques du solver
        stats = self.solver.get_solve_statistics() if hasattr(self.solver, 'get_solve_statistics') else {}
        
        return {
            "seed": getattr(self, "seed", None),
            "width": self.width,
            "height": self.height,
            "fill_ratio": round(fill_ratio, 3),
            "cells": cells,
            "words": self.placed_words,
            "statistics": stats,  # Ajout des statistiques
        }