"""Statistiques du curateur : avancement, objectif du jour, séries, niveau et badges.

Tout est recalculé à partir de data/lexicon/decisions.csv : aucune autre donnée n'est stockée,
la progression est donc la même sur tous les appareils.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from tools.lexicon.decisions import DELETE, KEEP, UNDO
from tools.lexicon.export import LENGTH_BANDS, _band_label

from .gamification import DEFAULT_DAILY_GOAL, achievements_for, best_streak, current_streak, level_for
from .repository import LexiconRepository
from .store import DecisionStore

# Conservé pour la compatibilité des imports
streak_days = current_streak


def _band(length: int) -> str:
    low, high = next(band for band in LENGTH_BANDS if band[0] <= length <= band[1])
    return _band_label(low, high)


def curation_stats(repository: LexiconRepository, store: DecisionStore, today: date | None = None,
                   daily_goal: int = DEFAULT_DAILY_GOAL) -> dict:
    today = today or datetime.now().astimezone().date()
    rows = store.rows()
    undone = {row.batch for row in rows if row.decision == UNDO}

    # Un mot compte une fois par jour, même si l'auteur change d'avis
    words_by_day: dict[date, set[str]] = defaultdict(set)
    hours: set[int] = set()
    batch_sizes: Counter = Counter()
    for row in rows:
        if row.decision == UNDO or row.batch in undone:
            continue
        moment = datetime.fromisoformat(row.date).astimezone()
        words_by_day[moment.date()].add(row.word)
        hours.add(moment.hour)
        batch_sizes[row.batch] += 1

    state = store.state()
    decisions = Counter(state.values())
    decided_by_band = Counter(_band(len(word)) for word, suggestion in repository.suggestions(list(state)).items()
                              if suggestion != "keep")
    totals = {_band_label(low, high): 0 for low, high in LENGTH_BANDS}
    for length, total in repository.queue_totals_by_length().items():
        totals[_band(length)] += total
    remaining = {label: totals[label] - decided_by_band[label] for label in totals}

    active_days = set(words_by_day)
    metrics = {
        "total": len(state),
        "best_day": max((len(words) for words in words_by_day.values()), default=0),
        "best_streak": best_streak(active_days),
        "keeps": decisions[KEEP],
        "deletes": decisions[DELETE],
        "family_batches": sum(1 for size in batch_sizes.values() if size > 1),
        "hours": hours,
        "remaining_by_length": remaining,
        "totals_by_length": totals,
    }

    return {
        "today": len(words_by_day.get(today, ())),
        "daily_goal": daily_goal,
        "streak_days": current_streak(active_days, today),
        "best_streak": metrics["best_streak"],
        "best_day": metrics["best_day"],
        "total_decided": metrics["total"],
        "decisions": dict(decisions),
        "level": level_for(metrics["total"]),
        "week": [
            {"date": day.isoformat(), "count": len(words_by_day.get(day, ()))}
            for day in (today - timedelta(days=offset) for offset in range(6, -1, -1))
        ],
        "remaining_by_length": remaining,
        "totals_by_length": totals,
        "handled_by_rules": repository.handled_by_rules(),
        "achievements": achievements_for(metrics),
    }
