"""
Catalogue des layouts sur disque : `backend/layouts/<L>x<H>/<NNN>.txt` (ADR 0006).

Lecture, vérification complète (règles du validateur, nom et dossier du fichier, grilles en double)
et enregistrement d'un nouveau layout sans jamais écraser un fichier. Sans Flask : utilisé par l'API,
le générateur, le benchmark, la CLI `check_layouts.py` et l'éditeur du curateur (tools/curator).
"""

import os
import re
import threading

from engine.layout_format import format_layout, layout_size
from engine.layout_validator import issue, validate_text

# Dossier des layouts, résolu depuis ce fichier (indépendant du répertoire courant)
DEFAULT_LAYOUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layouts")
FORMAT_DIR_NAME = re.compile(r"^(\d+)x(\d+)$")
LAYOUT_FILE_NAME = re.compile(r"^\d{3}\.txt$")
MAX_LAYOUTS_PER_FORMAT = 999

_save_lock = threading.Lock()


class LayoutSaveError(ValueError):
    """Enregistrement refusé : grille invalide, déjà présente ou dossier refusé."""

    def __init__(self, message: str, report: dict | None = None, duplicate_of: str | None = None):
        super().__init__(message)
        self.report = report
        self.duplicate_of = duplicate_of


def layout_id(layout_path: str) -> str:
    """Identifiant d'un layout, déduit de son chemin : `<L>x<H>/001.txt` → `<L>x<H>-001`."""
    format_name = os.path.basename(os.path.dirname(layout_path))
    return f"{format_name}-{os.path.splitext(os.path.basename(layout_path))[0]}"


def _format_dirs(layouts_dir: str) -> list[tuple[int, int, str]]:
    """Dossiers de format [(largeur, hauteur, chemin)], du plus petit au plus grand."""
    if not os.path.isdir(layouts_dir):
        return []
    formats = []
    for name in os.listdir(layouts_dir):
        match = FORMAT_DIR_NAME.fullmatch(name)
        path = os.path.join(layouts_dir, name)
        if match and os.path.isdir(path):
            formats.append((int(match[1]), int(match[2]), path))
    return sorted(formats, key=lambda f: (f[0] * f[1], f[0]))


def _layout_files(format_dir: str) -> list[str]:
    return sorted(name for name in os.listdir(format_dir) if name.endswith(".txt"))


def available_formats(layouts_dir: str | None = None) -> list[dict]:
    """Liste les formats disponibles (ex: [{'width': 6, 'height': 7, 'layouts': 1}]), triés."""
    formats = []
    for width, height, path in _format_dirs(layouts_dir or DEFAULT_LAYOUTS_DIR):
        count = len(_layout_files(path))
        if count:
            formats.append({"width": width, "height": height, "layouts": count})
    return formats


def check_layout_file(path: str) -> dict:
    """Rapport complet d'un fichier : règles du validateur, nom du fichier, taille conforme au dossier."""
    try:
        with open(path, encoding="utf-8") as f:
            report = validate_text(f.read())
    except (OSError, UnicodeDecodeError) as error:
        report = {"valid": False, "errors": [issue(f"Fichier illisible : {error}")], "warnings": [],
                  "stats": None, "rows": None}

    extra = []
    name = os.path.basename(path)
    if not LAYOUT_FILE_NAME.fullmatch(name):
        extra.append(issue(f"Nom de fichier « {name} » : un numéro à trois chiffres est attendu (ex. 001.txt)."))
    folder = os.path.basename(os.path.dirname(path))
    match = FORMAT_DIR_NAME.fullmatch(folder)
    if report["rows"]:
        width, height = layout_size(report["rows"])
        if not match or (int(match[1]), int(match[2])) != (width, height):
            extra.append(issue(f"La grille mesure {width}x{height} mais se trouve dans le dossier « {folder} »."))
    if extra:
        report = {**report, "valid": False, "errors": report["errors"] + extra}
    return report


