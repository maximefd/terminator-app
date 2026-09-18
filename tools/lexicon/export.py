"""Export du lexique curé et statistiques de curation."""

import csv
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

from .autorules import FROM_CLAUSE, condition
from .decisions import DELETE, KEEP, effective_decisions, read_decisions
from .scoring import KEEP as SUGGEST_KEEP
from .scoring import LIKELY_DELETE

LENGTH_BANDS = ((2, 5), (6, 8), (9, 11), (12, 99))

# Filtre « positif » : au lieu de ne retirer que ce qui a été trié, ne garder que ce qui a une
# chance d'être un vrai mot. Mesuré sur les décisions de l'auteur : « moyen » conserve les
# conjugaisons des verbes ordinaires (ce qu'il garde) et retire les formes des verbes inconnus.
FILTER_NONE = "aucun"
FILTER_MEDIUM = "moyen"
FILTERS = (FILTER_NONE, FILTER_MEDIUM)
# Un mot passe le filtre « moyen » s'il est connu de Lexique, défini pour lui-même,
# ou formé sur un lemme au moins un peu courant.
MEDIUM_LEMMA_ZIPF = 2.0


def _select(auto_rules) -> str:
    clause = condition(auto_rules or ())
    auto = f"({clause})" if clause else "0"
    return (f"SELECT w.norm, w.display_forms, w.definition, w.zipf, w.suggestion, "
            f"COALESCE(w.definition_kind, '') AS kind, COALESCE(l.zipf, 0) AS lemma_zipf, "
            f"{auto} AS auto_hit, w.length FROM {FROM_CLAUSE}")


def _passes_medium(zipf: float, kind: str, lemma_zipf: float) -> bool:
    return zipf > 0 or kind == "own" or lemma_zipf >= MEDIUM_LEMMA_ZIPF


def export_curated(db_path, decisions_path, out_path, exclude_suggested_deletes: bool = False,
                   filter_level: str = FILTER_NONE, auto_rules=()) -> dict:
    """Écrit le lexique curé au format `MOT;forme affichée;définition;zipf`.

    Retire, dans cet ordre : les mots supprimés par l'auteur, ceux visés par une règle
    automatique activée (`autorules`), ceux suggérés « likely_delete » si
    `exclude_suggested_deletes`, puis ceux qui ne passent pas `filter_level`.
    **Un mot explicitement gardé n'est jamais retiré.**

    La première colonne est compatible avec `DictionnaireTrie.load_dela_csv` (backend).
    """
    if filter_level not in FILTERS:
        raise ValueError(f"filtre inconnu : {filter_level} (attendu : {', '.join(FILTERS)})")
    decisions = effective_decisions(read_decisions(decisions_path))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp")

    counts: Counter = Counter()
    connection = sqlite3.connect(db_path)
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";", lineterminator="\n")
            query = f"{_select(auto_rules)} ORDER BY w.norm"
            for norm, forms, definition, zipf, suggestion, kind, lemma_zipf, auto_hit, _length in \
                    connection.execute(query):
                decision = decisions.get(norm)
                if decision == DELETE:
                    counts["deleted_by_author"] += 1
                    continue
                if decision != KEEP:
                    if auto_hit:
                        counts["deleted_by_rule"] += 1
                        continue
                    if exclude_suggested_deletes and suggestion == LIKELY_DELETE:
                        counts["deleted_by_suggestion"] += 1
                        continue
                    if filter_level == FILTER_MEDIUM and not _passes_medium(zipf, kind, lemma_zipf):
                        counts["deleted_by_filter"] += 1
                        continue
                writer.writerow([norm, json.loads(forms)[0], definition or "", zipf])
                counts["exported"] += 1
    finally:
        connection.close()
    os.replace(tmp_path, out_path)
    return dict(counts)


def lexicon_stats(db_path, decisions_path, auto_rules=()) -> dict:
    """Avancement de la curation : décisions, mots restant à trier par tranche de longueur.

    Les mots visés par une règle automatique activée ne sont plus à trier : ils sont comptés
    à part (`handled_by_rules`).
    """
    decisions = effective_decisions(read_decisions(decisions_path))
    connection = sqlite3.connect(db_path)
    try:
        query = (f"SELECT w.norm, w.length, w.suggestion, {_auto_expression(auto_rules)} AS auto_hit "
                 f"FROM {FROM_CLAUSE}")
        rows = connection.execute(query).fetchall()
    finally:
        connection.close()

    to_review = {_band_label(low, high): 0 for low, high in LENGTH_BANDS}
    handled_by_rules = 0
    for normalized, length, suggestion, auto_hit in rows:
        if suggestion == SUGGEST_KEEP or normalized in decisions:
            continue
        if auto_hit:
            handled_by_rules += 1
            continue
        low, high = next(band for band in LENGTH_BANDS if band[0] <= length <= band[1])
        to_review[_band_label(low, high)] += 1

    return {
        "words": len(rows),
        "suggestions": dict(Counter(row[2] for row in rows)),
        "decisions": dict(Counter(decisions.values())),
        "to_review_by_length": to_review,
        "handled_by_rules": handled_by_rules,
        "auto_rules": list(auto_rules or ()),
    }


def _auto_expression(auto_rules) -> str:
    clause = condition(auto_rules or ())
    return f"({clause})" if clause else "0"


def _band_label(low: int, high: int) -> str:
    return f"{low}+" if high >= 99 else f"{low}-{high}"
