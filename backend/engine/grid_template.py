import logging

class GridTemplate:
    BLACK_SQUARE = "#"
    EMPTY_CELL = "."

    def __init__(self, width, height, template_path=None):
        self.width = width
        self.height = height
        self.grid = [[self.EMPTY_CELL for _ in range(width)] for _ in range(height)]

        if template_path:
            if not self._load_from_file(template_path):
                raise FileNotFoundError(f"Impossible de charger le template : {template_path}")

    @classmethod
    def from_rows(cls, rows: list[str]) -> "GridTemplate":
        """Construit un template directement depuis ses lignes (ex: ['#.#', '...'])."""
        height = len(rows)
        width = max((len(row) for row in rows), default=0)
        template = cls(width, height)
        template._apply_rows(rows)
        return template

    def _apply_rows(self, rows) -> None:
        """Place les cases noires décrites par les lignes ; tout le reste est une case vide."""
        for y, line in enumerate(rows):
            if y >= self.height:
                break
            line = line.rstrip('\n')
            for x, char in enumerate(line):
                if x >= self.width:
                    break
                self.grid[y][x] = self.BLACK_SQUARE if char == self.BLACK_SQUARE else self.EMPTY_CELL

    def _load_from_file(self, file_path: str) -> bool:
        """Charge une structure de grille depuis un fichier .txt."""
        try:
            with open(file_path, 'r') as f:
                self._apply_rows(f)
            return True
        except Exception as e:
            logging.error(f"Erreur lors du chargement du template {file_path}: {e}")
            return False

    def get_cell(self, x, y):
        """Récupère le caractère à une coordonnée donnée."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.grid[y][x]
        return None # Retourne None si en dehors des limites

    def is_black_square(self, x, y):
        """Vérifie si une case est une case noire."""
        return self.get_cell(x, y) == self.BLACK_SQUARE

    # --- FUTURES FONCTIONS (Backlog A1, A2) ---
    def validate_aesthetic_rules(self):
        """Vérifie si le template respecte nos règles (ex: cases noires adjacentes)."""
        # À IMPLÉMENTER (Story A1)
        pass

    def __str__(self):
        """Représentation textuelle de la grille pour le débogage."""
        return "\n".join("".join(cell for cell in row) for row in self.grid)
