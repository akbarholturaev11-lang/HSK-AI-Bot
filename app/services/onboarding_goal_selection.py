"""Validated additional onboarding choices; no XP, entitlement or reminder grant.

Legacy clients keep the original scalar goal. New clients can save an ordered
multi-goal selection whose first member is the scalar primary goal.
"""
from __future__ import annotations

import json

ALLOWED_GOALS = frozenset({
    "hsk_exam", "daily_communication", "travel", "work_china", "study_china",
})
ALLOWED_STREAK_TARGETS = frozenset({7, 14, 30, 50})


def normalize_onboarding_goals(value, *, primary_goal: str) -> tuple[str, ...] | None:
    """None means no new selection supplied by a legacy client."""
    if value is None:
        return None
    if not isinstance(value, list) or not 1 <= len(value) <= len(ALLOWED_GOALS):
        raise ValueError("onboarding_goals_invalid")
    if any(type(item) is not str or item not in ALLOWED_GOALS for item in value):
        raise ValueError("onboarding_goals_invalid")
    if len(set(value)) != len(value) or value[0] != primary_goal:
        raise ValueError("onboarding_goals_invalid")
    return tuple(value)


def read_onboarding_goals(raw: str | None, *, primary_goal: str) -> list[str]:
    """Old or malformed records fall back to the validated scalar legacy goal."""
    primary = primary_goal if primary_goal in ALLOWED_GOALS else "hsk_exam"
    if raw:
        try:
            value = json.loads(raw)
            normalized = normalize_onboarding_goals(value, primary_goal=primary)
            if normalized is not None:
                return list(normalized)
        except (ValueError, TypeError):
            pass
    return [primary]


def normalize_streak_target(value) -> int | None:
    """Unset preserves an existing target; bool must not coerce to int."""
    if value is None:
        return None
    if type(value) is not int or value not in ALLOWED_STREAK_TARGETS:
        raise ValueError("onboarding_streak_target_invalid")
    return value
