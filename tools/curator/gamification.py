"""Ludification du curateur : niveaux, séries et badges.

Fonctions pures, sans état : tout est recalculé à partir des décisions (voir stats.py).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

DEFAULT_DAILY_GOAL = 100
LEVEL_STEP = 25
# Niveau à partir duquel le titre s'applique
LEVEL_TITLES = (
    (1, "Apprenti"),
    (3, "Cruciverbiste"),
    (6, "Verbicruciste"),
    (10, "Maître des cases"),
    (15, "Lexicographe"),
    (25, "Gardien du dictionnaire"),
    (40, "Grand Terminator"),
)


def level_threshold(level: int) -> int:
    """Mots triés nécessaires pour atteindre `level` : 0, 50, 150, 300, 500, 750…"""
    return LEVEL_STEP * level * (level - 1)


def level_for(total: int) -> dict:
    level = 1
    while level_threshold(level + 1) <= total:
        level += 1
    current, following = level_threshold(level), level_threshold(level + 1)
    return {
        "number": level,
        "title": [title for start, title in LEVEL_TITLES if start <= level][-1],
        "current": current,
        "next": following,
        "progress": round((total - current) / (following - current), 3),
    }


def current_streak(active_days: set[date], today: date) -> int:
    """Jours consécutifs avec au moins une décision. Une série reste en cours
    tant que la journée d'aujourd'hui n'est pas terminée."""
    day = today if today in active_days else today - timedelta(days=1)
    streak = 0
    while day in active_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def best_streak(active_days: set[date]) -> int:
    best = run = 0
    previous = None
    for day in sorted(active_days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


@dataclass(frozen=True)
class Achievement:
    id: str
    icon: str
    name: str
    description: str
    condition: Callable[[dict], bool]


def _band_finished(label: str) -> Callable[[dict], bool]:
    return lambda m: m["totals_by_length"].get(label, 0) > 0 and m["remaining_by_length"].get(label, 0) <= 0


# Dans l'ordre où ils sont généralement obtenus
ACHIEVEMENTS = (
    Achievement("first_word", "🌱", "Premier coup de ciseaux", "Trier un premier mot.",
                lambda m: m["total"] >= 1),
    Achievement("streak_3", "🔥", "Sur la lancée", "Trier trois jours de suite.",
                lambda m: m["best_streak"] >= 3),
    Achievement("family", "👪", "Toute la famille", "Supprimer d'un coup un mot et toutes ses formes.",
                lambda m: m["family_batches"] >= 1),
    Achievement("hundred_day", "💯", "Centurion", "Trier 100 mots dans la même journée.",
                lambda m: m["best_day"] >= 100),
    Achievement("early_bird", "🌅", "Lève-tôt", "Trier des mots avant 8 h.",
                lambda m: any(hour < 8 for hour in m["hours"])),
    Achievement("night_owl", "🦉", "Oiseau de nuit", "Trier des mots après 23 h.",
                lambda m: any(hour >= 23 for hour in m["hours"])),
    Achievement("streak_7", "📅", "Une semaine pile", "Trier sept jours de suite.",
                lambda m: m["best_streak"] >= 7),
    Achievement("keeps_500", "🛡️", "Gardien des mots", "Garder 500 mots.",
                lambda m: m["keeps"] >= 500),
    Achievement("marathon", "🏃", "Marathon", "Trier 500 mots dans la même journée.",
                lambda m: m["best_day"] >= 500),
    Achievement("deletes_1000", "✂️", "Grand ménage", "Supprimer 1 000 mots.",
                lambda m: m["deletes"] >= 1000),
    Achievement("band_2_5", "🧩", "Petits mots, grand ménage", "Finir le tri des mots de 2 à 5 lettres.",
                _band_finished("2-5")),
    Achievement("streak_30", "🏆", "Un mois sans faute", "Trier trente jours de suite.",
                lambda m: m["best_streak"] >= 30),
    Achievement("band_6_8", "🏅", "Cap des huit lettres", "Finir le tri des mots de 6 à 8 lettres.",
                _band_finished("6-8")),
    Achievement("ten_thousand", "🎖️", "Dix mille", "Trier 10 000 mots.",
                lambda m: m["total"] >= 10_000),
)


def achievements_for(metrics: dict) -> list[dict]:
    return [
        {"id": a.id, "icon": a.icon, "name": a.name, "description": a.description, "unlocked": bool(a.condition(metrics))}
        for a in ACHIEVEMENTS
    ]
