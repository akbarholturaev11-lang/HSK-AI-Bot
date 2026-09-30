from app.repositories.user_repo import UserRepository
from app.services.course_engine_service import CourseEngineService
from app.services.course_levels import (
    TRACK_HSK30,
    content_level as registry_content_level,
    is_hsk30_level,
    onboarding_levels,
    render_level as registry_render_level,
)
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_track_service import CourseTrackService
from app.services.course_trial_service import CourseTrialService
from app.services.hsk30_feature_service import Hsk30FeatureService
from app.services.hsk30_manifest_service import Hsk30ManifestService


# Keep the old public constant exactly legacy-only. HSK 3.0 choices are added
# dynamically only while the server-owned feature flag is enabled.
COURSE_ONBOARDING_LEVELS = set(onboarding_levels())


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

    async def _normalize_request_level(self, level: str) -> str:
        normalized = str(level or "").strip().lower()
        enabled = await Hsk30FeatureService(self.session).is_enabled()
        if normalized not in onboarding_levels(hsk30_enabled=enabled):
            raise ValueError("Unknown course level")
        return normalized

    @staticmethod
    def content_level(level: str) -> str:
        return registry_content_level(level)

    @staticmethod
    def render_level(level: str, lesson_order: int | None = None) -> str:
        return registry_render_level(level, lesson_order)

    @staticmethod
    def requires_foundation(
        *,
        level: str,
        start_mode: str,
        onboarding_completed: bool,
        review_only: bool,
    ) -> bool:
        """Starter 0 remains the legacy beginner prerequisite only."""
        return bool(
            level == "beginner"
            and start_mode == "lesson_1"
            and not onboarding_completed
            and not review_only
        )

    async def _complete_hsk30(
        self,
        *,
        user,
        profile,
        requested_level: str,
        goal: str,
        daily_minutes: int,
        start_mode: str,
        language: str | None,
        timezone_offset_minutes: int,
        activation_variant: str,
        onboarding_was_completed: bool,
    ) -> dict:
        requested_content_level = self.content_level(requested_level)
        requested_manifest = Hsk30ManifestService.load(requested_content_level)
        if not requested_manifest:
            return {"ok": False, "error": "course_no_lessons_available"}

        track_service = CourseTrackService(self.session)
        access = await track_service.hsk30_access(user)
        if not access.allowed:
            return {"ok": False, "error": access.reason}
        if not await track_service.hsk30_feature.is_level_live(requested_content_level):
            return {"ok": False, "error": "hsk30_level_not_live"}

        current_track = track_service.track_for_level(getattr(user, "level", None))
        if current_track != TRACK_HSK30:
            await track_service.switch(
                user,
                target_track=TRACK_HSK30,
                requested_level=requested_level,
            )

        progress = await self.engine.progress_repo.get_by_user_id(
            user.id,
            for_update=True,
        )
        if not progress:
            progress = await self.engine.progress_repo.create(
                user_id=user.id,
                level=self.content_level(getattr(user, "level", None) or requested_level),
                current_lesson_id=None,
                current_step="intro",
                waiting_for="none",
            )

        active_level = str(getattr(user, "level", "") or requested_level).lower()
        if not is_hsk30_level(active_level):
            active_level = requested_level
            user.level = active_level
        active_content_level = self.content_level(active_level)
        manifest = Hsk30ManifestService.load(active_content_level)
        if not manifest:
            return {"ok": False, "error": "course_no_lessons_available"}

        launch_tab = "course"
        review_only = False
        if start_mode == "placement":
            launch_tab = "tests"
            launch_lesson = None
        elif start_mode == "continue":
            completed = max(0, int(progress.completed_lessons_count or 0))
            launch_lesson = min(
                manifest.lesson_count,
                max(manifest.first_lesson_order, completed + 1),
            )
        else:
            launch_lesson = manifest.first_lesson_order
            # A first-start selection inside the HSK 3.0 track resets only the
            # active HSK 3.0 progress. The HSK 2.0 snapshot is already stored
            # by CourseTrackService and is not touched.
            if active_level != requested_level:
                user.level = requested_level
                active_level = requested_level
                active_content_level = self.content_level(active_level)
                manifest = Hsk30ManifestService.load(active_content_level)
                if not manifest:
                    return {"ok": False, "error": "course_no_lessons_available"}
                launch_lesson = manifest.first_lesson_order
                progress.completed_lessons_count = 0
            progress.level = active_content_level
            progress.current_lesson_id = None
            progress.current_step = "intro"
            progress.waiting_for = "none"
            progress.homework_status = "none"
            progress.needs_review_prompt = False

        await self.profile_service.save_preferences(
            profile,
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
            timezone_offset_minutes=timezone_offset_minutes,
            complete_onboarding=True,
            goal_explicit=True,
        )
        await self.session.commit()

        launch_level = self.render_level(active_content_level, launch_lesson)
        analytics = CourseMiniAppAnalyticsService(self.session)
        event_payloads = (
            ("level_selected", {"level": requested_level}, f"onboarding:level:{requested_level}"),
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
                    "level": requested_level,
                    "goal": goal,
                    "daily_minutes": daily_minutes,
                    "daily_time": daily_minutes,
                    "start_mode": start_mode,
                    "start_point": start_mode,
                    "language": str(language or "").strip().lower()[:8] or None,
                    "activation_variant": activation_variant,
                    "track": TRACK_HSK30,
                },
                f"onboarding:{profile.id}:completed",
            ),
        )
        for event_name, payload, dedupe_key in event_payloads:
            await analytics.record_server_event(
                event_name=event_name,
                telegram_id=user.telegram_id,
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
            "track": TRACK_HSK30,
            "level": launch_level,
            "lesson": launch_lesson,
            "tab": launch_tab,
            "placement": start_mode == "placement",
            "review_only": review_only,
            "foundation_required": False,
        }

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
        activation_variant: str | None = None,
    ) -> dict:
        level = await self._normalize_request_level(level)
        goal, daily_minutes, start_mode = self.profile_service.validate_preferences(
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
        )
        activation_variant = str(activation_variant or "legacy_or_standard").strip()[:32]

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        profile = await self.profile_service.get_or_create(user.id)
        onboarding_was_completed = profile.onboarding_completed_at is not None

        if is_hsk30_level(level):
            return await self._complete_hsk30(
                user=user,
                profile=profile,
                requested_level=level,
                goal=goal,
                daily_minutes=daily_minutes,
                start_mode=start_mode,
                language=language,
                timezone_offset_minutes=timezone_offset_minutes,
                activation_variant=activation_variant,
                onboarding_was_completed=onboarding_was_completed,
            )

        # Legacy HSK 2.0 path below is intentionally unchanged in behavior.
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
                if level == "beginner" and not onboarding_was_completed and not review_only:
                    user.level = level
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
                await CourseTrialService(self.session).mark_trial_lesson(user, first_lesson.id)

        if current_lesson and start_mode == "continue":
            await CourseTrialService(self.session).mark_trial_lesson(user, current_lesson.id)

        await self.profile_service.save_preferences(
            profile,
            goal=goal,
            daily_minutes=daily_minutes,
            start_mode=start_mode,
            timezone_offset_minutes=timezone_offset_minutes,
            complete_onboarding=True,
            goal_explicit=True,
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
                    "activation_variant": activation_variant,
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
            "foundation_required": self.requires_foundation(
                level=level,
                start_mode=start_mode,
                onboarding_completed=onboarding_was_completed,
                review_only=review_only,
            ),
        }
