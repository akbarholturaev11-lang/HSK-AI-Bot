from dataclasses import dataclass

from sqlalchemy import func, select

from app.db.models.course_miniapp_event import CourseMiniAppEvent


@dataclass(frozen=True)
class MiniAppCourseStats:
    opened_users: int
    lesson_users: int
    completed_users: int
    completed_sections: int
    completed_book_lessons: int


async def _count_unique_users(session, event_names: tuple[str, ...]) -> int:
    return (
        await session.execute(
            select(func.count(func.distinct(CourseMiniAppEvent.telegram_id)))
            .select_from(CourseMiniAppEvent)
            .where(CourseMiniAppEvent.event_name.in_(event_names))
        )
    ).scalar() or 0


async def _count_events(session, event_names: str | tuple[str, ...]) -> int:
    names = (event_names,) if isinstance(event_names, str) else event_names
    return (
        await session.execute(
            select(func.count())
            .select_from(CourseMiniAppEvent)
            .where(CourseMiniAppEvent.event_name.in_(names))
        )
    ).scalar() or 0


async def miniapp_course_stats(session) -> MiniAppCourseStats:
    return MiniAppCourseStats(
        opened_users=await _count_unique_users(session, ("miniapp_opened",)),
        lesson_users=await _count_unique_users(session, ("lesson_started", "section_started")),
        completed_users=await _count_unique_users(
            session,
            ("section_completed", "book_lesson_completed", "lesson_completed"),
        ),
        completed_sections=await _count_events(session, "section_completed"),
        completed_book_lessons=await _count_events(session, ("book_lesson_completed", "lesson_completed")),
    )
