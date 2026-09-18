"""Accès en lecture seule à la base du lexique."""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Callable

from tools.lexicon.autorules import COMPOSED_FORM, condition

# Les requêtes joignent le lemme : les règles automatiques en ont besoin, et la carte « famille »
# affiche la fréquence du lemme.
FROM_WORDS = "words w LEFT JOIN words l ON l.norm = w.lemma_norm"
FIELDS = ("w.norm, w.display_forms, w.definition, w.definition_kind, w.zipf, w.lemma, w.lemma_norm, "
          "w.pos, w.suggestion, w.length, w.queue_order")
QUEUE_SUGGESTIONS = ("likely_delete", "review", "likely_keep")
SCAN_BATCH = 500
# Une famille montre au plus ce nombre de formes : au-delà, la carte ne se lit plus
MAX_FAMILY_FORMS = 40
# En deçà, ce n'est pas une famille : un nom et son pluriel se jugent aussi vite mot à mot.
# Mesure sur le lexique : 91 188 « familles » de 1 ou 2 formes contre 19 190 vraies familles.
MIN_FAMILY_FORMS = 3
# `COMPOSED_FORM` (importé plus haut) : les formes en plusieurs mots (« à eau », « as de ») ne font
# jamais famille, même quand les règles automatiques sont désactivées.


