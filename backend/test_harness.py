# DANS backend/test_harness.py
"""
Benchmark reproductible du générateur de grilles ("le laboratoire").

Génère plusieurs grilles par layout avec des seeds fixes (0..N-1), puis écrit :
  - un fichier JSON de résultats (taux de succès, temps p50/p95, backtracks...) ;
  - optionnellement un rapport HTML visuel.

Usage (depuis backend/) :
    python test_harness.py                          # tous les layouts, 5 seeds
    python test_harness.py --format 6x7 --seeds 10
    python test_harness.py --output benchmarks/baseline.json --html report.html

Toute modification du moteur doit être comparée à benchmarks/baseline.json.
Les temps dépendent de la machine : comparer sur la même machine.
"""

import argparse
import json
import logging
import os
import platform
import random
import statistics
import subprocess
import time
from datetime import datetime, timezone

from engine.grid_template import GridTemplate
from engine.slot_finder import SlotFinder
from grid_generator import GridGenerator
from layout_catalog import DEFAULT_LAYOUTS_DIR, available_formats, layout_id
from trie_engine import DictionnaireTrie

# Un mot « courant » au sens de l'auteur : c'est ce qu'on impose à une grille. En dessous, on
# imposerait des formes que personne n'écrirait, et on mesurerait autre chose.
MUST_WORD_MIN_ZIPF = 3.0

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DICTIONARY = os.path.join(BACKEND_DIR, "dela_clean.csv")
DEFAULT_OUTPUT = os.path.join(BACKEND_DIR, "benchmarks", "latest.json")


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark reproductible du générateur de grilles.")
    parser.add_argument("--seeds", type=int, default=5, help="Nombre de seeds par layout (0..N-1).")
    parser.add_argument("--time-budget", type=float, default=60, help="Budget temps par grille (secondes).")
    parser.add_argument("--format", action="append", dest="formats", help="Limiter à un format (ex: 6x7). Répétable.")
    parser.add_argument("--dictionary", default=DEFAULT_DICTIONARY, help="Fichier dictionnaire (CSV DELA).")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Fichier JSON de résultats.")
    parser.add_argument("--html", help="Chemin d'un rapport HTML visuel (optionnel).")
    parser.add_argument("--restart-unit", type=int, default=None,
                        help="Unité des redémarrages en appels récursifs (0 : un seul essai ; défaut : réglage du générateur).")
    parser.add_argument("--min-safe-candidates", type=int, default=None,
                        help="Seuil du forward checking : un emplacement croisé doit garder au moins N candidats "
                             "(minimum 2 ; défaut : réglage du solveur).")
    parser.add_argument("--frequency-mode", default=None,
                        choices=["none", "exact", "band", "known", "tiebreak"],
                        help="Place de la fréquence dans le tri des candidats (défaut : réglage du solveur).")
    parser.add_argument("--frequency-band", type=float, default=None,
                        help="Largeur des paliers de fréquence pour le tri des candidats "
                             "(0 : valeur exacte ; défaut : réglage du solveur).")
    parser.add_argument("--max-candidates", type=int, default=None,
                        help="Candidats essayés par emplacement (défaut : réglage du solveur).")
    parser.add_argument("--by-format", action="store_true",
                        help="Mesurer par format : le moteur choisit son layout, comme l'API "
                             "(défaut : une mesure par layout, base de la baseline).")
    parser.add_argument("--max-layouts", type=int, default=None, metavar="N",
                        help="Nombre de layouts que le moteur peut essayer par format "
                             "(1 : comportement d'avant le correctif ; défaut : tous).")
    parser.add_argument("--layout-order", default=None, choices=["seed", "crossings"],
                        help="Ordre des layouts candidats avec mots imposés (défaut : réglage du générateur).")
    parser.add_argument("--must-max-length", type=int, default=None, metavar="N",
                        help="Plafonne la longueur des mots imposés tirés. Indispensable pour "
                             "comparer des formats : sans plafond, les grands reçoivent des mots "
                             "plus longs, donc plus durs.")
    parser.add_argument("--must-words", type=int, default=0, metavar="N",
                        help="Imposer N mots courants par grille, de longueurs distinctes tirées "
                             "selon la seed (0 : aucun, génération libre).")
    return parser.parse_args()


