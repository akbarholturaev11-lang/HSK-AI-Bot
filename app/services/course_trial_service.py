from datetime import datetime, timezone

from app.services.user_access_state_service import UserAccessState, UserAccessStateService


class CourseTrialService:
    def __init__(self, session):
        self.session = session

    def _as_utc(self, value):
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def is_paid_user(self, user) -> bool:
        return UserAccessStateService.is_paid(user)

    def is_free_user(self, user) -> bool:
        return bool(
            user
            and not self.is_paid_user(user)
            and UserAccessStateService.classify(user) in UserAccessStateService.COURSE_ELIGIBLE_STATES
        )

    async def _lesson_access(self, user, lesson_id, *, consume):
        from app.repositories.course_lesson_repo import CourseLessonRepository
        from app.repositories.course_progress_repo import CourseProgressRepository
        from app.services.entitlements.lesson_access import LessonAccessService
        lesson = await CourseLessonRepository(self.session).get_by_id(lesson_id)
        if not lesson:
            return False
        progress = await CourseProgressRepository(self.session).get_by_user_id(user.id)
        completed = int(progress.completed_lessons_count or 0) if progress and progress.level == lesson.level else 0
        result = await LessonAccessService(self.session).status(
            user, level=lesson.level, lesson_order=lesson.lesson_order,
            completed=completed, consume=consume,
        )
        if result["allowed"] and consume:
            await self.mark_trial_lesson(user, lesson_id)
        return bool(result["allowed"])

    async def mark_trial_lesson(self, user, lesson_id) -> None:
        """Qaysi dars shu o'quvchining birinchisi ekanini eslab qoladi.

        Hech narsa SARFLAMAYDI. Chegara darsni haqiqatan boshlaganda yeyiladi,
        onboardingda emas: o'quvchi boshlash nuqtasini tanladi, xolos.
        """
        if lesson_id and not getattr(user, "trial_course_lesson_id", None):
            user.trial_course_lesson_id = lesson_id
            user.trial_course_started_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def ensure_trial_lesson(self, user, lesson_id: int) -> bool:
        return await self._lesson_access(user, lesson_id, consume=True)

    async def can_access_lesson(self, user, lesson_id: int | None) -> bool:
        return bool(lesson_id) and await self._lesson_access(user, lesson_id, consume=False)

    async def mark_trial_completed(self, user, lesson_id: int | None) -> None:
        if not self.is_free_user(user) or not lesson_id:
            return
        current_lesson_id = getattr(user, "trial_course_lesson_id", None)
        if current_lesson_id and int(current_lesson_id) == int(lesson_id):
            if getattr(user, "trial_course_completed_at", None) is None:
                user.trial_course_completed_at = datetime.now(timezone.utc)
                if UserAccessStateService.classify(user) == UserAccessState.TRIAL:
                    user.status = "free"
                await self.session.flush()

    async def mark_force_sub_required(self, user) -> None:
        if not self.is_free_user(user):
            return
        if getattr(user, "force_sub_required_at", None) is None:
            user.force_sub_required_at = datetime.now(timezone.utc)
            await self.session.flush()

    def should_start_force_sub_at_step(self, step: str) -> bool:
        return False