class LexiconRepository:
    """`auto_rules` : identifiants des règles automatiques activées (voir tools/lexicon/autorules.py).

    Les mots qu'elles visent ne sont plus proposés au tri ni comptés dans le reste à trier.
    """

    def __init__(self, db_path, auto_rules=()):
        self.db_path = Path(db_path).resolve()
        self.auto_rules = tuple(auto_rules)
        self._auto_clause = condition(self.auto_rules)
        self._local = threading.local()

    def connection(self) -> sqlite3.Connection:
        """Une connexion par thread, ouverte en lecture seule : la mini-app ne peut pas modifier la base."""
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(f"{self.db_path.as_uri()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            self._local.connection = connection
        return connection

    @property
    def _not_ruled_out(self) -> str:
        """Fragment SQL : « ce mot n'est visé par aucune règle activée » (toujours vrai sans règle)."""
        return f"NOT {self._auto_clause}" if self._auto_clause else "1 = 1"

    @staticmethod
    def _card(row: sqlite3.Row) -> dict:
        card = dict(row)
        card["forms"] = json.loads(card.pop("display_forms"))
        return card

    def queue(self, after: int, limit: int, min_length: int, max_length: int,
              suggestion: str | None, is_decided: Callable[[str], bool]) -> tuple[list[dict], int]:
        """Prochains mots à trier (hors mots courants, mots décidés et mots visés par une règle).

        Renvoie les cartes et la position de reprise (`queue_order` du dernier mot examiné).
        """
        suggestion_condition = "w.suggestion = ?" if suggestion else "w.suggestion != 'keep'"
        cards: list[dict] = []
        cursor = after
        while len(cards) < limit:
            params = [cursor] + ([suggestion] if suggestion else []) + [min_length, max_length]
            rows = self.connection().execute(
                f"SELECT {FIELDS} FROM {FROM_WORDS} WHERE w.queue_order > ? AND {suggestion_condition} "
                f"AND w.length BETWEEN ? AND ? AND {self._not_ruled_out} "
                f"ORDER BY w.queue_order LIMIT {SCAN_BATCH}",
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

    def families(self, after: int, limit: int, min_length: int, max_length: int,
                 is_decided: Callable[[str], bool]) -> tuple[list[dict], int]:
        """Prochaines familles à trier : un lemme, sa définition, sa fréquence et ses formes.

        Une famille doit avoir au moins `MIN_FAMILY_FORMS` formes encore à trier : en dessous,
        les mots restent dans le tri mot à mot, où ils se jugent aussi vite. Les formes en
        plusieurs mots (« abeille charpentière ») ne font jamais famille.

        Les familles sont rangées comme le premier de leurs mots dans la file (les plus courts
        d'abord), ce qui garde la même position de reprise que le tri mot à mot.
        """
        families: list[dict] = []
        cursor = after
        while len(families) < limit:
            rows = self.connection().execute(
                f"SELECT COALESCE(w.lemma_norm, w.norm) AS family, MIN(w.queue_order) AS family_order "
                f"FROM {FROM_WORDS} WHERE w.queue_order > ? AND w.suggestion != 'keep' "
                f"AND w.length BETWEEN ? AND ? AND NOT {COMPOSED_FORM} AND {self._not_ruled_out} "
                f"GROUP BY family ORDER BY family_order LIMIT {SCAN_BATCH}",
                [cursor, min_length, max_length],
            ).fetchall()
            if not rows:
                break
            for row in rows:
                cursor = row["family_order"]
                card = self.family_card(row["family"], is_decided)
                if card is None:
                    continue
                families.append(card)
                if len(families) == limit:
                    break
        return families, cursor

    def family_card(self, family: str, is_decided: Callable[[str], bool]) -> dict | None:
        """Carte d'une famille, ou None si elle n'a pas assez de formes à trier.

        Chaque forme porte sa propre définition : c'est ce qui permet de voir qu'une famille
        mélange deux mots (« hier », l'adverbe, et « hier », le verbe qui damait les pavés) et de
        les trier séparément.
        """
        rows = self.connection().execute(
            f"SELECT {FIELDS} FROM {FROM_WORDS} "
            f"WHERE (w.lemma_norm = ? OR w.norm = ?) AND NOT {COMPOSED_FORM} AND {self._not_ruled_out} "
            f"ORDER BY w.length, w.norm",
            [family, family],
        ).fetchall()
        if not rows:
            return None

        forms = [self._card(row) for row in rows]
        pending = [form for form in forms if form["suggestion"] != "keep" and not is_decided(form["norm"])]
        if len(pending) < MIN_FAMILY_FORMS:
            return None

        head = next((form for form in forms if form["norm"] == family), None) or pending[0]
        lemma_zipf = max(form["zipf"] for form in forms)
        return {
            "family": family,
            "lemma": head["lemma"] or head["forms"][0],
            "norm": head["norm"],
            "definition": head["definition"] or next((f["definition"] for f in forms if f["definition"]), None),
            "definition_kind": head["definition_kind"],
            "pos": head["pos"],
            "zipf": lemma_zipf,
            "forms": [{"norm": form["norm"], "form": form["forms"][0], "length": form["length"],
                       "suggestion": form["suggestion"], "decided": is_decided(form["norm"]),
                       "protected": form["suggestion"] == "keep", "definition": form["definition"],
                       "zipf": form["zipf"]}
                      for form in forms[:MAX_FAMILY_FORMS]],
            "total_forms": len(forms),
            "pending": [form["norm"] for form in pending],
            "pending_count": len(pending),
        }

    def cards(self, words: list[str]) -> list[dict]:
        """Cartes des mots demandés, dans l'ordre demandé (mots inconnus ignorés)."""
        if not words:
            return []
        placeholders = ", ".join("?" for _ in words)
        rows = self.connection().execute(
            f"SELECT {FIELDS} FROM {FROM_WORDS} WHERE w.norm IN ({placeholders})", words)
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

    def family_key(self, word: str) -> str | None:
        """Nom de la famille d'un mot : son lemme, ou lui-même s'il est le lemme."""
        row = self.connection().execute(
            "SELECT COALESCE(lemma_norm, norm) AS family FROM words WHERE norm = ?", (word,)
        ).fetchone()
        return row["family"] if row else None

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
        """Nombre de mots à trier (hors mots courants et mots visés par une règle) par longueur."""
        rows = self.connection().execute(
            f"SELECT w.length AS length, COUNT(*) AS total FROM {FROM_WORDS} "
            f"WHERE w.suggestion != 'keep' AND {self._not_ruled_out} GROUP BY w.length"
        )
        return {row["length"]: row["total"] for row in rows}

    def handled_by_rules(self) -> int:
        """Mots que les règles activées retirent du tri (0 si aucune règle)."""
        if not self._auto_clause:
            return 0
        row = self.connection().execute(
            f"SELECT COUNT(*) AS total FROM {FROM_WORDS} "
            f"WHERE w.suggestion != 'keep' AND {self._auto_clause}"
        ).fetchone()
        return row["total"]
