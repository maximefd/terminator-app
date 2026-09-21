# DANS backend/grid_generator.py

import logging
import os
import random
import time

from engine.arrows import clues_for_words
from engine.grid_template import GridTemplate
from engine.must_words import check_must_words
from engine.slot_finder import SlotFinder
from engine.word_repository import WordRepository
from engine.grid_solver import GridSolver
from layout_catalog import DEFAULT_LAYOUTS_DIR, layout_id
from trie_engine import DictionnaireTrie # NÉCESSAIRE

logger = logging.getLogger(__name__)

# Redémarrages : l'essai n°i s'arrête après UNITÉ × luby(i) appels récursifs (réglage mesuré au benchmark).
# Seuil en appels et non en secondes : même seed ⇒ même grille, quelle que soit la machine.
DEFAULT_RESTART_UNIT_CALLS = 300


# Ordres possibles des layouts candidats quand des mots sont imposés
LAYOUT_ORDERS = ("seed", "crossings")


def crossing_load(finder: SlotFinder, length: int) -> float | None:
    """Part minimale de lettres croisées parmi les emplacements de cette longueur (None : aucun).

    Un mot dont chaque lettre doit se croiser est bien plus contraint qu'un mot dont une lettre
    tombe en cul-de-sac. Mesuré sur les cas connus (#73), le critère sépare parfaitement les layouts
    qui accueillent « TAQUINER » de ceux qui le refusent — mais ne distingue rien sur « NEZ ».
    """
    occupe: dict[tuple[int, int], set] = {}
    for slot in finder.slots:
        for i in range(slot['length']):
            x = slot['x'] + (i if slot['direction'] == 'across' else 0)
            y = slot['y'] + (0 if slot['direction'] == 'across' else i)
            occupe.setdefault((x, y), set()).add(slot['direction'])

    charges = []
    for slot in finder.slots:
        if slot['length'] != length:
            continue
        croisees = 0
        for i in range(slot['length']):
            x = slot['x'] + (i if slot['direction'] == 'across' else 0)
            y = slot['y'] + (0 if slot['direction'] == 'across' else i)
            croisees += len(occupe[(x, y)]) > 1
        charges.append(croisees / slot['length'])
    return min(charges) if charges else None


class LayoutNotFoundError(RuntimeError):
    """Aucun layout n'existe pour le format demandé."""


