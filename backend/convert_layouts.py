"""
Convertit des layouts de l'ancien format (`#` / `.`) vers le format v1 (`x` / `-`).

Usage (depuis backend/) :
    python convert_layouts.py                 # tous les layouts de backend/layouts
    python convert_layouts.py chemin/001.txt  # fichiers précis

Les fichiers déjà au format v1 ne sont pas modifiés. Voir docs/LAYOUTS.md.
"""

import argparse
import glob
import os
import sys

from engine.layout_format import LayoutFormatError, format_layout, parse_layout
from grid_generator import DEFAULT_LAYOUTS_DIR


def convert_file(path: str) -> bool:
    """Réécrit le fichier au format v1 ; renvoie True s'il a changé."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    converted = format_layout(parse_layout(text))
    if converted == text:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(converted)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Convertit des layouts vers le format v1 (x / -).")
    parser.add_argument("paths", nargs="*", help="Fichiers à convertir (défaut : tout backend/layouts).")
    args = parser.parse_args()

    paths = args.paths or sorted(glob.glob(os.path.join(DEFAULT_LAYOUTS_DIR, "*", "*.txt")))
    errors = 0
    for path in paths:
        try:
            print(f"{path} : {'converti' if convert_file(path) else 'déjà au format v1'}")
        except LayoutFormatError as e:
            errors += 1
            print(f"{path} : erreur, {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
