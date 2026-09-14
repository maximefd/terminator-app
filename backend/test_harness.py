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
import statistics
import subprocess
import time
from datetime import datetime, timezone

from grid_generator import DEFAULT_TEMPLATES_DIR, GridGenerator, available_formats
from trie_engine import DictionnaireTrie

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
    return parser.parse_args()


def list_layouts(formats_filter):
    """Retourne [(largeur, hauteur, chemin_du_layout)] triés, filtrés par format si demandé."""
    layouts = []
    for fmt in available_formats():
        name = f"{fmt['width']}x{fmt['height']}"
        if formats_filter and name not in formats_filter:
            continue
        format_dir = os.path.join(DEFAULT_TEMPLATES_DIR, name)
        for file_name in sorted(os.listdir(format_dir)):
            if file_name.endswith(".txt"):
                layouts.append((fmt["width"], fmt["height"], os.path.join(format_dir, file_name)))
    return layouts


def percentile(values, pct):
    """Percentile au rang le plus proche (suffisant pour de petits échantillons)."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return ordered[index]


def run_layout(width, height, layout_path, words, trie, seeds, time_budget):
    """Génère une grille par seed pour un layout et collecte les mesures."""
    runs, grids = [], []
    layout_name = os.path.relpath(layout_path, DEFAULT_TEMPLATES_DIR)
    for seed in range(seeds):
        print(f"  {layout_name} seed={seed}...", end="", flush=True)
        start = time.perf_counter()
        generator = GridGenerator(width, height, words, prebuilt_trie=trie, seed=seed,
                                  layout_path=layout_path, time_budget_s=time_budget)
        success = generator.generate()
        elapsed = time.perf_counter() - start

        grid_data = generator.get_grid_data()
        metrics = grid_data["statistics"]["metrics"]
        runs.append({
            "seed": seed,
            "success": success,
            "budget_exceeded": generator.budget_exceeded,
            "time_s": round(elapsed, 3),
            "fill_ratio": grid_data["fill_ratio"] if success else 0,
            "recursive_calls": metrics["recursive_calls"],
            "backtracks": metrics["backtracks"],
            "candidates_tested": metrics["candidates_tested"],
        })
        if success:
            grid_data["generation_time"] = elapsed
            grids.append(grid_data)
        print(f" {'succès' if success else 'timeout' if generator.budget_exceeded else 'échec'} ({elapsed:.2f}s)")

    times = [r["time_s"] for r in runs]
    successes = sum(r["success"] for r in runs)
    summary = {
        "runs": len(runs),
        "successes": successes,
        "success_rate": round(successes / len(runs), 3) if runs else 0,
        "timeouts": sum(r["budget_exceeded"] for r in runs),
        "time_p50_s": percentile(times, 50),
        "time_p95_s": percentile(times, 95),
        "time_max_s": max(times, default=None),
        "mean_backtracks": round(statistics.mean(r["backtracks"] for r in runs), 1) if runs else None,
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
                   "dictionary": os.path.basename(args.dictionary), "dictionary_words": len(all_words)},
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
        print(f"\n--- Format {width}x{height} : {len(format_words)} mots ---")

        for w, h, layout_path in layouts:
            if (w, h) != (width, height):
                continue
            result, grids = run_layout(width, height, layout_path, format_words, format_trie,
                                       args.seeds, args.time_budget)
            report["layouts"].append(result)
            grids_by_layout[result["layout"]] = grids

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nRésultats JSON : {os.path.abspath(args.output)}")
    for layout in report["layouts"]:
        s = layout["summary"]
        print(f"  {layout['layout']}: succès {s['success_rate']:.0%}, p50 {s['time_p50_s']}s, "
              f"p95 {s['time_p95_s']}s, timeouts {s['timeouts']}")

    if args.html:
        generate_html_report(report, grids_by_layout, args.html)


if __name__ == "__main__":
    main()