def list_layouts(formats_filter):
    """Retourne [(largeur, hauteur, chemin_du_layout)] triés, filtrés par format si demandé."""
    layouts = []
    for fmt in available_formats():
        name = f"{fmt['width']}x{fmt['height']}"
        if formats_filter and name not in formats_filter:
            continue
        format_dir = os.path.join(DEFAULT_LAYOUTS_DIR, name)
        for file_name in sorted(os.listdir(format_dir)):
            if file_name.endswith(".txt"):
                layouts.append((fmt["width"], fmt["height"], os.path.join(format_dir, file_name)))
    return layouts


def common_words_by_length(words, trie, min_zipf: float = MUST_WORD_MIN_ZIPF) -> dict[int, list[str]]:
    """Mots par longueur, réduits aux mots courants quand le lexique porte des fréquences.

    Sans colonne de fréquence (DELA brut), toutes les fréquences valent 0 : on garde alors tous les
    mots de la longueur, faute de mieux — mais la mesure perd son sens d'« un mot que l'auteur
    connaît ».
    """
    by_length: dict[int, list[str]] = {}
    for word in words:
        by_length.setdefault(len(word), []).append(word)
    return {length: [w for w in group if trie.frequency(w) >= min_zipf] or group
            for length, group in by_length.items()}


def pick_must_words(slot_lengths, pool_by_length, count: int, rng: random.Random,
                    max_length: int | None = None) -> list[str]:
    """`count` mots courants, de longueurs **distinctes** présentes dans ce layout.

    Longueurs distinctes à dessein : la vérification préalable refuse plus de mots d'une longueur
    qu'il n'y a d'emplacements de cette longueur. En variant les longueurs, le benchmark mesure le
    solveur et non cette validation.

    `max_length` plafonne la longueur tirée. Sans lui, comparer des formats est **faussé** : un
    13×18 se voit imposer des mots jusqu'à 13 lettres là où un 6×7 n'en reçoit jamais plus de 7,
    et la longueur est un facteur de difficulté mesuré. À demande égale, il faut le même plafond.
    """
    lengths = sorted({length for length in slot_lengths if pool_by_length.get(length)
                      and (max_length is None or length <= max_length)})
    rng.shuffle(lengths)
    return [rng.choice(pool_by_length[length]) for length in lengths[:count]]


def slot_lengths_of(width: int, height: int, layout_path: str) -> list[int]:
    template = GridTemplate(width, height, layout_path)
    finder = SlotFinder(template)
    finder.find_all_slots()
    return [slot["length"] for slot in finder.slots]


def format_slot_lengths(width: int, height: int) -> list[int]:
    """Longueurs d'emplacement présentes dans **au moins un** layout du format.

    C'est la bonne base pour tirer un mot imposé en mode « par format » : l'auteur choisit un mot,
    et c'est au moteur de trouver un layout qui l'accueille.
    """
    lengths: set[int] = set()
    format_dir = os.path.join(DEFAULT_LAYOUTS_DIR, f"{width}x{height}")
    for name in sorted(os.listdir(format_dir)):
        if name.endswith(".txt"):
            lengths.update(slot_lengths_of(width, height, os.path.join(format_dir, name)))
    return sorted(lengths)


