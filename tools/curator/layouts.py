"""Éditeur de layouts du curateur : catalogue de backend/layouts avec les règles du backend (ADR 0006)."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
DEFAULT_LAYOUTS_DIR = BACKEND_DIR / "layouts"

# Le curateur réutilise le code sans Flask du backend (validateur, catalogue) au lieu de le dupliquer
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from engine.layout_format import layout_size  # noqa: E402
from engine.layout_validator import MAX_SIDE, validate_text  # noqa: E402
from layout_catalog import LayoutSaveError, catalog, find_duplicate, next_layout_id, save_layout  # noqa: E402

__all__ = ["DEFAULT_LAYOUTS_DIR", "LayoutSaveError", "catalog", "check_rows", "parse_rows", "save_layout"]


def parse_rows(value) -> list[str] | None:
    """Rangées envoyées par l'éditeur : 1 à 30 chaînes de 1 à 30 caractères (leur contenu est vérifié ensuite)."""
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SIDE:
        return None
    if not all(isinstance(row, str) and 1 <= len(row) <= MAX_SIDE for row in value):
        return None
    return value


def check_rows(rows: list[str], layouts_dir) -> dict:
    """Rapport du validateur, avec la grille identique déjà enregistrée et l'identifiant du prochain layout."""
    report = validate_text("\n".join(rows))
    parsed = report["rows"]
    return {
        **report,
        "duplicate_of": find_duplicate(parsed, str(layouts_dir)) if parsed else None,
        "next_id": next_layout_id(*layout_size(parsed), str(layouts_dir)) if report["valid"] else None,
    }
