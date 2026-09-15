"""Statistiques de motivation : décisions du jour, série de jours, mots restants par longueur."""

from collections import Counter
from datetime import date, datetime, timedelta

from tools.lexicon.decisions import UNDO
from tools.lexicon.export import LENGTH_BANDS, _band_label

from .repository import LexiconRepository
from .store import DecisionStore


def streak_days(active_days: set[date], today: date) -> int:
    """Jours consécutifs avec au moins une décision. Une série en cours reste valable
    tant que la journée d'aujourd'hui n'est pas terminée."""
    day = today if today in active_days else today - timedelta(days=1)
    streak = 0
    while day in active_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _band(length: int) -> str:
    low, high = next(band for band in LENGTH_BANDS if band[0] <= length <= band[1])
    return _band_label(low, high)


def curation_stats(repository: LexiconRepository, store: DecisionStore, today: date | None = None) -> dict:
    today = today or datetime.now().astimezone().date()
    rows = store.rows()
    undone = {row.batch for row in rows if row.decision == UNDO}
    active_dates = [datetime.fromisoformat(row.date).astimezone().date()
                    for row in rows if row.decision != UNDO and row.batch not in undone]

    state = store.state()
    decided_suggestions = repository.suggestions(list(state))
    decided_by_band = Counter(_band(len(word)) for word, suggestion in decided_suggestions.items()
                              if suggestion != "keep")
    totals_by_band = Counter()
    for length, total in repository.queue_totals_by_length().items():
        totals_by_band[_band(length)] += total

    return {
        "today": sum(1 for day in active_dates if day == today),
        "streak_days": streak_days(set(active_dates), today),
        "decisions": dict(Counter(state.values())),
        "remaining_by_length": {
            _band_label(low, high): totals_by_band[_band_label(low, high)] - decided_by_band[_band_label(low, high)]
            for low, high in LENGTH_BANDS
        },
    }
