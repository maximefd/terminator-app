# DANS backend/generation_slots.py
"""
Places de génération : combien de grilles se calculent à la fois, et une seule par visiteur.

Une génération occupe un cœur jusqu'à sa fin, parfois jusqu'au bout de son budget (20 s). Le rate
limiting compte les requêtes par minute, pas leur recouvrement : quelques demandes lancées ensemble
suffisent à saturer le serveur. Mesuré, quatre générations sur deux cœurs doublent la durée médiane et
poussent le pire cas au bord du budget ([ADR 0013](../docs/adr/0013-cible-hebergement-production.md)).
On borne donc la concurrence elle-même : au plus `max_concurrent` générations, une seule par visiteur.

Les places sont des verrous de fichiers (`flock`) : ils sont partagés entre les workers gunicorn, qui
sont des processus distincts, et le système les rend si un worker meurt en pleine génération.
"""

import contextlib
import fcntl
import hashlib
import os

# Un verrou par case d'un tableau haché plutôt que par visiteur : le nombre de fichiers reste borné.
# Deux visiteurs tombant dans la même case au même moment : le second attend son tour, rien de plus.
VISITOR_BUCKETS = 4096


class GenerationBusy(Exception):
    """Pas de place. `reason` : « visitor » (une génération de ce visiteur tourne déjà) ou « server »."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _try_lock(path: str):
    """Le fichier ouvert et verrouillé en exclusivité, ou None s'il l'est déjà (sans attendre)."""
    handle = open(path, "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


@contextlib.contextmanager
def generation_slot(lock_dir: str, visitor: str, max_concurrent: int):
    """Réserve une place de génération pour `visitor` le temps du bloc ; lève GenerationBusy sinon."""
    os.makedirs(lock_dir, mode=0o700, exist_ok=True)
    bucket = int.from_bytes(hashlib.sha256(visitor.encode()).digest()[:4], "big") % VISITOR_BUCKETS
    with contextlib.ExitStack() as held:
        own = _try_lock(os.path.join(lock_dir, f"visiteur-{bucket}.lock"))
        if own is None:
            raise GenerationBusy("visitor")
        held.callback(own.close)  # fermer le fichier rend le verrou
        for slot in range(max_concurrent):
            place = _try_lock(os.path.join(lock_dir, f"place-{slot}.lock"))
            if place is not None:
                held.callback(place.close)
                break
        else:
            raise GenerationBusy("server")
        yield
