"""Durable, server-only start record for Mini App clients predating signed proofs.

Old cached clients call /api/v3/lesson/start but do not echo completion_proof.
The *server* records a successful access-gated start for both Free and Pro,
so those clients can finish without accepting an unauthorised completion.
Reuses the existing course_miniapp_events table; no migration or client update.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.services.course_lesson_completion_proof import (
    PROOF_FUTURE_SKEW_SECONDS,
    PROOF_TTL_SECONDS,
)

# Never included in the allowlist for client-reported telemetry events.
AUTHORIZED_START_EVENT = "v3_lesson_authorized_start"


def _dedupe_key(level: str, lesson_order: int) -> str:
    return f"v3-start:{level}:{int(lesson_order)}"


async def remember_authorized_lesson_start(
    session, *, user, level: str, lesson_order: int,
) -> None:
    """Persist only AFTER the start endpoint's identity, course and access gates."""
    key = _dedupe_key(level, lesson_order)
    started_at = datetime.now(timezone.utc)
    record = await session.scalar(
        select(CourseMiniAppEvent).where(
            CourseMiniAppEvent.user_id == user.id,
            CourseMiniAppEvent.event_name == AUTHORIZED_START_EVENT,
            CourseMiniAppEvent.dedupe_key == key,
        ).limit(1)
    )
    if record is not None:
        # A reopened lesson renews the legacy window without adding rows.
        record.created_at = started_at
        return
    session.add(CourseMiniAppEvent(
        user_id=user.id,
        telegram_id=user.telegram_id,
        event_name=AUTHORIZED_START_EVENT,
        source="course_v3_server",
        level=level,
        lesson_order=lesson_order,
        session_id="lesson-start",
        dedupe_key=key,
        created_at=started_at,
    ))


async def has_recent_authorized_lesson_start(
    session, *, user_id: int, level: str, lesson_order: int,
    now: datetime | None = None,
) -> bool:
    """Accept missing proofs from cached clients, never malformed supplied ones."""
    started_at = await session.scalar(
        select(CourseMiniAppEvent.created_at).where(
            CourseMiniAppEvent.user_id == int(user_id),
            CourseMiniAppEvent.event_name == AUTHORIZED_START_EVENT,
            CourseMiniAppEvent.dedupe_key == _dedupe_key(level, lesson_order),
            CourseMiniAppEvent.level == level,
            CourseMiniAppEvent.lesson_order == int(lesson_order),
        ).limit(1)
    )
    if not isinstance(started_at, datetime):
        return False
    if started_at.tzinfo is None:  # SQLite stores aware timestamps as naive.
        started_at = started_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    age_seconds = (current - started_at).total_seconds()
    return -PROOF_FUTURE_SKEW_SECONDS <= age_seconds <= PROOF_TTL_SECONDS
