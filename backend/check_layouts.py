"""
Vérifie tous les layouts du catalogue (règles de docs/LAYOUTS.md). Utilisé par `make layouts-check` et la CI.

Usage :
    python backend/check_layouts.py
    python backend/check_layouts.py --dir chemin/vers/layouts

Code de sortie 1 si au moins un layout est invalide (les avertissements ne bloquent pas).
"""

import argparse
import sys

from layout_catalog import DEFAULT_LAYOUTS_DIR, list_layouts


def describe(stats: dict) -> str:
    lengths = ", ".join(f"{count} de {length}" for length, count in stats["lengths"].items())
    return (f"{stats['words']} mots, {round(stats['definition_ratio'] * 100)} % de cases définitions"
            f" (mots par longueur : {lengths} lettres)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vérifie les layouts du catalogue.")
    parser.add_argument("--dir", default=DEFAULT_LAYOUTS_DIR, help="Dossier des layouts (défaut : backend/layouts).")
    args = parser.parse_args()

    entries = list_layouts(args.dir)
    if not entries:
        print(f"Aucun layout trouvé dans {args.dir}.")
        return 1

    invalid = 0
    for entry in entries:
        report = entry["report"]
        mark = "✓" if report["valid"] else "✗"
        print(f"{mark} {entry['id']}" + (f" : {describe(report['stats'])}" if report["stats"] else ""))
        for error in report["errors"]:
            print(f"    erreur : {error['message']}")
        for warning in report["warnings"]:
            print(f"    attention : {warning['message']}")
        invalid += not report["valid"]

    print(f"\n{len(entries)} layout(s) vérifié(s), {invalid} invalide(s).")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
