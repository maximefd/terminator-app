"""Téléchargement des sources externes, avec empreintes consignées dans un fichier versionné."""

import json
import os
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .build import sha256_file


@dataclass(frozen=True)
class Source:
    url: str
    filename: str
    license: str
    homepage: str


SOURCES = {
    "lexique": Source(
        url="http://www.lexique.org/databases/Lexique383/Lexique383.tsv",
        filename="Lexique383.tsv",
        license="CC BY-SA 4.0",
        homepage="http://www.lexique.org",
    ),
    "wiktionary": Source(
        url="https://kaikki.org/frwiktionary/Fran%C3%A7ais/kaikki.org-dictionary-Fran%C3%A7ais.jsonl.gz",
        filename="kaikki-fr-wiktionary-francais.jsonl.gz",
        license="CC BY-SA 4.0 (contenu du Wiktionnaire)",
        homepage="https://kaikki.org/frwiktionary/",
    ),
}


class ChecksumMismatch(RuntimeError):
    """Le fichier local ne correspond pas à l'empreinte consignée."""


def fetch_url(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url) as response, open(destination, "wb") as out:
        shutil.copyfileobj(response, out, length=1024 * 1024)


def _read_lock(lock_path: Path) -> dict:
    return json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}


def download_sources(raw_dir, lock_path, refresh: bool = False,
                     fetch: Callable[[str, Path], None] = fetch_url,
                     log: Callable[[str], None] = print) -> dict:
    """Télécharge les sources manquantes et vérifie les autres.

    - fichier absent (ou `refresh`) : téléchargé, empreinte consignée dans le lock ;
    - fichier présent : son empreinte doit correspondre au lock (sinon `ChecksumMismatch`) ;
      sans entrée dans le lock, l'empreinte est simplement consignée.
    """
    raw_dir, lock_path = Path(raw_dir), Path(lock_path)
    raw_dir.mkdir(parents=True, exist_ok=True)
    lock = _read_lock(lock_path)

    for name, source in SOURCES.items():
        destination = raw_dir / source.filename
        if destination.exists() and not refresh:
            digest = sha256_file(destination)
            expected = lock.get(name, {}).get("sha256")
            if expected and digest != expected:
                raise ChecksumMismatch(
                    f"{destination} ne correspond pas à {lock_path} (relancer avec --refresh pour mettre à jour la source)"
                )
            log(f"{name} : présent, empreinte vérifiée")
            if expected:
                continue
        else:
            log(f"{name} : téléchargement de {source.url}…")
            tmp_path = destination.with_suffix(destination.suffix + ".part")
            fetch(source.url, tmp_path)
            os.replace(tmp_path, destination)
            digest = sha256_file(destination)

        lock[name] = {
            "url": source.url,
            "file": source.filename,
            "sha256": digest,
            "size": destination.stat().st_size,
            "license": source.license,
            "homepage": source.homepage,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return lock
