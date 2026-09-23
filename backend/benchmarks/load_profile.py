"""
Profil de charge de l'API : RAM, CPU et durées d'une génération, et ce que deviennent plusieurs générations
lancées ensemble ([ADR 0013](../../docs/adr/0013-cible-hebergement-production.md)).

Là où `test_harness.py` mesure le **moteur** (taux de succès par layout), ce script mesure la **machine** :
il reprend le chemin de `POST /api/grids/generate` (lexique entier, choix du layout par format) et répond
aux questions d'hébergement — combien de RAM après chargement, combien de CPU par grille, que se passe-t-il
quand deux ou quatre générations se chevauchent. Les processus sont forkés après le chargement, comme les
workers de gunicorn.

Linux uniquement (mémoire lue dans /proc). Depuis backend/ :
    python benchmarks/load_profile.py --output benchmarks/load.json
Sur le serveur, dans le conteneur de l'API :
    docker compose exec api python benchmarks/load_profile.py --output /tmp/load.json
"""

import argparse
import json
import os
import platform
import random
import statistics
import sys
import threading
import time
from datetime import datetime, timezone

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


def rss_mb(pid="self") -> float:
    """Mémoire résidente d'un processus (Mo)."""
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def pss_mb(pid) -> float:
    """Part de mémoire propre au processus, les pages partagées divisées entre ceux qui les partagent (Mo).

    C'est la seule mesure qui s'additionne entre des processus forkés : leurs RSS comptent plusieurs fois
    le lexique qu'ils partagent.
    """
    try:
        with open(f"/proc/{pid}/smaps_rollup") as f:
            for line in f:
                if line.startswith("Pss:"):
                    return int(line.split()[1]) / 1024
    except OSError:  # processus déjà terminé
        pass
    return 0.0


RSS_START = rss_mb()

from engine.word_repository import WholeLexicon  # noqa: E402
from grid_generator import GridGenerator  # noqa: E402
from layout_catalog import available_formats  # noqa: E402
from lexicon_loader import DEFAULT_LEXICON_PATH, load_trie  # noqa: E402
from test_harness import common_words_by_length, format_slot_lengths, pick_must_words  # noqa: E402

# Formats et nombre de mots imposés des cas « avec mots obligatoires » : ceux qui touchent le budget
MUST_FORMATS = [(6, 7), (10, 13), (13, 16)]
MUST_COUNT, MUST_MAX_LENGTH = 2, 7
# Générations répétées pour mesurer la concurrence : un format moyen, assez long pour se chevaucher
CONCURRENCY_FORMAT, CONCURRENCY_JOBS = (10, 13), 8


def generate(trie, width, height, seed, must_words=(), budget=20.0) -> dict:
    """Le corps de la route de génération, sans Flask."""
    started, cpu_started = time.perf_counter(), time.thread_time()
    generator = GridGenerator(width, height, WholeLexicon(max(width, height)), prebuilt_trie=trie, seed=seed,
                              time_budget_s=budget, must_words=sorted(must_words))
    success = False if generator.must_word_problems else generator.generate()
    generator.get_grid_data()
    return {"format": f"{width}x{height}", "seed": seed, "must_words": list(must_words), "success": success,
            "timeout": generator.budget_exceeded, "time_s": round(time.perf_counter() - started, 3),
            "cpu_s": round(time.thread_time() - cpu_started, 3)}


def percentile(values, pct):
    values = sorted(values)
    if not values:
        return None
    k = (len(values) - 1) * pct / 100
    low, high = int(k), min(int(k) + 1, len(values) - 1)
    return round(values[low] + (values[high] - values[low]) * (k - low), 3)


def summarize(runs) -> dict:
    times = [r["time_s"] for r in runs]
    return {"runs": len(runs), "successes": sum(r["success"] for r in runs),
            "timeouts": sum(r["timeout"] for r in runs), "time_p50_s": percentile(times, 50),
            "time_p95_s": percentile(times, 95), "time_max_s": max(times, default=None),
            "cpu_mean_s": round(statistics.mean(r["cpu_s"] for r in runs), 3) if runs else None}


class PeakRss:
    """Pic de mémoire résidente pendant un bloc (échantillon toutes les 20 ms)."""

    def __enter__(self):
        self.peak = rss_mb()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def _sample(self):
        while not self._stop.wait(0.02):
            self.peak = max(self.peak, rss_mb())

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self.peak = round(max(self.peak, rss_mb()))


