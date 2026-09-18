"""Décisions de curation : lecture et écriture sérialisées du fichier data/lexicon/decisions.csv."""

import threading
from pathlib import Path

from tools.lexicon.decisions import (
    REVISION,
    DecisionRow,
    append_decisions,
    effective_decisions,
    read_decisions,
    undo_last_batch,
)


class DecisionStore:
    """Toutes les écritures passent par un verrou ; l'état est relu si le fichier change
    (y compris hors de l'application, par exemple après un `git pull`)."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._signature = None
        self._rows: list[DecisionRow] = []
        self._state: dict[str, str] = {}

    def _refresh(self) -> None:
        signature = (self.path.stat().st_mtime_ns, self.path.stat().st_size) if self.path.exists() else None
        if signature != self._signature:
            self._rows = read_decisions(self.path)
            self._state = effective_decisions(self._rows)
            self._signature = signature

    def state(self) -> dict[str, str]:
        with self._lock:
            self._refresh()
            return dict(self._state)

    def rows(self) -> list[DecisionRow]:
        with self._lock:
            self._refresh()
            return list(self._rows)

    def append(self, words: list[str], decision: str) -> str:
        with self._lock:
            batch = append_decisions(self.path, words, decision)
            self._signature = None
            return batch

    def revise(self, words: list[str], decision: str) -> str:
        """Deuxième regard : même écriture, dans un lot marqué « revision ».

        Le mot ne revient plus dans la liste des décisions à revoir, même si la décision
        ne change pas (voir tools/lexicon/review.py).
        """
        with self._lock:
            batch = append_decisions(self.path, words, decision, kind=REVISION)
            self._signature = None
            return batch

    def undo(self) -> list[str]:
        with self._lock:
            words = undo_last_batch(self.path)
            self._signature = None
            return words
