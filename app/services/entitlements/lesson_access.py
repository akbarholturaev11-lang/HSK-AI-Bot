"""Shared course start reservations and map access for all clients.

A lesson is one numbered mini lesson, as displayed on the course map. Starting
it reserves one slot. Reopening/completing that lesson never spends another.
"""
from sqlalchemy import select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.services.entitlements import actions as A
from app.services.entitlements.engine import EntitlementEngine
from app.services.entitlements.state import EntitlementState, resolve_state
from app.services.course_miniapp_access_service import CourseMiniAppAccessService, COURSE_DAILY_EVENT_NAME
from app.services.course_access_policy_service import CourseAccessPolicyService


class LessonAccessService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def reference(level, lesson_order):
        return f"lesson:{level}:{int(lesson_order)}"

    async def _reserved(self, user, reference):
        result = await self.session.execute(select(CourseMiniAppEvent.id).where(
            CourseMiniAppEvent.telegram_id == user.telegram_id,
            CourseMiniAppEvent.event_name == COURSE_DAILY_EVENT_NAME,
            CourseMiniAppEvent.session_id == "lesson",
            CourseMiniAppEvent.dedupe_key.endswith(f":ref:{reference}"),
        ).limit(1))
        return result.scalar_one_or_none() is not None

    async def status(self, user, *, level, lesson_order, completed=0, consume=False, bot=None):
        # Serialize starts across Mini App, bot, Android and desktop.
        if consume:
            await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
        access = CourseMiniAppAccessService(self.session)
        engine = EntitlementEngine(self.session)
        decision = await engine.check(user, A.LESSON_START)
        payload = decision.as_dict(language=getattr(user, "language", "ru"))
        reference = self.reference(level, lesson_order)
        if resolve_state(user) == EntitlementState.BLOCKED:
            return payload
        if (await CourseAccessPolicyService(self.session).get_policy()).free_active:
            return {**payload, "ok": True, "allowed": True, "policy_free": True,
                    "limit": None, "remaining": None, "window": "none", "reset_at": None}
        if lesson_order <= completed or await self._reserved(user, reference):
            return {**payload, "ok": True, "allowed": True, "idempotent": True}
        if consume:
            decision = await engine.consume(user, A.LESSON_START, ref=reference, notify_bot=bot)
            payload = decision.as_dict(language=getattr(user, "language", "ru"))
        return payload

    async def apply_map(self, data, user, *, level, completed):
        status = await self.status(user, level=level, lesson_order=completed + 1, completed=completed)
        data["lesson_limit"] = status
        for unit in data.get("units", []):
            for lesson in unit.get("lessons", []):
                n = int(lesson.get("n") or 0)
                done = n <= completed
                current = n == completed + 1
                for key in ("preview_half", "locked_premium", "ad_required", "ad_unlockable", "completion_error"):
                    lesson.pop(key, None)
                lesson["status"] = "done" if done else "current" if current and status["allowed"] else "locked"
                lesson["completion_allowed"] = done or (current and status["allowed"])
                if current and not status["allowed"]:
                    lesson["locked_premium"] = True
                    lesson["completion_error"] = status.get("error", "free_feature_limit_reached")
                elif not done and not current:
                    lesson["completion_error"] = "course_lesson_not_unlocked"
            if any(x.get("status") in {"done", "current"} for x in unit.get("lessons", [])):
                unit.pop("status", None)
            else:
                unit["status"] = "locked"
