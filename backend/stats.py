"""`flask stats` : ce que disent les événements d'usage ([ADR 0016](../docs/adr/0016-mesure-d-usage-sans-cookie.md)).

Lu sur le serveur, en attendant le poste de pilotage (Phase 8). Chaque question de l'ADR a sa réponse ici,
sauf le temps passé, qui attend la balise du navigateur :
- combien de visiteurs, de recherches, de générations, de comptes et de grilles conservées ;
- quelles générations réussissent, dans quels formats, avec combien de mots imposés ;
- combien de refus « occupé » ou de rate limiting, face aux seuils de l'ADR 0013 ;
- quel temps CPU les générations consomment ;
- quelles erreurs, sur quelles routes ;
- quels mots imposés manquent au lexique (pour la curation).

Les visiteurs se comptent par jour : une empreinte change chaque jour (usage.py). Sur 7 ou 30 jours, le
chiffre est la somme des visiteurs de chaque jour, et non un nombre de personnes distinctes.
"""

import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import click
from flask import current_app
from flask.cli import AppGroup

from models import UsageEvent
import usage

PERIODS = (("Aujourd'hui", 1), ("7 jours", 7), ("30 jours", 30))
BUSY = ("busy_visitor", "busy_server")
# Seuils de l'ADR 0013 : au-delà, passer au VPS-2
P95_THRESHOLD_S = 15
BUSY_THRESHOLD = 0.05


