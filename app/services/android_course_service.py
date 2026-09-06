"""Course v3 adapter for the native Android client.

Android shares every course rule with the desktop client: the same access
policy, the same XP and streak awards, the same mistake persistence and the
same idempotent completion. Nothing is reimplemented here.

The only difference is the analytics and dedupe namespace, so that an Android
completion can never collide with a desktop one and Android never appears in
the desktop funnel.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_onboarding_service import CourseMiniAppOnboardingService
from app.services.course_miniapp_profile_service import (
    COURSE_FOUNDATION_ID,
    COURSE_FOUNDATION_VERSION,
    CourseMiniAppProfileService,
)
from app.services.desktop_course_service import (
    DesktopCourseError,
    DesktopCourseService,
)


__all__ = ["AndroidCourseError", "AndroidCourseService"]

AndroidCourseError = DesktopCourseError

_FOUNDATION_SOURCE = Path("app/static/course_v3_data/hsk1/lesson_01.json")
_FOUNDATION_REQUIRED_ERROR = "android_foundation_required"


class AndroidCourseService(DesktopCourseService):
    CLIENT_NAMESPACE = "android"

    async def _foundation_status(self, user) -> dict:
        return await CourseMiniAppProfileService(self.session).foundation_status(user)

    async def _require_foundation_complete(self, access_token: str) -> None:
        context = await self._context(access_token)
        status = await self._foundation_status(context.user)
        if bool(status.get("required")) and not bool(status.get("completed")):
            raise DesktopCourseError(_FOUNDATION_REQUIRED_ERROR, status_code=403)

    async def course_map(
        self,
        access_token: str,
        *,
        timezone_offset_minutes: int | None = None,
    ) -> dict:
        """Return Course v3 plus the same server-owned Starter 0 state as Mini App."""
        result = await super().course_map(
            access_token,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        context = await self._context(access_token)
        foundation = await self._foundation_status(context.user)
        result["foundation"] = foundation

        # Required Starter 0 is a real prerequisite, not merely a visual card.
        # Keep completed history visible, but make every unfinished path node
        # unreachable until the server records the shared foundation event.
        if bool(foundation.get("required")) and not bool(foundation.get("completed")):
            for unit in result.get("units", []):
                if not isinstance(unit, dict):
                    continue
                for lesson in unit.get("lessons", []):
                    if not isinstance(lesson, dict) or lesson.get("status") == "done":
                        continue
                    lesson["status"] = "locked"
                    lesson["completion_allowed"] = False
                    lesson["completion_error"] = _FOUNDATION_REQUIRED_ERROR
                    lesson.pop("preview_half", None)
                    lesson.pop("locked_premium", None)
        await self.session.commit()
        return result

    async def lesson(
        self,
        access_token: str,
        *,
        lesson_order: int,
    ) -> dict[str, Any]:
        await self._require_foundation_complete(access_token)
        return await super().lesson(access_token, lesson_order=lesson_order)

    async def complete(
        self,
        access_token: str,
        *,
        lesson_order: int,
        event_id: str,
        mistakes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        await self._require_foundation_complete(access_token)
        return await super().complete(
            access_token,
            lesson_order=lesson_order,
            event_id=event_id,
            mistakes=mistakes,
        )

    async def foundation(self, access_token: str) -> dict:
        """Return the checked-in Starter 0 payload used by the Mini App."""
        context = await self._context(access_token)
        try:
            lesson = json.loads(_FOUNDATION_SOURCE.read_text(encoding="utf-8"))
            foundation = lesson.get("foundation")
        except (OSError, json.JSONDecodeError) as exc:
            raise DesktopCourseError(
                "android_foundation_unavailable",
                status_code=503,
            ) from exc
        if not isinstance(foundation, dict) or not isinstance(foundation.get("cards"), list):
            raise DesktopCourseError("android_foundation_unavailable", status_code=503)
        if (
            str(foundation.get("id") or "") != COURSE_FOUNDATION_ID
            or int(foundation.get("version") or 0) != COURSE_FOUNDATION_VERSION
        ):
            raise DesktopCourseError("android_foundation_unavailable", status_code=503)

        status = await self._foundation_status(context.user)
        return {
            "ok": True,
            "foundation": foundation,
            "status": status,
        }

    async def complete_foundation(
        self,
        access_token: str,
        *,
        foundation_id: str,
        foundation_version: int,
        speaking_bonus: bool,
        event_id: str,
    ) -> dict:
        """Persist Starter 0 completion through the Mini App event contract."""
        if (
            str(foundation_id or "").strip() != COURSE_FOUNDATION_ID
            or int(foundation_version or 0) != COURSE_FOUNDATION_VERSION
        ):
            raise DesktopCourseError("android_foundation_invalid", status_code=409)
        dedupe_key = str(event_id or "").strip()[:120]
        if not dedupe_key:
            raise DesktopCourseError("android_request_invalid", status_code=422)

        context = await self._context(access_token)
        analytics = CourseMiniAppAnalyticsService(self.session)
        result = await analytics.record_server_event(
            event_name="foundation_completed",
            telegram_id=int(context.user.telegram_id),
            user_id=getattr(context.user, "id", None),
            source="android_course",
            level="hsk1",
            dedupe_key=dedupe_key,
            payload={
                "foundation_id": COURSE_FOUNDATION_ID,
                "foundation_version": COURSE_FOUNDATION_VERSION,
                "speaking_bonus": bool(speaking_bonus),
            },
        )
        if not result.get("ok"):
            raise DesktopCourseError("android_foundation_save_failed", status_code=503)
        await self.session.commit()
        return {
            "ok": True,
            "duplicate": bool(result.get("duplicate")),
            "foundation": await self._foundation_status(context.user),
        }

    async def onboarding_status(self, access_token: str) -> dict:
        """Return the canonical onboarding state for the authenticated learner."""
        context = await self._context(access_token)
        profile = await CourseMiniAppProfileService(self.session).get_or_create(
            context.user.id
        )
        await self.session.commit()
        return {
            "ok": True,
            "completed": profile.onboarding_completed_at is not None,
            "level": str(getattr(context.user, "level", "") or ""),
            "profile": {
                "goal": profile.goal,
                "daily_minutes": profile.daily_minutes,
                "start_mode": profile.start_mode,
                "timezone_offset_minutes": profile.timezone_offset_minutes,
            },
        }

    async def complete_onboarding(
        self,
        access_token: str,
        *,
        level: str,
        goal: str,
        daily_minutes: int,
        start_mode: str,
        language: str | None = None,
        timezone_offset_minutes: int = 0,
        activation_variant: str | None = None,
    ) -> dict:
        """Complete onboarding through the exact service used by the Mini App."""
        context = await self._context(access_token)
        return await CourseMiniAppOnboardingService(self.session).complete(
            int(context.user.telegram_id),
            level=level,
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
            language=language,
            timezone_offset_minutes=timezone_offset_minutes,
            activation_variant=activation_variant,
        )

    async def set_study_preferences(
        self,
        access_token: str,
        *,
        goal: str | None = None,
        daily_minutes: int | None = None,
        preferred_focus: str | None = None,
    ) -> dict:
        """Persist the same progressive-personalization answers as Mini App."""
        if goal is None and daily_minutes is None and preferred_focus is None:
            raise DesktopCourseError("android_request_invalid", status_code=422)

        context = await self._context(access_token)
        progress = await self._progress(context.user, for_update=True)
        service = CourseMiniAppProfileService(self.session)
        profile = await service.get_or_create(context.user.id)

        next_goal = str(goal or profile.goal)
        next_minutes = int(daily_minutes if daily_minutes is not None else profile.daily_minutes)
        try:
            await service.save_preferences(
                profile,
                goal=next_goal,
                daily_minutes=next_minutes,
                start_mode=profile.start_mode,
                timezone_offset_minutes=profile.timezone_offset_minutes,
                preferred_focus=preferred_focus,
                goal_explicit=goal is not None,
            )
        except (TypeError, ValueError) as exc:
            raise DesktopCourseError("android_request_invalid", status_code=422) from exc

        profile.daily_plan_key = None
        profile.daily_plan_json = None
        await self.session.commit()
        return {
            "ok": True,
            "study_setup": service.study_setup(
                profile,
                completed_parts=int(progress.completed_lessons_count or 0),
            ),
        }

    async def open_reward_chest(self, access_token: str) -> dict:
        """Open the exact same server-owned chest the Mini App opens."""
        context = await self._context(access_token)
        user = await self._locked_context_user(context)
        result = await CourseGamificationService(self.session).open_reward_chest(user)
        await self.session.commit()
        return result
