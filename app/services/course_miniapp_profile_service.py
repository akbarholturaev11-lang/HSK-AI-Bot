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

# Onboardingdagi "nimaga ko'proq urg'u beraylik" javobi. Bu o'z-o'zini tashxis
# EMAS — reja qurishda boshlang'ich taxmin (prior) bo'lib, real natijalar
# to'plangach ta'siri so'nadi. "none" = "farqi yo'q", ya'ni prior umuman yo'q.
COURSE_PREFERRED_FOCUS = {"speaking", "listening", "vocabulary", "grammar", "none"}

# daily_minutes -> (kunlik reja task soni, kunlik XP maqsadi).
#
# XP miqdorlari mavjud koddan: dars qismi 20, xato takrori 5, skill drill 8,
# test/voice 10, kunning birinchi faoliyatiga +5 bonus.
#
# Reja — POL, maqsad — SHIFT: 1-2 tasklik rejalar maqsadni to'liq yopadi,
# 3-4 tasklikda maqsad biroz yuqori turadi (halqa avtomatik emas, intilishli).
# 30 daqiqa 4 task oladi, aks holda 20 daqiqadan farqlanmasdi.
COURSE_DAILY_TARGETS = {
    5: (1, 25),
    10: (2, 30),
    15: (2, 35),
    20: (3, 40),
    30: (4, 50),
}
_DEFAULT_DAILY_MINUTES = 10

# Foydalanuvchi maqsadni o'zi tanlaganda shu oraliqqa qisiladi.
DAILY_GOAL_XP_MIN = 10
DAILY_GOAL_XP_MAX = 500


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
    def normalize_preferred_focus(value) -> str | None:
        """Bo'sh/berilmagan qiymat -> None ("hali so'ralmagan"). Noma'lum -> xato.

        None va "none" farqi ataylab saqlanadi: birinchisi savol berilmaganini,
        ikkinchisi o'quvchi "farqi yo'q" deb javob berganini bildiradi. Reja
        uchun ikkalasi ham prior=0, lekin onboarding oqimi ularni ajratadi.
        """
        focus = str(value or "").strip().lower()
        if not focus:
            return None
        if focus not in COURSE_PREFERRED_FOCUS:
            raise ValueError("Unknown preferred focus")
        return focus

    @staticmethod
    def daily_plan_size(daily_minutes) -> int:
        """Kunlik rejadagi task soni. Noma'lum qiymat -> 10 daqiqalik default."""
        try:
            minutes = int(daily_minutes)
        except (TypeError, ValueError):
            minutes = _DEFAULT_DAILY_MINUTES
        size, _ = COURSE_DAILY_TARGETS.get(
            minutes, COURSE_DAILY_TARGETS[_DEFAULT_DAILY_MINUTES]
        )
        return size

    @classmethod
    def resolve_daily_goal_xp(cls, profile) -> int:
        """Kunlik XP maqsadi: foydalanuvchi tanlagani, bo'lmasa daqiqadan avto.

        Ilgari bu Mini App ichidagi oddiy JS o'zgaruvchi edi (`dailyGoal=50`) va
        hech qayerga saqlanmasdi — ilova qayta ochilganda tanlov yo'qolardi.
        """
        stored = getattr(profile, "daily_goal_xp", None)
        if stored:
            try:
                return cls.clamp_daily_goal_xp(stored)
            except (TypeError, ValueError):
                pass
        try:
            minutes = int(getattr(profile, "daily_minutes", None) or _DEFAULT_DAILY_MINUTES)
        except (TypeError, ValueError):
            minutes = _DEFAULT_DAILY_MINUTES
        _, goal_xp = COURSE_DAILY_TARGETS.get(
            minutes, COURSE_DAILY_TARGETS[_DEFAULT_DAILY_MINUTES]
        )
        return goal_xp

    @staticmethod
    def clamp_daily_goal_xp(value) -> int:
        goal_xp = int(value)
        return max(DAILY_GOAL_XP_MIN, min(DAILY_GOAL_XP_MAX, goal_xp))

    async def set_daily_goal_xp(self, profile: CourseMiniAppProfile, value) -> int:
        """None -> avto rejimga qaytarish; son -> qisilgan holda saqlash."""
        if value is None:
            profile.daily_goal_xp = None
        else:
            profile.daily_goal_xp = self.clamp_daily_goal_xp(value)
        await self.session.flush()
        return self.resolve_daily_goal_xp(profile)

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
        preferred_focus=None,
    ) -> CourseMiniAppProfile:
        goal, daily_minutes, start_mode = self.validate_preferences(
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
        )
        # Berilmagan bo'lsa mavjud qiymat saqlanadi — eski chaqiruvchilar
        # (bot onboarding oqimi) fokusni tasodifan tozalab yubormasin.
        focus = self.normalize_preferred_focus(preferred_focus)
        timezone_offset_minutes = max(-720, min(840, int(timezone_offset_minutes or 0)))

        profile.goal = goal
        profile.daily_minutes = daily_minutes
        profile.start_mode = start_mode
        profile.timezone_offset_minutes = timezone_offset_minutes
        if focus is not None:
            profile.preferred_focus = focus
        if complete_onboarding and profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return profile
