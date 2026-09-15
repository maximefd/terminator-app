"""
Validation d'un layout (voir docs/LAYOUTS.md et l'ADR 0006).

Les mêmes règles partout : la CLI `check_layouts.py`, les tests, l'API et l'éditeur du curateur
appellent ces fonctions. Pures : aucune lecture ni écriture de fichier.
"""

from .layout_format import DEFINITION, LayoutFormatError, layout_size, parse_layout

MIN_SIDE = 2
MAX_SIDE = 30
# Proportion de cases définitions d'une grille publiée ; en dehors, une erreur de recopie est probable
USUAL_DEFINITION_RATIO = (0.10, 0.45)


def issue(message: str, cells=()) -> dict:
    """Erreur ou avertissement : message en français et cases concernées ([x, y], à partir de 0)."""
    return {"message": message, "cells": [list(cell) for cell in cells]}


def find_words(rows: list[str]) -> list[dict]:
    """Emplacements de mots (2 lettres ou plus), horizontaux puis verticaux : [{x, y, direction, length}]."""
    width, height = layout_size(rows)
    words = []
    for y, row in enumerate(rows):
        x = 0
        while x < width:
            start = x
            while x < width and row[x] != DEFINITION:
                x += 1
            if x - start >= 2:
                words.append({"x": start, "y": y, "direction": "across", "length": x - start})
            x += 1
    for x in range(width):
        y = 0
        while y < height:
            start = y
            while y < height and rows[y][x] != DEFINITION:
                y += 1
            if y - start >= 2:
                words.append({"x": x, "y": start, "direction": "down", "length": y - start})
            y += 1
    return words


def validate_rows(rows: list[str]) -> dict:
    """Vérifie un layout déjà lu (rangées `x` / `-`) : {valid, errors, warnings, stats}.

    Un mot peut commencer au bord de la grille : aucune règle ne l'interdit.
    """
    width, height = layout_size(rows)
    errors, warnings = [], []

    if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
        errors.append(issue(
            f"Format {width}x{height} non pris en charge : largeur et hauteur de {MIN_SIDE} à {MAX_SIDE} cases."
        ))

    words = find_words(rows)
    covered = set()
    for word in words:
        for i in range(word["length"]):
            covered.add((word["x"] + i, word["y"]) if word["direction"] == "across" else (word["x"], word["y"] + i))
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char != DEFINITION and (x, y) not in covered:
                errors.append(issue(
                    f"Ligne {y + 1}, colonne {x + 1} : case lettre isolée, "
                    "elle n'appartient à aucun mot de 2 lettres ou plus.",
                    [(x, y)],
                ))
    if not words:
        errors.append(issue("La grille ne contient aucun mot : ajoutez des cases lettres (-)."))

    definitions = sum(row.count(DEFINITION) for row in rows)
    ratio = definitions / (width * height)
    low, high = USUAL_DEFINITION_RATIO
    if words and not low <= ratio <= high:
        warnings.append(issue(
            f"{round(ratio * 100)} % de cases définitions : c'est inhabituel "
            f"(entre {round(low * 100)} et {round(high * 100)} % d'ordinaire). Vérifiez la recopie."
        ))

    lengths: dict[int, int] = {}
    for word in words:
        lengths[word["length"]] = lengths.get(word["length"], 0) + 1
    stats = {
        "width": width,
        "height": height,
        "words": len(words),
        "across": sum(word["direction"] == "across" for word in words),
        "down": sum(word["direction"] == "down" for word in words),
        "lengths": {str(length): lengths[length] for length in sorted(lengths)},
        "definition_cells": definitions,
        "definition_ratio": round(ratio, 3),
    }
    return {"valid": not errors, "errors": errors, "warnings": warnings, "stats": stats}


def validate_text(text: str) -> dict:
    """Lit puis vérifie le texte d'un layout ; une erreur de format devient une erreur du rapport.

    Renvoie {valid, errors, warnings, stats, rows} (`rows` et `stats` valent None si le texte est illisible).
    """
    try:
        rows = parse_layout(text)
    except LayoutFormatError as error:
        return {"valid": False, "errors": [issue(str(error))], "warnings": [], "stats": None, "rows": None}
    return {**validate_rows(rows), "rows": rows}