def _percentile(values: list[int], share: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def _rate(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f} %" if whole else "—"


def _period_figures(events: list[UsageEvent], days: int, cpu_count: int) -> dict:
    by_kind = defaultdict(list)
    for event in events:
        by_kind[event.kind].append(event)
    generations = by_kind["generation"]
    outcomes = Counter(e.outcome for e in generations)
    accounts = Counter(e.outcome for e in by_kind["account"])
    durations = [e.duration_ms for e in generations if e.outcome == "grid" and e.duration_ms is not None]
    cpu_ms = sum(e.cpu_ms or 0 for e in generations)
    visitor_days = len({(e.created_at.date(), e.visitor) for e in events if e.visitor})
    return {
        "visitors": visitor_days,
        "searches": len(by_kind["search"]),
        "generations": len(generations),
        "grids": outcomes["grid"],
        "success": _rate(outcomes["grid"], len(generations) - sum(outcomes[b] for b in BUSY)
                         - outcomes["rate_limited"]),
        "busy": sum(outcomes[b] for b in BUSY),
        "rate_limited": outcomes["rate_limited"],
        "p50": _percentile(durations, 0.5),
        "p95": _percentile(durations, 0.95),
        "cpu_s": cpu_ms / 1000,
        "cpu_share": cpu_ms / 1000 / (days * 86400 * cpu_count),
        "register": accounts["register"],
        "verify": accounts["verify"],
        "login": accounts["login"],
        "delete": accounts["delete"],
        "saved": len(by_kind["grid"]),
        "errors": sum(1 for e in events if e.status >= 400),
        "server_errors": sum(1 for e in events if e.status >= 500),
    }


def compute(now: datetime | None = None, cpu_count: int | None = None) -> dict:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    cpu_count = cpu_count or os.cpu_count() or 1
    since = now - timedelta(days=30)
    events = UsageEvent.query.filter(UsageEvent.created_at >= since).order_by(UsageEvent.created_at).all()
    start_of_today = datetime.combine(now.date(), datetime.min.time())

    periods = {}
    for label, days in PERIODS:
        start = start_of_today if days == 1 else now - timedelta(days=days)
        periods[label] = _period_figures([e for e in events if e.created_at >= start], days, cpu_count)

    generations = [e for e in events if e.kind == "generation"]
    formats = defaultdict(Counter)
    by_must_count = defaultdict(Counter)
    unknown_words = Counter()
    for event in generations:
        if event.outcome in BUSY or event.outcome == "rate_limited":
            continue
        succeeded = "grid" if event.outcome == "grid" else "échec"
        formats[event.data.get("format", "?")][succeeded] += 1
        must = event.data.get("must", [])
        by_must_count[min(len(must), 3)][succeeded] += 1
        must_texts = (event.words or {}).get("must", [])
        for detail, text in zip(must, must_texts):
            if not detail.get("known", True):
                unknown_words[text] += 1

    return {
        "now": now,
        "periods": periods,
        "outcomes": Counter(e.outcome for e in generations),
        "formats": formats,
        "by_must_count": by_must_count,
        "unknown_words": unknown_words,
        "countries": Counter(e.country or "?" for e in events if e.visitor),
        "errors": Counter((e.route or "?", e.status) for e in events if e.status >= 400),
        "latest": list(reversed(generations))[:10],
    }


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds") + "Z"


def as_json(stats: dict) -> dict:
    """Les mêmes chiffres pour le poste de pilotage (`GET /api/admin/stats`, admin.py).

    Des agrégats seulement. Les dernières générations y figurent sans rien qui désigne un visiteur : ni
    empreinte, ni compte, ni mots imposés (seul leur nombre).
    """
    month = stats["periods"]["30 jours"]

    def split(counter: Counter) -> dict:
        return {"grid": counter["grid"], "failed": counter["échec"]}

    return {
        "now": _iso(stats["now"]),
        "periods": [{"label": label, "days": days, **stats["periods"][label]} for label, days in PERIODS],
        # Seuils de l'ADR 0013, sur 30 jours comme dans `flask stats`
        "thresholds": {
            "p95_ms": month["p95"],
            "p95_limit_ms": P95_THRESHOLD_S * 1000,
            "busy_share": month["busy"] / month["generations"] if month["generations"] else 0,
            "busy_limit": BUSY_THRESHOLD,
        },
        "outcomes": [{"outcome": outcome or "?", "count": count}
                     for outcome, count in stats["outcomes"].most_common()],
        "formats": [{"format": fmt, **split(counter)}
                    for fmt, counter in sorted(stats["formats"].items(), key=lambda item: -sum(item[1].values()))],
        "by_must_count": [{"must": count, **split(counter)} for count, counter in sorted(stats["by_must_count"].items())],
        "unknown_words": [{"word": word, "count": count} for word, count in stats["unknown_words"].most_common(50)],
        "countries": [{"country": country, "events": count} for country, count in stats["countries"].most_common(20)],
        "errors": [{"route": route, "status": status, "count": count}
                   for (route, status), count in stats["errors"].most_common(30)],
        "latest": [{
            "at": _iso(event.created_at),
            "format": event.data.get("format"),
            "layout": event.data.get("layout"),
            "outcome": event.outcome,
            "duration_ms": event.duration_ms,
            "must": len(event.data.get("must", [])),
        } for event in stats["latest"]],
    }


def _seconds(ms: float | None) -> str:
    return "—" if ms is None else f"{ms / 1000:.2f} s"


def render(stats: dict) -> str:
    config = current_app.config
    periods = stats["periods"]
    lines = [f"{config['SITE_NAME']} ({config['SITE']}) — mesure d'usage au {stats['now']:%d/%m/%Y %H:%M} UTC", ""]

    rows = [
        ("Visiteurs (somme par jour)", "visitors"),
        ("Recherches", "searches"),
        ("Générations demandées", "generations"),
        ("  grilles obtenues", "grids"),
        ("  taux de réussite", "success"),
        ("  refus « occupé »", "busy"),
        ("  refus rate limiting", "rate_limited"),
        ("  durée médiane (réussies)", "p50"),
        ("  durée p95 (réussies)", "p95"),
        ("  temps CPU", "cpu_s"),
        ("  part de la capacité CPU", "cpu_share"),
        ("Inscriptions", "register"),
        ("Adresses confirmées", "verify"),
        ("Connexions", "login"),
        ("Comptes supprimés", "delete"),
        ("Grilles conservées", "saved"),
        ("Erreurs (4xx et 5xx)", "errors"),
        ("  dont 5xx", "server_errors"),
    ]
    header = f"{'':32}" + "".join(f"{label:>14}" for label, _ in PERIODS)
    lines.append(header)
    for label, key in rows:
        cells = []
        for period, _ in PERIODS:
            value = periods[period][key]
            if key in ("p50", "p95"):
                value = _seconds(value)
            elif key == "cpu_s":
                value = f"{value:.0f} s"
            elif key == "cpu_share":
                value = f"{100 * value:.2f} %"
            cells.append(f"{value!s:>14}")
        lines.append(f"{label:32}" + "".join(cells))

    month = periods["30 jours"]
    lines += ["", "Seuils de l'ADR 0013 (30 jours) :"]
    p95 = month["p95"]
    lines.append(f"  p95 des générations : {_seconds(p95)} (seuil {P95_THRESHOLD_S} s)"
                 + ("  ⚠️ DÉPASSÉ" if p95 is not None and p95 > P95_THRESHOLD_S * 1000 else ""))
    busy_share = month["busy"] / month["generations"] if month["generations"] else 0
    lines.append(f"  refus « occupé » : {100 * busy_share:.1f} % des générations (seuil {100 * BUSY_THRESHOLD:.0f} %)"
                 + ("  ⚠️ DÉPASSÉ" if busy_share > BUSY_THRESHOLD else ""))

    def section(title, counter, fmt=lambda key, value: f"{key} : {value}", limit=15):
        lines.extend(["", title])
        if not counter:
            lines.append("  (rien)")
        for key, value in counter.most_common(limit) if isinstance(counter, Counter) else counter:
            lines.append(f"  {fmt(key, value)}")

    section("Issues des générations (30 jours) :", stats["outcomes"])
    section("Formats (30 jours, hors refus) :",
            sorted(stats["formats"].items(), key=lambda item: -sum(item[1].values())),
            lambda fmt, c: f"{fmt} : {sum(c.values())} demandes, réussite {_rate(c['grid'], sum(c.values()))}")
    section("Réussite selon le nombre de mots imposés (30 jours) :",
            sorted(stats["by_must_count"].items()),
            lambda n, c: f"{'3 et plus' if n == 3 else n} : {sum(c.values())} demandes, "
                         f"réussite {_rate(c['grid'], sum(c.values()))}")
    section("Mots imposés absents du lexique (30 jours, pour la curation) :", stats["unknown_words"])
    section("Pays des visiteurs (30 jours, événements) :", stats["countries"], limit=10)
    section("Erreurs par route et statut (30 jours) :", stats["errors"],
            lambda key, value: f"{key[1]} {key[0]} : {value}")

    lines.extend(["", "Dernières générations :"])
    if not stats["latest"]:
        lines.append("  (aucune)")
    for event in stats["latest"]:
        must = event.data.get("must", [])
        lines.append(f"  {event.created_at:%d/%m %H:%M}  {event.data.get('format', '?'):>6}  "
                     f"{event.outcome or '?':<20} {_seconds(event.duration_ms):>7}  "
                     f"{len(must)} mot(s) imposé(s)")
    return "\n".join(lines)


usage_cli = AppGroup("usage", help="Mesure d'usage (ADR 0016).")


@usage_cli.command("purge")
def purge_command():
    """Efface les mots imposés de plus de 90 jours, les événements de plus de 13 mois et les sels passés."""
    usage.purge()
    click.echo("Mesure d'usage : ménage fait.")


@click.command("stats")
def stats_command():
    """Chiffres du jour, de 7 et de 30 jours : visiteurs, générations, comptes, erreurs (ADR 0016)."""
    click.echo(render(compute()))


def init_stats_cli(app) -> None:
    app.cli.add_command(stats_command)
    app.cli.add_command(usage_cli)
