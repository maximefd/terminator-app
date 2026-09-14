"""Interface en ligne de commande : python -m tools.lexicon <commande>."""

import argparse
import json
from pathlib import Path

from .build import build_lexicon
from .download import SOURCES, download_sources
from .export import export_curated, lexicon_stats
from .scoring import Thresholds

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "lexicon"
RAW_DIR = DATA_DIR / "raw"
BUILD_DIR = DATA_DIR / "build"

DEFAULT_DELA = REPO_ROOT / "backend" / "dela_clean.csv"
DEFAULT_DB = BUILD_DIR / "lexicon.sqlite"
DEFAULT_DECISIONS = DATA_DIR / "decisions.csv"
DEFAULT_EXPORT = BUILD_DIR / "lexique_cure.csv"
DEFAULT_LOCK = DATA_DIR / "sources.lock.json"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m tools.lexicon", description="Pipeline du lexique de Terminator.")
    commands = parser.add_subparsers(dest="command", required=True)

    download = commands.add_parser("download", help="Télécharge et vérifie les sources (Lexique 3.83, Wiktionnaire)")
    download.add_argument("--refresh", action="store_true", help="Retélécharge les sources et met à jour les empreintes")

    build = commands.add_parser("build", help="Construit la base locale data/lexicon/build/lexicon.sqlite")
    build.add_argument("--dela", type=Path, default=DEFAULT_DELA)
    build.add_argument("--db", type=Path, default=DEFAULT_DB)
    build.add_argument("--no-wiktionary", action="store_true", help="Sans définitions (construction rapide)")
    build.add_argument("--auto-keep-zipf", type=float, default=Thresholds().auto_keep_zipf)
    build.add_argument("--likely-keep-zipf", type=float, default=Thresholds().likely_keep_zipf)

    export = commands.add_parser("export", help="Exporte le lexique curé selon les décisions")
    export.add_argument("--db", type=Path, default=DEFAULT_DB)
    export.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    export.add_argument("--out", type=Path, default=DEFAULT_EXPORT)
    export.add_argument("--exclude-suggested-deletes", action="store_true",
                        help="Retire aussi les mots suggérés « likely_delete » non gardés explicitement")

    stats = commands.add_parser("stats", help="Avancement de la curation")
    stats.add_argument("--db", type=Path, default=DEFAULT_DB)
    stats.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)

    args = parser.parse_args(argv)

    if args.command == "download":
        download_sources(RAW_DIR, DEFAULT_LOCK, refresh=args.refresh)
    elif args.command == "build":
        wiktionary = None if args.no_wiktionary else RAW_DIR / SOURCES["wiktionary"].filename
        stats_result = build_lexicon(
            args.dela, RAW_DIR / SOURCES["lexique"].filename, args.db, wiktionary,
            Thresholds(auto_keep_zipf=args.auto_keep_zipf, likely_keep_zipf=args.likely_keep_zipf),
        )
        print(json.dumps(stats_result.__dict__, indent=2, ensure_ascii=False))
    elif args.command == "export":
        print(json.dumps(export_curated(args.db, args.decisions, args.out, args.exclude_suggested_deletes), indent=2))
    elif args.command == "stats":
        print(json.dumps(lexicon_stats(args.db, args.decisions), indent=2, ensure_ascii=False))
