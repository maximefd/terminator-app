from .layout_format import DEFINITION, LayoutFormatError, layout_size, parse_layout


class GridTemplate:
    BLACK_SQUARE = "#"
    EMPTY_CELL = "."

    def __init__(self, width, height, template_path=None):
        self.width = width
        self.height = height
        self.grid = [[self.EMPTY_CELL for _ in range(width)] for _ in range(height)]

        if template_path:
            self._load_from_file(template_path)

    @classmethod
    def from_rows(cls, rows: list[str]) -> "GridTemplate":
        """Construit un template directement depuis ses lignes (ex: ['x-x', '---'] ou ['#.#', '...'])."""
        parsed = parse_layout("\n".join(rows))
        template = cls(*layout_size(parsed))
        template._apply_rows(parsed)
        return template

    def _apply_rows(self, rows: list[str]) -> None:
        """Place les cases définitions décrites par des rangées au format v1 (`x` / `-`)."""
        for y, row in enumerate(rows):
            for x, char in enumerate(row):
                self.grid[y][x] = self.BLACK_SQUARE if char == DEFINITION else self.EMPTY_CELL

    def _load_from_file(self, file_path: str) -> None:
        """Charge un layout ; sa taille doit correspondre à celle demandée (le nom de son dossier)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except OSError as e:
            raise FileNotFoundError(f"Impossible de charger le layout : {file_path}") from e

        try:
            rows = parse_layout(text)
        except LayoutFormatError as e:
            raise LayoutFormatError(f"{file_path} : {e}") from e
        width, height = layout_size(rows)
        if (width, height) != (self.width, self.height):
            raise LayoutFormatError(
                f"{file_path} : la grille mesure {width}x{height} alors que le format attendu est "
                f"{self.width}x{self.height}."
            )
        self._apply_rows(rows)

    def get_cell(self, x, y):
        """Récupère le caractère à une coordonnée donnée."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.grid[y][x]
        return None # Retourne None si en dehors des limites

    def is_black_square(self, x, y):
        """Vérifie si une case est une case noire."""
        return self.get_cell(x, y) == self.BLACK_SQUARE

    def __str__(self):
        """Représentation textuelle de la grille pour le débogage."""
        return "\n".join("".join(cell for cell in row) for row in self.grid)
