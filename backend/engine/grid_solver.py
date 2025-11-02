# DANS backend/engine/grid_solver.py

import logging
import random
import time

from .grid_template import GridTemplate
from .slot_finder import SlotFinder
from .word_repository import WordRepository

logger = logging.getLogger(__name__)

class GridSolver:

    # --- CONSTANTES ---
    MAX_CANDIDATES_PER_SLOT = 100 # Réduit pour accélérer le backtracking
    MIN_SAFE_CANDIDATES = 3 # Nombre minimum de candidats pour considérer un slot "sûr" (Forward Checking strict)
    # NOUVELLE CONSTANTE : Timeout adaptatif par slot
    MAX_ATTEMPTS_PER_SLOT = 30 # Nombre max de tentatives avant d'abandonner un slot problématique (À AJUSTER)
    # ---------------------------------------------

    LETTER_SCORES = {
        'A': 9, 'B': 2, 'C': 2, 'D': 3, 'E': 13, 'F': 1, 'G': 1, 'H': 1,
        'I': 8, 'J': 1, 'K': 0, 'L': 6, 'M': 3, 'N': 7, 'O': 6, 'P': 3,
        'Q': 1, 'R': 8, 'S': 8, 'T': 7, 'U': 6, 'V': 2, 'W': 0, 'X': 0,
        'Y': 0, 'Z': 1
    }

    def __init__(self, template: GridTemplate, repository: WordRepository, finder: SlotFinder):
        self.template = template
        self.repository = repository
        self.slots = []
        for slot in finder.slots:
            new_slot = slot.copy()
            new_slot['is_filled'] = False
            self.slots.append(new_slot)
        self.grid = [row[:] for row in template.grid]
        self.height = template.height
        self.width = template.width
        self.placed_words = []
        self.nogoods = {}
        # Pré-calcul des intersections (suppose que _precompute_intersections est appelé)
        self._precompute_intersections()
        # Initialisation des métriques
        self.metrics = {
            'candidates_tested': 0, 'fc_skips': 0, 'fc_checks': 0,
            'recursive_calls': 0, 'backtracks': 0, 'cache_hits': 0,
            'cache_misses': 0,
            # NOUVELLE MÉTRIQUE pour le timeout adaptatif
            'slot_timeouts': 0
        }

    def solve(self) -> bool:
        """Point d'entrée principal pour lancer la résolution."""
        logging.info("Début de la résolution de la grille (Heuristique MRV)...")
        self.start_time = time.time()
        self.nogoods = {} # Réinitialiser les nogoods
        # NOUVEAU : Initialiser le dictionnaire de tentatives pour cet appel à solve()
        slot_attempts = {}

        try:
            # NOUVEAU : Passer le dictionnaire slot_attempts initial
            result = self._solve_recursive(slot_attempts)
            return result
        finally:
            self._print_metrics() # Afficher les métriques même en cas d'échec/timeout global

    def _choose_next_slot(self) -> dict | None:
        """
        Choisit dynamiquement le prochain slot à traiter (heuristique MRV améliorée).
        """
        best_slot = None
        best_score = float('inf') # On cherche le score le plus bas (le plus contraint)

        for slot in self.slots:
            # Ignorer les slots déjà remplis
            if slot.get('is_filled', False):
                continue

            pattern = self._get_slot_pattern(slot)
            nb_unknowns = pattern.count('?')

            # Si rempli par croisement, ignorer
            if nb_unknowns == 0:
                continue

            # Obtenir le nombre de candidats (utilise le cache du repo)
            candidates = self.repository.get_candidates(pattern)
            nb_candidates = len(candidates) if candidates else 0

            # Si aucun candidat, c'est le slot le plus contraint (priorité absolue)
            if nb_candidates == 0:
                return slot

            # Calculer le nombre d'intersections pour ce slot
            nb_intersections = 0
            for pos_idx in range(slot['length']):
                if slot['direction'] == 'across':
                    x, y = slot['x'] + pos_idx, slot['y']
                else:
                    x, y = slot['x'], slot['y'] + pos_idx
                # Utiliser la version rapide pré-calculée
                if self._find_intersecting_slot_fast(x, y, slot['direction']):
                    nb_intersections += 1

            # Calculer le score (moins = mieux)
            # Favorise les slots avec peu de candidats et beaucoup d'intersections
            score = nb_candidates / (1 + nb_intersections)

            # Mettre à jour le meilleur slot trouvé
            if score < best_score:
                best_score = score
                best_slot = slot

        return best_slot

    # NOUVEAU : La signature accepte slot_attempts
    def _solve_recursive(self, slot_attempts: dict) -> bool:
        """
        Implémente l'algorithme de backtracking avec Nogoods, FC et Timeout adaptatif.
        """
        self.metrics['recursive_calls'] += 1
        slot = self._choose_next_slot()

        # Condition d'arrêt : succès
        if not slot:
            logging.info("SUCCÈS : Tous les slots ont été remplis.")
            return True

        # --- GESTION DU TIMEOUT ADAPTATIF PAR SLOT (Début) ---
        slot_id = slot.get('id', id(slot))
        # Initialiser le compteur si c'est la première fois qu'on visite ce slot DANS CETTE BRANCHE
        if slot_id not in slot_attempts:
            slot_attempts[slot_id] = 0

        # Vérifier si on a DÉJÀ dépassé la limite AVANT de chercher les candidats
        if slot_attempts[slot_id] >= self.MAX_ATTEMPTS_PER_SLOT:
            logging.warning(f"  MAX_ATTEMPTS_PER_SLOT ({self.MAX_ATTEMPTS_PER_SLOT}) atteint pour le slot {slot_id}, abandon (backtrack).")
            self.metrics['slot_timeouts'] += 1 # Compter cet abandon spécifique
            # Important : On ne marque PAS comme Nogood, car c'est un abandon, pas une impossibilité logique.
            return False
        # --- GESTION DU TIMEOUT ADAPTATIF PAR SLOT (Fin) ---

        pattern = self._get_slot_pattern(slot)
        # Log amélioré incluant le compte des tentatives pour ce slot dans cette branche
        logging.info(f"[Slot {slot.get('id', '?')}] {slot['direction']}, L={slot['length']}, Pattern='{pattern}' (Tentatives: {slot_attempts.get(slot_id, 0)})")

        # Vérification Nogood (basique)
        if self._is_nogood_pattern(slot_id, pattern):
            logging.debug(f"  Pattern '{pattern}' est un nogood connu, backtrack immédiat !")
            return False

        # Récupération des candidats (via cache du repo)
        candidates = self.repository.get_candidates(pattern)
        if not candidates:
            logging.debug(f"  Aucun candidat pour ce slot, backtrack !")
            self._record_nogood(slot_id, pattern) # Apprendre l'échec
            return False

        # Tri, Limitation et Mélange des candidats
        scored_candidates = [(self._score_word(w), w) for w in candidates]
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        scored_candidates = scored_candidates[:self.MAX_CANDIDATES_PER_SLOT] # Limiter

        # Mélanger le top 20% pour varier l'exploration
        top_20_percent = max(1, len(scored_candidates) // 5)
        if top_20_percent > 1:
            top_candidates = scored_candidates[:top_20_percent]
            random.shuffle(top_candidates)
            scored_candidates = top_candidates + scored_candidates[top_20_percent:]

        logging.debug(f"   {len(scored_candidates)} candidats (limité à {self.MAX_CANDIDATES_PER_SLOT}, top 20% aléatoire).")

        # Boucle de test des candidats
        for i, (score, word) in enumerate(scored_candidates):
            self.metrics['candidates_tested'] += 1

            # NOUVEAU : Incrémenter le compteur de tentatives POUR CE SLOT à chaque mot essayé
            slot_attempts[slot_id] += 1

            # NOUVEAU : Re-vérifier la limite APRES incrémentation (sécurité, si MAX_ATTEMPTS est très bas)
            if slot_attempts[slot_id] > self.MAX_ATTEMPTS_PER_SLOT:
                 logging.warning(f"  MAX_ATTEMPTS_PER_SLOT ({self.MAX_ATTEMPTS_PER_SLOT}) dépassé DANS la boucle pour slot {slot_id}, abandon.")
                 self.metrics['slot_timeouts'] += 1
                 # Si on est ici, on a déjà essayé au moins un mot sans succès.
                 # On abandonne ce slot pour cette branche.
                 # On ne revert rien car le mot courant n'a pas été validé/placé.
                 return False # Abandonner ce slot

            logging.debug(f"    Tentative {i+1}/{len(scored_candidates)} (Total slot: {slot_attempts[slot_id]}): mot '{word}' (Score: {score})")

            # Placer temporairement le mot
            original_state = self._place_word_on_grid(word, slot)

            # Vérification Nogood (Forward Checking : ce mot crée-t-il un nogood connu ?)
            if self._would_create_nogoods(word, slot, original_state):
                logging.debug(f"      -> Mot '{word}' créerait des nogoods connus, skip.")
                self._revert_grid_state(original_state)
                continue # Essayer le mot suivant

            # Vérification de validité simple (fragments croisés)
            if not self._is_placement_valid(word, slot, original_state):
                self._revert_grid_state(original_state)
                continue # Essayer le mot suivant

            # Forward Checking strict (ce mot laisse-t-il assez de candidats aux voisins ?)
            self.metrics['fc_checks'] += 1
            if not self._forward_check(word, slot, original_state):
                self.metrics['fc_skips'] += 1
                logging.debug(f"      -> Mot '{word}' échoue au FC strict (dead-end), skip.")
                self._revert_grid_state(original_state)
                continue # Essayer le mot suivant

            # --- Si on arrive ici, le mot est prometteur ---
            slot['is_filled'] = True
            self.repository.remove_word_from_available(word, slot['length']) # Consommer le mot
            logging.info(f"  → Place '{word}'")

            # Appel récursif pour le slot suivant
            # IMPORTANT : Passer une COPIE de slot_attempts pour l'isolation des branches
            if self._solve_recursive(slot_attempts.copy()):
                # Succès de la branche ! Ajouter le mot à la solution
                self.placed_words.insert(0, {
                    "text": word, "x": slot['x'], "y": slot['y'],
                    "direction": slot['direction'], "id": slot['id'],
                    "score": score
                })
                return True # Propager le succès vers le haut
            else:
                # Échec de la branche (Backtrack)
                self.metrics['backtracks'] += 1
                # Invalider les nogoods des voisins car le contexte change
                self._invalidate_dependent_nogoods(slot)
                # Remettre le mot disponible
                self.repository.add_word_to_available(word, slot['length'])
                slot['is_filled'] = False
                logging.debug(f"      <- Retour arrière (Backtrack) pour '{word}'.")
                # Annuler le placement sur la grille
                self._revert_grid_state(original_state)
                # Continuer la boucle for pour essayer le prochain mot pour CE slot

        # Si la boucle for se termine, tous les candidats ont échoué pour ce slot DANS CE CONTEXTE
        logging.debug(f"  ÉCHEC : Tous les {len(scored_candidates)} candidats ont échoué pour le slot {slot_id} avec pattern '{pattern}'.")
        # Apprendre l'échec : ce pattern est un Nogood dans ce contexte
        self._record_nogood(slot_id, pattern)
        return False # Propager l'échec vers le haut

    # ===================================================================
    # Méthodes utilitaires (inchangées)
    # ===================================================================

    def _get_slot_pattern(self, slot: dict) -> str:
        """Génère le motif du slot (ex : 'A??E?')."""
        pattern = []
        placeholder = '?'
        for i in range(slot['length']):
            if slot['direction'] == 'across': x, y = slot['x'] + i, slot['y']
            else: x, y = slot['x'], slot['y'] + i
            if 0 <= y < self.height and 0 <= x < self.width:
                 char = self.grid[y][x]
                 if char in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL,'', ' ', None):
                      pattern.append(placeholder)
                 else:
                      pattern.append(char)
            else: # Sécurité si coordonnées hors grille
                 pattern.append(placeholder)
        return ''.join(pattern)

    def _place_word_on_grid(self, word: str, slot: dict) -> list[tuple[int, int, str]]:
        """Place un mot et renvoie l'état précédent."""
        original_state = []
        x, y, direction = slot['x'], slot['y'], slot['direction']
        for i, char in enumerate(word):
            px = x + i if direction == 'across' else x
            py = y if direction == 'across' else y + i
            # Vérifier les limites avant d'accéder à la grille
            if 0 <= py < self.height and 0 <= px < self.width:
                original_state.append((px, py, self.grid[py][px]))
                self.grid[py][px] = char
            else:
                 # Gérer le cas où les coordonnées sont hors limites (ne devrait pas arriver avec des slots valides)
                 logging.error(f"Tentative d'écriture hors grille à ({px},{py}) pour le mot '{word}'")
        return original_state

    def _revert_grid_state(self, original_state: list[tuple[int, int, str]]):
        """Restaure l'état précédent de la grille."""
        for (x, y, old_char) in original_state:
             # Vérifier les limites avant d'écrire
             if 0 <= y < self.height and 0 <= x < self.width:
                 self.grid[y][x] = old_char
             else:
                  logging.error(f"Tentative de revert hors grille à ({x},{y})")


    def _is_placement_valid(self, word: str, slot: dict, original_state: list[tuple[int, int, str]]) -> bool:
        """Vérifie si le mot crée des fragments valides dans l'autre sens."""
        for i, (char, (px, py, old_char)) in enumerate(zip(word, original_state)):
            if old_char == char: continue # Pas de changement, pas de vérification nécessaire

            fragment = ""
            if slot['direction'] == 'across':
                fragment = self._get_vertical_fragment(px, py)
            else: # 'down'
                fragment = self._get_horizontal_fragment(px, py)

            # Si fragment > 1 lettre et pas un mot valide (via repo qui utilise le Trie)
            if len(fragment) > 1 and not self.repository.is_word_valid(fragment):
                logging.debug(f"      -> REJETÉ : Mot '{word}' crée fragment invalide '{fragment}'")
                return False
        return True # Tous les fragments créés sont valides

    def _get_vertical_fragment(self, x: int, y: int) -> str:
        """Construit le mot vertical complet passant par (x,y)."""
        if not (0 <= x < self.width): return "" # Sécurité
        fragment = ""
        # Remonter au début du mot vertical
        cy = y
        while cy >= 0 and self.grid[cy][x] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            cy -= 1
        cy += 1 # Revenir sur la première lettre
        # Descendre pour lire le mot
        while cy < self.height and self.grid[cy][x] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            fragment += self.grid[cy][x]; cy += 1
        return fragment

    def _get_horizontal_fragment(self, x: int, y: int) -> str:
        """Construit le mot horizontal complet passant par (x,y)."""
        if not (0 <= y < self.height): return "" # Sécurité
        fragment = ""
        # Reculer au début du mot horizontal
        cx = x
        while cx >= 0 and self.grid[y][cx] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            cx -= 1
        cx += 1 # Revenir sur la première lettre
        # Avancer pour lire le mot
        while cx < self.width and self.grid[y][cx] not in (self.template.BLACK_SQUARE, self.template.EMPTY_CELL, ' ', ''):
            fragment += self.grid[y][cx]; cx += 1
        return fragment

    def _score_word(self, word: str) -> int:
        """Calcule le 'score d'utilité' d'un mot."""
        return sum(self.LETTER_SCORES.get(char.upper(), 0) for char in word)

    # ===================================================================
    # Système de Nogoods (intégrant l'invalidation)
    # ===================================================================

    def _record_nogood(self, slot_id, pattern: str):
        """Enregistre un pattern qui a échoué pour un slot donné."""
        if slot_id not in self.nogoods: self.nogoods[slot_id] = set()
        # N'enregistrer que si le pattern contient au moins une lettre
        if '?' in pattern and pattern.count('?') < len(pattern):
            self.nogoods[slot_id].add(pattern)
            logging.debug(f"  [NOGOOD] Enregistré pour slot {slot_id}: '{pattern}'")

    def _is_nogood_pattern(self, slot_id, pattern: str) -> bool:
        """Vérifie si un pattern est un nogood connu pour ce slot."""
        return slot_id in self.nogoods and pattern in self.nogoods[slot_id]

    # Note: _clear_nogoods_for_slot a été jugé incorrect logiquement et supprimé.
    # Un nogood reste vrai ("ABC???" impossible) même si on trouve une solution ailleurs.

    def _invalidate_dependent_nogoods(self, slot: dict):
        """Efface les nogoods des slots intersectés lors du backtrack."""
        slots_to_clear = set()
        slot_id_parent = slot.get('id', id(slot)) # ID du slot d'où on backtrack

        for pos_idx in range(slot['length']):
            if slot['direction'] == 'across': x, y = slot['x'] + pos_idx, slot['y']
            else: x, y = slot['x'], slot['y'] + pos_idx

            intersected = self._find_intersecting_slot_fast(x, y, slot['direction'])
            if intersected:
                intersected_id = intersected.get('id', id(intersected))
                # Ne pas s'invalider soi-même
                if intersected_id != slot_id_parent:
                     slots_to_clear.add(intersected_id)

        for slot_id in slots_to_clear:
            if slot_id in self.nogoods:
                logging.debug(f"  [NOGOOD] Invalidation des nogoods du slot {slot_id} (backtrack depuis slot {slot_id_parent})")
                del self.nogoods[slot_id] # Supprimer l'entrée pour ce slot

    def _would_create_nogoods(self, word: str, slot: dict, original_state: list[tuple[int, int, str]]) -> bool:
        """Forward Checking : vérifie si placer ce mot créerait un nogood connu."""
        for i, (char, (px, py, old_char)) in enumerate(zip(word, original_state)):
            if old_char == char: continue # Lettre inchangée

            intersected_slot = self._find_intersecting_slot_fast(px, py, slot['direction'])
            if not intersected_slot or intersected_slot.get('is_filled', False): continue # Slot inexistant ou déjà rempli

            # Calcule le pattern qui *serait* créé si on plaçait le mot
            # _calculate_future_pattern lit la grille *après* placement temporaire
            future_pattern = self._calculate_future_pattern(intersected_slot)
            intersected_slot_id = intersected_slot.get('id', id(intersected_slot))

            # Si ce futur pattern est un nogood DÉJÀ CONNU pour ce slot, alors rejeter ce mot
            if self._is_nogood_pattern(intersected_slot_id, future_pattern):
                logging.debug(f"        FC Nogood: Placer '{word}' créerait nogood connu '{future_pattern}' pour slot {intersected_slot_id}")
                return True # Oui, ce mot créerait un nogood
        return False # Non, ce mot ne crée pas de nogood connu a priori

    def _calculate_future_pattern(self, slot: dict) -> str:
        """Calcule le pattern actuel d'un slot (après placement temporaire)."""
        # _get_slot_pattern lit self.grid, qui contient le mot placé temporairement
        return self._get_slot_pattern(slot)

    # ===================================================================
    # OPTIMISATION : Pré-calcul et recherche rapide des intersections
    # ===================================================================

    def _precompute_intersections(self):
        """Pré-calcule un mapping (x, y, direction) -> slot."""
        self.intersection_map = {}
        for slot in self.slots:
            for pos_idx in range(slot['length']):
                if slot['direction'] == 'across': x, y = slot['x'] + pos_idx, slot['y']
                else: x, y = slot['x'], slot['y'] + pos_idx
                key = (x, y, slot['direction'])
                self.intersection_map[key] = slot
        logging.debug(f"Pré-calcul de {len(self.intersection_map)} positions de slots terminé.")

    def _find_intersecting_slot_fast(self, x: int, y: int, current_direction: str) -> dict | None:
        """Version O(1) pour trouver le slot croisé via la map pré-calculée."""
        opposite_direction = 'down' if current_direction == 'across' else 'across'
        key = (x, y, opposite_direction)
        return self.intersection_map.get(key) # Renvoie None si pas de slot croisé à cet endroit

    # ===================================================================
    # FORWARD CHECKING : Détection précoce des branches mortes
    # ===================================================================

    def _forward_check(self, word: str, slot: dict, original_state: list[tuple[int, int, str]]) -> bool:
        """Forward Checking STRICT."""
        intersected_slot_ids_to_check = set()
        for i, (char, (px, py, old_char)) in enumerate(zip(word, original_state)):
            if old_char == char: continue # Vérifier seulement si la lettre change
            intersected_slot = self._find_intersecting_slot_fast(px, py, slot['direction'])
            if intersected_slot and not intersected_slot.get('is_filled', False):
                intersected_slot_ids_to_check.add(intersected_slot.get('id', id(intersected_slot)))

        for slot_id in intersected_slot_ids_to_check:
            # On doit retrouver l'objet slot à partir de l'ID (ou passer les objets directement)
            s = next((s for s in self.slots if s.get('id', id(s)) == slot_id), None)
            if not s: continue # Ne devrait pas arriver

            # Le pattern est calculé APRES le placement temporaire
            future_pattern = self._get_slot_pattern(s)
            candidates = self.repository.get_candidates(future_pattern)
            nb_candidates = len(candidates) if candidates else 0

            if nb_candidates < self.MIN_SAFE_CANDIDATES:
                logging.debug(f"        FC STRICT Échec: Slot {slot_id} n'aurait que {nb_candidates} candidats (min {self.MIN_SAFE_CANDIDATES}, pattern '{future_pattern}')")
                return False # Échec du Forward Check
        return True # OK, tous les voisins ont assez de candidats

    # ===================================================================
    # Métriques
    # ===================================================================

    def _print_metrics(self):
        """Affiche les métriques de performance après une tentative de solve."""
        m = self.metrics
        elapsed_time = time.time() - self.start_time
        logging.info("-" * 40)
        logging.info(f"Fin de la résolution - Temps total: {elapsed_time:.3f} sec")
        logging.info(f"Appels récursifs     : {m['recursive_calls']}")
        logging.info(f"Candidats testés     : {m['candidates_tested']}")
        logging.info(f"FC Checks            : {m['fc_checks']}")
        logging.info(f"FC Skips (dead-ends) : {m['fc_skips']} ({ (m['fc_skips'] / m['fc_checks'] * 100) if m['fc_checks'] else 0 :.1f}%)")
        logging.info(f"Backtracks           : {m['backtracks']}")
        logging.info(f"Abandons (timeout/slot): {m.get('slot_timeouts', 0)}") # Afficher la nouvelle métrique

        # === CORRECTION ICI ===
        # Récupérer les stats du cache directement depuis le repo
        repo_cache_stats = {'hits': 0, 'misses': 0}
        if hasattr(self.repository, '_cache_stats'):
             repo_cache_stats = self.repository._cache_stats
        # === FIN CORRECTION ===

        cache_hits = repo_cache_stats.get('hits', 0)
        cache_misses = repo_cache_stats.get('misses', 0)
        cache_total = cache_hits + cache_misses
        logging.info(f"Cache Hits (Repo)    : {cache_hits} ({ (cache_hits / cache_total * 100) if cache_total else 0 :.1f}%)")
        logging.info(f"Cache Misses (Repo)  : {cache_misses}")
        logging.info("-" * 40)

    def get_solve_statistics(self) -> dict:
         """Retourne les métriques et l'historique pour le rapport."""
         # === CORRECTION ICI ===
         # Appeler une méthode dédiée dans WordRepository pour obtenir les stats formatées
         repo_cache_stats = {}
         if hasattr(self.repository, 'get_cache_stats'):
              repo_cache_stats = self.repository.get_cache_stats()
         else: # Fallback si la méthode n'existe pas encore
              raw_stats = getattr(self.repository, '_cache_stats', {'hits': 0, 'misses': 0})
              total = raw_stats['hits'] + raw_stats['misses']
              ratio = (raw_stats['hits'] / total * 100) if total else 0
              repo_cache_stats = {'hits': raw_stats['hits'], 'misses': raw_stats['misses'], 'total': total, 'hit_ratio': ratio}
         # === FIN CORRECTION ===
         # Combiner avec les métriques du solver
         combined_metrics = self.metrics.copy()
         combined_metrics.update({
             'cache_hits': repo_cache_stats['hits'],
             'cache_misses': repo_cache_stats['misses'],
             'cache_total': repo_cache_stats['total'],
             'cache_hit_ratio': repo_cache_stats['hit_ratio']
         })

         # Simplifier l'historique (juste les mots placés avec score)
         final_placement_history = [
             {'text': p['text'], 'score': p.get('score', 0)} for p in reversed(self.placed_words)
         ]

         return {
             'metrics': combined_metrics,
             'cache_stats': repo_cache_stats, # Garder pour compatibilité ? Ou juste metrics suffit ?
             'placement_history': final_placement_history,
         }