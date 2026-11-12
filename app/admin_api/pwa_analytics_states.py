"""Machine-readable V10 metric states; the legacy value payload stays intact."""
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def _registry():
    path = Path(__file__).resolve().parents[2] / "docs/analytics/FEATURE_ANALYTICS_COVERAGE.json"
    sections = {}
    for row in json.loads(path.read_text(encoding="utf-8"))["metrics"]:
        sections.setdefault(row["section"], []).append(row)
    return sections


def has_legacy_filter(section, platform):
    return any(platform in row["filters"] for row in _registry().get(section, ()))


def _null_reason(section, key, metrics):
    if section == "course":
        limited = {
            "activation": "activation", "direct_activation": "activation",
            "foundation": "foundation", "voice_minutes": "voice_minutes",
            "sessions": "sessions", "session_seconds": "sessions",
            "timed_lessons": "timed_lessons", "lesson_seconds": "timed_lessons",
        }
        # A platform view also reports None before any attributed row exists.
        if key in limited and limited[key] in metrics and metrics[limited[key]] is None and metrics.get("detail_limited", True):
            return "detail_limited"
    if (section, key) in (("funnel", "attempt_funnel"), ("funnel", "pwa_pro_attempt_funnel"), ("money", "ai_models")):
        return "detail_limited"
    return "no_data"


def metric_states(section, platform, metrics):
    values = metrics or {}
    states = {}
    for row in _registry().get(section, ()):
        if row["kind"] != "metric":
            continue
        key = row["key"]
        status = row["platforms"].get(platform, {}).get("status")
        if status == "not_applicable":
            state, reason = "not_applicable", "not_applicable"
        elif key in values and platform in row["filters"]:
            state, reason = ("unavailable", _null_reason(section, key, values)) if values[key] is None else ("available", None)
        else:
            state = "unavailable"
            reason = "not_instrumented" if status == "not_instrumented" else "attribution_not_audited"
        states[key] = {"state": state, "reason": reason}
    return states
