import random

class GridGenerator:
    def __init__(self, width, height, words):
        self.width = width
        self.height = height
        self.words = sorted(words, key=len, reverse=True)
        self.grid = [['' for _ in range(width)] for _ in range(height)]
        self.placed_words = []

    def generate(self):
        # ... (cette fonction ne change pas par rapport à la V2)
        if not self.words:
            return False
        
        first_word = self.words.pop(0)
        if len(first_word) > self.width and len(first_word) > self.height:
            return False # Le mot le plus long ne rentre même pas dans la grille

        if random.random() > 0.5 and len(first_word) <= self.width:
            x, y = (self.width - len(first_word)) // 2, self.height // 2
            self._place_word(first_word, x, y, "across")
        elif len(first_word) <= self.height:
            x, y = self.width // 2, (self.height - len(first_word)) // 2
            self._place_word(first_word, x, y, "down")
        else:
             # Si le premier choix aléatoire ne fonctionne pas, on tente l'autre
            x, y = (self.width - len(first_word)) // 2, self.height // 2
            self._place_word(first_word, x, y, "across")

        attempts = 0
        while attempts < len(self.words) * 2:
            word_placed = self._try_to_place_one_word()
            if not word_placed:
                attempts += 1
            else:
                attempts = 0
        
        return True

    def _try_to_place_one_word(self):
        # ... (cette fonction ne change pas par rapport à la V2)
        random.shuffle(self.placed_words)

        for anchor_word_info in self.placed_words:
            for i, char in enumerate(anchor_word_info["text"]):
                
                for word_to_place in self.words:
                    for j, char_to_match in enumerate(word_to_place):
                        if char == char_to_match:
                            if anchor_word_info["direction"] == "across":
                                new_x = anchor_word_info["x"] + i
                                new_y = anchor_word_info["y"] - j
                                if self._can_place_word(word_to_place, new_x, new_y, "down"):
                                    self._place_word(word_to_place, new_x, new_y, "down")
                                    self.words.remove(word_to_place)
                                    return True
                            else:
                                new_x = anchor_word_info["x"] - j
                                new_y = anchor_word_info["y"] + i
                                if self._can_place_word(word_to_place, new_x, new_y, "across"):
                                    self._place_word(word_to_place, new_x, new_y, "across")
                                    self.words.remove(word_to_place)
                                    return True
        return False

    def _can_place_word(self, word, x, y, direction):
        """
        Vérification V3 : inclut les règles de non-adjacence des mots croisés.
        """
        if direction == "across":
            # 1. Vérification des bords de la grille
            if x < 0 or x + len(word) > self.width or y < 0 or y >= self.height:
                return False
            
            # 2. Vérification de la case juste avant et juste après le mot
            if x > 0 and self.grid[y][x - 1]: return False
            if x + len(word) < self.width and self.grid[y][x + len(word)]: return False

            # 3. Vérification des collisions et des adjacences perpendiculaires
            for i, char in enumerate(word):
                current_char = self.grid[y][x + i]
                # Si la case n'est pas vide, elle doit contenir la même lettre (point de croisement)
                if current_char and current_char != char:
                    return False
                # Si la case est vide (pas un croisement), on vérifie ses voisins du dessus et du dessous
                if not current_char:
                    if y > 0 and self.grid[y - 1][x + i]: return False
                    if y < self.height - 1 and self.grid[y + 1][x + i]: return False
        
        else: # direction == "down"
            if y < 0 or y + len(word) > self.height or x < 0 or x >= self.width:
                return False
            
            if y > 0 and self.grid[y - 1][x]: return False
            if y + len(word) < self.height and self.grid[y + len(word)][x]: return False
                
            for i, char in enumerate(word):
                current_char = self.grid[y + i][x]
                if current_char and current_char != char:
                    return False
                if not current_char:
                    if x > 0 and self.grid[y + i][x - 1]: return False
                    if x < self.width - 1 and self.grid[y + i][x + 1]: return False

        return True # Si toutes les vérifications passent, le placement est valide
    
    def _place_word(self, word, x, y, direction):
        # ... (cette fonction ne change pas)
        self.placed_words.append({"text": word, "x": x, "y": y, "direction": direction})
        for i, char in enumerate(word):
            if direction == "across":
                self.grid[y][x + i] = char
            else:
                self.grid[y + i][x] = char

    def get_grid_data(self):
        """Formate la grille et ajoute les métriques de performance."""
        filled_cells = 0
        cells = []
        for y, row in enumerate(self.grid):
            for x, char in enumerate(row):
                is_black = not bool(char)
                if not is_black:
                    filled_cells += 1
                cells.append({"x": x, "y": y, "char": char, "is_black": is_black})
        
        # Suggestion A: Calculer et inclure le ratio de remplissage
        fill_ratio = filled_cells / (self.width * self.height)

        return {
            "width": self.width,
            "height": self.height,
            "fill_ratio": round(fill_ratio, 3), # On arrondit pour la lisibilité
            "cells": cells,
            "words": self.placed_words
        }