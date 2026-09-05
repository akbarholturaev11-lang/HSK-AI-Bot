"""Course v3 adapter for the native Android client.

Android shares every course rule with the desktop client: the same access
policy, the same XP and streak awards, the same mistake persistence and the
same idempotent completion. Nothing is reimplemented here.

The only difference is the analytics and dedupe namespace, so that an Android
completion can never collide with a desktop one and Android never appears in
the desktop funnel.
"""

from __future__ import annotations

from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_onboarding_service import CourseMiniAppOnboardingService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.desktop_course_service import (
    DesktopCourseError,
    DesktopCourseService,
)


__all__ = ["AndroidCourseError", "AndroidCourseService"]

# The error contract is shared on purpose: one stable set of codes for every
# native client means the clients can share their error-to-copy mapping.
AndroidCourseError = DesktopCourseError


class AndroidCourseService(DesktopCourseService):
    CLIENT_NAMESPACE = "android"

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
        result["foundation"] = await CourseMiniAppProfileService(
            self.session
        ).foundation_status(context.user)
        await self.session.commit()
        return result

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

        # Goal/time/focus all affect today's plan. Rebuild on the next map fetch
        # so Android and Mini App cannot show stale task identities after a choice.
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
