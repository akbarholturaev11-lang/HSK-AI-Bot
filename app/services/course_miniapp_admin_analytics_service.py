from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any, Iterable

from sqlalchemy import func, select

from app.db.models.course_miniapp_event import COURSE_MINIAPP_EVENT_NAMES, CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent


FOUNDATION_FUNNEL_EVENT_NAMES = (
    "foundation_started",
    "foundation_completed",
    "interaction_completed",
    "section_completed",
    "lesson_completed",
    "book_lesson_completed",
    "test_completed",
    "training_completed",
    "mistake_review_completed",
    "paywall_seen",
)
FOUNDATION_MEANINGFUL_LEARNING_EVENTS = frozenset(
    {
        "section_completed",
        "lesson_completed",
        "book_lesson_completed",
        "test_completed",
        "training_completed",
        "mistake_review_completed",
    }
)
FOUNDATION_CHECKPOINT_PAYWALL_WINDOW = timedelta(hours=24)
FOUNDATION_D1_WINDOW_START = timedelta(hours=24)
FOUNDATION_D1_WINDOW_END = timedelta(hours=48)


@dataclass(frozen=True)
class LessonDropoffRow:
    level: str
    lesson_order: int
    started: int
    completed: int


def _as_utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_checkpoint_paywall_source(source: Any) -> bool:
    normalized = _text(source).lower()
    return (
        normalized in {"v3_paywall", "v3_locked_lesson", "v3_lesson_ad_offer"}
        or "checkpoint" in normalized
        or "locked_lesson" in normalized
    )