def percentile(values, pct):
    """Percentile au rang le plus proche (suffisant pour de petits échantillons)."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return ordered[index]


def run_layout(width, height, layout_path, words, trie, seeds, time_budget, restart_unit=None,
               min_safe_candidates=None, frequency_mode=None, frequency_band=None,
               max_candidates=None, must_count=0, must_pool=None, max_layouts=None,
               must_max_length=None, layout_order=None):
    """Génère une grille par seed et collecte les mesures.

    `layout_path` à None : mode « par format », le moteur choisit lui-même son layout parmi ceux du
    format — c'est le chemin que prend l'API. Le mode par layout (défaut) mesure une géométrie
    précise ; lui seul sert de baseline, car il ne dépend pas du tirage.
    """
    runs, grids = [], []
    by_format = layout_path is None
    layout_name = f"{width}x{height}" if by_format else layout_id(layout_path)
    restart = {} if restart_unit is None else {"restart_unit_calls": restart_unit or None}
    if min_safe_candidates is not None:
        restart["min_safe_candidates"] = min_safe_candidates
    if frequency_mode is not None:
        restart["frequency_mode"] = frequency_mode
    if frequency_band is not None:
        restart["frequency_band"] = frequency_band
    if max_candidates is not None:
        restart["max_candidates"] = max_candidates
    if max_layouts is not None:
        restart["max_layouts"] = max_layouts
    if layout_order is not None:
        restart["layout_order"] = layout_order
    if by_format:
        restart["layouts_dir"] = DEFAULT_LAYOUTS_DIR
    if not must_count:
        lengths = []
    elif by_format:
        lengths = format_slot_lengths(width, height)
    else:
        lengths = slot_lengths_of(width, height, layout_path)
    for seed in range(seeds):
        # Tirage dérivé du nom du layout et de la seed : reproductible d'une machine à l'autre
        # (une chaîne est hachée de façon déterministe par random, contrairement à un tuple).
        must_words = pick_must_words(lengths, must_pool or {}, must_count,
                                     random.Random(f"{layout_name}:{seed}"),
                                     must_max_length) if must_count else []
        print(f"  {layout_name} seed={seed}"
              f"{' ' + '+'.join(must_words) if must_words else ''}...", end="", flush=True)
        start = time.perf_counter()
        generator = GridGenerator(width, height, words, prebuilt_trie=trie, seed=seed,
                                  layout_path=layout_path, time_budget_s=time_budget,
                                  must_words=must_words, **restart)
        chosen = layout_id(generator.layout_path)
        success = generator.generate()
        elapsed = time.perf_counter() - start

        grid_data = generator.get_grid_data()
        metrics = grid_data["statistics"]["metrics"]
        placed = [word["text"] for word in grid_data["words"]]
        zipfs = [trie.frequency(word) for word in placed]
        runs.append({
            "seed": seed,
            "success": success,
            "budget_exceeded": generator.budget_exceeded,
            "time_s": round(elapsed, 3),
            "fill_ratio": grid_data["fill_ratio"] if success else 0,
            # Qualité des mots : un taux de succès n'en dit rien. Moyenne des zipf des mots placés
            # (0 si le lexique n'a pas de fréquence), et part de mots totalement absents des corpus.
            "mean_zipf": round(statistics.mean(zipfs), 3) if zipfs else None,
            "unknown_share": round(sum(1 for z in zipfs if z == 0) / len(zipfs), 3) if zipfs else None,
            "must_words": must_words,
            "layout": chosen,  # en mode par format, le layout que le moteur a retenu
            # Distinguer « le solveur n'a pas su placer ce mot » de « le budget a expiré » :
            # c'est toute la différence entre une demande trop dure et une machine trop lente.
            "must_unplaced": list(generator.unplaced_must_words) if not success else [],
            "recursive_calls": metrics["recursive_calls"],
            "backtracks": metrics["backtracks"],
            "candidates_tested": metrics["candidates_tested"],
            "attempts": grid_data["statistics"].get("attempts", 1),
        })
        if success:
            grid_data["generation_time"] = elapsed
            grids.append(grid_data)
        print(f" {'succès' if success else 'timeout' if generator.budget_exceeded else 'échec'} ({elapsed:.2f}s)")

    times = [r["time_s"] for r in runs]
    successes = sum(r["success"] for r in runs)
    # La qualité ne se mesure que sur les grilles réellement produites
    quality = [r["mean_zipf"] for r in runs if r["success"] and r["mean_zipf"] is not None]
    unknown = [r["unknown_share"] for r in runs if r["success"] and r["unknown_share"] is not None]
    summary = {
        "runs": len(runs),
        "successes": successes,
        "success_rate": round(successes / len(runs), 3) if runs else 0,
        "timeouts": sum(r["budget_exceeded"] for r in runs),
        "time_p50_s": percentile(times, 50),
        "time_p95_s": percentile(times, 95),
        "time_max_s": max(times, default=None),
        "mean_backtracks": round(statistics.mean(r["backtracks"] for r in runs), 1) if runs else None,
        "mean_zipf": round(statistics.mean(quality), 3) if quality else None,
        "unknown_share": round(statistics.mean(unknown), 3) if unknown else None,
        "must_words_per_grid": must_count,
        "failed_on_must_words": sum(1 for r in runs if r["must_unplaced"]),
    }
    return {"layout": layout_name, "width": width, "height": height, "summary": summary, "runs": runs}, grids


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=BACKEND_DIR,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def generate_html_report(report, grids_by_layout, path):
    """Génère un rapport HTML visuel (grilles, métriques, historique de construction)."""
    html = """
    <html>
    <head>
        <title>Rapport de Génération de Grilles</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: sans-serif; margin: 2em; background-color: #f8f9fa; }
            h1, h2 { color: #343a40; border-bottom: 1px solid #dee2e6; padding-bottom: 10px; }
            .report-summary { background-color: #e9ecef; padding: 1em; border-radius: 5px; margin-bottom: 2em; }
            .grid-container { display: flex; flex-wrap: wrap; gap: 2em; }
            .grid-item { background-color: white; padding: 1em; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { border-collapse: collapse; }
            td { border: 1px solid #ccc; width: 25px; height: 25px; text-align: center; vertical-align: middle; font-weight: bold; font-size: 12px; }
            .black { background-color: #343a40; }
        </style>
    </head>
    <body>
        <h1>Rapport de Génération de Grilles</h1>
        <p>Généré le : """ + report["generated_at"] + """</p>
    """

    for layout in report["layouts"]:
        summary = layout["summary"]
        grids = grids_by_layout.get(layout["layout"], [])
        html += f"<h2>{layout['layout']} : {summary['successes']} / {summary['runs']} grilles</h2>"
        html += f"""
        <div class="report-summary">
            <strong>Temps p50 :</strong> {summary['time_p50_s']} s |
            <strong>p95 :</strong> {summary['time_p95_s']} s |
            <strong>Timeouts :</strong> {summary['timeouts']} |
            <strong>Backtracks moyens :</strong> {summary['mean_backtracks']}
        </div>
        """

        html += '<div class="grid-container">'
        for grid_data in grids:
            html += f"""
            <div class="grid-item">
                <h3>Seed: {grid_data['seed']} | Remplissage: {grid_data['fill_ratio']*100:.1f}% | Temps: {grid_data['generation_time']*1000:.0f}ms</h3>
                <table><tbody>
            """
            rows = [[] for _ in range(grid_data['height'])]
            for cell in grid_data['cells']:
                rows[cell['y']].append(cell)
            for row in rows:
                html += "<tr>"
                for cell in row:
                    class_name = "black" if cell['is_black'] else ""
                    html += f'<td class="{class_name}">{cell["char"] or ""}</td>'
                html += "</tr>"
            html += "</tbody></table>"

            stats = grid_data.get('statistics', {})
            metrics = stats.get('metrics', {})
            cache_stats = stats.get('cache_stats', {})
            placement_history = stats.get('placement_history', [])

            html += "<h4>Métriques de Performance</h4>"
            html += "<ul style='font-size: 12px;'>"
            html += f"<li>Appels récursifs: {metrics.get('recursive_calls', 0):,}</li>"
            html += f"<li>Candidats testés: {metrics.get('candidates_tested', 0):,}</li>"
            html += f"<li>Backtracks: {metrics.get('backtracks', 0):,}</li>"
            fc_checks = metrics.get('fc_checks', 0)
            fc_skips = metrics.get('fc_skips', 0)
            if fc_checks > 0:
                html += f"<li>Forward Checking: {fc_skips:,}/{fc_checks:,} ({fc_skips / fc_checks * 100:.1f}% éliminés)</li>"
            total_cache = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
            if total_cache > 0:
                hit_rate = cache_stats.get('hits', 0) / total_cache * 100
                html += f"<li>Cache: {cache_stats.get('hits', 0):,} hits / {total_cache:,} ({hit_rate:.1f}%)</li>"
            html += "</ul>"

            if placement_history:
                html += f"<h4>Historique de Construction ({len(placement_history)} mots)</h4>"
                html += "<ol style='font-size: 11px; max-height: 400px; overflow-y: auto;'>"
                for entry in placement_history:
                    html += (f"<li><strong>{entry.get('word', '')}</strong> (Slot {entry.get('slot_id', '?')}, "
                             f"{entry.get('direction', '')}, score: {entry.get('score', 0):.0f})</li>")
                html += "</ol>"
            html += "</div>"
        html += "</div>"

    html += "</body></html>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Rapport HTML généré : {os.path.abspath(path)}")


def main():
    args = parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

    print(f"Chargement du dictionnaire depuis {args.dictionary}...")
    dictionary = DictionnaireTrie()
    dictionary.load_dela_csv(args.dictionary)
    # Tri : l'ordre d'insertion du Trie ne dépend que du contenu (reproductibilité)
    all_words = sorted(dictionary.get_all_words())
    print(f"{len(all_words)} mots uniques.")

    layouts = list_layouts(args.formats)
    if not layouts:
        raise SystemExit("Aucun layout ne correspond aux formats demandés.")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "cpu_count": os.cpu_count()},
        "config": {"seeds": args.seeds, "time_budget_s": args.time_budget,
                   "dictionary": os.path.basename(args.dictionary), "dictionary_words": len(all_words),
                   "restart_unit_calls": args.restart_unit,
                   "min_safe_candidates": args.min_safe_candidates,
                   "frequency_mode": args.frequency_mode,
                   "frequency_band": args.frequency_band,
                   "max_candidates": args.max_candidates,
                   "must_words_per_grid": args.must_words,
                   "must_max_length": args.must_max_length,
                   "layout_order": args.layout_order,
                   "by_format": args.by_format, "max_layouts": args.max_layouts},
        "layouts": [],
    }
    grids_by_layout = {}

    # Le Trie est construit une seule fois par format, avec les mots de longueur compatible
    for width, height in sorted({(w, h) for w, h, _ in layouts}):
        max_len = max(width, height)
        format_words = [w for w in all_words if len(w) <= max_len]
        format_trie = DictionnaireTrie()
        for word in format_words:
            format_trie.insert(word)
        # Le Trie du format est reconstruit mot à mot : sans ce report, il perdrait les fréquences
        # du lexique, et le benchmark mesurerait un moteur privé de son critère de qualité.
        format_trie.frequencies = {word: dictionary.frequency(word) for word in format_words}
        must_pool = common_words_by_length(format_words, format_trie) if args.must_words else None
        print(f"\n--- Format {width}x{height} : {len(format_words)} mots ---")

        chemins = [None] if args.by_format else [p for w, h, p in layouts if (w, h) == (width, height)]
        for layout_path in chemins:
            result, grids = run_layout(width, height, layout_path, format_words, format_trie,
                                       args.seeds, args.time_budget, args.restart_unit,
                                       args.min_safe_candidates, args.frequency_mode,
                                       args.frequency_band, args.max_candidates,
                                       args.must_words, must_pool, args.max_layouts,
                                       args.must_max_length, args.layout_order)
            report["layouts"].append(result)
            grids_by_layout[result["layout"]] = grids

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nRésultats JSON : {os.path.abspath(args.output)}")
    for layout in report["layouts"]:
        s = layout["summary"]
        quality = "" if s["mean_zipf"] is None else f", zipf moyen {s['mean_zipf']}, inconnus {s['unknown_share']:.0%}"
        if s["must_words_per_grid"]:
            quality += f", {s['must_words_per_grid']} mot(s) impose(s), {s['failed_on_must_words']} non place(s)"
        print(f"  {layout['layout']}: succès {s['success_rate']:.0%}, p50 {s['time_p50_s']}s, "
              f"p95 {s['time_p95_s']}s, timeouts {s['timeouts']}{quality}")

    if args.html:
        generate_html_report(report, grids_by_layout, args.html)


if __name__ == "__main__":
    main()
