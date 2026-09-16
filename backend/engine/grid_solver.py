# DANS backend/engine/grid_solver.py

import logging
import random
import time

from .grid_template import GridTemplate
from .slot_finder import SlotFinder
from .word_repository import WordRepository

logger = logging.getLogger(__name__)


class SolverBudgetExceeded(Exception):
    """Levée quand le solveur dépasse son budget de temps (`reason="time"`) ou d'appels récursifs (`"calls"`)."""

    def __init__(self, message: str, reason: str):
        super().__init__(message)
        self.reason = reason


class GridSolver:

    # --- CONSTANTE ---
    MAX_CANDIDATES_PER_SLOT = 100  # Réduit pour accélérer le backtracking
    MIN_SAFE_CANDIDATES = 3  # Nombre minimum de candidats pour considérer un slot "sûr" (Forward Checking strict)
    # ---------------------------------------------

    LETTER_SCORES = {
        # ... (scores inchangés)
        'A': 9, 'B': 2, 'C': 2, 'D': 3, 'E': 13, 'F': 1, 'G': 1, 'H': 1,
        'I': 8, 'J': 1, 'K': 0, 'L': 6, 'M': 3, 'N': 7, 'O': 6, 'P': 3,
        'Q': 1, 'R': 8, 'S': 8, 'T': 7, 'U': 6, 'V': 2, 'W': 0, 'X': 0,
        'Y': 0, 'Z': 1
    }

    def __init__(
        self,
        template: GridTemplate,
        repository: WordRepository,
        finder: SlotFinder,
        time_budget_s: float | None = None,
        max_recursive_calls: int | None = None,
        min_safe_candidates: int = MIN_SAFE_CANDIDATES,
        rng: random.Random | None = None,
    ):
        # Générateur aléatoire propre à cette résolution : reproductible et sans état global partagé
        self.rng = rng or random.Random()
        # INVARIANT : le forward checking doit exiger au moins 2 candidats.
        # Un slot entièrement complété par ses croisements a au plus 1 candidat : avec un
        # seuil >= 2, ce placement est rejeté, ce qui garantit que chaque slot est rempli
        # explicitement (mot validé, consommé et présent dans placed_words).
        if min_safe_candidates < 2:
            raise ValueError("min_safe_candidates doit être >= 2 (voir l'invariant ci-dessus).")
        self.min_safe_candidates = min_safe_candidates
        self.time_budget_s = time_budget_s
        self.max_recursive_calls = max_recursive_calls
        self.budget_exceeded = False
        self.stop_reason = None  # "time" ou "calls" si la résolution a été interrompue
        # Mots retirés du dépôt par la branche en cours : rendus si la résolution est interrompue
        self._consumed: list[tuple[str, int]] = []

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
        
        # NOUVEAU : Système de nogoods pour éviter les boucles
        # Format: {slot_id: {pattern1, pattern2, ...}}
        # Enregistre les patterns qui ont échoué pour chaque slot
        self.nogoods = {}
        
        # OPTIMISATION : Pré-calculer les intersections entre slots
        self._precompute_intersections()
        
        # MÉTRIQUES de performance
        self.metrics = {
            'candidates_tested': 0,      # Nombre total de mots testés
            'fc_skips': 0,               # Combien de mots éliminés par FC
            'fc_checks': 0,              # Combien de fois FC a été appelé
            'recursive_calls': 0,        # Nombre d'appels récursifs
            'backtracks': 0,             # Nombre de backtracks
            'cache_hits': 0,             # Nombre de cache hits
            'cache_misses': 0,           # Nombre de cache misses
        }

    def solve(self) -> bool:
        """Point d'entrée principal pour lancer la résolution (démarre la récursion MRV)."""
        logging.info("Début de la résolution de la grille (Heuristique MRV)...")
        self.start_time = time.time()
        self.budget_exceeded = False

        try:
            return self._solve_recursive()
        except SolverBudgetExceeded as e:
            # Un seuil d'appels atteint est un redémarrage prévu, pas une anomalie
            (logging.warning if e.reason == "time" else logging.info)(f"Résolution interrompue : {e}")
            self.budget_exceeded = True
            self.stop_reason = e.reason
            self.placed_words = []
            # Le dépôt redevient intact : un nouvel essai peut repartir de zéro avec les mêmes mots
            for word, length in reversed(self._consumed):
                self.repository.add_word_to_available(word, length)
            self._consumed.clear()
            return False
        finally:
            # Afficher les métriques dans TOUS les cas (succès, échec, timeout)
            self._print_metrics()
    
    def _choose_next_slot(self) -> dict | None:
        """
        Choisit dynamiquement le prochain slot à traiter avec l'heuristique MRV AMÉLIORÉE.
        
        Score = nb_candidats / (1 + nb_intersections)
        
        Logique :
        - Moins il y a de candidats, plus le slot est contraint (prioritaire)
        - Plus il y a d'intersections, plus le slot contraint les autres (prioritaire)
        
        On choisit le slot avec le SCORE LE PLUS BAS.
        """
        best_slot = None
        best_score = float('inf')

        for slot in self.slots:
            # Ignorer les slots déjà remplis
            if slot.get('is_filled', False):
                continue
                
            pattern = self._get_slot_pattern(slot)
            nb_unknowns = pattern.count('?')
            
            # Si complètement rempli par croisements, ignorer
            if nb_unknowns == 0:
                continue

            # Nombre de candidats pour ce pattern (compté sans construire la liste)
            nb_candidates = self.repository.count_candidates(pattern)
            
            # Si aucun candidat, ce slot est un dead-end immédiat
            # (sera géré par _solve_recursive qui fera backtrack)
            if nb_candidates == 0:
                # Slot impossible : on le choisit pour déclencher le backtrack immédiatement
                return slot
            
            # Compter le nombre d'intersections de ce slot
            nb_intersections = 0
            for pos_idx in range(slot['length']):
                if slot['direction'] == 'across':
                    x = slot['x'] + pos_idx
                    y = slot['y']
                else:
                    x = slot['x']
                    y = slot['y'] + pos_idx
                
                # Vérifier s'il y a un slot qui croise à cette position
                if self._find_intersecting_slot_fast(x, y, slot['direction']):
                    nb_intersections += 1
            
            # Calculer le score : on veut MINIMISER ce score
            # Plus de candidats = mauvais (moins contraint)
            # Plus d'intersections = bon (plus contraignant pour les autres)
            score = nb_candidates / (1 + nb_intersections)
            
            # Choisir le slot avec le score le plus bas
            if score < best_score:
                best_score = score
                best_slot = slot
        
        return best_slot
        
    def _solve_recursive(self) -> bool:
        """
        Implémente l'algorithme de backtracking. Utilise _choose_next_slot() (MRV).
        """
        self.metrics['recursive_calls'] += 1
        self._check_budget()

        # 1. Choix dynamique du slot le plus contraint
        slot = self._choose_next_slot()
        
        # 2. Condition d'arrêt (Succès : tous les slots sont remplis)
        if not slot:
            logging.info("SUCCÈS : Tous les slots ont été remplis.")
            return True

        pattern = self._get_slot_pattern(slot)
        slot_id = slot.get('id', id(slot))
        
        logging.debug(f"[Slot {slot.get('id', '?')}] {slot['direction']}, L={slot['length']}, Pattern='{pattern}'")

        # NOUVEAU : Vérifier si ce pattern est un nogood connu
        if self._is_nogood_pattern(slot_id, pattern):
            logging.debug(f"  Pattern '{pattern}' est un nogood connu, backtrack immédiat !")
            return False

        # 3. Récupération des candidats possibles
        candidates = self.repository.get_candidates(pattern)
        if not candidates:
            logging.debug(f"  Aucun candidat pour ce slot, backtrack !")
            # NOUVEAU : Enregistrer ce pattern comme nogood (aucun mot n'existe dans le dico)
            self._record_nogood(slot_id, pattern)
            return False
        
        # Tri des candidats par score (heuristique) - les meilleurs en premier
        scored_candidates = [(self._score_word(w), w) for w in candidates]
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Limiter le nombre de candidats pour accélérer le backtracking
        scored_candidates = scored_candidates[:self.MAX_CANDIDATES_PER_SLOT]
        
        # OPTIMISATION : Ajouter un peu d'aléatoire uniquement dans le top 20%
        # pour éviter de toujours essayer les mêmes mots en premier
        top_20_percent = max(1, len(scored_candidates) // 5)
        if top_20_percent > 1:
            top_candidates = scored_candidates[:top_20_percent]
            self.rng.shuffle(top_candidates)
            scored_candidates = top_candidates + scored_candidates[top_20_percent:]

        logging.debug(f"   {len(scored_candidates)} candidats (limité à {self.MAX_CANDIDATES_PER_SLOT}, top 20% aléatoire).")

        # 4. Boucle de test des candidats
        for i, (score, word) in enumerate(scored_candidates):
            self.metrics['candidates_tested'] += 1
            
            logging.debug(f"    Tentative {i+1}/{len(scored_candidates)} : mot '{word}' (Score: {score})")

            # Place le mot temporairement et sauvegarde l'état pour le revert
            original_state = self._place_word_on_grid(word, slot)

            # NOUVEAU : Vérifier que ce mot ne crée pas de nogoods pour les slots intersectés
            if self._would_create_nogoods(word, slot, original_state):
                logging.debug(f"      -> Mot '{word}' créerait des nogoods connus, skip.")
                self._revert_grid_state(original_state)
                continue

            # --- MODIFICATION 1 : On passe original_state à la validation ---
            if not self._is_placement_valid(word, slot, original_state):
                self._revert_grid_state(original_state)
                continue
            
            # FORWARD CHECKING : Vérifier que les slots intersectés auront encore des candidats
            self.metrics['fc_checks'] += 1
            if not self._forward_check(word, slot, original_state):
                self.metrics['fc_skips'] += 1
                logging.debug(f"      -> Mot '{word}' échoue au FC (dead-end), skip.")
                self._revert_grid_state(original_state)
                continue
            
            # Si on arrive ici, le mot est valide ET passe le forward checking
            # --- CONSOMMATION ---
            slot['is_filled'] = True # Marque le slot comme rempli
            self.repository.remove_word_from_available(word, slot['length'])
            self._consumed.append((word, slot['length']))
            logging.debug(f"  → Place '{word}'")

            if self._solve_recursive(): # Appel récursif SANS INDEX
                # SUCCES
                self.placed_words.insert(0, {
                    "text": word, "x": slot['x'], "y": slot['y'],
                    "direction": slot['direction'], "id": slot['id'],
                    "score": score  # Ajouter le score pour l'historique
                })
                return True
            else:
                # ÉCHEC RÉCURSIF (Backtrack)
                self.metrics['backtracks'] += 1
                # CRITIQUE : Effacer les nogoods des slots intersectés car le contexte change
                self._invalidate_dependent_nogoods(slot)
                
                # Annule la consommation du mot et marque le slot comme vide
                self.repository.add_word_to_available(word, slot['length'])
                self._consumed.pop()
                slot['is_filled'] = False
                logging.debug(f"      <- Retour arrière (Backtrack) pour '{word}'.")
                
                # --- REVERT DE LA GRILLE ---
                self._revert_grid_state(original_state)

        # 5. Échec de tous les candidats (aligné avec la boucle for)
        logging.debug(f"  ÉCHEC : Tous les candidats ont échoué pour ce slot.")
        # NE PAS enregistrer comme nogood ici : l'échec est contextuel, pas absolu
        # Le pattern pourrait fonctionner avec un autre contexte (autres mots placés)
        return False

    def _check_budget(self) -> None:
        """Interrompt la résolution si le budget de temps ou d'appels est dépassé."""
        if self.time_budget_s is not None and time.time() - self.start_time > self.time_budget_s:
            raise SolverBudgetExceeded(f"budget de temps dépassé ({self.time_budget_s}s)", "time")
        if self.max_recursive_calls is not None and self.metrics['recursive_calls'] > self.max_recursive_calls:
            raise SolverBudgetExceeded(f"budget d'appels récursifs dépassé ({self.max_recursive_calls})", "calls")

    def _check_grid_integrity(self):
        """
        Vérifie si des lettres orphelines (non associées à un slot non rempli) existent.
        ATTENTION : Très coûteux en performance, à utiliser pour le débogage seulement.
        """
        
        active_slots_indices = set()
        for slot in self.slots:
            if not slot.get('is_filled', False):
                active_slots_indices.add(slot.get('id', self.slots.index(slot))) 

        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                
                if cell not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, '', ' '):
                    # Logique de vérification (non implémentée)
                    pass
        
    def _get_slot_pattern(self, slot: dict) -> str:
        """
        Génère le motif du slot (ex : 'A??E?').
        '?' représente une case vide.
        """
        pattern = []
        placeholder = '?'

        logging.debug(f"   Génération du motif pour slot {slot.get('id', 'N/A')} ({slot['direction']}, L={slot['length']})")

        for i in range(slot['length']):
            if slot['direction'] == 'across':
                x = slot['x'] + i
                y = slot['y']
            else:  # down
                x = slot['x']
                y = slot['y'] + i

            if y >= self.height or x >= self.width:
                logging.warning(f"    Coordonnées invalides ({x},{y}) hors grille (max {self.width-1},{self.height-1})")
                continue
                
            char = self.grid[y][x]

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
        x, y, direction = slot['x'], slot['y'], slot['direction']

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

    def _is_placement_valid(self, word: str, slot: dict, original_state: list[tuple[int, int, str]]) -> bool:
        """
        Vérifie les mots créés dans l'autre sens par les lettres qui ont réellement changé.

        On ne vérifie qu'un mot **terminé** : une suite de lettres bordée des deux côtés par une
        case définition ou par le bord de la grille. Une suite encore ouverte (« AB » au milieu
        d'un emplacement de 5 cases) n'est qu'un mot en cours d'écriture : exiger qu'elle existe
        au dictionnaire rejetait des placements parfaitement valides et empêchait toute grille de
        plus d'une trentaine de mots d'aboutir. Le forward checking garantit par ailleurs qu'un
        emplacement encore ouvert conserve des candidats.
        """
        for char, (px, py, old_char) in zip(word, original_state):
            # Si la lettre n'a pas changé, le mot croisé l'a déjà été
            if old_char == char:
                continue

            if slot['direction'] == 'across':
                fragment = self._get_vertical_fragment(px, py)
                finished = self._is_run_finished(px, py, 'down')
            else:
                fragment = self._get_horizontal_fragment(px, py)
                finished = self._is_run_finished(px, py, 'across')

            if finished and len(fragment) > 1 and not self.repository.is_word_valid(fragment):
                logging.debug(f"      -> REJETÉ : Le mot '{word}' crée un mot invalide : '{fragment}'")
                return False

        return True

    def _is_run_finished(self, x: int, y: int, direction: str) -> bool:
        """La suite de lettres qui contient (x, y) est-elle terminée dans cette direction ?

        Terminée = bordée des deux côtés par une case définition ou par le bord de la grille.
        Si une case lettre vide la prolonge, le mot s'écrit encore.
        """
        empty = (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', '', None)
        dx, dy = (0, 1) if direction == 'down' else (1, 0)

        for step in (1, -1):
            cx, cy = x, y
            while (0 <= cx + dx * step < self.width and 0 <= cy + dy * step < self.height
                   and self.grid[cy + dy * step][cx + dx * step] not in empty):
                cx, cy = cx + dx * step, cy + dy * step
            nx, ny = cx + dx * step, cy + dy * step
            if 0 <= nx < self.width and 0 <= ny < self.height and self.grid[ny][nx] == self.template.EMPTY_CELL:
                return False  # une case vide prolonge la suite : le mot n'est pas fini
        return True

    def _get_vertical_fragment(self, x: int, y: int) -> str:
        """Construit le mot vertical complet passant par (x,y)."""
        fragment = ""
        cy = y
        # Remonte pour trouver le début du mot
        while cy >= 0 and self.grid[cy][x] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            cy -= 1
        cy += 1 # Revient à la première lettre
        
        # Descend pour construire le mot
        while cy < self.height and self.grid[cy][x] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            fragment += self.grid[cy][x]
            cy += 1
        return fragment

    def _get_horizontal_fragment(self, x: int, y: int) -> str:
        """Construit le mot horizontal complet passant par (x,y)."""
        fragment = ""
        cx = x
        # Recule pour trouver le début du mot
        while cx >= 0 and self.grid[y][cx] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            cx -= 1
        cx += 1 # Revient à la première lettre
        
        # Avance pour construire le mot
        while cx < self.width and self.grid[y][cx] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            fragment += self.grid[y][cx]
            cx += 1
        return fragment
    
    def _score_word(self, word: str) -> int:
        """Calcule le 'score d'utilité' d'un mot."""
        return sum(self.LETTER_SCORES.get(char, 0) for char in word)
    
    # ===================================================================
    # NOUVEAU : Système de Nogoods pour éviter les boucles
    # ===================================================================
    
    def _record_nogood(self, slot_id, pattern: str):
        """
        Enregistre un pattern qui a échoué pour un slot donné.
        Ce pattern devient un 'nogood' qu'on évitera de recréer.
        """
        if slot_id not in self.nogoods:
            self.nogoods[slot_id] = set()
        self.nogoods[slot_id].add(pattern)
        logging.debug(f"  [NOGOOD] Enregistré pour slot {slot_id}: '{pattern}'")
    
    def _is_nogood_pattern(self, slot_id, pattern: str) -> bool:
        """
        Vérifie si un pattern est un nogood connu pour ce slot.
        """
        return slot_id in self.nogoods and pattern in self.nogoods[slot_id]
    
    def _clear_nogoods_for_slot(self, slot_id):
        """
        Nettoie les nogoods d'un slot.
        """
        if slot_id in self.nogoods:
            del self.nogoods[slot_id]
    
    def _invalidate_dependent_nogoods(self, slot: dict):
        """
        Efface les nogoods de tous les slots qui intersectent avec ce slot.
        Appelé lors du backtrack car les nogoods sont contextuels.
        """
        slots_to_clear = set()
        
        # Trouver tous les slots qui intersectent avec ce slot
        for pos_idx in range(slot['length']):
            if slot['direction'] == 'across':
                x = slot['x'] + pos_idx
                y = slot['y']
            else:
                x = slot['x']
                y = slot['y'] + pos_idx
            
            # Trouver le slot intersecté (version optimisée)
            intersected = self._find_intersecting_slot_fast(x, y, slot['direction'])
            if intersected:
                intersected_id = intersected.get('id', id(intersected))
                slots_to_clear.add(intersected_id)
        
        # Effacer les nogoods de tous les slots intersectés
        for slot_id in slots_to_clear:
            if slot_id in self.nogoods:
                logging.debug(f"  [NOGOOD] Invalidation des nogoods du slot {slot_id} (backtrack)")
                del self.nogoods[slot_id]
    
    def _would_create_nogoods(self, word: str, slot: dict, original_state: list[tuple[int, int, str]]) -> bool:
        """
        Vérifie si placer ce mot créerait un pattern nogood dans un slot intersecté.
        C'est ici qu'on implémente la logique clé : éviter de placer une lettre
        qui créerait un pattern déjà connu comme impossible.
        """
        # Pour chaque lettre du mot placé, on vérifie les slots intersectés
        for i, (char, (px, py, old_char)) in enumerate(zip(word, original_state)):
            # Si la lettre n'a pas changé, pas de problème
            if old_char == char:
                continue
            
            # Trouver le slot intersecté à cette position (version optimisée)
            intersected_slot = self._find_intersecting_slot_fast(px, py, slot['direction'])
            if not intersected_slot:
                continue
            
            # Ne vérifier que les slots non encore remplis
            if intersected_slot.get('is_filled', False):
                continue
            
            # Calculer le pattern que ce placement créerait pour le slot intersecté
            future_pattern = self._calculate_future_pattern(intersected_slot)
            intersected_slot_id = intersected_slot.get('id', id(intersected_slot))
            
            # Si ce pattern est un nogood connu, rejeter ce mot
            if self._is_nogood_pattern(intersected_slot_id, future_pattern):
                logging.debug(f"        Placer '{word}' créerait nogood '{future_pattern}' pour slot {intersected_slot_id}")
                return True
        
        return False
    
    def _find_intersecting_slot(self, x: int, y: int, current_direction: str) -> dict | None:
        """
        Trouve un slot qui passe par la position (x, y) dans la direction opposée.
        """
        opposite_direction = 'down' if current_direction == 'across' else 'across'
        
        for slot in self.slots:
            if slot['direction'] != opposite_direction:
                continue
            
            # Vérifier si (x, y) est dans ce slot
            if slot['direction'] == 'across':
                if slot['y'] == y and slot['x'] <= x < slot['x'] + slot['length']:
                    return slot
            else:  # down
                if slot['x'] == x and slot['y'] <= y < slot['y'] + slot['length']:
                    return slot
        
        return None
    
    def _calculate_future_pattern(self, slot: dict) -> str:
        """
        Calcule le pattern actuel d'un slot (ce qu'il serait maintenant,
        avec les lettres déjà placées sur la grille).
        """
        return self._get_slot_pattern(slot)
    
    # ===================================================================
    # OPTIMISATION : Pré-calcul des intersections
    # ===================================================================
    
    def _precompute_intersections(self):
        """
        Pré-calcule toutes les intersections entre slots pour éviter
        de parcourir tous les slots à chaque recherche.
        
        Format: {
            (x, y, 'across'): slot_down_qui_croise,
            (x, y, 'down'): slot_across_qui_croise
        }
        """
        self.intersection_map = {}  # (x, y, direction) -> slot intersecté
        
        # Pour chaque cellule et direction, trouver quel slot l'occupe
        for slot in self.slots:
            for pos_idx in range(slot['length']):
                if slot['direction'] == 'across':
                    x = slot['x'] + pos_idx
                    y = slot['y']
                else:
                    x = slot['x']
                    y = slot['y'] + pos_idx
                
                # Enregistrer ce slot pour cette cellule et direction
                key = (x, y, slot['direction'])
                self.intersection_map[key] = slot
        
        logging.debug(f"Pré-calcul de {len(self.intersection_map)} positions de slots")
    
    def _find_intersecting_slot_fast(self, x: int, y: int, current_direction: str) -> dict | None:
        """
        Version optimisée de _find_intersecting_slot utilisant le pré-calcul.
        Trouve un slot qui passe par la position (x, y) dans la direction opposée.
        """
        opposite_direction = 'down' if current_direction == 'across' else 'across'
        key = (x, y, opposite_direction)
        return self.intersection_map.get(key)
    
    # ===================================================================
    # FORWARD CHECKING : Détection précoce des branches mortes
    # ===================================================================
    
    def _forward_check(self, word: str, slot: dict, original_state: list[tuple[int, int, str]]) -> bool:
        """
        Forward Checking STRICT : Vérifie que placer ce mot ne crée pas de dead-end.
        Pour chaque slot intersecté non rempli, vérifie qu'il aura encore
        au moins MIN_SAFE_CANDIDATES candidats valides après le placement.
        
        Logique : Exiger au moins 5 candidats (au lieu de 1) donne une marge de sécurité
        et évite d'explorer des branches qui mènent presque toujours à des impasses.
        """
        # Collecter tous les slots intersectés uniques
        intersected_slots = set()
        
        for i, (char, (px, py, old_char)) in enumerate(zip(word, original_state)):
            # Trouver le slot intersecté
            intersected_slot = self._find_intersecting_slot_fast(px, py, slot['direction'])
            
            if not intersected_slot:
                continue
            
            # Ignorer les slots déjà remplis
            if intersected_slot.get('is_filled', False):
                continue
            
            # Ajouter à la liste des slots à vérifier
            slot_id = intersected_slot.get('id', id(intersected_slot))
            intersected_slots.add(slot_id)
        
        # Pour chaque slot intersecté, vérifier qu'il a encore des candidats
        for slot_id in intersected_slots:
            # Retrouver le slot complet
            intersected_slot = next((s for s in self.slots if s.get('id', id(s)) == slot_id), None)
            
            if not intersected_slot:
                continue
            
            # Calculer le pattern que ce slot aurait après le placement
            future_pattern = self._get_slot_pattern(intersected_slot)
            
            # Vérifier s'il reste assez de candidats pour ce pattern
            nb_candidates = self.repository.count_candidates(future_pattern)
            
            if nb_candidates < self.min_safe_candidates:
                # DEAD-END détecté : ce placement laisse trop peu de candidats
                logging.debug(f"        FC STRICT: Slot {slot_id} n'aurait que {nb_candidates} candidat(s) (min: {self.min_safe_candidates}, pattern: '{future_pattern}')")
                return False
        
        # Tous les slots intersectés ont encore des candidats
        return True
    
    def _print_metrics(self):
        """
        Affiche les métriques de performance pour diagnostiquer l'efficacité des optimisations.
        """
        m = self.metrics
        cache_stats = getattr(self.repository, '_cache_stats', {'hits': 0, 'misses': 0})
        
        logging.info("\n" + "="*60)
        logging.info("MÉTRIQUES DE PERFORMANCE")
        logging.info("="*60)
        logging.info(f"Appels récursifs      : {m['recursive_calls']}")
        logging.info(f"Candidats testés       : {m['candidates_tested']}")
        logging.info(f"Backtracks             : {m['backtracks']}")
        logging.info(f"")
        logging.info(f"FORWARD CHECKING:")
        logging.info(f"  - Vérifications FC    : {m['fc_checks']}")
        logging.info(f"  - Mots éliminés (FC)  : {m['fc_skips']}")
        if m['fc_checks'] > 0:
            fc_efficiency = (m['fc_skips'] / m['fc_checks']) * 100
            logging.info(f"  - Efficacité FC       : {fc_efficiency:.1f}% (mots éliminés)")
        logging.info(f"")
        logging.info(f"CACHE get_candidates:")
        total_cache = cache_stats['hits'] + cache_stats['misses']
        if total_cache > 0:
            hit_rate = (cache_stats['hits'] / total_cache) * 100
            logging.info(f"  - Hits                : {cache_stats['hits']}")
            logging.info(f"  - Misses              : {cache_stats['misses']}")
            logging.info(f"  - Taux de hit         : {hit_rate:.1f}%")
        else:
            logging.info(f"  - Aucune donnée de cache")
        logging.info("="*60 + "\n")
    
    def get_solve_statistics(self) -> dict:
        """
        Retourne un dictionnaire avec toutes les statistiques de résolution
        pour le rapport HTML.
        """
        cache_stats = getattr(self.repository, '_cache_stats', {'hits': 0, 'misses': 0})
        
        # Construire l'historique à partir des mots finalement placés
        # (dans l'ordre inverse car placed_words est construit avec insert(0))
        final_placement_history = []
        for idx, word_info in enumerate(reversed(self.placed_words)):
            final_placement_history.append({
                'word': word_info.get('text', ''),
                'slot_id': word_info.get('id', '?'),
                'direction': word_info.get('direction', ''),
                'length': len(word_info.get('text', '')),
                'score': word_info.get('score', 0),
                'order': idx + 1
            })
        
        return {
            'metrics': self.metrics.copy(),
            'cache_stats': cache_stats.copy(),
            'placement_history': final_placement_history,
        }