"""Interface en ligne de commande : python -m tools.lexicon <commande>."""

import argparse
import json
from pathlib import Path

from .autorules import DEFAULT_RULES, RULES, load_enabled, preview, save_enabled
from .build import build_lexicon
from .download import SOURCES, download_sources
from .export import FILTER_NONE, FILTERS, export_curated, lexicon_stats
from .review import report as review_report
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
DEFAULT_RULES_FILE = DATA_DIR / "auto_rules.json"


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


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
    export.add_argument("--filtre", choices=FILTERS, default=FILTER_NONE,
                        help="« moyen » ne garde que les mots connus de Lexique, définis pour eux-mêmes "
                             "ou formés sur un lemme courant (les mots gardés à la main restent)")
    export.add_argument("--rules", type=Path, default=DEFAULT_RULES_FILE, help="Fichier des règles automatiques")
    export.add_argument("--sans-regles", action="store_true", help="Ignore les règles automatiques activées")

    stats = commands.add_parser("stats", help="Avancement de la curation")
    stats.add_argument("--db", type=Path, default=DEFAULT_DB)
    stats.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    stats.add_argument("--rules", type=Path, default=DEFAULT_RULES_FILE)

    autorules = commands.add_parser(
        "autorules", help="Règles automatiques : aperçu, activation, désactivation")
    autorules.add_argument("--db", type=Path, default=DEFAULT_DB)
    autorules.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    autorules.add_argument("--rules", type=Path, default=DEFAULT_RULES_FILE)
    autorules.add_argument("--activer", nargs="*", metavar="REGLE",
                           help="Active ces règles (sans argument : les règles conseillées)")
    autorules.add_argument("--aucune", action="store_true", help="Désactive toutes les règles")
    autorules.add_argument("--exemples", type=int, default=10, help="Nombre de mots montrés par règle")

    revision = commands.add_parser("revision", help="Décisions douteuses à revoir (fatigue, familles incohérentes)")
    revision.add_argument("--db", type=Path, default=DEFAULT_DB)
    revision.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    revision.add_argument("--limite", type=int, default=200)

    args = parser.parse_args(argv)

    if args.command == "download":
        download_sources(RAW_DIR, DEFAULT_LOCK, refresh=args.refresh)
    elif args.command == "build":
        wiktionary = None if args.no_wiktionary else RAW_DIR / SOURCES["wiktionary"].filename
        stats_result = build_lexicon(
            args.dela, RAW_DIR / SOURCES["lexique"].filename, args.db, wiktionary,
            Thresholds(auto_keep_zipf=args.auto_keep_zipf, likely_keep_zipf=args.likely_keep_zipf),
        )
        _print(stats_result.__dict__)
    elif args.command == "export":
        rules = () if args.sans_regles else load_enabled(args.rules)
        _print(export_curated(args.db, args.decisions, args.out, args.exclude_suggested_deletes,
                              filter_level=args.filtre, auto_rules=rules))
    elif args.command == "stats":
        _print(lexicon_stats(args.db, args.decisions, auto_rules=load_enabled(args.rules)))
    elif args.command == "autorules":
        _autorules(args)
    elif args.command == "revision":
        _print(review_report(args.db, args.decisions, limit=args.limite))


def _autorules(args) -> None:
    """Aperçu par défaut ; n'écrit le fichier des règles qu'avec --activer ou --aucune."""
    if args.aucune:
        enabled = save_enabled(args.rules, [])
    elif args.activer is not None:
        enabled = save_enabled(args.rules, args.activer or DEFAULT_RULES)
    else:
        enabled = load_enabled(args.rules)

    overview = preview(args.db, args.decisions, sample=args.exemples)
    _print({
        "regles_activees": list(enabled),
        "fichier": str(args.rules),
        "regles": {rule.id: {**overview[rule.id], "active": rule.id in enabled} for rule in RULES},
    })
