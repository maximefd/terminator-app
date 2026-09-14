"""Accès en lecture seule à la base du lexique."""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Callable

FIELDS = ("norm, display_forms, definition, definition_kind, zipf, lemma, lemma_norm, pos, "
          "suggestion, length, queue_order")
QUEUE_SUGGESTIONS = ("likely_delete", "review", "likely_keep")
SCAN_BATCH = 500


class LexiconRepository:
    def __init__(self, db_path):
        self.db_path = Path(db_path).resolve()
        self._local = threading.local()

    def connection(self) -> sqlite3.Connection:
        """Une connexion par thread, ouverte en lecture seule : la mini-app ne peut pas modifier la base."""
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(f"{self.db_path.as_uri()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            self._local.connection = connection
        return connection

    @staticmethod
    def _card(row: sqlite3.Row) -> dict:
        card = dict(row)
        card["forms"] = json.loads(card.pop("display_forms"))
        return card

    def queue(self, after: int, limit: int, min_length: int, max_length: int,
              suggestion: str | None, is_decided: Callable[[str], bool]) -> tuple[list[dict], int]:
        """Prochains mots à trier (hors mots courants et mots déjà décidés).

        Renvoie les cartes et la position de reprise (`queue_order` du dernier mot examiné).
        """
        condition = "suggestion = ?" if suggestion else "suggestion != 'keep'"
        cards: list[dict] = []
        cursor = after
        while len(cards) < limit:
            params = [cursor] + ([suggestion] if suggestion else []) + [min_length, max_length]
            rows = self.connection().execute(
                f"SELECT {FIELDS} FROM words WHERE queue_order > ? AND {condition} "
                f"AND length BETWEEN ? AND ? ORDER BY queue_order LIMIT {SCAN_BATCH}",
                params,
            ).fetchall()
            if not rows:
                break
            for row in rows:
                cursor = row["queue_order"]
                if is_decided(row["norm"]):
                    continue
                cards.append(self._card(row))
                if len(cards) == limit:
                    break
        return cards, cursor

    def cards(self, words: list[str]) -> list[dict]:
        """Cartes des mots demandés, dans l'ordre demandé (mots inconnus ignorés)."""
        if not words:
            return []
        placeholders = ", ".join("?" for _ in words)
        rows = self.connection().execute(f"SELECT {FIELDS} FROM words WHERE norm IN ({placeholders})", words)
        by_word = {row["norm"]: self._card(row) for row in rows}
        return [by_word[word] for word in words if word in by_word]

    def existing(self, words: list[str]) -> set[str]:
        return {card["norm"] for card in self.cards(list(dict.fromkeys(words)))}

    def family(self, word: str) -> list[tuple[str, str]]:
        """Le mot, son lemme et toutes les formes du même lemme : [(mot, suggestion)]."""
        row = self.connection().execute("SELECT lemma_norm FROM words WHERE norm = ?", (word,)).fetchone()
        if row is None:
            return []
        keys = {word, row["lemma_norm"]} - {None}
        placeholders = ", ".join("?" for _ in keys)
        rows = self.connection().execute(
            f"SELECT norm, suggestion FROM words WHERE norm = ? OR norm IN ({placeholders}) "
            f"OR lemma_norm IN ({placeholders}) ORDER BY queue_order",
            [word, *keys, *keys],
        )
        return [(r["norm"], r["suggestion"]) for r in rows]

    def suggestions(self, words: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for start in range(0, len(words), 900):  # limite de variables SQLite
            chunk = words[start:start + 900]
            placeholders = ", ".join("?" for _ in chunk)
            for row in self.connection().execute(
                f"SELECT norm, suggestion FROM words WHERE norm IN ({placeholders})", chunk
            ):
                result[row["norm"]] = row["suggestion"]
        return result

    def queue_totals_by_length(self) -> dict[int, int]:
        """Nombre de mots à trier (hors mots courants) par longueur."""
        rows = self.connection().execute(
            "SELECT length, COUNT(*) AS total FROM words WHERE suggestion != 'keep' GROUP BY length"
        )
        return {row["length"]: row["total"] for row in rows}
