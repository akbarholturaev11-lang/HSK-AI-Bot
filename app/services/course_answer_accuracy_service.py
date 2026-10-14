"""Verified answer accuracy for the two profile rings.

Scores are weighted by the number of server-graded questions, not by a mean of
percentages. Missing/ungraded data is not treated as a 100% score.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models.course_attempts import CourseAttempt
from app.db.models.course_miniapp_event import CourseMiniAppEvent

ACCURACY_EVENTS = (
    "section_completed",
    "section_attempt_scored",
    "training_completed",
    "practice_attempt_scored",
    "test_completed",
    "mistake_review_answered",
)


def _utc(value) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _payload(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        obj = json.loads(raw or "{}")
    except (ValueError, TypeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def _safe_pair(payload: dict) -> tuple[int, int] | None:
    """Require an actual denominator. Percentage-only or AI-graded results are excluded."""
    correct = payload.get("correct", payload.get("score"))
    total = payload.get("total")
    if isinstance(correct, bool) or isinstance(total, bool):
        return None
    try:
        correct = int(correct)
        total = int(total)
    except (TypeError, ValueError):
        return None
    if not (0 <= correct <= total <= 1000 and total > 0):
        return None
    return correct, total


def accuracy_summary(event_rows, quiz_rows, *, timezone_offset_minutes: int = 0, now=None) -> dict:
    """Input: (name, lesson_id, payload_json, created_at), quiz: (answers_json, created_at).

    Old successful section completions and new scored section attempts represent
    the same answer. Count the newer telemetry only, retaining older history.
    """
    now_utc = _utc(now) or datetime.now(timezone.utc)
    offset_minutes = max(-720, min(840, int(timezone_offset_minutes or 0)))
    local_day = (now_utc + timedelta(minutes=offset_minutes)).date()
    scored_starts = {}
    practice_first = {}
    decoded = []
    for name, lesson_id, raw, created_at in event_rows:
        stamp = _utc(created_at)
        if stamp is None:
            continue
        payload = _payload(raw)
        decoded.append((name, lesson_id, payload, stamp))
        if name == "practice_attempt_scored":
            mode = str(payload.get("mode") or "")
            if mode in {"training", "mock", "placement"}:
                legacy_event = "training_completed" if mode == "training" else "test_completed"
                if legacy_event not in practice_first or stamp < practice_first[legacy_event]:
                    practice_first[legacy_event] = stamp
        if name == "section_attempt_scored":
            section = str(payload.get("section_key") or "")
            if section:
                key = (lesson_id, section)
                if key not in scored_starts or stamp < scored_starts[key]:
                    scored_starts[key] = stamp

    all_correct = all_total = day_correct = day_total = 0

    def add(pair, at):
        nonlocal all_correct, all_total, day_correct, day_total
        if pair is None:
            return
        right, total = pair
        all_correct += right
        all_total += total
        if (at + timedelta(minutes=offset_minutes)).date() == local_day:
            day_correct += right
            day_total += total

    for name, lesson_id, payload, stamp in decoded:
        if name == "section_completed":
            key = (lesson_id, str(payload.get("section_key") or ""))
            if key in scored_starts and stamp >= scored_starts[key]:
                continue
            pair = _safe_pair(payload)
        elif name in {"test_completed", "training_completed"}:
            # The first new practice-scored event was written just after the
            # corresponding legacy completion. Do not double-count that pair.
            first = practice_first.get(name)
            if first and abs((stamp - first).total_seconds()) <= 10:
                continue
            pair = _safe_pair(payload)
        elif name in {"section_attempt_scored", "practice_attempt_scored"}:
            pair = _safe_pair(payload)
        elif name == "mistake_review_answered":
            if payload.get("answer_type") == "tokens" and isinstance(payload.get("correct"), bool):
                pair = (int(payload["correct"]), 1)
            else:
                a, b = payload.get("selected_index"), payload.get("correct_index")
                pair = (int(a == b), 1) if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) and not isinstance(b, bool) else None
        else:
            continue
        add(pair, stamp)

    for raw, created_at in quiz_rows:
        stamp = _utc(created_at)
        if stamp is None:
            continue
        item = _payload(raw)
        if item.get("source") != "miniapp_server_graded":
            continue
        add(_safe_pair(item), stamp)

    def result(correct, total):
        return {
            "percent": round(correct / total * 100) if total else None,
            "correct": correct,
            "total": total,
            "wrong": total - correct,
        }

    return {
        "overall": result(all_correct, all_total),
        "today": result(day_correct, day_total),
        "local_date": local_day.isoformat(),
        "scope": "verified_graded_answers",
        "partial_history": True,
    }


class CourseAnswerAccuracyService:
    def __init__(self, session):
        self.session = session

    async def summarize(self, *, user_id: int, timezone_offset_minutes: int = 0):
        event_result = await self.session.execute(
            select(
                CourseMiniAppEvent.event_name,
                CourseMiniAppEvent.lesson_id,
                CourseMiniAppEvent.payload_json,
                CourseMiniAppEvent.created_at,
            )
            .where(
                CourseMiniAppEvent.user_id == user_id,
                CourseMiniAppEvent.event_name.in_(ACCURACY_EVENTS),
            )
            .order_by(CourseMiniAppEvent.created_at.asc())
        )
        attempts = await self.session.execute(
            select(CourseAttempt.answers_json, CourseAttempt.created_at)
            .where(CourseAttempt.user_id == user_id, CourseAttempt.attempt_type == "quiz")
            .order_by(CourseAttempt.created_at.asc())
        )
        return accuracy_summary(
            event_result.all(),
            attempts.all(),
            timezone_offset_minutes=timezone_offset_minutes,
        )
