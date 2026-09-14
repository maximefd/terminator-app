"""Lecture des sources : DELA, Lexique 3.83 et extrait du Wiktionnaire (kaikki.org)."""

import csv
import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from .normalize import is_usable, normalize_word

MAX_DEFINITION_LENGTH = 240


# --- DELA ---

def read_dela(path) -> dict[str, list[str]]:
    """Forme normalisée -> formes affichées (avec accents), dans l'ordre du fichier."""
    forms: dict[str, list[str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter=";"):
            if not row:
                continue
            normalized = normalize_word(row[0])
            if not is_usable(normalized):
                continue
            display = row[1].strip() if len(row) > 1 and row[1].strip() else row[0].strip().lower()
            known = forms.setdefault(normalized, [])
            if display not in known:
                known.append(display)
    return forms


# --- Lexique 3.83 ---

@dataclass
class LexiqueEntry:
    # Occurrences par million de mots (moyenne films / livres), cumulées sur les homographes
    frequency: float = 0.0
    lemma: str | None = None
    pos: str | None = None
    _best_row_frequency: float = field(default=-1.0, repr=False)


def _to_float(value: str | None) -> float:
    try:
        return float((value or "").replace(",", "."))
    except ValueError:
        return 0.0


def read_lexique(path) -> dict[str, LexiqueEntry]:
    """Forme normalisée -> fréquence cumulée, lemme et catégorie de la ligne la plus fréquente."""
    entries: dict[str, LexiqueEntry] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            normalized = normalize_word(row["ortho"])
            if not is_usable(normalized):
                continue
            row_frequency = (_to_float(row["freqfilms2"]) + _to_float(row["freqlivres"])) / 2
            entry = entries.setdefault(normalized, LexiqueEntry())
            entry.frequency += row_frequency
            if row_frequency > entry._best_row_frequency:
                entry._best_row_frequency = row_frequency
                entry.lemma = row["lemme"] or None
                entry.pos = row["cgram"] or None
    return entries


# --- Wiktionnaire (extrait kaikki.org, JSON Lines éventuellement compressé) ---

@dataclass
class WiktionaryEntry:
    definition: str | None = None   # première définition d'un sens « normal »
    form_gloss: str | None = None   # « Première personne du pluriel ... de ouvrager. »
    form_lemma: str | None = None   # « ouvrager »
    forms: list[str] = field(default_factory=list)


def _iter_jsonl(path) -> Iterator[dict]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_wiktionary(path, wanted: set[str] | None = None,
                    progress: Callable[[int], None] | None = None) -> dict[str, WiktionaryEntry]:
    """Définitions françaises par forme normalisée.

    Les définitions des sens « normaux » sont gardées pour tous les mots (elles servent aussi à
    expliquer les formes fléchies via leur lemme) ; les formes fléchies et formes affichées ne
    sont gardées que pour les mots de `wanted`, pour limiter la mémoire.
    """
    entries: dict[str, WiktionaryEntry] = {}
    for count, record in enumerate(_iter_jsonl(path), start=1):
        if progress and count % 200_000 == 0:
            progress(count)
        if record.get("lang_code") != "fr":
            continue
        word = record.get("word")
        normalized = normalize_word(word)
        if not is_usable(normalized):
            continue
        is_wanted = wanted is None or normalized in wanted

        for sense in record.get("senses") or []:
            glosses = [g.strip() for g in sense.get("glosses") or [] if isinstance(g, str) and g.strip()]
            if not glosses:
                continue
            is_form = "form-of" in (sense.get("tags") or []) or bool(sense.get("form_of"))
            if is_form:
                if not is_wanted:
                    continue
                entry = entries.setdefault(normalized, WiktionaryEntry())
                if entry.form_gloss is None:
                    entry.form_gloss = glosses[0]
                    targets = sense.get("form_of") or []
                    if targets and isinstance(targets[0], dict):
                        entry.form_lemma = targets[0].get("word")
            else:
                entry = entries.setdefault(normalized, WiktionaryEntry())
                if entry.definition is None:
                    entry.definition = glosses[0]
                break  # une vraie définition suffit pour cet article

        if is_wanted and normalized in entries and word not in entries[normalized].forms:
            entries[normalized].forms.append(word)
    return entries


def _shorten(text: str) -> str:
    if len(text) <= MAX_DEFINITION_LENGTH:
        return text
    cut = text[:MAX_DEFINITION_LENGTH].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def resolve_definition(normalized: str, wiktionary: dict[str, WiktionaryEntry]) -> str | None:
    """Définition à afficher : celle du mot, sinon « forme de X — définition de X »."""
    entry = wiktionary.get(normalized)
    if entry is None:
        return None
    if entry.definition:
        return _shorten(entry.definition)
    if entry.form_gloss:
        lemma_entry = wiktionary.get(normalize_word(entry.form_lemma)) if entry.form_lemma else None
        if lemma_entry and lemma_entry.definition:
            return _shorten(f"{entry.form_gloss} — {lemma_entry.definition}")
        return _shorten(entry.form_gloss)
    return None


def source_label(path) -> str:
    return Path(path).name
