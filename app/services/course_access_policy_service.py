from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.repositories.bot_setting_repo import BotSettingRepository


COURSE_ACCESS_POLICY_KEY = "course_lesson_access_policy"
COURSE_ACCESS_MODE_SUBSCRIPTION = "subscription"
COURSE_ACCESS_MODE_ADS = "ads"
COURSE_ACCESS_MODE_FREE_UNTIL = "free_until"
COURSE_ACCESS_MODES = frozenset(
    {
        COURSE_ACCESS_MODE_SUBSCRIPTION,
        COURSE_ACCESS_MODE_ADS,
        COURSE_ACCESS_MODE_FREE_UNTIL,
    }
)
COURSE_ACCESS_OPEN = "open"
COURSE_ACCESS_SUBSCRIPTION = "subscription"
COURSE_ACCESS_AD = "ad"
COURSE_ACCESS_MAX_DURATION_DAYS = 36500


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return _as_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    except ValueError:
        return None


def _iso(value: datetime | None) -> str | None:
    value = _as_utc(value)
    if not value:
        return None
    return value.isoformat()


@dataclass(frozen=True)
class CourseLessonAccessPolicy:
    mode: str = COURSE_ACCESS_MODE_SUBSCRIPTION
    free_until: datetime | None = None
    updated_by_telegram_id: int | None = None
    saved_at: datetime | None = None

    @property
    def active_mode(self) -> str:
        if self.mode == COURSE_ACCESS_MODE_FREE_UNTIL:
            until = _as_utc(self.free_until)
            if until and until > _utcnow():
                return COURSE_ACCESS_MODE_FREE_UNTIL
            return COURSE_ACCESS_MODE_SUBSCRIPTION
        if self.mode == COURSE_ACCESS_MODE_ADS:
            return COURSE_ACCESS_MODE_ADS
        return COURSE_ACCESS_MODE_SUBSCRIPTION

    @property
    def free_active(self) -> bool:
        return self.active_mode == COURSE_ACCESS_MODE_FREE_UNTIL

    def is_protected_lesson(self, lesson_order: int | None, *, free_lessons: int) -> bool:
        try:
            order = int(lesson_order or 0)
        except (TypeError, ValueError):
            order = 0
        return order > int(free_lessons or 0)

    def requirement_for(
        self,
        *,
        lesson_order: int | None,
        is_paid: bool,
        free_lessons: int,
    ) -> str:
        if is_paid:
            return COURSE_ACCESS_OPEN
        if not self.is_protected_lesson(lesson_order, free_lessons=free_lessons):
            return COURSE_ACCESS_OPEN
        mode = self.active_mode
        if mode == COURSE_ACCESS_MODE_FREE_UNTIL:
            return COURSE_ACCESS_OPEN
        if mode == COURSE_ACCESS_MODE_ADS:
            return COURSE_ACCESS_AD
        return COURSE_ACCESS_SUBSCRIPTION

    def public_payload(self) -> dict:
        return {
            "mode": self.mode,
            "effective_mode": self.active_mode,
            "free_active": self.free_active,
            "free_until": _iso(self.free_until),
            "saved_at": _iso(self.saved_at),
            "updated_by_telegram_id": self.updated_by_telegram_id,
        }

    def stored_payload(self) -> dict:
        return {
            "mode": self.mode,
            "free_until": _iso(self.free_until),
            "saved_at": _iso(self.saved_at),
            "updated_by_telegram_id": self.updated_by_telegram_id,
        }


class CourseAccessPolicyService:
    def __init__(self, session):
        self.session = session
        self.repo = BotSettingRepository(session)

    @staticmethod
    def default_policy() -> CourseLessonAccessPolicy:
        return CourseLessonAccessPolicy()

    @classmethod
    def from_payload(cls, payload: dict | None) -> CourseLessonAccessPolicy:
        if not isinstance(payload, dict):
            return cls.default_policy()
        mode = str(payload.get("mode") or COURSE_ACCESS_MODE_SUBSCRIPTION).strip().lower()
        if mode not in COURSE_ACCESS_MODES:
            mode = COURSE_ACCESS_MODE_SUBSCRIPTION
        try:
            updated_by = int(payload.get("updated_by_telegram_id") or 0) or None
        except (TypeError, ValueError):
            updated_by = None
        return CourseLessonAccessPolicy(
            mode=mode,
            free_until=_parse_dt(payload.get("free_until")),
            saved_at=_parse_dt(payload.get("saved_at")),
            updated_by_telegram_id=updated_by,
        )

    async def get_policy(self) -> CourseLessonAccessPolicy:
        raw = await self.repo.get(COURSE_ACCESS_POLICY_KEY)
        if not raw:
            return self.default_policy()
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return self.default_policy()
        return self.from_payload(payload)

    async def get_payload(self) -> dict:
        return (await self.get_policy()).public_payload()

    async def save_policy(
        self,
        *,
        mode: str,
        duration_days: int | None = None,
        free_until: datetime | None = None,
        updated_by_telegram_id: int | None = None,
    ) -> CourseLessonAccessPolicy:
        normalized = str(mode or "").strip().lower()
        if normalized not in COURSE_ACCESS_MODES:
            raise ValueError("invalid_course_access_mode")

        until = _as_utc(free_until)
        if normalized == COURSE_ACCESS_MODE_FREE_UNTIL:
            if until is None:
                try:
                    days = int(duration_days or 0)
                except (TypeError, ValueError):
                    days = 0
                if days <= 0 or days > COURSE_ACCESS_MAX_DURATION_DAYS:
                    raise ValueError("invalid_course_access_duration")
                until = _utcnow() + timedelta(days=days)
            if until <= _utcnow():
                raise ValueError("invalid_course_access_duration")
        else:
            until = None

        try:
            updated_by = int(updated_by_telegram_id or 0) or None
        except (TypeError, ValueError):
            updated_by = None
        policy = CourseLessonAccessPolicy(
            mode=normalized,
            free_until=until,
            saved_at=_utcnow(),
            updated_by_telegram_id=updated_by,
        )
        await self.repo.set(
            COURSE_ACCESS_POLICY_KEY,
            json.dumps(policy.stored_payload(), ensure_ascii=False, separators=(",", ":")),
        )
        return policy