def list_layouts(layouts_dir: str | None = None) -> list[dict]:
    """Tous les fichiers du catalogue avec leur rapport ; une grille identique à une précédente est signalée."""
    entries = []
    for width, height, format_dir in _format_dirs(layouts_dir or DEFAULT_LAYOUTS_DIR):
        for name in _layout_files(format_dir):
            path = os.path.join(format_dir, name)
            entries.append({"id": layout_id(path), "path": path, "width": width, "height": height,
                            "report": check_layout_file(path)})

    first_with_grid: dict[tuple, str] = {}
    for entry in entries:
        rows = entry["report"]["rows"]
        if not rows:
            continue
        key = tuple(rows)
        if key in first_with_grid:
            entry["report"]["warnings"].append(issue(f"Grille identique à {first_with_grid[key]}."))
        else:
            first_with_grid[key] = entry["id"]
    return entries


def catalog(layouts_dir: str | None = None) -> list[dict]:
    """Layouts valides regroupés par format : [{width, height, layouts: [{id, rows, stats}]}]."""
    formats: dict[tuple[int, int], list[dict]] = {}
    for entry in list_layouts(layouts_dir):
        report = entry["report"]
        if report["valid"]:
            formats.setdefault((entry["width"], entry["height"]), []).append(
                {"id": entry["id"], "rows": report["rows"], "stats": report["stats"]}
            )
    return [{"width": width, "height": height, "layouts": layouts} for (width, height), layouts in formats.items()]


def find_duplicate(rows: list[str], layouts_dir: str | None = None) -> str | None:
    """Identifiant d'un layout du catalogue identique à cette grille, s'il y en a un."""
    for entry in list_layouts(layouts_dir):
        if entry["report"]["rows"] == rows:
            return entry["id"]
    return None


def _next_number(format_dir: str) -> int:
    if not os.path.isdir(format_dir):
        return 1
    numbers = [int(name[:3]) for name in os.listdir(format_dir) if LAYOUT_FILE_NAME.fullmatch(name)]
    return max(numbers, default=0) + 1


def next_layout_id(width: int, height: int, layouts_dir: str | None = None) -> str:
    """Identifiant que recevra le prochain layout enregistré dans ce format."""
    format_dir = os.path.join(layouts_dir or DEFAULT_LAYOUTS_DIR, f"{width}x{height}")
    return f"{width}x{height}-{_next_number(format_dir):03d}"


def save_layout(rows: list[str], layouts_dir: str | None = None) -> dict:
    """Enregistre un nouveau layout valide sous le prochain numéro libre, sans jamais écraser un fichier.

    Le chemin est construit ici, à partir de la taille de la grille, jamais depuis une donnée reçue.
    Renvoie {id, path, report} ; lève LayoutSaveError.
    """
    report = validate_text("\n".join(rows))
    if not report["valid"]:
        raise LayoutSaveError("La grille n'est pas valide : corrigez les erreurs signalées.", report)
    rows = report["rows"]
    width, height = layout_size(rows)
    layouts_dir = os.path.realpath(layouts_dir or DEFAULT_LAYOUTS_DIR)

    with _save_lock:
        duplicate = find_duplicate(rows, layouts_dir)
        if duplicate:
            raise LayoutSaveError(f"Cette grille existe déjà : {duplicate}.", report, duplicate)
        format_dir = os.path.join(layouts_dir, f"{width}x{height}")
        if os.path.islink(format_dir):
            raise LayoutSaveError("Enregistrement refusé : le dossier du format est un lien symbolique.", report)
        os.makedirs(format_dir, exist_ok=True)

        number = _next_number(format_dir)
        while number <= MAX_LAYOUTS_PER_FORMAT:
            path = os.path.join(format_dir, f"{number:03d}.txt")
            try:
                # O_EXCL : échoue si le fichier (ou un lien) existe déjà, même créé entre-temps
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                number += 1
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as f:
                f.write(format_layout(rows))
            return {"id": layout_id(path), "path": path, "report": report}
    raise LayoutSaveError(f"Le format {width}x{height} compte déjà {MAX_LAYOUTS_PER_FORMAT} layouts.", report)
