# DANS backend/grid_generator.py

import random

class GridGenerator:
    def __init__(self, width, height, words):
        self.width = width
        self.height = height
        self.grid = [['' for _ in range(width)] for _ in range(height)]
        self.placed_words = []
        
        # --- NOUVEAUTÉ V4 : Construction de l'index ---
        self.words_by_len = {}
        self.index = {}
        self._build_index(words)

    def _build_index(self, words):
        """Prépare les mots et construit un index pour une recherche rapide."""
        for word in words:
            length = len(word)
            if length not in self.words_by_len:
                self.words_by_len[length] = []
            self.words_by_len[length].append(word)
            
            for i, char in enumerate(word):
                key = (char, i, length)
                if key not in self.index:
                    self.index[key] = []
                self.index[key].append(word)

    def generate(self):
        """Génère une grille en utilisant l'index pour être plus performant."""
        # On commence par le mot le plus long possible pour la grille
        for length in sorted(self.words_by_len.keys(), reverse=True):
            if length <= max(self.width, self.height):
                first_word = random.choice(self.words_by_len[length])
                
                if random.random() > 0.5 and len(first_word) <= self.width:
                    x, y = (self.width - len(first_word)) // 2, self.height // 2
                    self._place_word(first_word, x, y, "across")
                elif len(first_word) <= self.height:
                    x, y = self.width // 2, (self.height - len(first_word)) // 2
                    self._place_word(first_word, x, y, "down")
                else: # Fallback si le premier choix ne rentrait pas
                    x, y = (self.width - len(first_word)) // 2, self.height // 2
                    self._place_word(first_word, x, y, "across")

                # On retire tous les mots de cette longueur de la liste principale pour ne pas les réutiliser
                self.words_by_len[length].remove(first_word)
                break
        else: # Si aucun mot n'a pu être placé
            return False

        # Boucle de remplissage optimisée
        while self._try_to_place_one_word():
            pass # Continue tant qu'on arrive à placer des mots
        
        return True

    def _try_to_place_one_word(self):
        """Version V5: Utilise le calcul de position corrigé et un nettoyage d'index robuste."""
        random.shuffle(self.placed_words)

        for anchor_word_info in self.placed_words:
            anchor_direction = anchor_word_info["direction"]
            new_word_direction = "down" if anchor_direction == "across" else "across"

            # i = index de la lettre dans le mot d'ancrage
            for i, char in enumerate(anchor_word_info["text"]):
                
                # On cherche des mots candidats via l'index
                # On ne peut croiser qu'un mot de longueur >= 3
                for length in range(3, max(self.width, self.height) + 1):
                    # k = index de la même lettre dans le mot candidat
                    key = (char, 0, length) # On recherche le caractère au début du mot, puis on vérifie les autres positions
                    
                    candidates = self.index.get(key, [])
                    random.shuffle(candidates)

                    for word_to_place in candidates:
                        # Correction 1: On trouve la position de la lettre correspondante (k)
                        try:
                            k = word_to_place.index(char)
                        except ValueError:
                            continue

                        # Correction 1: Calcul géométrique correct du point de départ
                        if anchor_direction == "across":
                            new_x = anchor_word_info["x"] + i
                            new_y = anchor_word_info["y"] - k
                        else: # anchor_direction == "down"
                            new_x = anchor_word_info["x"] - k
                            new_y = anchor_word_info["y"] + i

                        if self._can_place_word(word_to_place, new_x, new_y, new_word_direction):
                            self._place_word(word_to_place, new_x, new_y, new_word_direction)
                            
                            # On retire le mot de nos listes pour ne pas le réutiliser
                            self.words_by_len[length].remove(word_to_place)
                            
                            # Correction 2: Nettoyage robuste de l'index
                            for idx, c in enumerate(word_to_place):
                                index_key = (c, idx, length)
                                if index_key in self.index:
                                    self.index[index_key] = [w for w in self.index[index_key] if w != word_to_place]
                            
                            return True # Mot placé, on arrête et on recommence la boucle principale
        
        return False # Aucun mot n'a pu être placé dans cette passe

    def _can_place_word(self, word, x, y, direction):
        # ... (cette fonction ne change pas par rapport à la V3) ...
        if direction == "across":
            if x < 0 or x + len(word) > self.width or y < 0 or y >= self.height: return False
            if x > 0 and self.grid[y][x - 1]: return False
            if x + len(word) < self.width and self.grid[y][x + len(word)]: return False
            for i, char in enumerate(word):
                current_char = self.grid[y][x + i]
                if current_char and current_char != char: return False
                if not current_char:
                    if y > 0 and self.grid[y - 1][x + i]: return False
                    if y < self.height - 1 and self.grid[y + 1][x + i]: return False
        else: # down
            if y < 0 or y + len(word) > self.height or x < 0 or x >= self.width: return False
            if y > 0 and self.grid[y - 1][x]: return False
            if y + len(word) < self.height and self.grid[y + len(word)][x]: return False
            for i, char in enumerate(word):
                current_char = self.grid[y + i][x]
                if current_char and current_char != char: return False
                if not current_char:
                    if x > 0 and self.grid[y + i][x - 1]: return False
                    if x < self.width - 1 and self.grid[y + i][x + 1]: return False
        return True

    def _place_word(self, word, x, y, direction):
        # ... (cette fonction ne change pas) ...
        self.placed_words.append({"text": word, "x": x, "y": y, "direction": direction})
        for i, char in enumerate(word):
            if direction == "across":
                self.grid[y][x + i] = char
            else:
                self.grid[y + i][x] = char

    def get_grid_data(self):
        # ... (cette fonction ne change pas) ...
        filled_cells = 0
        cells = []
        for y, row in enumerate(self.grid):
            for x, char in enumerate(row):
                is_black = not bool(char)
                if not is_black: filled_cells += 1
                cells.append({"x": x, "y": y, "char": char, "is_black": is_black})
        fill_ratio = filled_cells / (self.width * self.height)
        return {"width": self.width, "height": self.height, "fill_ratio": round(fill_ratio, 3), "cells": cells, "words": self.placed_words}