import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User


COURSE_GOALS = {"hsk_exam", "study_china", "work_china", "daily_communication", "travel"}
COURSE_DAILY_MINUTES = {5, 10, 15, 20, 30}
COURSE_START_MODES = {"lesson_1", "continue", "placement"}
COURSE_FOUNDATION_ID = "starter0_hsk1"
COURSE_FOUNDATION_VERSION = 1


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

    async def foundation_status(self, user) -> dict:
        """Return server-backed Starter 0 state without adding a new table."""
        learner_level = str(getattr(user, "level", "") or "").strip().lower()
        telegram_id = getattr(user, "telegram_id", None)
        completed = False
        if telegram_id:
            result = await self.session.execute(
                select(CourseMiniAppEvent.payload_json)
                .where(
                    CourseMiniAppEvent.telegram_id == int(telegram_id),
                    CourseMiniAppEvent.event_name == "foundation_completed",
                )
            )
            for raw_payload in result.scalars().all():
                try:
                    event_payload = json.loads(raw_payload or "{}")
                    event_foundation_id = str(
                        event_payload.get("foundation_id") or COURSE_FOUNDATION_ID
                    ).strip()
                    raw_version = event_payload.get("foundation_version")
                    event_version = (
                        COURSE_FOUNDATION_VERSION
                        if str(raw_version or "").strip().lower() == "starter-0-v1"
                        else int(raw_version or 0)
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if (
                    event_foundation_id == COURSE_FOUNDATION_ID
                    and event_version == COURSE_FOUNDATION_VERSION
                ):
                    completed = True
                    break

        required = learner_level == "beginner"
        return {
            "id": COURSE_FOUNDATION_ID,
            "version": COURSE_FOUNDATION_VERSION,
            "required": required,
            "completed": completed,
            "status": "completed" if completed else "required" if required else "optional",
        }

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
