"""Construction de la base locale du lexique (SQLite, reconstructible, jamais versionnée)."""

import hashlib
import json
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .readers import read_dela, read_lexique, read_wiktionary, resolve_definition, wiktionary_pos
from .scoring import SUGGESTIONS, Thresholds, suggest, zipf_from_per_million

SCHEMA = f"""
CREATE TABLE words (
    norm TEXT PRIMARY KEY,          -- forme normalisée (celle des grilles)
    length INTEGER NOT NULL,
    display_forms TEXT NOT NULL,    -- liste JSON des formes affichées
    zipf REAL NOT NULL,             -- 0 si absent de Lexique
    lemma TEXT,
    pos TEXT,
    definition TEXT,
    definition_kind TEXT CHECK (definition_kind IN ('own', 'inflection')),  -- NULL si pas de définition
    suggestion TEXT NOT NULL CHECK (suggestion IN ({", ".join(f"'{s}'" for s in SUGGESTIONS)}))
);
CREATE INDEX idx_words_queue ON words (length, zipf);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


@dataclass
class BuildStats:
    words: int
    with_frequency: int
    with_definition: int
    suggestions: dict[str, int]


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_lexicon(dela_path, lexique_path, db_path, wiktionary_path=None,
                  thresholds: Thresholds = Thresholds(), log: Callable[[str], None] = print) -> BuildStats:
    log(f"Lecture du DELA ({dela_path})…")
    dela = read_dela(dela_path)
    log(f"  {len(dela)} mots distincts")

    log(f"Lecture de Lexique ({lexique_path})…")
    lexique = read_lexique(lexique_path)
    log(f"  {len(lexique)} formes")

    wiktionary = {}
    if wiktionary_path:
        log(f"Lecture du Wiktionnaire ({wiktionary_path}), plusieurs minutes…")
        wiktionary = read_wiktionary(wiktionary_path, wanted=set(dela),
                                     progress=lambda n: log(f"  {n} articles lus"))
        log(f"  {len(wiktionary)} mots avec des données")

    rows = []
    for normalized, displays in dela.items():
        entry = lexique.get(normalized)
        zipf = zipf_from_per_million(entry.frequency) if entry else 0.0
        definition = resolve_definition(normalized, wiktionary, wiktionary_pos(entry.pos) if entry else None)
        forms = list(displays)
        if normalized in wiktionary:
            forms += [f for f in wiktionary[normalized].forms if f not in forms]
        # La forme affichée en premier (et exportée) est l'orthographe la plus fréquente selon Lexique
        if entry and entry.display in forms:
            forms.remove(entry.display)
            forms.insert(0, entry.display)
        rows.append((
            normalized,
            len(normalized),
            json.dumps(forms, ensure_ascii=False),
            zipf,
            entry.lemma if entry else None,
            entry.pos if entry else None,
            definition.text if definition else None,
            ("own" if definition.own else "inflection") if definition else None,
            suggest(zipf, bool(definition and definition.own), thresholds),
        ))

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_suffix(".tmp")
    tmp_path.unlink(missing_ok=True)

    sources = {"dela": {"file": Path(dela_path).name, "sha256": sha256_file(dela_path)},
               "lexique": {"file": Path(lexique_path).name, "sha256": sha256_file(lexique_path)}}
    if wiktionary_path:
        sources["wiktionary"] = {"file": Path(wiktionary_path).name, "sha256": sha256_file(wiktionary_path)}

    connection = sqlite3.connect(tmp_path)
    try:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO words VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        connection.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("thresholds", json.dumps(thresholds.as_dict())),
            ("sources", json.dumps(sources)),
        ])
        connection.commit()
    finally:
        connection.close()
    os.replace(tmp_path, db_path)  # la base n'est remplacée qu'une fois complète

    stats = BuildStats(
        words=len(rows),
        with_frequency=sum(1 for r in rows if r[3] > 0),
        with_definition=sum(1 for r in rows if r[6]),
        suggestions=dict(Counter(r[8] for r in rows)),
    )
    log(f"Base écrite : {db_path} ({stats.words} mots)")
    return stats
