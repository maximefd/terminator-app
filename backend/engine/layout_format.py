"""
Format des fichiers de layout (voir docs/LAYOUTS.md et l'ADR 0006).

Une ligne par rangée : `x` = case définition, `-` = case lettre. L'ancien format
(`#` / `.`) reste lu, mais un même fichier ne mélange pas les deux. Le format
(largeur × hauteur) se déduit de la grille elle-même.
"""

DEFINITION = "x"
LETTER = "-"
LEGACY_TO_V1 = {"#": DEFINITION, ".": LETTER}


class LayoutFormatError(ValueError):
    """Le texte d'un layout ne respecte pas le format."""


def parse_layout(text: str) -> list[str]:
    """Lit un layout et renvoie ses rangées au format v1 (`x` / `-`).

    Les espaces en fin de ligne et les lignes vides en fin de fichier sont ignorés.
    Lève LayoutFormatError avec un message qui situe l'erreur.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        raise LayoutFormatError("Le layout est vide.")

    rows, formats_seen = [], set()
    for y, line in enumerate(lines, start=1):
        if not line:
            raise LayoutFormatError(f"Ligne {y} : ligne vide au milieu de la grille.")
        row = []
        for x, char in enumerate(line, start=1):
            if char in (DEFINITION, LETTER):
                formats_seen.add("v1")
                row.append(char)
            elif char in LEGACY_TO_V1:
                formats_seen.add("ancien")
                row.append(LEGACY_TO_V1[char])
            else:
                raise LayoutFormatError(
                    f"Ligne {y}, colonne {x} : caractère « {char} » non autorisé "
                    f"({DEFINITION} = case définition, {LETTER} = case lettre)."
                )
        rows.append("".join(row))

    if len(formats_seen) > 1:
        raise LayoutFormatError("Le layout mélange l'ancien format (# et .) et le nouveau (x et -).")

    width = len(rows[0])
    for y, row in enumerate(rows, start=1):
        if len(row) != width:
            raise LayoutFormatError(f"Ligne {y} : {len(row)} cases au lieu de {width} (largeur de la ligne 1).")
    return rows


def layout_size(rows: list[str]) -> tuple[int, int]:
    """(largeur, hauteur) d'un layout déjà lu."""
    return len(rows[0]), len(rows)


def format_layout(rows: list[str]) -> str:
    """Texte d'un fichier de layout v1."""
    return "\n".join(rows) + "\n"
