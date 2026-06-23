from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User


COURSE_GOALS = {"hsk_exam", "study_china", "work_china", "daily_communication", "travel"}
COURSE_DAILY_MINUTES = {5, 10, 15, 20, 30}
COURSE_START_MODES = {"lesson_1", "continue", "placement"}


class CourseMiniAppProfileService:
    def __init__(self, session):
        self.session = session

    async def get_or_create(self, user_id: int) -> CourseMiniAppProfile:
        user_result = await self.session.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        )
        if user_result.scalar_one_or_none() is None:
            raise ValueError("Course Mini App user not found")

        result = await self.session.execute(
            select(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        profile = CourseMiniAppProfile(user_id=user_id)
        self.session.add(profile)
        await self.session.flush()
        return profile

    @staticmethod
    def validate_preferences(*, goal: str, daily_minutes: int, start_mode: str) -> tuple[str, int, str]:
        goal = str(goal or "").strip().lower()
        start_mode = str(start_mode or "").strip().lower()
        try:
            daily_minutes = int(daily_minutes)
        except (TypeError, ValueError) as error:
            raise ValueError("daily_minutes must be one of 10, 15, 20, 30") from error

        if goal not in COURSE_GOALS:
            raise ValueError("Unknown course goal")
        if daily_minutes not in COURSE_DAILY_MINUTES:
            raise ValueError("daily_minutes must be one of 10, 15, 20, 30")
        if start_mode not in COURSE_START_MODES:
            raise ValueError("Unknown course start mode")
        return goal, daily_minutes, start_mode

    async def save_preferences(
        self,
        profile: CourseMiniAppProfile,
        *,
        goal: str,
        daily_minutes: int,
        start_mode: str,
        timezone_offset_minutes: int = 0,
        complete_onboarding: bool = False,
    ) -> CourseMiniAppProfile:
        goal, daily_minutes, start_mode = self.validate_preferences(
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
        )
        timezone_offset_minutes = max(-720, min(840, int(timezone_offset_minutes or 0)))

        profile.goal = goal
        profile.daily_minutes = daily_minutes
        profile.start_mode = start_mode
        profile.timezone_offset_minutes = timezone_offset_minutes
        if complete_onboarding and profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return profile
