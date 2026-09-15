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

# Dossier des layouts, résolu depuis ce fichier (indépendant du répertoire courant)
DEFAULT_LAYOUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layouts")


class LayoutNotFoundError(RuntimeError):
    """Aucun layout n'existe pour le format demandé."""


def layout_id(layout_path: str) -> str:
    """Identifiant d'un layout, déduit de son chemin : `<L>x<H>/001.txt` → `<L>x<H>-001`."""
    format_name = os.path.basename(os.path.dirname(layout_path))
    return f"{format_name}-{os.path.splitext(os.path.basename(layout_path))[0]}"


def available_formats(layouts_dir: str | None = None) -> list[dict]:
    """Liste les formats disponibles (ex: [{'width': 6, 'height': 7, 'layouts': 1}]), triés."""
    layouts_dir = layouts_dir or DEFAULT_LAYOUTS_DIR
    formats = []
    if not os.path.isdir(layouts_dir):
        return formats
    for name in os.listdir(layouts_dir):
        path = os.path.join(layouts_dir, name)
        width, sep, height = name.partition("x")
        if not (os.path.isdir(path) and sep and width.isdigit() and height.isdigit()):
            continue
        layouts = [f for f in os.listdir(path) if f.endswith(".txt")]
        if layouts:
            formats.append({"width": int(width), "height": int(height), "layouts": len(layouts)})
    return sorted(formats, key=lambda f: (f["width"] * f["height"], f["width"]))


class GridGenerator:
    """
    Chef d'orchestre qui pilote la création d'une grille de A à Z.
    """

    def __init__(
        self,
        width: int,
        height: int,
        valid_words: list[str],
        prebuilt_trie: DictionnaireTrie,
        seed: int | float | None = None,
        layouts_dir: str | None = None,
        layout_path: str | None = None,
        time_budget_s: float | None = None,
    ):
        """
        Initialise le générateur.

        Args:
            width (int): Largeur de la grille.
            height (int): Hauteur de la grille.
            valid_words (list[str]): Liste de mots DÉJÀ FILTRÉS pour la taille de la grille.
            prebuilt_trie (DictionnaireTrie): Un Trie DÉJÀ CONSTRUIT avec les valid_words.
            seed (int, optional): Seed pour la reproductibilité.
            layouts_dir (str, optional): Dossier des layouts (défaut : backend/layouts).
            layout_path (str, optional): Layout précis à utiliser (sinon tirage aléatoire dans le format).
            time_budget_s (float, optional): Temps maximum accordé au solveur.
        """
        self.width = width
        self.height = height
        self.seed = seed
        # Générateur aléatoire dédié : même seed ⇒ même grille, sans toucher à l'état global
        # (plusieurs générations peuvent coexister dans le même processus).
        self.rng = random.Random(seed)

        self.prebuilt_trie = prebuilt_trie
        self.layouts_dir = layouts_dir or DEFAULT_LAYOUTS_DIR

        # 1. Charger le layout
        self.layout_path = layout_path or self._find_layout_path(width, height)
        if not self.layout_path:
            raise LayoutNotFoundError(f"Aucun layout trouvé pour la taille {width}x{height}.")
        self.template = GridTemplate(width, height, self.layout_path)

        # 2. Préparer le dictionnaire (utilise le Trie et les mots pré-filtrés)
        self.repository = self._create_repository(valid_words)

        # 3. Trouver les slots
        finder = SlotFinder(self.template)
        finder.find_all_slots()

        # 4. Initialiser le solveur
        self.solver = GridSolver(self.template, self.repository, finder, time_budget_s=time_budget_s, rng=self.rng)

        self.placed_words = []

    @property
    def budget_exceeded(self) -> bool:
        return self.solver.budget_exceeded

    def _find_layout_path(self, width: int, height: int) -> str | None:
        """Trouve un fichier de layout au hasard pour la taille donnée."""
        format_dir = os.path.join(self.layouts_dir, f"{width}x{height}")
        if not os.path.isdir(format_dir):
            return None
        # Tri pour que le tirage dépende uniquement du seed, pas de l'ordre du système de fichiers
        layouts = sorted(f for f in os.listdir(format_dir) if f.endswith('.txt'))
        return os.path.join(format_dir, self.rng.choice(layouts)) if layouts else None

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

        # Récupérer les statistiques du solver
        stats = self.solver.get_solve_statistics() if hasattr(self.solver, 'get_solve_statistics') else {}

        return {
            "seed": getattr(self, "seed", None),
            "width": self.width,
            "height": self.height,
            "layout": layout_id(self.layout_path),
            "fill_ratio": round(fill_ratio, 3),
            "cells": cells,
            "words": self.placed_words,
            "statistics": stats,  # Ajout des statistiques
        }