def luby(i: int) -> int:
    """Suite de Luby (1, 1, 2, 1, 1, 2, 4, 1…) : essais courts fréquents, parfois plus longs."""
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    if i == (1 << k) - 1:
        return 1 << (k - 1)
    return luby(i - (1 << (k - 1)) + 1)


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
        restart_unit_calls: int | None = DEFAULT_RESTART_UNIT_CALLS,
        wish_words: list[str] | tuple = (),
        must_words: list[str] | tuple = (),
        min_safe_candidates: int | None = None,
        frequency_mode: str | None = None,
        frequency_band: float | None = None,
        max_candidates: int | None = None,
        max_layouts: int | None = None,
        layout_order: str = "seed",
    ):
        """
        Initialise le générateur.

        Args:
            width (int): Largeur de la grille.
            height (int): Hauteur de la grille.
            valid_words (list[str]): Mots du lexique commun, DÉJÀ FILTRÉS pour la taille de la grille.
            prebuilt_trie (DictionnaireTrie): Un Trie DÉJÀ CONSTRUIT avec les valid_words.
            seed (int, optional): Seed pour la reproductibilité.
            layouts_dir (str, optional): Dossier des layouts (défaut : backend/layouts).
            layout_path (str, optional): Layout précis à utiliser (sinon tirage aléatoire dans le format).
            time_budget_s (float, optional): Temps maximum accordé à la génération (tous essais confondus).
            restart_unit_calls (int, optional): Unité des redémarrages en appels récursifs (None : un seul essai).
            min_safe_candidates (int, optional): Seuil du forward checking (None : réglage du solveur).
            frequency_mode (str, optional): Place de la fréquence dans le tri (None : réglage du solveur).
            frequency_band (float, optional): Largeur des paliers de fréquence (None : réglage du solveur).
            max_candidates (int, optional): Candidats essayés par emplacement (None : réglage du solveur).
            max_layouts (int, optional): Layouts que les redémarrages peuvent essayer (None : tous).
            layout_order (str): Ordre des layouts candidats — « seed » (tirage) ou « crossings »
                (les moins contraints pour les mots imposés d'abord).
            wish_words (list[str], optional): Mots souhaités (dictionnaires personnels et thématiques),
                essayés avant le lexique commun et valides aux croisements même s'ils n'y sont pas (#17).
            must_words (list[str], optional): Mots obligatoires, essayés avant tous les autres.
        """
        self.width = width
        self.height = height
        self.seed = seed
        self.time_budget_s = time_budget_s
        self.restart_unit_calls = restart_unit_calls
        # None : on laisse le solveur appliquer son propre défaut (MIN_SAFE_CANDIDATES)
        self.min_safe_candidates = min_safe_candidates
        self.frequency_mode = frequency_mode
        self.frequency_band = frequency_band
        self.max_candidates = max_candidates
        self.max_layouts = max_layouts
        if layout_order not in LAYOUT_ORDERS:
            raise ValueError(f"ordre de layouts inconnu : {layout_order}")
        self.layout_order = layout_order
        self.attempts: list[dict] = []
        self._timed_out = False
        # Doublons écartés, ordre stable : le placement des mots obligatoires doit rester reproductible
        self.must_words = sorted(set(must_words))
        self.unplaced_must_words = list(self.must_words)
        # Rempli à la construction : mots imposés qui n'entrent dans aucun layout candidat
        self.must_word_problems: list[dict] = []
        # Layout courant parmi ceux retenus ; n'avance que sur une recherche épuisée
        self._layout_index = 0
        # Générateur aléatoire dédié : même seed ⇒ même grille, sans toucher à l'état global
        # (plusieurs générations peuvent coexister dans le même processus).
        self.rng = random.Random(seed)

        self.prebuilt_trie = prebuilt_trie
        self.layouts_dir = layouts_dir or DEFAULT_LAYOUTS_DIR

        # 1. Choisir les layouts candidats, puis écarter ceux qui n'accueillent pas les mots imposés
        candidates = self._layout_candidates(width, height, layout_path)
        if not candidates:
            raise LayoutNotFoundError(f"Aucun layout trouvé pour la taille {width}x{height}.")
        self.must_word_problems, self._layouts = self._usable_layouts(candidates)
        if self.max_layouts is not None:
            self._layouts = self._layouts[:max(1, self.max_layouts)]

        # 2. Préparer le dictionnaire (utilise le Trie et les mots pré-filtrés)
        self.repository = self._create_repository(valid_words, wish_words, must_words)

        # 3. Layout, gabarit et emplacements du premier essai
        self.layout_path, self.template, self.finder = self._layouts[0]

        # 4. Initialiser le solveur du premier essai (même trajectoire qu'avant les redémarrages)
        self.solver = self._new_solver(self.rng, time_budget_s, attempt=1)

        self.placed_words = []

    @property
    def budget_exceeded(self) -> bool:
        """True si la génération s'est arrêtée faute de temps (et non faute de solution)."""
        return self._timed_out

    def _new_solver(self, rng: random.Random, time_budget_s: float | None, attempt: int) -> GridSolver:
        # Le layout ne change QUE lorsque la recherche a été épuisée sur le précédent (voir
        # `generate`). Changer à chaque essai détruit l'intérêt des redémarrages de Luby, qui
        # reposent sur plusieurs trajectoires d'une même géométrie : mesuré, cela faisait perdre
        # 3 points sur un mot imposé au lieu d'en gagner.
        self.layout_path, self.template, self.finder = self._layouts[self._layout_index]
        max_calls = None if self.restart_unit_calls is None else self.restart_unit_calls * luby(attempt)
        threshold = {} if self.min_safe_candidates is None else {"min_safe_candidates": self.min_safe_candidates}
        return GridSolver(self.template, self.repository, self.finder, time_budget_s=time_budget_s,
                          max_recursive_calls=max_calls, rng=rng, must_words=self.must_words,
                          frequency_mode=self.frequency_mode, frequency_band=self.frequency_band,
                          max_candidates=self.max_candidates, **threshold)

    def _layout_candidates(self, width: int, height: int, layout_path: str | None) -> list[str]:
        """Layouts à essayer, dans l'ordre.

        Sans mot imposé, on garde le comportement d'origine : **un** tirage, et la même consommation
        du générateur aléatoire — les grilles produites restent identiques, donc la baseline reste
        comparable. Avec des mots imposés, tous les layouts du format sont candidats, dans un ordre
        dérivé du seed.
        """
        if layout_path:
            return [layout_path]
        format_dir = os.path.join(self.layouts_dir, f"{width}x{height}")
        if not os.path.isdir(format_dir):
            return []
        # Tri pour que le tirage dépende uniquement du seed, pas de l'ordre du système de fichiers
        layouts = sorted(f for f in os.listdir(format_dir) if f.endswith('.txt'))
        if not layouts:
            return []
        if not self.must_words:
            return [os.path.join(format_dir, self.rng.choice(layouts))]
        order = [os.path.join(format_dir, name) for name in layouts]
        self.rng.shuffle(order)
        return order

    def _usable_layouts(self, candidates: list[str]) -> tuple[list[dict], list[tuple]]:
        """Écarte les layouts où un mot imposé n'entre pas, et renvoie (problèmes, layouts retenus).

        La vérification porte sur **chaque** candidat : un mot qui n'entre pas dans un layout du
        format peut très bien entrer dans un autre, et refuser la demande sur le premier venu serait
        faux. Les problèmes renvoyés sont ceux du premier candidat examiné, pour l'explication à
        l'auteur quand aucun layout ne convient.
        """
        first_problems: list[dict] = []
        usable = []
        for path in candidates:
            template = GridTemplate(self.width, self.height, path)
            finder = SlotFinder(template)
            finder.find_all_slots()
            problems = check_must_words(finder.slots, self.must_words)
            if problems:
                first_problems = first_problems or problems
                continue
            usable.append((path, template, finder))
        if usable:
            if self.layout_order == "crossings":
                # Le moins contraint d'abord : somme, sur les mots imposés, de la part minimale de
                # lettres croisées. Le chemin départage, pour rester déterministe.
                usable.sort(key=lambda entree: (
                    sum(crossing_load(entree[2], len(mot)) or 0 for mot in self.must_words), entree[0]))
            return [], usable
        # Aucun layout n'accueille ces mots : on garde le premier pour la forme de la réponse
        template = GridTemplate(self.width, self.height, candidates[0])
        finder = SlotFinder(template)
        finder.find_all_slots()
        return first_problems, [(candidates[0], template, finder)]

    def _create_repository(self, valid_words: list[str], wish_words, must_words) -> WordRepository:
        """
        Crée un repository en RÉUTILISANT le Trie pré-construit (et ses index)
        et les trois pools de mots DÉJÀ FILTRÉS.
        """
        repo = WordRepository.from_pools(self.prebuilt_trie, valid_words, wish_words, must_words)
        logging.info(f"{len(repo.pools)} mots pertinents indexés pour cette grille "
                     f"({len(wish_words)} souhaités, {len(must_words)} obligatoires).")
        return repo

    def generate(self) -> bool:
        """Lance le solveur ; tant qu'un essai atteint son seuil d'appels, en relance un autre dans le budget temps.

        La réussite dépend surtout de la trajectoire aléatoire (profil « vite ou jamais », voir
        benchmarks/README.md) : plusieurs essais courts valent mieux qu'un seul long.
        """
        if self.must_word_problems:
            return False  # aucun layout n'accueille ces mots : inutile de chercher
        start = time.monotonic()
        attempt = 1
        while True:
            success = self.solver.solve()
            self.attempts.append({"attempt": attempt, "stop_reason": self.solver.stop_reason,
                                  "layout": layout_id(self.layout_path),
                                  "metrics": self.solver.metrics.copy()})
            # On garde l'essai qui est allé le plus loin : c'est lui qui explique le mieux l'échec
            if len(self.solver.unplaced_must) < len(self.unplaced_must_words):
                self.unplaced_must_words = list(self.solver.unplaced_must)
            # « Recherche épuisée sur CE layout » ne veut pas dire « épuisée partout » : mesuré
            # (#73), un mot impossible sur un layout est souvent trivial sur un autre du même
            # format. On ne change de géométrie que dans ce cas précis — celui qui terminait la
            # boucle auparavant —, jamais tant que les redémarrages progressent sur la courante.
            epuise = self.solver.stop_reason != "calls"
            change_de_layout = (epuise and self.solver.stop_reason != "time"
                                and self._layout_index + 1 < len(self._layouts))
            if change_de_layout:
                self._layout_index += 1
            if success or (not change_de_layout
                           and (self.restart_unit_calls is None or epuise)):
                # Réussite, redémarrages désactivés, absence de solution ou budget temps dépassé
                self._timed_out = self.solver.stop_reason == "time"
                break
            remaining = None if self.time_budget_s is None else self.time_budget_s - (time.monotonic() - start)
            if self.solver.stop_reason == "time" or (remaining is not None and remaining <= 0):
                # Le temps manque : changer de géométrie n'y changerait rien
                self._timed_out = True
                break
            attempt += 1
            # Nouvelle trajectoire, dérivée du seed : la suite des essais reste reproductible
            self.solver = self._new_solver(random.Random(self.rng.getrandbits(64)), remaining, attempt)

        if success:
            # On trie les mots dans l'ordre de leur slot pour un affichage cohérent
            self.placed_words = sorted(self.solver.placed_words, key=lambda p: p['id'])
            self.unplaced_must_words = []
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
        if self.attempts:
            # Métriques cumulées sur tous les essais ; l'historique et le cache restent ceux du dernier
            totals: dict[str, int] = {}
            for attempt in self.attempts:
                for name, value in attempt["metrics"].items():
                    totals[name] = totals.get(name, 0) + value
            stats = {**stats, "metrics": totals, "attempts": len(self.attempts)}

        # Part des mots de l'auteur (obligatoires et souhaités) parmi les mots placés (ADR 0007)
        wished = sum(1 for word in self.placed_words if word.get("source") in ("must", "wish"))
        wish_ratio = wished / len(self.placed_words) if self.placed_words else 0.0

        return {
            "seed": getattr(self, "seed", None),
            "width": self.width,
            "height": self.height,
            "layout": layout_id(self.layout_path),
            "fill_ratio": round(fill_ratio, 3),
            "wish_ratio": round(wish_ratio, 3),
            "must_words": self.must_words,
            "cells": cells,
            "words": self.placed_words,
            # Où s'écrit la définition de chaque mot et par où part sa flèche (#26)
            "clues": clues_for_words(self.template, self.placed_words),
            "statistics": stats,  # Ajout des statistiques
        }
