from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select
from app.db.models.assistant import AssistantAssessment


async def assessment_started(session, user_id: int, kind: str, result: dict):
    payload = result.get("session") or {}
    if not result.get("ok") or not payload.get("id"):
        return
    row = await session.scalar(select(AssistantAssessment).where(
        AssistantAssessment.user_id == user_id,
        AssistantAssessment.session_id == str(payload["id"]),
    ))
    if row is None:
        row = AssistantAssessment(id=str(uuid4()), user_id=user_id, session_id=str(payload["id"]), kind=kind)
        session.add(row)
    # Reopening a cancelled attempt may not make its questions available to AI.
    row.status = "active"
    row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=min(240, max(10, int(payload.get("duration_min") or 120))))
    await session.commit()


async def assessment_finished(session, user_id: int, session_id: str, status="completed"):
    row = await session.scalar(select(AssistantAssessment).where(
        AssistantAssessment.user_id == user_id, AssistantAssessment.session_id == session_id,
    ))
    if row:
        row.status = status
        await session.commit()


async def active_assessment(session, user_id: int) -> bool:
    return bool(await session.scalar(select(AssistantAssessment.id).where(
        AssistantAssessment.user_id == user_id,
        AssistantAssessment.status == "active",
        AssistantAssessment.expires_at > datetime.now(timezone.utc),
    ).limit(1)))


async def assessment_abandoned(session, user_id: int, session_id: str) -> bool:
    return bool(await session.scalar(select(AssistantAssessment.id).where(
        AssistantAssessment.user_id == user_id, AssistantAssessment.session_id == session_id,
        AssistantAssessment.status == "abandoned",
    ).limit(1)))
