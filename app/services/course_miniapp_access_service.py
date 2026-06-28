from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_feature_usage import COURSE_FEATURE_KEYS, CourseFeatureUsage
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.user_access_state_service import UserAccessStateService


FREE_FEATURE_LIMITS = {feature_key: 1 for feature_key in COURSE_FEATURE_KEYS}
FREE_COURSE_LESSONS_PER_LEVEL = 3


class CourseMiniAppAccessService:
    """Server-side Course Mini App entitlements without changing payment rules."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _as_utc(value):
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def is_paid_user(cls, user) -> bool:
        return UserAccessStateService.is_paid(user)

    @classmethod
    def is_free_user(cls, user) -> bool:
        return bool(
            user
            and not cls.is_paid_user(user)
            and UserAccessStateService.classify(user) in UserAccessStateService.COURSE_ELIGIBLE_STATES
        )

    @classmethod
    def lesson_requires_premium(cls, level: str | None, lesson_order: int | None = None) -> bool:
        try:
            order = int(lesson_order or 0)
        except (TypeError, ValueError):
            order = 0
        return order > FREE_COURSE_LESSONS_PER_LEVEL

    @staticmethod
    def _normalize_feature_key(feature_key: str) -> str:
        normalized = str(feature_key or "").strip().lower()
        if normalized not in COURSE_FEATURE_KEYS:
            raise ValueError(f"Unknown Course Mini App feature: {normalized or '<empty>'}")
        return normalized

    async def _recorded_counts(self, user_id: int) -> dict[str, int]:
        result = await self.session.execute(
            select(CourseFeatureUsage.feature_key, func.count(CourseFeatureUsage.id))
            .where(CourseFeatureUsage.user_id == user_id)
            .group_by(CourseFeatureUsage.feature_key)
        )
        return {str(feature): int(count or 0) for feature, count in result.all()}

    async def _legacy_counts(self, user) -> dict[str, int]:
        counts = {feature_key: 0 for feature_key in COURSE_FEATURE_KEYS}
        if getattr(user, "trial_course_completed_at", None):
            counts["lesson"] = 1
        if getattr(user, "trial_voice_used_at", None):
            counts["voice"] = 1

        voice_result = await self.session.execute(
            select(func.count(VoicePracticeSession.id)).where(
                VoicePracticeSession.user_telegram_id == user.telegram_id
            )
        )
        if int(voice_result.scalar_one() or 0) > 0:
            counts["voice"] = 1
        return counts

    async def get_entitlements(self, user) -> dict[str, dict]:
        paid = self.is_paid_user(user)
        if paid:
            return {
                feature_key: {
                    "allowed": True,
                    "is_paid": True,
                    "free_limit": FREE_FEATURE_LIMITS[feature_key],
                    "used": 0,
                    "remaining_free": None,
                }
                for feature_key in COURSE_FEATURE_KEYS
            }

        if not self.is_free_user(user):
            return {
                feature_key: {
                    "allowed": False,
                    "is_paid": False,
                    "free_limit": FREE_FEATURE_LIMITS[feature_key],
                    "used": 0,
                    "remaining_free": 0,
                }
                for feature_key in COURSE_FEATURE_KEYS
            }

        recorded = await self._recorded_counts(user.id)
        legacy = await self._legacy_counts(user)
        entitlements = {}
        for feature_key in COURSE_FEATURE_KEYS:
            used = max(int(recorded.get(feature_key, 0)), int(legacy.get(feature_key, 0)))
            limit = FREE_FEATURE_LIMITS[feature_key]
            entitlements[feature_key] = {
                "allowed": used < limit,
                "is_paid": False,
                "free_limit": limit,
                "used": used,
                "remaining_free": max(0, limit - used),
            }
        return entitlements

    async def consume_free_use(self, user, *, feature_key: str, usage_ref: str) -> dict:
        feature_key = self._normalize_feature_key(feature_key)
        usage_ref = str(usage_ref or "").strip()[:120]
        if not usage_ref:
            raise ValueError("usage_ref is required")
        if self.is_paid_user(user):
            return {"allowed": True, "recorded": False, "is_paid": True, "idempotent": False}
        if not self.is_free_user(user):
            return {"allowed": False, "recorded": False, "error": "course_access_blocked"}

        locked_result = await self.session.execute(
            select(User).where(User.id == user.id).with_for_update()
        )
        locked_user = locked_result.scalar_one_or_none()
        if not locked_user:
            return {"allowed": False, "recorded": False, "error": "user_not_found"}

        existing_result = await self.session.execute(
            select(CourseFeatureUsage).where(
                CourseFeatureUsage.user_id == locked_user.id,
                CourseFeatureUsage.feature_key == feature_key,
                CourseFeatureUsage.usage_ref == usage_ref,
            )
        )
        if existing_result.scalar_one_or_none():
            return {"allowed": True, "recorded": False, "is_paid": False, "idempotent": True}

        entitlements = await self.get_entitlements(locked_user)
        if not entitlements[feature_key]["allowed"]:
            return {
                "allowed": False,
                "recorded": False,
                "is_paid": False,
                "error": "free_feature_limit_reached",
            }

        usage = CourseFeatureUsage(
            user_id=locked_user.id,
            feature_key=feature_key,
            usage_ref=usage_ref,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(usage)
                await self.session.flush()
        except IntegrityError:
            duplicate_result = await self.session.execute(
                select(CourseFeatureUsage.id).where(
                    CourseFeatureUsage.user_id == locked_user.id,
                    CourseFeatureUsage.feature_key == feature_key,
                    CourseFeatureUsage.usage_ref == usage_ref,
                )
            )
            if duplicate_result.scalar_one_or_none():
                return {"allowed": True, "recorded": False, "is_paid": False, "idempotent": True}
            raise

        return {"allowed": True, "recorded": True, "is_paid": False, "idempotent": False}
