"""Corriger une grille à la main : les lettres font foi, les mots s'en déduisent (#27, ADR 0012).

Une grille conservée n'est plus seulement ce que le moteur a produit : l'auteur y revient, change un
« O » en « E », et la grille doit suivre. Deux principes rendent cela sûr :

1. **Les emplacements ne bougent jamais.** Ils sont dictés par les cases définitions, que l'édition
   manuelle ne touche pas. Une définition écrite pour le mot « qui part en (1,2) vers la droite »
   reste attachée à cet emplacement, quel que soit le mot qui l'occupe.
2. **Les mots se recalculent** à partir des lettres. Changer une lettre en touche toujours deux — un
   horizontal et un vertical — et les recalculer évite de tenir deux vérités qui divergeraient.

Module pur : ni Flask, ni base, ni lexique. Ce que contient le dictionnaire se décide ailleurs.
"""

ACROSS = "across"
DOWN = "down"


def letters_of(cells: list[dict]) -> dict[tuple[int, int], str]:
    """Les lettres de la grille, par case. Les cases définitions n'en ont pas."""
    return {(cell["x"], cell["y"]): (cell.get("char") or "") for cell in cells if not cell.get("is_black")}


def _size(cells: list[dict]) -> tuple[int, int]:
    return (max((c["x"] for c in cells), default=-1) + 1, max((c["y"] for c in cells), default=-1) + 1)


def slots_of(cells: list[dict]) -> list[dict]:
    """Les emplacements de la grille : suites d'au moins deux cases lettres, comme à la génération.

    Même règle que `SlotFinder`, mais lue depuis une grille déjà produite plutôt que depuis un
    gabarit : c'est le seul endroit où l'on dispose des deux.
    """
    width, height = _size(cells)
    black = {(cell["x"], cell["y"]) for cell in cells if cell.get("is_black")}
    slots = []

    for y in range(height):
        for x in range(width):
            if (x, y) in black:
                continue
            if (x == 0 or (x - 1, y) in black):
                length = 0
                while x + length < width and (x + length, y) not in black:
                    length += 1
                if length > 1:
                    slots.append({"x": x, "y": y, "direction": ACROSS, "length": length})
            if (y == 0 or (x, y - 1) in black):
                length = 0
                while y + length < height and (x, y + length) not in black:
                    length += 1
                if length > 1:
                    slots.append({"x": x, "y": y, "direction": DOWN, "length": length})
    return slots


def cells_of_slot(slot: dict) -> list[tuple[int, int]]:
    """Les cases qu'occupe un emplacement, du début à la fin."""
    return [
        (slot["x"] + (i if slot["direction"] == ACROSS else 0),
         slot["y"] + (0 if slot["direction"] == ACROSS else i))
        for i in range(slot["length"])
    ]


def slot_at(cells: list[dict], x: int, y: int, direction: str) -> dict | None:
    """L'emplacement qui passe par cette case dans ce sens, ou None s'il n'y en a pas."""
    for slot in slots_of(cells):
        if slot["direction"] == direction and (x, y) in cells_of_slot(slot):
            return slot
    return None


def text_of(slot: dict, letters: dict[tuple[int, int], str]) -> str:
    return "".join(letters.get(cell, "") for cell in cells_of_slot(slot))


def apply_letters(cells: list[dict], edits: list[dict]) -> tuple[list[dict], list[str]]:
    """Pose les lettres demandées. Renvoie les cases mises à jour et ce qui a été refusé.

    Une case définition ne reçoit pas de lettre : la refuser vaut mieux que de l'écrire quelque part
    où elle ne s'affichera jamais.
    """
    by_position = {(cell["x"], cell["y"]): cell for cell in cells}
    problems = []
    updated = [dict(cell) for cell in cells]
    index = {(cell["x"], cell["y"]): cell for cell in updated}

    for edit in edits:
        position = (edit["x"], edit["y"])
        target = by_position.get(position)
        if target is None:
            problems.append(f"la case ({edit['x']}, {edit['y']}) n'existe pas dans cette grille")
            continue
        if target.get("is_black"):
            problems.append(f"la case ({edit['x']}, {edit['y']}) est une case définition")
            continue
        index[position]["char"] = edit["char"]

    return updated, problems


def words_from_cells(cells: list[dict], previous: list[dict] | None = None) -> list[dict]:
    """Les mots que la grille contient aujourd'hui.

    `previous` sert à garder la provenance (`must`, `wish`, `common`) des mots inchangés ; un mot
    dont le texte a changé devient « manuel », parce qu'il ne vient plus du moteur.
    """
    letters = letters_of(cells)
    before = {(word["x"], word["y"], word["direction"]): word for word in (previous or [])}

    words = []
    for index, slot in enumerate(slots_of(cells)):
        text = text_of(slot, letters)
        old = before.get((slot["x"], slot["y"], slot["direction"]))
        source = old["source"] if old and old.get("text") == text else "manuel"
        words.append({
            "id": index,
            "text": text,
            "x": slot["x"],
            "y": slot["y"],
            "direction": slot["direction"],
            "source": source,
        })
    return words


def allowed_letters(cells: list[dict], slot: dict, is_word) -> list[set[str]]:
    """Pour chaque case de l'emplacement, les lettres qui laissent son croisement valide.

    C'est la cohérence d'arc du solveur, appliquée à une seule case : une lettre n'est proposée que
    si le mot perpendiculaire reste un mot une fois cette lettre posée. Sans croisement, tout passe.
    """
    letters = letters_of(cells)
    perpendicular = DOWN if slot["direction"] == ACROSS else ACROSS
    allowed = []

    for position in cells_of_slot(slot):
        crossing = slot_at(cells, position[0], position[1], perpendicular)
        if crossing is None:
            allowed.append(set())  # aucun croisement : aucune contrainte
            continue
        cells_crossing = cells_of_slot(crossing)
        at = cells_crossing.index(position)
        base = [letters.get(cell, "") for cell in cells_crossing]
        possible = set()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            base[at] = letter
            if is_word("".join(base)):
                possible.add(letter)
        allowed.append(possible)
    return allowed
