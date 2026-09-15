from datetime import date

import pytest

from tools.curator.gamification import (
    ACHIEVEMENTS,
    achievements_for,
    best_streak,
    current_streak,
    level_for,
    level_threshold,
)


def base_metrics(**overrides):
    metrics = {
        "total": 0, "best_day": 0, "best_streak": 0, "keeps": 0, "deletes": 0, "family_batches": 0,
        "hours": set(), "remaining_by_length": {"2-5": 10, "6-8": 10}, "totals_by_length": {"2-5": 10, "6-8": 10},
    }
    return {**metrics, **overrides}


def unlocked(metrics):
    return {a["id"] for a in achievements_for(metrics) if a["unlocked"]}


# --- Niveaux ---

@pytest.mark.parametrize("level, threshold", [(1, 0), (2, 50), (3, 150), (4, 300), (5, 500), (10, 2250)])
def test_level_thresholds(level, threshold):
    assert level_threshold(level) == threshold


@pytest.mark.parametrize("total, number, title", [
    (0, 1, "Apprenti"),
    (49, 1, "Apprenti"),
    (50, 2, "Apprenti"),
    (150, 3, "Cruciverbiste"),
    (750, 6, "Verbicruciste"),
    (2250, 10, "Maître des cases"),
    (100_000, 63, "Grand Terminator"),
])
def test_level_for(total, number, title):
    level = level_for(total)

    assert (level["number"], level["title"]) == (number, title)
    assert level["current"] <= total < level["next"]
    assert 0 <= level["progress"] < 1


# --- Séries ---

def test_current_streak_keeps_running_until_the_day_ends():
    today = date(2026, 9, 15)
    days = {date(2026, 9, 13), date(2026, 9, 14)}

    assert current_streak(days, today) == 2
    assert current_streak(days | {today}, today) == 3
    assert current_streak({date(2026, 9, 10)}, today) == 0


def test_best_streak_finds_the_longest_run():
    days = {date(2026, 9, d) for d in (1, 2, 3, 5, 6, 7, 8, 12)}

    assert best_streak(days) == 4
    assert best_streak(set()) == 0


# --- Badges ---

def test_no_badge_at_the_start():
    assert unlocked(base_metrics()) == set()


@pytest.mark.parametrize("overrides, badge", [
    ({"total": 1}, "first_word"),
    ({"best_streak": 3}, "streak_3"),
    ({"best_streak": 7}, "streak_7"),
    ({"best_streak": 30}, "streak_30"),
    ({"best_day": 100}, "hundred_day"),
    ({"best_day": 500}, "marathon"),
    ({"deletes": 1000}, "deletes_1000"),
    ({"keeps": 500}, "keeps_500"),
    ({"family_batches": 1}, "family"),
    ({"hours": {6}}, "early_bird"),
    ({"hours": {23}}, "night_owl"),
    ({"remaining_by_length": {"2-5": 0, "6-8": 10}}, "band_2_5"),
    ({"remaining_by_length": {"2-5": 10, "6-8": 0}}, "band_6_8"),
    ({"total": 10_000}, "ten_thousand"),
])
def test_each_badge_unlocks_on_its_condition(overrides, badge):
    assert badge in unlocked(base_metrics(**overrides))


def test_an_empty_band_is_not_a_finished_band():
    metrics = base_metrics(remaining_by_length={"2-5": 0}, totals_by_length={"2-5": 0})

    assert "band_2_5" not in unlocked(metrics)


def test_badges_have_unique_ids_and_french_texts():
    ids = [a.id for a in ACHIEVEMENTS]

    assert len(ids) == len(set(ids)) == 14
    assert all(a.name and a.description.endswith(".") for a in ACHIEVEMENTS)
