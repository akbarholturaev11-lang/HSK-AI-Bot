from datetime import datetime, timezone


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
        if not user:
            return False
        if getattr(user, "status", "") != "active":
            return False
        if getattr(user, "payment_status", "") != "approved":
            return False
        end_date = self._as_utc(getattr(user, "end_date", None))
        return end_date is None or end_date > datetime.now(timezone.utc)

    def is_free_user(self, user) -> bool:
        return bool(user and not self.is_paid_user(user) and getattr(user, "status", "") != "blocked")

    async def ensure_trial_lesson(self, user, lesson_id: int) -> bool:
        if self.is_paid_user(user):
            return True
        if not self.is_free_user(user):
            return False

        current_lesson_id = getattr(user, "trial_course_lesson_id", None)
        if current_lesson_id is None:
            user.trial_course_lesson_id = lesson_id
            user.trial_course_started_at = datetime.now(timezone.utc)
            await self.session.flush()
            return True

        return int(current_lesson_id) == int(lesson_id)

    def can_access_lesson(self, user, lesson_id: int | None) -> bool:
        if self.is_paid_user(user):
            return True
        if not self.is_free_user(user) or not lesson_id:
            return False
        current_lesson_id = getattr(user, "trial_course_lesson_id", None)
        return bool(current_lesson_id and int(current_lesson_id) == int(lesson_id))

    async def mark_trial_completed(self, user, lesson_id: int | None) -> None:
        if not self.is_free_user(user) or not lesson_id:
            return
        current_lesson_id = getattr(user, "trial_course_lesson_id", None)
        if current_lesson_id and int(current_lesson_id) == int(lesson_id):
            if getattr(user, "trial_course_completed_at", None) is None:
                user.trial_course_completed_at = datetime.now(timezone.utc)
                await self.session.flush()

    async def mark_force_sub_required(self, user) -> None:
        if not self.is_free_user(user):
            return
        if getattr(user, "force_sub_required_at", None) is None:
            user.force_sub_required_at = datetime.now(timezone.utc)
            await self.session.flush()

    def should_start_force_sub_at_step(self, step: str) -> bool:
        return False
