"""Deuxième regard : retrouver les décisions douteuses pour les confirmer ou les corriger.

Trier 500 mots d'affilée fatigue, et la fatigue laisse des traces mesurables dans
`decisions.csv` : deux formes du même verbe traitées à l'opposé, un mot courant supprimé,
plusieurs décisions dans la même seconde. Ce module les retrouve ; le curateur les repropose
une par une (« Révision »).

Confirmer ou corriger écrit une nouvelle ligne dans `decisions.csv`, dans un lot marqué
`revision` : le mot ne revient donc plus dans la liste, même si la décision ne change pas.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .decisions import (
    DELETE,
    KEEP,
    REVISION,
    append_decisions,
    batch_kind,
    batch_sizes,
    effective_rows,
    read_decisions,
)

# Raisons de revoir une décision, de la plus parlante à la moins parlante
MIXED_FAMILY = "famille-incoherente"
FREQUENT_DELETED = "mot-courant-supprime"
FLASH_DECISION = "decision-eclair"
REASONS = (MIXED_FAMILY, FREQUENT_DELETED, FLASH_DECISION)

# Un mot de cette fréquence supprimé mérite une deuxième lecture (zipf 2,5 ≈ 3 fois par million)
FREQUENT_ZIPF = 2.5
# Nombre de décisions prises dans la même seconde au-delà duquel on soupçonne un appui répété
FLASH_BURST = 3


def _family_key(detail: dict) -> str:
    """Un lemme absent de Lexique n'a pas de `lemma_norm` : il se regroupe alors sous son propre nom,
    ce qui range « ouvrager » avec « ouvrageâmes »."""
    return detail.get("lemma_norm") or detail["norm"]


def _word_details(connection, words: list[str]) -> dict[str, dict]:
    details: dict[str, dict] = {}
    for start in range(0, len(words), 900):  # limite de variables SQLite
        chunk = words[start:start + 900]
        placeholders = ", ".join("?" for _ in chunk)
        rows = connection.execute(
            f"SELECT norm, display_forms, definition, zipf, lemma, lemma_norm, length "
            f"FROM words WHERE norm IN ({placeholders})", chunk
        )
        for norm, forms, definition, zipf, lemma, lemma_norm, length in rows:
            details[norm] = {
                "norm": norm,
                "form": (json.loads(forms) or [norm.lower()])[0],
                "definition": definition,
                "zipf": zipf,
                "lemma": lemma,
                "lemma_norm": lemma_norm,
                "length": length,
            }
    return details


def _mixed_families(solo: dict[str, str], details: dict[str, dict]) -> dict[str, str]:
    """Familles dont les formes ont été jugées à l'opposé, mot à mot : mot -> détail."""
    by_family: dict[str, dict[str, list[str]]] = {}
    for word, decision in solo.items():
        detail = details.get(word)
        if detail is None:
            continue
        by_family.setdefault(_family_key(detail), {KEEP: [], DELETE: []})[decision].append(word)

    suspicious_words: dict[str, str] = {}
    for family, sides in by_family.items():
        if not (sides[KEEP] and sides[DELETE]):
            continue
        detail = (f"Dans la famille « {family.lower()} », vous avez gardé "
                  f"{len(sides[KEEP])} forme(s) et supprimé {len(sides[DELETE])} forme(s).")
        for word in sides[KEEP] + sides[DELETE]:
            suspicious_words[word] = detail
    return suspicious_words


def _flash_decisions(rows, solo: dict[str, str]) -> set[str]:
    """Mots décidés lors d'une rafale : au moins `FLASH_BURST` décisions dans la même seconde."""
    by_second: dict[str, list[str]] = {}
    for row in rows:
        if row.word in solo:
            by_second.setdefault(row.date, []).append(row.word)
    return {word for words in by_second.values() if len(words) >= FLASH_BURST for word in words}


