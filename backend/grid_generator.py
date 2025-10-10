import random
import logging

class GridGenerator:
    BLACK_SQUARE = "#"

    def __init__(self, width, height, words, seed=None):
        self.width = width
        self.height = height
        self.grid = [['' for _ in range(width)] for _ in range(height)]
        self.placed_words = []
        
        if seed is not None:
            random.seed(seed)
        
        self.words_by_len = {}
        valid_words = [w for w in words if len(w) > 1 and len(w) <= max(width, height)]
        self._build_index(valid_words)

    def _build_index(self, words):
        for word in words:
            length = len(word)
            if length not in self.words_by_len: self.words_by_len[length] = []
            self.words_by_len[length].append(word)

    def generate(self, target_fill_ratio=0.55):
        """Stratégie V16 : Génération multi-phases pour une grille de qualité professionnelle."""
        
        # --- PHASE 1 : LA CHARPENTE (1-2 mots longs) ---
        long_word_lengths = [l for l in self.words_by_len if l > (max(self.width, self.height) * 0.7)]
        for _ in range(random.randint(1, 2)):
            if not self._place_word_of_lengths(sorted(long_word_lengths, reverse=True)):
                break
        
        # --- PHASE 2 : LE CŒUR (3-5 mots moyens) ---
        medium_word_lengths = [l for l in self.words_by_len if (max(self.width, self.height) * 0.4) <= l <= (max(self.width, self.height) * 0.7)]
        for _ in range(random.randint(3, 5)):
            if not self._place_word_of_lengths(sorted(medium_word_lengths, reverse=True), prioritize_intersections=True):
                break

        # --- PHASE 3 : LES FINITIONS (remplissage par meilleur score) ---
        while True:
            if self.get_grid_data()['fill_ratio'] >= target_fill_ratio:
                logging.info(f"Target fill ratio reached. Stopping.")
                break
            if not self._place_best_move():
                logging.info("No more valid moves found. Stopping.")
                break
        
        self._cleanup_grid()
        return True

    def _place_word_of_lengths(self, lengths_to_try, prioritize_intersections=False):
        """Tente de placer un mot parmi une liste de longueurs données."""
        for length in lengths_to_try:
            candidates = self.words_by_len.get(length, [])[:]
            random.shuffle(candidates)
            
            # Pour la phase de remplissage, on cherche le meilleur emplacement possible
            if prioritize_intersections:
                best_move = None
                max_score = -1
                for word in candidates:
                    slots = self._get_slots_for_word(word)
                    for slot in slots:
                        score = self._calculate_score(word, slot['x'], slot['y'], slot['direction'])
                        if score > max_score:
                            max_score = score
                            best_move = {'word': word, 'x': slot['x'], 'y': slot['y'], 'direction': slot['direction']}
                
                if best_move:
                    self._execute_move(best_move)
                    return True
            else: # Pour la charpente, on place le premier qui rentre
                for word in candidates:
                    slots = self._get_slots_for_word(word)
                    if slots:
                        slot = random.choice(slots)
                        self._execute_move({'word': word, 'x': slot['x'], 'y': slot['y'], 'direction': slot['direction']})
                        return True
        return False
        
    def _place_best_move(self):
        """Analyse tous les coups possibles et exécute le meilleur."""
        best_move = None
        max_score = -1
        
        all_lengths = list(self.words_by_len.keys())
        random.shuffle(all_lengths)

        for length in all_lengths:
            candidates = self.words_by_len.get(length, [])[:]
            random.shuffle(candidates)
            for word in candidates:
                slots = self._get_slots_for_word(word)
                for slot in slots:
                    score = self._calculate_score(word, slot['x'], slot['y'], slot['direction'])
                    if score > max_score:
                        max_score = score
                        best_move = {'word': word, 'x': slot['x'], 'y': slot['y'], 'direction': slot['direction'], 'score': score}
        
        if best_move:
            logging.info(f"-> FINISHING MOVE: '{best_move['word']}' with score {best_move['score']}")
            self._execute_move(best_move)
            return True
        return False

    def _execute_move(self, move):
        """Factorise l'action de placer un mot et de le retirer des listes."""
        word, x, y, direction = move['word'], move['x'], move['y'], move['direction']
        self._place_word(word, x, y, direction)
        length = len(word)
        if length in self.words_by_len and word in self.words_by_len[length]:
            self.words_by_len[length].remove(word)

    def _get_slots_for_word(self, word):
        """Trouve tous les slots valides pour un mot donné."""
        valid_slots = []
        length = len(word)
        # Horizontal
        for y in range(self.height):
            for x in range(self.width - length + 1):
                if self._can_place_word(word, x, y, "across"):
                    valid_slots.append({'x': x, 'y': y, 'direction': 'across'})
        # Vertical
        for x in range(self.width):
            for y in range(self.height - length + 1):
                 if self._can_place_word(word, x, y, "down"):
                    valid_slots.append({'x': x, 'y': y, 'direction': 'down'})
        return valid_slots

    def _calculate_score(self, word, x, y, direction):
        intersections = 0
        if direction == "across":
            for i, char in enumerate(word):
                if self.grid[y][x + i] == char: intersections += 1
        else:
            for i, char in enumerate(word):
                if self.grid[y + i][x] == char: intersections += 1
        return (intersections * 10) + (len(word) * 0.5)

    def _cleanup_grid(self):
        for y, row in enumerate(self.grid):
            for x, char in enumerate(row):
                if not char: self.grid[y][x] = self.BLACK_SQUARE

    def _can_place_word(self, word, x, y, direction):
        """Vérification complète (collisions et adjacence)."""
        if direction == "across":
            if x < 0 or x + len(word) > self.width: return False
            if x > 0 and self.grid[y][x - 1] not in ('', self.BLACK_SQUARE): return False
            if x + len(word) < self.width and self.grid[y][x + len(word)] not in ('', self.BLACK_SQUARE): return False
            for i, char in enumerate(word):
                if y < 0 or y >= self.height: return False
                current_char = self.grid[y][x + i]
                if current_char and current_char != char: return False
                if not current_char:
                    if (y > 0 and self.grid[y - 1][x + i] not in ('', self.BLACK_SQUARE)) or \
                       (y < self.height - 1 and self.grid[y + 1][x + i] not in ('', self.BLACK_SQUARE)):
                        return False
        else: # "down"
            if y < 0 or y + len(word) > self.height: return False
            if y > 0 and self.grid[y - 1][x] not in ('', self.BLACK_SQUARE): return False
            if y + len(word) < self.height and self.grid[y + len(word)][x] not in ('', self.BLACK_SQUARE): return False
            for i, char in enumerate(word):
                if x < 0 or x >= self.width: return False
                current_char = self.grid[y + i][x]
                if current_char and current_char != char: return False
                if not current_char:
                    if (x > 0 and self.grid[y + i][x - 1] not in ('', self.BLACK_SQUARE)) or \
                       (x < self.width - 1 and self.grid[y + i][x + 1] not in ('', self.BLACK_SQUARE)):
                        return False
        return True

    def _place_word(self, word, x, y, direction):
        """Place un mot sur la grille."""
        self.placed_words.append({"text": word, "x": x, "y": y, "direction": direction})
        for i, char in enumerate(word):
            if direction == "across": self.grid[y][x + i] = char
            else: self.grid[y + i][x] = char

    def get_grid_data(self):
        """Formate la grille et ses métriques pour la réponse JSON."""
        filled_cells = 0
        cells = []
        for y, row in enumerate(self.grid):
            for x, char in enumerate(row):
                is_black = (char == self.BLACK_SQUARE or not bool(char))
                if not is_black: filled_cells += 1
                cells.append({"x": x, "y": y, "char": char, "is_black": is_black})
        fill_ratio = filled_cells / (self.width * self.height) if (self.width * self.height) > 0 else 0
        return {"width": self.width, "height": self.height, "fill_ratio": round(fill_ratio, 3), "cells": cells, "words": self.placed_words}