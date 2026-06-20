import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_pilot_event import CoursePilotEvent


PILOT_LEVELS = {"hsk1", "hsk2", "hsk3", "hsk4"}
PILOT_LESSON_MAX_ORDER = 3


def is_course_pilot_lesson(level: str | None, lesson_order: int | None) -> bool:
    try:
        order = int(lesson_order or 0)
    except (TypeError, ValueError):
        order = 0
    return (level or "").strip().lower() in PILOT_LEVELS and 1 <= order <= PILOT_LESSON_MAX_ORDER


class CoursePilotEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        telegram_id: int,
        level: str,
        lesson_order: int,
        event_type: str,
        step_name: str,
        user_id: int | None = None,
        lesson_id: int | None = None,
        block_no: int | None = None,
        mode: str = "course",
        payload: dict[str, Any] | None = None,
    ) -> CoursePilotEvent | None:
        normalized_level = (level or "").strip().lower()
        if not is_course_pilot_lesson(normalized_level, lesson_order):
            return None

        event = CoursePilotEvent(
            user_id=user_id,
            telegram_id=telegram_id,
            lesson_id=lesson_id,
            level=normalized_level,
            lesson_order=int(lesson_order),
            block_no=block_no,
            event_type=event_type,
            step_name=step_name,
            mode=mode or "course",
            payload_json=json.dumps(payload or {}, ensure_ascii=False) if payload else None,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def distinct_user_count(self, event_type: str | None = None) -> int:
        query = select(func.count(func.distinct(CoursePilotEvent.telegram_id)))
        if event_type:
            query = query.where(CoursePilotEvent.event_type == event_type)
        result = await self.session.execute(query)
        return int(result.scalar() or 0)

    async def lesson_breakdown(self) -> list[tuple[str, int, int, int]]:
        opened = func.count(func.distinct(CoursePilotEvent.telegram_id)).filter(
            CoursePilotEvent.event_type == "opened"
        )
        completed = func.count(func.distinct(CoursePilotEvent.telegram_id)).filter(
            CoursePilotEvent.event_type == "completed"
        )
        result = await self.session.execute(
            select(CoursePilotEvent.level, CoursePilotEvent.lesson_order, opened, completed)
            .group_by(CoursePilotEvent.level, CoursePilotEvent.lesson_order)
            .order_by(CoursePilotEvent.level, CoursePilotEvent.lesson_order)
        )
        return [(row[0], int(row[1]), int(row[2] or 0), int(row[3] or 0)) for row in result.fetchall()]

    async def drop_steps(self, limit: int = 6) -> list[tuple[str, int]]:
        result = await self.session.execute(
            select(CoursePilotEvent.step_name, func.count().label("cnt"))
            .where(CoursePilotEvent.event_type == "returned")
            .group_by(CoursePilotEvent.step_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(str(row[0] or ""), int(row[1] or 0)) for row in result.fetchall()]