def suspicious(db_path, decisions_path, limit: int | None = None) -> list[dict]:
    """Décisions à revoir, les plus parlantes d'abord (déjà revues : exclues).

    Sans `limit`, la liste est complète : c'est elle qui donne le compte à afficher. Tronquer
    avant de compter donnerait « 5 décisions à revoir » au lieu du vrai total.
    """
    rows = read_decisions(decisions_path)
    current = effective_rows(rows)
    sizes = batch_sizes(rows)

    # On ne revient que sur les décisions prises mot à mot et jamais revues :
    # une suppression par famille est un geste volontaire, pas une erreur de fatigue.
    solo = {word: row.decision for word, row in current.items()
            if sizes.get(row.batch, 1) == 1 and batch_kind(row.batch) != REVISION}
    if not solo:
        return []

    connection = sqlite3.connect(db_path)
    try:
        details = _word_details(connection, list(solo))
    finally:
        connection.close()

    mixed = _mixed_families(solo, details)
    flash = _flash_decisions([row for row in rows if row.word in solo], solo)

    found: list[dict] = []
    for word, decision in solo.items():
        detail = details.get(word)
        if detail is None:
            continue
        if word in mixed:
            reason, explanation = MIXED_FAMILY, mixed[word]
        elif decision == DELETE and detail["zipf"] >= FREQUENT_ZIPF:
            reason = FREQUENT_DELETED
            explanation = (f"Vous avez supprimé ce mot alors qu'il est courant "
                           f"(fréquence {detail['zipf']:.1f}).")
        elif word in flash:
            reason = FLASH_DECISION
            explanation = (f"Plusieurs décisions dans la même seconde : « {detail['form']} » est "
                           f"peut-être passé sans être lu.")
        else:
            continue
        found.append({**detail, "decision": decision, "reason": reason, "explanation": explanation,
                      "decided_at": current[word].date})

    found.sort(key=lambda item: (REASONS.index(item["reason"]), item["norm"]))
    return found if limit is None else found[:limit]


def counts_by_reason(items: list[dict]) -> dict[str, int]:
    return {reason: sum(1 for item in items if item["reason"] == reason) for reason in REASONS}


def revise(decisions_path, words: list[str], decision: str, now: datetime | None = None) -> str:
    """Confirme ou corrige une décision : nouvelle ligne dans un lot marqué « revision »."""
    return append_decisions(decisions_path, words, decision, now=now, kind=REVISION)


def family_of(db_path, word: str, decisions: dict[str, str]) -> list[dict]:
    """Les formes du même lemme et leur décision, pour juger la famille d'un coup d'œil.

    Le lemme lui-même en fait partie, même quand il est absent de Lexique (`lemma_norm` vide).
    """
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute("SELECT lemma_norm FROM words WHERE norm = ?", (word,)).fetchone()
        if row is None:
            return []
        keys = sorted({word, row[0]} - {None})
        placeholders = ", ".join("?" for _ in keys)
        rows = connection.execute(
            f"SELECT norm, display_forms, length FROM words "
            f"WHERE norm IN ({placeholders}) OR lemma_norm IN ({placeholders}) "
            f"ORDER BY length, norm",
            [*keys, *keys],
        ).fetchall()
    finally:
        connection.close()
    return [{"norm": norm, "form": (json.loads(forms) or [norm.lower()])[0], "length": length,
             "decision": decisions.get(norm)} for norm, forms, length in rows]


def report(db_path, decisions_path, limit: int = 200) -> dict:
    """Résumé pour la ligne de commande : les comptes portent sur tout, la liste est tronquée."""
    items = suspicious(db_path, decisions_path)
    return {"total": len(items), "by_reason": counts_by_reason(items),
            "items": [{key: item[key] for key in ("norm", "form", "decision", "reason", "explanation")}
                      for item in items[:limit]]}


def default_paths(repo_root: Path) -> tuple[Path, Path]:
    return (repo_root / "data" / "lexicon" / "build" / "lexicon.sqlite",
            repo_root / "data" / "lexicon" / "decisions.csv")
