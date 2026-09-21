"""Où va la définition de chaque mot, et par où sort sa flèche (Phase 5, #26).

Les layouts n'encodent pas les flèches ([ADR 0006](../../docs/adr/0006-format-des-layouts.md)) : elles se
déduisent de la géométrie. Un mot horizontal se définit depuis la case à sa gauche, un mot vertical depuis
la case au-dessus. Quand cette case n'existe pas — le mot commence au bord de la grille — la définition
passe dans la case perpendiculaire et la flèche se coude.

Mesuré sur les 21 layouts du catalogue (821 mots) : **aucun mot sans case de définition**, et **aucune case
qui en porterait plus de deux**. Mieux, dans une case qui en porte deux, l'une sort toujours par la droite
et l'autre par le bas — jamais deux du même côté. C'est ce qui permet de couper la case en deux moitiés
sans jamais avoir à arbitrer (`tests/test_arrows.py` le vérifie sur tout le catalogue).
"""

# Les quatre flèches, nommées par ce qu'elles font voir à l'auteur
RIGHT = "droite"                 # la définition est à gauche du mot
DOWN = "bas"                     # la définition est au-dessus du mot
BENT_DOWN_RIGHT = "coudee_bas_droite"   # mot collé au bord gauche : on descend, puis on part à droite
BENT_RIGHT_DOWN = "coudee_droite_bas"   # mot collé au bord haut : on va à droite, puis on descend

# Par quel côté de la case définition la flèche sort. Dans une case qui porte deux définitions,
# celle qui sort par la droite occupe la moitié haute, celle qui sort par le bas la moitié basse.
EXITS = {
    RIGHT: "right",
    BENT_RIGHT_DOWN: "right",
    DOWN: "bottom",
    BENT_DOWN_RIGHT: "bottom",
}


def clue_for_slot(template, x: int, y: int, direction: str) -> tuple[tuple[int, int], str] | None:
    """La case définition d'un mot et la forme de sa flèche, ou None si la grille n'en offre aucune."""
    if direction == "across":
        if x > 0 and template.is_black_square(x - 1, y):
            return (x - 1, y), RIGHT
        if y > 0 and template.is_black_square(x, y - 1):
            return (x, y - 1), BENT_DOWN_RIGHT
    else:
        if y > 0 and template.is_black_square(x, y - 1):
            return (x, y - 1), DOWN
        if x > 0 and template.is_black_square(x - 1, y):
            return (x - 1, y), BENT_RIGHT_DOWN
    return None


def clues_for_slots(template, slots: list[dict]) -> list[dict]:
    """Pour chaque slot, où s'écrit sa définition et par où part sa flèche.

    Un slot sans case de définition est rendu tel quel (`cell` à None) plutôt qu'écarté : le catalogue
    n'en contient aucun, mais un layout recopié de travers ne doit pas faire disparaître un mot en silence.
    """
    clues = []
    for slot in slots:
        found = clue_for_slot(template, slot["x"], slot["y"], slot["direction"])
        cell, arrow = found if found else (None, None)
        clues.append({
            "slot_id": slot.get("id"),
            "x": slot["x"],
            "y": slot["y"],
            "direction": slot["direction"],
            "length": slot.get("length"),
            "cell_x": cell[0] if cell else None,
            "cell_y": cell[1] if cell else None,
            "arrow": arrow,
            "exit": EXITS.get(arrow),
        })
    return clues


def clues_for_words(template, words: list[dict]) -> list[dict]:
    """Même chose à partir des mots placés : c'est ce que l'API renvoie avec la grille."""
    slots = [
        {"id": index, "x": word["x"], "y": word["y"], "direction": word["direction"],
         "length": len(word.get("text", ""))}
        for index, word in enumerate(words)
    ]
    return [
        {**clue, "text": words[index].get("text", "")}
        for index, clue in enumerate(clues_for_slots(template, slots))
    ]


class _CellGrid:
    """Vue minimale d'une grille déjà produite : seules les cases noires comptent pour les flèches."""

    def __init__(self, cells: list[dict]):
        self.width = max((cell["x"] for cell in cells), default=-1) + 1
        self.height = max((cell["y"] for cell in cells), default=-1) + 1
        self._black = {(cell["x"], cell["y"]) for cell in cells if cell.get("is_black")}

    def is_black_square(self, x: int, y: int) -> bool:
        return (x, y) in self._black


def clues_from_grid_data(cells: list[dict], words: list[dict]) -> list[dict]:
    """Les flèches d'une grille déjà produite (réponse de génération, ou grille conservée).

    On les recalcule au lieu de les stocker : elles ne dépendent que des cases noires et des débuts
    de mots, tous deux conservés. Une grille gardée avant l'arrivée des flèches en reçoit donc aussi.
    """
    return clues_for_words(_CellGrid(cells), words)