def build_foundation_metrics(rows: Iterable[tuple], *, now: datetime) -> dict[str, Any]:
    """Build Starter 0 cohort metrics from the existing event stream.

    Tuple shape: ``(event_name, telegram_id, source, level, lesson_order,
    payload_json, created_at)``. Conversions are chronological and version-bound;
    a completion without a matching earlier start is deliberately excluded.
    """

    now_utc = _as_utc(now) or datetime.now(timezone.utc)
    events: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 7:
            continue
        created_at = _as_utc(row[6])
        telegram_id = _int(row[1])
        if not created_at or not telegram_id:
            continue
        events.append(
            {
                "event_name": _text(row[0]),
                "telegram_id": telegram_id,
                "source": _text(row[2]),
                "level": _text(row[3]).lower(),
                "lesson_order": _int(row[4]),
                "payload": _payload(row[5]),
                "created_at": created_at,
            }
        )
    events.sort(key=lambda item: item["created_at"])

    starts: dict[tuple[int, str], datetime] = {}
    start_entry_levels: dict[tuple[int, str], str] = {}
    completion_candidates: list[dict[str, Any]] = []
    for event in events:
        data = event["payload"]
        version = _text(data.get("foundation_version"))
        if not version:
            continue
        key = (event["telegram_id"], version)
        if event["event_name"] == "foundation_started":
            starts.setdefault(key, event["created_at"])
            start_entry_levels.setdefault(key, _text(data.get("entry_level")).lower() or "unknown")
        elif event["event_name"] == "foundation_completed":
            completion_candidates.append(event)

    completions: dict[tuple[int, str], datetime] = {}
    for event in completion_candidates:
        version = _text(event["payload"].get("foundation_version"))
        key = (event["telegram_id"], version)
        started_at = starts.get(key)
        if started_at and event["created_at"] >= started_at:
            completions.setdefault(key, event["created_at"])

    started_users = {telegram_id for telegram_id, _ in starts}
    completed_users = {telegram_id for telegram_id, _ in completions}
    completed_at_by_user: dict[int, datetime] = {}
    for (telegram_id, _), completed_at in completions.items():
        current = completed_at_by_user.get(telegram_id)
        if current is None or completed_at < current:
            completed_at_by_user[telegram_id] = completed_at

    first_attempts: dict[tuple[int, str, str], tuple[datetime, bool]] = {}
    for event in events:
        if event["event_name"] != "interaction_completed":
            continue
        data = event["payload"]
        version = _text(data.get("foundation_version"))
        objective_id = _text(data.get("objective_id"))
        card_id = _text(data.get("card_id"))
        if (
            not version
            or not objective_id
            or not card_id
            or _int(data.get("attempt")) != 1
            or data.get("guided") is not False
            or not isinstance(data.get("correct"), bool)
        ):
            continue
        foundation_key = (event["telegram_id"], version)
        started_at = starts.get(foundation_key)
        completed_at = completions.get(foundation_key)
        if not started_at or event["created_at"] < started_at:
            continue
        if completed_at and event["created_at"] > completed_at:
            continue
        objective_key = (event["telegram_id"], version, objective_id)
        current = first_attempts.get(objective_key)
        if current is None or event["created_at"] < current[0]:
            first_attempts[objective_key] = (event["created_at"], data["correct"])

    part_users: dict[int, set[int]] = {1: set(), 2: set(), 3: set()}
    part_completed_at: dict[tuple[int, int], datetime] = {}
    for event in events:
        if (
            event["event_name"] != "section_completed"
            or event["level"] != "hsk1"
            or event["lesson_order"] != 1
        ):
            continue
        part_no = _int(event["payload"].get("section_no"))
        completed_at = completed_at_by_user.get(event["telegram_id"])
        if part_no not in part_users or not completed_at or event["created_at"] < completed_at:
            continue
        part_users[part_no].add(event["telegram_id"])
        key = (event["telegram_id"], part_no)
        current = part_completed_at.get(key)
        if current is None or event["created_at"] < current:
            part_completed_at[key] = event["created_at"]

    checkpoint_users = part_users[3]
    checkpoint_paywall_users: set[int] = set()
    for event in events:
        if event["event_name"] != "paywall_seen" or not _is_checkpoint_paywall_source(event["source"]):
            continue
        checkpoint_at = part_completed_at.get((event["telegram_id"], 3))
        if (
            checkpoint_at
            and checkpoint_at <= event["created_at"] <= checkpoint_at + FOUNDATION_CHECKPOINT_PAYWALL_WINDOW
        ):
            checkpoint_paywall_users.add(event["telegram_id"])

    d1_eligible = {
        telegram_id
        for telegram_id, completed_at in completed_at_by_user.items()
        if completed_at + FOUNDATION_D1_WINDOW_END <= now_utc
    }
    d1_returned: set[int] = set()
    for event in events:
        telegram_id = event["telegram_id"]
        completed_at = completed_at_by_user.get(telegram_id)
        if telegram_id not in d1_eligible or not completed_at:
            continue
        if (
            event["event_name"] in FOUNDATION_MEANINGFUL_LEARNING_EVENTS
            and completed_at + FOUNDATION_D1_WINDOW_START
            <= event["created_at"]
            < completed_at + FOUNDATION_D1_WINDOW_END
        ):
            d1_returned.add(telegram_id)

    entry_levels: dict[str, dict[str, set[int]]] = {}
    for key in starts:
        entry_level = start_entry_levels.get(key, "unknown")
        entry_levels.setdefault(entry_level, {"started": set(), "completed": set()})["started"].add(key[0])
    for key in completions:
        entry_level = start_entry_levels.get(key, "unknown")
        entry_levels.setdefault(entry_level, {"started": set(), "completed": set()})["completed"].add(key[0])

    first_attempt_total = len(first_attempts)
    first_attempt_correct = sum(1 for _, correct in first_attempts.values() if correct)
    completed_total = len(completed_users)
    checkpoint_total = len(checkpoint_users)
    return {
        "started_users": len(started_users),
        "completed_users": completed_total,
        "completion_rate": CourseMiniAppAdminAnalyticsService._pct(completed_total, len(started_users)),
        "first_attempt": {
            "objectives": first_attempt_total,
            "correct": first_attempt_correct,
            "accuracy": CourseMiniAppAdminAnalyticsService._pct(first_attempt_correct, first_attempt_total),
        },
        "parts": [
            {
                "part": part_no,
                "completed_users": len(part_users[part_no]),
                "rate_from_foundation": CourseMiniAppAdminAnalyticsService._pct(
                    len(part_users[part_no]), completed_total
                ),
            }
            for part_no in (1, 2, 3)
        ],
        "checkpoint_to_paywall": {
            "checkpoint_users": checkpoint_total,
            "paywall_users": len(checkpoint_paywall_users),
            "rate": CourseMiniAppAdminAnalyticsService._pct(len(checkpoint_paywall_users), checkpoint_total),
            "attribution_hours": int(FOUNDATION_CHECKPOINT_PAYWALL_WINDOW.total_seconds() // 3600),
        },
        "d1_meaningful_return": {
            "eligible": len(d1_eligible),
            "returned": len(d1_returned),
            "rate": CourseMiniAppAdminAnalyticsService._pct(len(d1_returned), len(d1_eligible)),
            "window_hours": [24, 48],
        },
        "entry_levels": [
            {
                "entry_level": entry_level,
                "started_users": len(values["started"]),
                "completed_users": len(values["completed"]),
                "completion_rate": CourseMiniAppAdminAnalyticsService._pct(
                    len(values["completed"]), len(values["started"])
                ),
            }
            for entry_level, values in sorted(entry_levels.items())
        ],
        "explain": (
            "Starter completion bir xil foundation_version ichida startdan keyin hisoblanadi. "
            "First-attempt = guided bo'lmagan ilk objective javobi. P1/P2/P3 faqat Starterdan keyingi "
            "HSK1-1 qismlar; checkpoint paywall 24 soatlik course-paywall attribution. D1 meaningful "
            "return = Starterdan 24–48 soat keyingi real learning completion event'i."
        ),
    }


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

    async def foundation_metrics(
        self,
        *,
        since: datetime | None,
        now: datetime,
    ) -> dict[str, Any]:
        cohort = select(CourseMiniAppEvent.telegram_id).where(
            CourseMiniAppEvent.event_name == "foundation_started",
            CourseMiniAppEvent.created_at <= now,
        )
        if since is not None:
            cohort = cohort.where(CourseMiniAppEvent.created_at >= since)
        cohort = cohort.distinct()

        conditions = [
            CourseMiniAppEvent.event_name.in_(FOUNDATION_FUNNEL_EVENT_NAMES),
            CourseMiniAppEvent.telegram_id.in_(cohort),
            CourseMiniAppEvent.created_at <= now,
        ]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.source,
                    CourseMiniAppEvent.level,
                    CourseMiniAppEvent.lesson_order,
                    CourseMiniAppEvent.payload_json,
                    CourseMiniAppEvent.created_at,
                ).where(*conditions)
            )
        ).all()
        return build_foundation_metrics([tuple(row) for row in rows], now=now)

    async def admin_text(self, *, week_ago: datetime) -> str:
        now = datetime.now(timezone.utc)
        all_unique = await self._counts_by_event(unique=True)
        week_unique = await self._counts_by_event(since=week_ago, unique=True)
        week_counts = await self._counts_by_event(since=week_ago)
        weekly_xp = await self._weekly_xp(since=week_ago)
        lesson_dropoff = await self._lesson_dropoff(since=week_ago)
        foundation = await self.foundation_metrics(since=week_ago, now=now)

        section_start = self._event(week_counts, "section_started")
        section_completed = self._event(week_counts, "section_completed")
        chapter_completed = self._event(week_counts, "chapter_completed")
        book_completed = self._event(week_counts, "book_lesson_completed")
        test_started = self._event(week_counts, "test_started")
        training_started = self._event(week_counts, "training_started")
        voice_started = self._event(week_counts, "voice_started")
        paywall_seen = self._event(week_counts, "paywall_seen")
        checkout_opened = self._event(week_counts, "checkout_opened")
        foundation_first = foundation["first_attempt"]
        foundation_parts = {int(item["part"]): item for item in foundation["parts"]}
        checkpoint_paywall = foundation["checkpoint_to_paywall"]
        foundation_d1 = foundation["d1_meaningful_return"]

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
                "  Starter 0 7 kun (unikal): "
                f"Boshladi <b>{foundation['started_users']}</b>→<b>{foundation['completed_users']}</b> "
                f"(<b>{foundation['completion_rate']}%</b>) · "
                f"Birinchi urinish <b>{foundation_first['correct']}</b>/<b>{foundation_first['objectives']}</b> "
                f"(<b>{foundation_first['accuracy']}%</b>)"
            ),
            (
                "  Starter → HSK1-1: "
                f"P1 <b>{foundation_parts[1]['completed_users']}</b> "
                f"(<b>{foundation_parts[1]['rate_from_foundation']}%</b>) · "
                f"P2 <b>{foundation_parts[2]['completed_users']}</b> "
                f"(<b>{foundation_parts[2]['rate_from_foundation']}%</b>) · "
                f"P3 <b>{foundation_parts[3]['completed_users']}</b> "
                f"(<b>{foundation_parts[3]['rate_from_foundation']}%</b>) · "
                f"Checkpoint→paywall <b>{checkpoint_paywall['paywall_users']}</b>/"
                f"<b>{checkpoint_paywall['checkpoint_users']}</b> "
                f"(<b>{checkpoint_paywall['rate']}%</b>)"
            ),
            (
                "  Starter D1 meaningful return: "
                f"<b>{foundation_d1['returned']}</b>/<b>{foundation_d1['eligible']}</b> "
                f"(<b>{foundation_d1['rate']}%</b>)"
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
