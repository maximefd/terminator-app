# DANS backend/grid_generator.py

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

    def generate(self):
        """Génère la grille en plaçant un premier mot puis en remplissant par passes."""
        if not self._place_first_word():
            logging.warning("Could not place the first word.")
            return False

        while self._fill_pass() > 0:
            pass

        return True

    def _place_first_word(self):
        """Place le premier mot au centre de la grille, en testant les deux directions."""
        for length in sorted(self.words_by_len.keys(), reverse=True):
            candidates = self.words_by_len.get(length, [])
            if not candidates: continue

            random.shuffle(candidates)
            word = candidates[0]

            # Tenter horizontalement
            if length <= self.width:
                x, y = (self.width - length) // 2, self.height // 2
                if self._can_place_word(word, x, y, "across"):
                    self._place_word(word, x, y, "across")
                    self.words_by_len[length].remove(word)
                    return True

            # Tenter verticalement
            if length <= self.height:
                x, y = self.width // 2, (self.height - length) // 2
                if self._can_place_word(word, x, y, "down"):
                    self._place_word(word, x, y, "down")
                    self.words_by_len[length].remove(word)
                    return True
        return False

    def _fill_pass(self):
        """V13.1 : Correction finale qui autorise les croisements."""
        slots = self._get_slots()
        if not slots:
            return 0

        slots.sort(key=lambda s: s['length'], reverse=True)
        
        words_placed_this_pass = 0
        for slot in slots:
            # ON A SUPPRIMÉ LA LIGNE "if self.grid[...] != ''" QUI ÉTAIT ICI
            
            length = slot['length']
            candidates = self.words_by_len.get(length, [])[:]
            random.shuffle(candidates)
            
            for word in candidates:
                if self._can_place_word(word, slot['x'], slot['y'], slot['direction']):
                    self._place_word(word, slot['x'], slot['y'], slot['direction'])
                    if length in self.words_by_len and word in self.words_by_len[length]:
                        self.words_by_len[length].remove(word)
                    words_placed_this_pass += 1
                    # On sort de la boucle des candidats et on passe au slot suivant
                    break 
                    
        return words_placed_this_pass

    def _get_slots(self):
        """Détecte tous les emplacements possibles."""
        slots = []
        for y in range(self.height):
            for x in range(self.width):
                if x == 0 or self.grid[y][x-1] == self.BLACK_SQUARE:
                    length = 0
                    while x + length < self.width and self.grid[y][x + length] != self.BLACK_SQUARE: length += 1
                    if length > 1: slots.append({'x': x, 'y': y, 'direction': 'across', 'length': length})

                if y == 0 or self.grid[y-1][x] == self.BLACK_SQUARE:
                    length = 0
                    while y + length < self.height and self.grid[y + length][x] != self.BLACK_SQUARE: length += 1
                    if length > 1: slots.append({'x': x, 'y': y, 'direction': 'down', 'length': length})
        return slots

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