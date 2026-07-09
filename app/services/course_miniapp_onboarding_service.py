from app.repositories.user_repo import UserRepository
from app.services.course_engine_service import CourseEngineService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_trial_service import CourseTrialService


COURSE_ONBOARDING_LEVELS = {"beginner", "hsk1", "hsk2", "hsk3", "hsk4"}


class CourseMiniAppOnboardingService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.engine = CourseEngineService(session)
        self.profile_service = CourseMiniAppProfileService(session)

    @staticmethod
    def normalize_level(level: str) -> str:
        normalized = str(level or "").strip().lower()
        if normalized not in COURSE_ONBOARDING_LEVELS:
            raise ValueError("Unknown course level")
        return normalized

    @staticmethod
    def content_level(level: str) -> str:
        return "hsk1" if level == "beginner" else level

    @staticmethod
    def render_level(level: str, lesson_order: int | None = None) -> str:
        if level == "hsk4":
            return "hsk4b" if int(lesson_order or 0) > 10 else "hsk4a"
        return "hsk1" if level == "beginner" else level

    async def complete(
        self,
        telegram_id: int,
        *,
        level: str,
        goal: str,
        daily_minutes: int,
        start_mode: str,
        language: str | None = None,
        timezone_offset_minutes: int = 0,
    ) -> dict:
        level = self.normalize_level(level)
        goal, daily_minutes, start_mode = self.profile_service.validate_preferences(
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
        )

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        profile = await self.profile_service.get_or_create(user.id)
        progress = await self.engine.progress_repo.get_by_user_id(user.id, for_update=True)
        current_lesson = None
        if progress and progress.current_lesson_id:
            current_lesson = await self.engine.lesson_repo.get_by_id(progress.current_lesson_id)

        selected_content_level = self.content_level(level)
        existing_content_level = str(getattr(current_lesson, "level", "") or "").lower()
        if (
            current_lesson
            and start_mode == "lesson_1"
            and existing_content_level != selected_content_level
        ):
            return {"ok": False, "error": "course_level_change_requires_placement"}

        user.learning_mode = "course"
        user.voice_mode = "none"
        launch_lesson = None
        launch_tab = "course"
        review_only = False

        if start_mode == "continue" and current_lesson:
            launch_lesson = int(current_lesson.lesson_order)
            launch_level = self.render_level(existing_content_level, launch_lesson)
        elif start_mode == "placement":
            launch_tab = "tests"
            launch_level = self.render_level(
                existing_content_level or selected_content_level,
                getattr(current_lesson, "lesson_order", None),
            )
            if not current_lesson:
                user.level = level
        else:
            launch_level = self.render_level(selected_content_level, 1)
            first_lesson = await self.engine.lesson_repo.get_first_by_level(selected_content_level)
            if not first_lesson:
                return {"ok": False, "error": "course_no_lessons_available"}

            launch_lesson = int(first_lesson.lesson_order)
            if current_lesson:
                review_only = int(current_lesson.id) != int(first_lesson.id)
            else:
                user.level = level
                if not progress:
                    progress = await self.engine.progress_repo.create(
                        user_id=user.id,
                        level=level,
                        current_lesson_id=None,
                        current_step="intro",
                        waiting_for="none",
                    )
                progress.level = level
                await self.engine.progress_repo.set_current_lesson_and_step(
                    progress=progress,
                    lesson_id=first_lesson.id,
                    step="intro",
                    waiting_for="none",
                )
                current_lesson = first_lesson
                await CourseTrialService(self.session).ensure_trial_lesson(user, first_lesson.id)

        if current_lesson and start_mode == "continue":
            await CourseTrialService(self.session).ensure_trial_lesson(user, current_lesson.id)

        await self.profile_service.save_preferences(
            profile,
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
            timezone_offset_minutes=timezone_offset_minutes,
            complete_onboarding=True,
        )
        await self.session.commit()

        analytics = CourseMiniAppAnalyticsService(self.session)
        event_payloads = (
            ("level_selected", {"level": level}, f"onboarding:level:{level}"),
            ("goal_selected", {"goal": goal}, f"onboarding:goal:{goal}"),
            (
                "daily_time_selected",
                {"daily_minutes": daily_minutes},
                f"onboarding:minutes:{daily_minutes}",
            ),
            (
                "start_point_selected",
                {"start_mode": start_mode},
                f"onboarding:startMode:{start_mode}",
            ),
            (
                "onboarding_completed",
                {
                    "level": level,
                    "goal": goal,
                    "daily_minutes": daily_minutes,
                    "daily_time": daily_minutes,
                    "start_mode": start_mode,
                    "start_point": start_mode,
                    "language": str(language or "").strip().lower()[:8] or None,
                },
                f"onboarding:{profile.id}:completed",
            ),
        )
        for event_name, payload, dedupe_key in event_payloads:
            await analytics.record_server_event(
                event_name=event_name,
                telegram_id=telegram_id,
                user_id=user.id,
                source="course_onboarding",
                level=launch_level,
                lesson_order=launch_lesson,
                dedupe_key=dedupe_key,
                payload=payload,
            )
        await self.session.commit()

        return {
            "ok": True,
            "profile": {
                "goal": profile.goal,
                "daily_minutes": profile.daily_minutes,
                "start_mode": profile.start_mode,
                "timezone_offset_minutes": profile.timezone_offset_minutes,
                "onboarding_completed": profile.onboarding_completed_at is not None,
            },
            "level": launch_level,
            "lesson": launch_lesson,
            "tab": launch_tab,
            "placement": start_mode == "placement",
            "review_only": review_only,
        }
