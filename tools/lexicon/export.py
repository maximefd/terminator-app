"""Export du lexique curé et statistiques de curation."""

import csv
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

from .decisions import DELETE, KEEP, effective_decisions, read_decisions
from .scoring import KEEP as SUGGEST_KEEP
from .scoring import LIKELY_DELETE

LENGTH_BANDS = ((2, 5), (6, 8), (9, 11), (12, 99))


def export_curated(db_path, decisions_path, out_path, exclude_suggested_deletes: bool = False) -> dict:
    """Écrit le lexique curé au format `MOT;forme affichée;définition;zipf`.

    Par défaut, seuls les mots supprimés par l'auteur sont retirés. Avec
    `exclude_suggested_deletes`, les mots suggérés « likely_delete » non gardés explicitement
    sont aussi retirés.

    La première colonne est compatible avec `DictionnaireTrie.load_dela_csv` (backend).
    """
    decisions = effective_decisions(read_decisions(decisions_path))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp")

    counts = Counter()
    connection = sqlite3.connect(db_path)
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";", lineterminator="\n")
            query = "SELECT norm, display_forms, definition, zipf, suggestion FROM words ORDER BY norm"
            for normalized, forms_json, definition, zipf, suggestion in connection.execute(query):
                decision = decisions.get(normalized)
                if decision == DELETE:
                    counts["deleted_by_author"] += 1
                    continue
                if exclude_suggested_deletes and decision != KEEP and suggestion == LIKELY_DELETE:
                    counts["deleted_by_suggestion"] += 1
                    continue
                writer.writerow([normalized, json.loads(forms_json)[0], definition or "", zipf])
                counts["exported"] += 1
    finally:
        connection.close()
    os.replace(tmp_path, out_path)
    return dict(counts)


def lexicon_stats(db_path, decisions_path) -> dict:
    """Avancement de la curation : décisions, mots restant à trier par tranche de longueur."""
    decisions = effective_decisions(read_decisions(decisions_path))
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT norm, length, suggestion FROM words").fetchall()
    finally:
        connection.close()

    to_review = {_band_label(low, high): 0 for low, high in LENGTH_BANDS}
    for normalized, length, suggestion in rows:
        if suggestion == SUGGEST_KEEP or normalized in decisions:
            continue
        low, high = next(band for band in LENGTH_BANDS if band[0] <= length <= band[1])
        to_review[_band_label(low, high)] += 1

    return {
        "words": len(rows),
        "suggestions": dict(Counter(row[2] for row in rows)),
        "decisions": dict(Counter(decisions.values())),
        "to_review_by_length": to_review,
    }


def _band_label(low: int, high: int) -> str:
    return f"{low}+" if high >= 99 else f"{low}-{high}"
