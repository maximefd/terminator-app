"""Mise à jour du lexique curé pendant le tri : export en arrière-plan tous les N mots triés.

L'API de Terminator surveille le fichier exporté et le recharge d'elle-même (backend/lexicon_loader.py) :
tous les 500 mots triés, les grilles générées utilisent le lexique à jour.

L'export applique **les mêmes règles automatiques que la file de tri** : un mot retiré du tri par une
règle doit aussi quitter le lexique, sinon il resterait invisible à l'auteur tout en continuant de
remplir ses grilles.
"""

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from tools.lexicon.export import FILTER_NONE, FILTERS, export_curated

DEFAULT_EXPORT_EVERY = 500


class LexiconExporter:
    def __init__(self, db_path, decisions_path, out_path, every: int = DEFAULT_EXPORT_EVERY,
                 export: Callable = export_curated, background: bool = True,
                 auto_rules=(), filter_level: str = FILTER_NONE):
        if every < 1:
            raise ValueError("CURATOR_EXPORT_EVERY doit être un entier positif.")
        if filter_level not in FILTERS:
            raise ValueError(f"CURATOR_EXPORT_FILTER doit valoir {' ou '.join(FILTERS)}.")
        self.db_path, self.decisions_path, self.out_path = Path(db_path), Path(decisions_path), Path(out_path)
        self.every = every
        self.auto_rules = tuple(auto_rules)
        self.filter_level = filter_level
        self._export = export
        self._background = background
        self._lock = threading.Lock()
        self._milestone = 0
        self._status = {"state": "idle", "exported_at": None, "words": None, "deleted": None,
                        "deleted_by_rule": None, "decided_at_export": None, "error": None}

    def prime(self, decided_total: int) -> None:
        """Palier de départ : pas d'export au démarrage, seulement au prochain palier franchi."""
        with self._lock:
            self._milestone = decided_total // self.every

    def observe(self, decided_total: int) -> bool:
        """Lance un export si un nouveau palier (500, 1 000…) vient d'être franchi."""
        milestone = decided_total // self.every
        with self._lock:
            if milestone <= self._milestone:
                return False
            self._milestone = milestone
        return self.start(decided_total)

    def start(self, decided_total: int) -> bool:
        """Lance un export (sauf s'il y en a déjà un en cours)."""
        with self._lock:
            if self._status["state"] == "running":
                return False
            self._status = {**self._status, "state": "running", "error": None}
        if self._background:
            threading.Thread(target=self._run, args=(decided_total,), name="lexicon-export", daemon=True).start()
        else:
            self._run(decided_total)
        return True

    def _run(self, decided_total: int) -> None:
        try:
            counts = self._export(self.db_path, self.decisions_path, self.out_path,
                                  auto_rules=self.auto_rules, filter_level=self.filter_level)
        except Exception:
            logging.exception("Export du lexique curé impossible")
            with self._lock:
                self._status = {**self._status, "state": "error", "error": "La mise à jour du lexique a échoué."}
            return
        with self._lock:
            self._status = {
                "state": "done",
                "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "words": counts.get("exported", 0),
                "deleted": counts.get("deleted_by_author", 0),
                "deleted_by_rule": counts.get("deleted_by_rule", 0) + counts.get("deleted_by_filter", 0),
                "decided_at_export": decided_total,
                "error": None,
            }

    def snapshot(self) -> dict:
        with self._lock:
            return {**self._status, "every": self.every, "next_at": (self._milestone + 1) * self.every,
                    "auto_rules": list(self.auto_rules), "filter": self.filter_level}
