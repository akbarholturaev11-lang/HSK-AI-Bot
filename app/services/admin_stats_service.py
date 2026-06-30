from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select

from app.db.models.ai_usage import AIUsageEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.referral import Referral
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession


@dataclass(frozen=True)
class MiniAppCourseStats:
    opened_users: int
    lesson_users: int
    completed_users: int
    completed_sections: int
    completed_book_lessons: int


@dataclass(frozen=True)
class FeatureUsage:
    """Bir bo'lim bo'yicha aktiv (unikal) foydalanuvchilar soni."""

    label: str
    today_users: int
    week_users: int


@dataclass(frozen=True)
class TopReferrer:
    """Eng ko'p odam taklif qilgan foydalanuvchi."""

    telegram_id: int
    name: str
    total: int
    activated: int


async def top_referrers(session, limit: int = 5) -> list[TopReferrer]:
    """Eng ko'p referal chaqirgan foydalanuvchilarni qaytaradi.

    Jami chaqirilganlar soni bo'yicha kamayish tartibida; ism sifatida
    @username, bo'lmasa to'liq ism, u ham bo'lmasa telegram_id ko'rsatiladi.
    """
    activated_expr = func.sum(case((Referral.status == "active", 1), else_=0))
    rows = (
        await session.execute(
            select(
                Referral.referrer_telegram_id.label("tid"),
                func.count().label("total"),
                activated_expr.label("activated"),
            )
            .where(Referral.referrer_telegram_id.is_not(None))
            .group_by(Referral.referrer_telegram_id)
            .order_by(func.count().desc(), activated_expr.desc())
            .limit(max(1, int(limit or 1)))
        )
    ).fetchall()

    if not rows:
        return []

    telegram_ids = [int(row.tid) for row in rows]
    users = {
        u.telegram_id: u
        for u in (
            await session.execute(select(User).where(User.telegram_id.in_(telegram_ids)))
        ).scalars().all()
    }

    result: list[TopReferrer] = []
    for row in rows:
        tid = int(row.tid)
        user = users.get(tid)
        username = getattr(user, "username", None)
        full_name = getattr(user, "full_name", None)
        if username:
            name = f"@{username}"
        elif full_name:
            name = full_name
        else:
            name = str(tid)
        result.append(
            TopReferrer(
                telegram_id=tid,
                name=name,
                total=int(row.total or 0),
                activated=int(row.activated or 0),
            )
        )
    return result


def _event_conditions(event_names: tuple[str, ...], since: datetime | None = None) -> list:
    conditions = [CourseMiniAppEvent.event_name.in_(event_names)]
    if since is not None:
        conditions.append(CourseMiniAppEvent.created_at >= since)
    return conditions


async def _count_unique_users(session, event_names: tuple[str, ...], since: datetime | None = None) -> int:
    return (
        await session.execute(
            select(func.count(func.distinct(CourseMiniAppEvent.telegram_id)))
            .select_from(CourseMiniAppEvent)
            .where(*_event_conditions(event_names, since))
        )
    ).scalar() or 0


async def _count_events(session, event_names: str | tuple[str, ...], since: datetime | None = None) -> int:
    names = (event_names,) if isinstance(event_names, str) else event_names
    return (
        await session.execute(
            select(func.count())
            .select_from(CourseMiniAppEvent)
            .where(*_event_conditions(names, since))
        )
    ).scalar() or 0


async def _count_distinct(session, column, *conditions) -> int:
    stmt = select(func.count(func.distinct(column)))
    if conditions:
        stmt = stmt.where(*conditions)
    return (await session.execute(stmt)).scalar() or 0


# Bot bo'limlari -> ularni ifodalovchi mini-app event nomlari.
# (Voice va AI savol-javob alohida jadvallardan o'qiladi.)
_FEATURE_EVENT_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("📖 Darslar", ("lesson_started", "section_started")),
    ("📝 Testlar", ("test_started", "test_completed")),
    ("🏋️ Mashqlar", ("training_started", "training_completed")),
    ("🔁 Xatolar takrori", ("mistake_review_started",)),
)


async def feature_usage_stats(
    session,
    today_start: datetime,
    week_ago: datetime,
) -> list[FeatureUsage]:
    """Qaysi bo'lim ko'proq ishlatilayotganini (unikal aktiv user) qaytaradi.

    Natija haftalik aktiv user soni bo'yicha kamayish tartibida saralanadi.
    """
    features: list[FeatureUsage] = []

    for label, event_names in _FEATURE_EVENT_MAP:
        features.append(
            FeatureUsage(
                label=label,
                today_users=await _count_unique_users(session, event_names, today_start),
                week_users=await _count_unique_users(session, event_names, week_ago),
            )
        )

    # 🎤 Voice roleplay — voice_practice_sessions jadvalidan
    features.append(
        FeatureUsage(
            label="🎤 Voice roleplay",
            today_users=await _count_distinct(
                session, VoicePracticeSession.user_telegram_id, VoicePracticeSession.started_at >= today_start
            ),
            week_users=await _count_distinct(
                session, VoicePracticeSession.user_telegram_id, VoicePracticeSession.started_at >= week_ago
            ),
        )
    )

    # 🤖 AI savol-javob — ai_usage_events jadvalidan
    features.append(
        FeatureUsage(
            label="🤖 AI savol-javob",
            today_users=await _count_distinct(
                session, AIUsageEvent.user_telegram_id, AIUsageEvent.created_at >= today_start
            ),
            week_users=await _count_distinct(
                session, AIUsageEvent.user_telegram_id, AIUsageEvent.created_at >= week_ago
            ),
        )
    )

    features.sort(key=lambda item: (item.week_users, item.today_users), reverse=True)
    return features


async def miniapp_course_stats(session, since: datetime | None = None) -> MiniAppCourseStats:
    return MiniAppCourseStats(
        opened_users=await _count_unique_users(session, ("miniapp_opened",), since),
        lesson_users=await _count_unique_users(session, ("lesson_started", "section_started"), since),
        completed_users=await _count_unique_users(
            session,
            ("section_completed", "book_lesson_completed", "lesson_completed"),
            since,
        ),
        completed_sections=await _count_events(session, "section_completed", since),
        completed_book_lessons=await _count_events(session, ("book_lesson_completed", "lesson_completed"), since),
    )
