# DANS backend/grid_generator_v12_2.py

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
            
        # On ne pré-remplit plus les bords, l'algorithme est plus robuste
        
        self.words_by_len = {}
        valid_words = [w for w in words if len(w) > 1 and len(w) <= max(width, height)]
        self._build_index(valid_words)

        logging.debug("--- GRID GENERATOR INITIALIZED ---")
        logging.debug(f"Grid Size = {self.width}x{self.height}")
        total_words = sum(len(lst) for lst in self.words_by_len.values())
        logging.debug(f"Total valid words for this grid size = {total_words}")
        logging.debug("------------------------------------")
            
    def _build_index(self, words):
        for word in words:
            length = len(word)
            if length not in self.words_by_len: self.words_by_len[length] = []
            self.words_by_len[length].append(word)

    def generate(self):
        """Stratégie V13.1 : Amorçage clair + remplissage."""
        logging.debug("Starting generate()")
        
        # On place un premier mot pour amorcer le processus
        if not self._place_first_word():
            logging.warning("Could not place the first word.")
            return False # On signale l'échec si l'amorçage ne fonctionne pas
        
        # On continue les passes de remplissage tant qu'on arrive à ajouter des mots
        while self._fill_pass() > 0:
            pass
        
        logging.debug(f"Generation finished. Placed {len(self.placed_words)} words.")
        return True

    def _place_first_word(self):
        """Place le premier mot au centre de la grille."""
        for length in sorted(self.words_by_len.keys(), reverse=True):
            if length <= self.width:
                candidates = self.words_by_len[length]
                random.shuffle(candidates)
                for word in candidates:
                    x = (self.width - length) // 2
                    y = self.height // 2
                    if self._can_place_word(word, x, y, "across"):
                        self._place_word(word, x, y, "across")
                        self.words_by_len[length].remove(word)
                        logging.info(f"-> PLACED FIRST: '{word}' at ({x},{y}) direction: across")
                        return True
        return False

    def _fill_pass(self):
        """Effectue une passe de remplissage et retourne le nombre de mots placés."""
        slots = self._get_slots()
        logging.debug(f"Starting a fill pass, found {len(slots)} slots.")
        if not slots:
            return 0

        slots.sort(key=lambda s: s['length'], reverse=True)
        
        words_placed_this_pass = 0
        for slot in slots:
            if self.grid[slot['y']][slot['x']] != '' and all(c != '' for c in (self.grid[y][slot['x']] for y in range(slot['y'], slot['y'] + slot['length'])) if slot['direction'] == 'down') and all(c != '' for c in self.grid[slot['y']][slot['x']:slot['x'] + slot['length']] if slot['direction'] == 'across'): continue
            
            length = slot['length']
            candidates = self.words_by_len.get(length, [])[:]
            random.shuffle(candidates)
            
            for word in candidates:
                if self._can_place_word(word, slot['x'], slot['y'], slot['direction']):
                    self._place_word(word, slot['x'], slot['y'], slot['direction'])
                    if length in self.words_by_len and word in self.words_by_len[length]:
                        self.words_by_len[length].remove(word)
                    logging.info(f"-> PLACED: '{word}' at ({slot['x']},{slot['y']}) direction: {slot['direction']}")
                    words_placed_this_pass += 1
                    break
                    
        logging.debug(f"Fill pass finished, placed {words_placed_this_pass} words.")
        return words_placed_this_pass

    def _get_slots(self):
        """V13 : Détecte TOUS les slots, y compris ceux qui croisent des lettres existantes."""
        slots = []
        for y in range(self.height):
            for x in range(self.width):
                # Slot Horizontal
                if x == 0 or self.grid[y][x-1] == self.BLACK_SQUARE:
                    length = 0
                    while x + length < self.width and self.grid[y][x + length] != self.BLACK_SQUARE: length += 1
                    if length > 1: slots.append({'x': x, 'y': y, 'direction': 'across', 'length': length})
                
                # Slot Vertical
                if y == 0 or self.grid[y-1][x] == self.BLACK_SQUARE: ## CORRECTION FINALE ET DÉFINITIVE ICI ##
                    length = 0
                    while y + length < self.height and self.grid[y + length][x] != self.BLACK_SQUARE: length += 1
                    if length > 1: slots.append({'x': x, 'y': y, 'direction': 'down', 'length': length})
        return slots

    def _can_place_word(self, word, x, y, direction):
        # ton code existant reste inchangé
        ...

    def _place_word(self, word, x, y, direction):
        self.placed_words.append({"text": word, "x": x, "y": y, "direction": direction})
        for i, char in enumerate(word):
            if direction == "across":
                self.grid[y][x + i] = char
            else:
                self.grid[y + i][x] = char

    def get_grid_data(self):
        filled_cells = 0
        cells = []
        for y, row in enumerate(self.grid):
            for x, char in enumerate(row):
                is_black = (char == self.BLACK_SQUARE or not bool(char))
                if not is_black:
                    filled_cells += 1
                cells.append({"x": x, "y": y, "char": char, "is_black": is_black})
        fill_ratio = filled_cells / (self.width * self.height) if (self.width * self.height) > 0 else 0
        return {"width": self.width, "height": self.height, "fill_ratio": round(fill_ratio, 3),
                "cells": cells, "words": self.placed_words}
