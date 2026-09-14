"""
Décisions de curation : data/lexicon/decisions.csv (versionné, en ajout seul).

Format : `mot;decision;date;lot`
- `mot` : forme normalisée (celle des grilles), ex. `OUVRAGEAMES`
- `decision` : `keep`, `delete` ou `undo`
- `lot` : identifiant commun aux mots décidés en une seule action (ex. un mot et toutes ses formes)

Une ligne `undo` annule tout son lot. La décision effective d'un mot est la dernière qui
n'appartient pas à un lot annulé : annuler un « garder » fait revenir un « supprimer » antérieur.
"""

import csv
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

KEEP = "keep"
DELETE = "delete"
UNDO = "undo"
VALID_DECISIONS = (KEEP, DELETE, UNDO)
FIELDS = ["mot", "decision", "date", "lot"]
NORMALIZED_WORD = re.compile(r"[A-Z0-9]{2,}")


@dataclass(frozen=True)
class DecisionRow:
    word: str
    decision: str
    date: str
    batch: str


def read_decisions(path) -> list[DecisionRow]:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for line_number, row in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            if row["decision"] not in VALID_DECISIONS:
                raise ValueError(f"{path}:{line_number} : décision inconnue « {row['decision']} »")
            rows.append(DecisionRow(row["mot"], row["decision"], row["date"], row["lot"]))
    return rows


def _undone_batches(rows: list[DecisionRow]) -> set[str]:
    return {row.batch for row in rows if row.decision == UNDO}


def effective_decisions(rows: list[DecisionRow]) -> dict[str, str]:
    """Mot -> `keep` ou `delete` (les mots sans décision sont absents)."""
    undone = _undone_batches(rows)
    state: dict[str, str] = {}
    for row in rows:
        if row.decision != UNDO and row.batch not in undone:
            state[row.word] = row.decision
    return state


def _append_rows(path: Path, rows: list[DecisionRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        if is_new:
            writer.writerow(FIELDS)
        writer.writerows([row.word, row.decision, row.date, row.batch] for row in rows)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def append_decisions(path, words: list[str], decision: str, now: datetime | None = None) -> str:
    """Enregistre la même décision pour un ou plusieurs mots ; renvoie l'identifiant du lot."""
    if decision not in (KEEP, DELETE):
        raise ValueError(f"décision invalide : {decision}")
    if not words:
        raise ValueError("aucun mot à enregistrer")
    for word in words:
        if not NORMALIZED_WORD.fullmatch(word):
            raise ValueError(f"mot non normalisé : {word!r}")
    moment = _now(now)
    batch = f"{moment:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
    date = moment.isoformat(timespec="seconds")
    _append_rows(Path(path), [DecisionRow(word, decision, date, batch) for word in dict.fromkeys(words)])
    return batch


def undo_last_batch(path, now: datetime | None = None) -> list[str]:
    """Annule le dernier lot encore actif ; renvoie ses mots (liste vide s'il n'y a rien à annuler)."""
    path = Path(path)
    rows = read_decisions(path)
    undone = _undone_batches(rows)
    last_batch = next((row.batch for row in reversed(rows)
                       if row.decision != UNDO and row.batch not in undone), None)
    if last_batch is None:
        return []
    words = [row.word for row in rows if row.batch == last_batch and row.decision != UNDO]
    date = _now(now).isoformat(timespec="seconds")
    _append_rows(path, [DecisionRow(word, UNDO, date, last_batch) for word in words])
    return words
