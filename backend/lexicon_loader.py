# DANS backend/lexicon_loader.py
"""
Lexique de l'API : chargement et rechargement à chaud (Phase 1c).

L'API utilise le lexique curé (`LEXICON_PATH`, produit par `tools.lexicon export` ou par le
curateur tous les 500 mots triés) s'il existe, sinon le DELA complet. Quand le fichier change,
le nouveau Trie est construit à côté de l'ancien puis remplacé d'un coup : les requêtes en cours
gardent l'ancien lexique, les suivantes utilisent le nouveau. Aucun redémarrage n'est nécessaire.
"""

import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from engine.word_repository import prepare_lexicon
from layout_catalog import available_formats
from trie_engine import DictionnaireTrie

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_LEXICON_PATH = BACKEND_DIR / "dela_clean.csv"


@dataclass(frozen=True)
class LexiconInfo:
    source: str       # nom du fichier chargé
    curated: bool     # True : lexique curé ; False : DELA complet (repli)
    words: int
    loaded_at: str

    def as_dict(self) -> dict:
        return asdict(self)


def longest_grid_side() -> int:
    """Plus long mot qu'une grille du catalogue peut accueillir : son plus grand côté."""
    return max((max(f["width"], f["height"]) for f in available_formats()), default=0)


def load_trie(path: Path) -> DictionnaireTrie:
    trie = DictionnaireTrie()
    trie.load_dela_csv(str(path))
    # Index construits ici, une fois, plutôt qu'à la première génération de chaque longueur : lors
    # d'un rechargement, c'est l'ancien lexique qui sert pendant ce temps (ADR 0013).
    prepare_lexicon(trie, longest_grid_side())
    return trie


class LexiconManager:
    def __init__(self, preferred_path=None, fallback_path=DEFAULT_LEXICON_PATH,
                 loader: Callable[[Path], DictionnaireTrie] = load_trie):
        self.preferred_path = Path(preferred_path) if preferred_path else None
        self.fallback_path = Path(fallback_path)
        self._loader = loader
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._signature = None
        self.trie: DictionnaireTrie | None = None
        self.info: LexiconInfo | None = None

    def _source(self) -> Path:
        if self.preferred_path and self.preferred_path.exists():
            return self.preferred_path
        return self.fallback_path

    def check(self) -> bool:
        """(Re)charge le lexique si la source ou son contenu a changé. Renvoie True en cas de rechargement."""
        with self._lock:
            source = self._source()
            try:
                stat = source.stat()
            except FileNotFoundError:
                logging.error("Lexique introuvable : %s", source)
                return False
            signature = (str(source), stat.st_mtime_ns, stat.st_size)
            if signature == self._signature:
                return False

            started = time.monotonic()
            trie = self._loader(source)
            self.trie = trie
            self.info = LexiconInfo(
                source=source.name,
                curated=source != self.fallback_path,
                words=len(trie.words),
                loaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            self._signature = signature
            logging.info("Lexique chargé : %s (%s mots, %.1f s)", source, len(trie.words), time.monotonic() - started)
            return True

    def start_watching(self, interval_s: float, on_reload: Callable[["LexiconManager"], None]) -> threading.Thread:
        """Surveille la source en arrière-plan et appelle `on_reload` après chaque rechargement."""
        def watch():
            while not self._stop.wait(interval_s):
                try:
                    if self.check():
                        on_reload(self)
                except Exception:
                    logging.exception("Rechargement du lexique impossible")

        thread = threading.Thread(target=watch, name="lexicon-watcher", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()