def in_processes(trie, jobs, count) -> dict:
    """`count` processus forkés après chargement (comme les workers gunicorn), lancés ensemble."""
    readers, pids = [], []
    for i in range(count):
        read_end, write_end = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_end)
            results = [generate(trie, *job) for job in jobs[i::count]]
            os.write(write_end, json.dumps(results).encode())
            os._exit(0)
        os.close(write_end)
        readers.append(read_end)
        pids.append(pid)

    started, peak, alive = time.perf_counter(), 0.0, set(pids)
    while alive:
        peak = max(peak, pss_mb(os.getpid()) + sum(pss_mb(pid) for pid in alive))
        for pid in list(alive):
            if os.waitpid(pid, os.WNOHANG)[0]:
                alive.discard(pid)
        time.sleep(0.05)
    elapsed = time.perf_counter() - started

    results = []
    for read_end in readers:
        chunks = []
        while chunk := os.read(read_end, 1 << 20):
            chunks.append(chunk)
        os.close(read_end)
        results += json.loads(b"".join(chunks))
    return {"processes": count, "total_time_s": round(elapsed, 2), "peak_total_pss_mb": round(peak),
            **summarize(results)}


def in_threads(trie, jobs, count) -> dict:
    """`count` threads d'un même processus : le GIL les sérialise-t-il ?"""
    results, lock = [], threading.Lock()

    def worker(i):
        for job in jobs[i::count]:
            result = generate(trie, *job)
            with lock:
                results.append(result)

    started = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return {"threads": count, "total_time_s": round(time.perf_counter() - started, 2), **summarize(results)}


def parse_args():
    parser = argparse.ArgumentParser(description="Profil de charge de l'API (RAM, CPU, concurrence).")
    parser.add_argument("--lexicon", default=os.environ.get("LEXICON_PATH") or str(DEFAULT_LEXICON_PATH),
                        help="Lexique à charger (défaut : LEXICON_PATH, sinon le DELA complet).")
    parser.add_argument("--seeds", type=int, default=10, help="Générations par format (seeds 0..N-1).")
    parser.add_argument("--time-budget", type=float, default=20, help="Budget par génération (secondes).")
    parser.add_argument("--output", default=os.path.join(BACKEND_DIR, "benchmarks", "load.json"),
                        help="Fichier JSON de résultats.")
    return parser.parse_args()


def main():
    args = parse_args()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": {"python": f"{platform.python_implementation()} {platform.python_version()}",
                        "platform": platform.platform(), "cpu_count": os.cpu_count()},
        "config": {"lexicon": os.path.basename(args.lexicon), "seeds": args.seeds, "time_budget_s": args.time_budget},
        "memory_mb": {"start": round(RSS_START)},
    }

    started = time.perf_counter()
    trie = load_trie(args.lexicon)
    report["lexicon"] = {"words": len(trie.words), "load_time_s": round(time.perf_counter() - started, 1)}
    report["memory_mb"]["after_load"] = round(rss_mb())
    print(f"Lexique : {len(trie.words)} mots, {report['lexicon']['load_time_s']} s, "
          f"{report['memory_mb']['after_load']} Mo", flush=True)

    # 1. Génération libre, format par format
    formats = [(f["width"], f["height"]) for f in available_formats()]
    free = []
    with PeakRss() as peak:
        for width, height in formats:
            runs = [generate(trie, width, height, seed, budget=args.time_budget) for seed in range(args.seeds)]
            free += runs
            print(f"  {width}x{height} : {summarize(runs)}", flush=True)
    report["free"] = {"all": summarize(free),
                      "by_format": {f"{w}x{h}": summarize([r for r in free if r["format"] == f"{w}x{h}"])
                                    for w, h in formats}}
    report["memory_mb"]["peak_free"] = peak.peak

    # 2. Mots imposés : le cas qui atteint le budget
    pool = common_words_by_length(trie.words, trie)
    imposed = []
    with PeakRss() as peak:
        for width, height in MUST_FORMATS:
            lengths = format_slot_lengths(width, height)
            for seed in range(args.seeds):
                words = pick_must_words(lengths, pool, MUST_COUNT, random.Random(f"{width}x{height}:{seed}"),
                                        MUST_MAX_LENGTH)
                imposed.append(generate(trie, width, height, seed, words, args.time_budget))
    report["must_words"] = {"per_grid": MUST_COUNT, "max_length": MUST_MAX_LENGTH, **summarize(imposed)}
    report["memory_mb"]["peak_must_words"] = peak.peak
    print(f"  mots imposés : {summarize(imposed)}", flush=True)

    # 3. Concurrence : les mêmes générations en série, en threads, puis en processus
    width, height = CONCURRENCY_FORMAT
    jobs = [(width, height, seed, (), args.time_budget) for seed in range(CONCURRENCY_JOBS)]
    serial = [generate(trie, *job) for job in jobs]
    report["concurrency"] = {
        "format": f"{width}x{height}",
        "serial": {"total_time_s": round(sum(r["time_s"] for r in serial), 2), **summarize(serial)},
        "threads_2": in_threads(trie, jobs, 2),
        "processes_2": in_processes(trie, jobs, 2),
        "processes_4": in_processes(trie, jobs, 4),
    }
    for name, result in report["concurrency"].items():
        if name != "format":
            print(f"  {name} : {result}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nRésultats JSON : {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
