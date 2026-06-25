from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape

from sqlalchemy import func, select

from app.db.models.course_miniapp_event import COURSE_MINIAPP_EVENT_NAMES, CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent


@dataclass(frozen=True)
class LessonDropoffRow:
    level: str
    lesson_order: int
    started: int
    completed: int


class CourseMiniAppAdminAnalyticsService:
    EVENT_NAMES = COURSE_MINIAPP_EVENT_NAMES

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _pct(part: int, total: int) -> float:
        return round(part / total * 100, 1) if total > 0 else 0.0

    @staticmethod
    def _event(values: dict[str, int], name: str) -> int:
        return int(values.get(name, 0) or 0)

    @classmethod
    def _rate(cls, values: dict[str, int], numerator: str, denominator: str) -> float:
        return cls._pct(cls._event(values, numerator), cls._event(values, denominator))

    @staticmethod
    def _level_sort_key(level: str) -> tuple[int, str]:
        normalized = (level or "").lower()
        order = {"beginner": 0, "hsk1": 1, "hsk2": 2, "hsk3": 3, "hsk4": 4}
        return (order.get(normalized, 99), normalized)

    @classmethod
    def format_lesson_dropoff(cls, rows: list[LessonDropoffRow], limit: int = 8) -> str:
        if not rows:
            return "hali yo'q"

        sorted_rows = sorted(
            rows,
            key=lambda item: (
                item.started - item.completed,
                item.started,
                -cls._level_sort_key(item.level)[0],
                -item.lesson_order,
            ),
            reverse=True,
        )
        parts = []
        for row in sorted_rows[:limit]:
            label = f"{escape(row.level.upper())}-{row.lesson_order}"
            parts.append(f"{label}: <b>{row.started}</b>→<b>{row.completed}</b> ({cls._pct(row.completed, row.started)}%)")
        return " | ".join(parts)

    async def _counts_by_event(self, *, since: datetime | None = None, unique: bool = False) -> dict[str, int]:
        count_expr = (
            func.count(func.distinct(CourseMiniAppEvent.telegram_id))
            if unique
            else func.count()
        )
        stmt = (
            select(CourseMiniAppEvent.event_name, count_expr.label("cnt"))
            .select_from(CourseMiniAppEvent)
            .group_by(CourseMiniAppEvent.event_name)
        )
        if since is not None:
            stmt = stmt.where(CourseMiniAppEvent.created_at >= since)

        rows = (await self.session.execute(stmt)).fetchall()
        values = {str(row.event_name): int(row.cnt or 0) for row in rows}
        return {name: values.get(name, 0) for name in self.EVENT_NAMES}

    async def _weekly_xp(self, *, since: datetime) -> int:
        value = (
            await self.session.execute(
                select(func.coalesce(func.sum(CourseXpEvent.xp), 0)).where(CourseXpEvent.created_at >= since)
            )
        ).scalar()
        return int(value or 0)

    async def _lesson_dropoff(self, *, since: datetime) -> list[LessonDropoffRow]:
        stmt = (
            select(
                CourseMiniAppEvent.level,
                CourseMiniAppEvent.lesson_order,
                CourseMiniAppEvent.event_name,
                func.count(func.distinct(CourseMiniAppEvent.telegram_id)).label("cnt"),
            )
            .select_from(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.created_at >= since,
                CourseMiniAppEvent.event_name.in_(("section_started", "section_completed")),
                CourseMiniAppEvent.level.is_not(None),
                CourseMiniAppEvent.lesson_order.is_not(None),
            )
            .group_by(
                CourseMiniAppEvent.level,
                CourseMiniAppEvent.lesson_order,
                CourseMiniAppEvent.event_name,
            )
        )
        grouped: dict[tuple[str, int], dict[str, int]] = {}
        rows = (await self.session.execute(stmt)).fetchall()
        for row in rows:
            key = (str(row.level or "unknown").lower(), int(row.lesson_order or 0))
            grouped.setdefault(key, {"section_started": 0, "section_completed": 0})
            grouped[key][str(row.event_name)] = int(row.cnt or 0)

        return [
            LessonDropoffRow(
                level=level,
                lesson_order=lesson_order,
                started=counts.get("section_started", 0),
                completed=counts.get("section_completed", 0),
            )
            for (level, lesson_order), counts in grouped.items()
            if counts.get("section_started", 0) > 0
        ]

    async def admin_text(self, *, week_ago: datetime) -> str:
        all_unique = await self._counts_by_event(unique=True)
        week_unique = await self._counts_by_event(since=week_ago, unique=True)
        week_counts = await self._counts_by_event(since=week_ago)
        weekly_xp = await self._weekly_xp(since=week_ago)
        lesson_dropoff = await self._lesson_dropoff(since=week_ago)

        section_start = self._event(week_counts, "section_started")
        section_completed = self._event(week_counts, "section_completed")
        chapter_completed = self._event(week_counts, "chapter_completed")
        book_completed = self._event(week_counts, "book_lesson_completed")
        test_started = self._event(week_counts, "test_started")
        training_started = self._event(week_counts, "training_started")
        voice_started = self._event(week_counts, "voice_started")
        paywall_seen = self._event(week_counts, "paywall_seen")
        checkout_opened = self._event(week_counts, "checkout_opened")

        lines = [
            "<b>📱 KURS MINI APP</b>",
            (
                "  Foydalanuvchi funnel all/7 kun: "
                f"Ochdi <b>{self._event(all_unique, 'miniapp_opened')}</b>/<b>+{self._event(week_unique, 'miniapp_opened')}</b> · "
                f"Onboarding <b>{self._event(all_unique, 'onboarding_started')}</b>/<b>+{self._event(week_unique, 'onboarding_started')}</b> · "
                f"Tugatdi <b>{self._event(all_unique, 'onboarding_completed')}</b>/<b>+{self._event(week_unique, 'onboarding_completed')}</b>"
            ),
            (
                "  Tanlovlar 7 kun: "
                f"Daraja <b>{self._event(week_counts, 'level_selected')}</b> · "
                f"Maqsad <b>{self._event(week_counts, 'goal_selected')}</b> · "
                f"Vaqt <b>{self._event(week_counts, 'daily_time_selected')}</b> · "
                f"Boshlash nuqtasi <b>{self._event(week_counts, 'start_point_selected')}</b>"
            ),
            (
                "  Kurs yo'li 7 kun: "
                f"Qism <b>{section_start}</b>→<b>{section_completed}</b> "
                f"(<b>{self._pct(section_completed, section_start)}%</b>) · "
                f"Bob <b>{chapter_completed}</b> · "
                f"Kitob darsi <b>{book_completed}</b> · "
                f"Kartalar <b>{self._event(week_counts, 'card_seen')}</b> · "
                f"Interaksiyalar <b>{self._event(week_counts, 'interaction_completed')}</b>"
            ),
            (
                "  Test/Mashq 7 kun: "
                f"Test <b>{test_started}</b>→<b>{self._event(week_counts, 'test_completed')}</b> "
                f"(<b>{self._rate(week_counts, 'test_completed', 'test_started')}%</b>) · "
                f"Mashq <b>{training_started}</b>→<b>{self._event(week_counts, 'training_completed')}</b> "
                f"(<b>{self._rate(week_counts, 'training_completed', 'training_started')}%</b>)"
            ),
            (
                "  AI Voice 7 kun: "
                f"Boshladi <b>{voice_started}</b> · Tugatdi <b>{self._event(week_counts, 'voice_completed')}</b> "
                f"(<b>{self._rate(week_counts, 'voice_completed', 'voice_started')}%</b>)"
            ),
            (
                "  Xatolar 7 kun: "
                f"Takrorlash <b>{self._event(week_counts, 'mistake_review_started')}</b>→"
                f"<b>{self._event(week_counts, 'mistake_review_completed')}</b> "
                f"(<b>{self._rate(week_counts, 'mistake_review_completed', 'mistake_review_started')}%</b>)"
            ),
            (
                "  XP/Streak 7 kun: "
                f"XP eventlar <b>{self._event(week_counts, 'xp_earned')}</b> · "
                f"XP jami <b>{weekly_xp}</b> · "
                f"Streak <b>{self._event(week_counts, 'streak_updated')}</b> · "
                f"Liga <b>{self._event(week_counts, 'league_points_earned')}</b>"
            ),
            (
                "  To'lov konversiyasi 7 kun: "
                f"To'lov oynasi <b>{paywall_seen}</b> · To'lov ochildi <b>{checkout_opened}</b> "
                f"(<b>{self._pct(checkout_opened, paywall_seen)}%</b>) · "
                f"Tasdiq <b>{self._event(week_counts, 'subscription_approved')}</b> "
                f"(<b>{self._rate(week_counts, 'subscription_approved', 'checkout_opened')}%</b>)"
            ),
            f"  Qism drop-off 7 kun: {self.format_lesson_dropoff(lesson_dropoff)}",
        ]
        return "\n".join(lines)
