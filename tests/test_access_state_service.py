import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.access_service import AccessService
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.course_trial_service import CourseTrialService
from app.services.user_access_state_service import UserAccessState, UserAccessStateService


class _Session:
    def __init__(self):
        self.flush_count = 0
        self.commit_count = 0

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1


class _UserRepo:
    def __init__(self, user):
        self.user = user
        self.daily_offer_marked = False

    async def get_by_telegram_id(self, _telegram_id):
        return self.user

    def get_bonus_balance(self, user):
        return max((getattr(user, "bonus_questions", 0) or 0) - (getattr(user, "bonus_questions_used", 0) or 0), 0)

    async def was_daily_limit_offer_sent_today(self, _user):
        return False

    async def mark_daily_limit_offer_sent(self, _user):
        self.daily_offer_marked = True


class _PaymentRepo:
    def __init__(self, pending=False):
        self.pending = pending

    async def has_pending_by_user(self, _telegram_id):
        return self.pending


class UserAccessStateServiceTests(unittest.TestCase):
    def _user(self, **overrides):
        values = {
            "status": "trial",
            "payment_status": "none",
            "end_date": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_paid_requires_active_status_approved_payment_and_future_end_date(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        expired = datetime.now(timezone.utc) - timedelta(seconds=1)

        self.assertEqual(
            UserAccessStateService.classify(self._user(status="active", payment_status="approved", end_date=future)),
            UserAccessState.PAID,
        )
        self.assertEqual(
            UserAccessStateService.classify(self._user(status="active", payment_status="approved", end_date=expired)),
            UserAccessState.EXPIRED,
        )
        self.assertEqual(
            UserAccessStateService.classify(self._user(status="active", payment_status="approved", end_date=None)),
            UserAccessState.EXPIRED,
        )

    def test_active_non_paid_with_future_end_date_is_temporary_trial(self):
        user = self._user(
            status="active",
            payment_status="none",
            end_date=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        self.assertEqual(UserAccessStateService.classify(user), UserAccessState.TEMPORARY_TRIAL)


class AccessServiceFreeTierTests(unittest.IsolatedAsyncioTestCase):
    def _service(self, user, *, pending=False):
        session = _Session()
        service = AccessService(session)
        service.user_repo = _UserRepo(user)
        service.payment_repo = _PaymentRepo(pending)
        return service, session

    def _user(self, **overrides):
        values = {
            "telegram_id": 123,
            "status": "free",
            "payment_status": "none",
            "end_date": None,
            "learning_mode": "qa",
            "voice_mode": "none",
            "question_limit": 5,
            "questions_used": 0,
            "bonus_questions": 0,
            "bonus_questions_used": 0,
            "last_limit_reset_at": datetime.now(timezone.utc),
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    async def test_free_user_can_use_text_ai_instead_of_start_first(self):
        service, _ = self._service(self._user())
        self.assertEqual(await service.can_use_text_ai(123), (True, ""))

    async def test_free_user_daily_limit_is_enforced(self):
        user = self._user(questions_used=5)
        service, _ = self._service(user)
        self.assertEqual(await service.can_use_text_ai(123), (False, "access_daily_limit_reached"))
        self.assertTrue(service.user_repo.daily_offer_marked)

    async def test_expired_paid_user_becomes_expired_not_trial_and_gets_free_tier(self):
        user = self._user(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        service, _ = self._service(user)
        self.assertEqual(await service.can_use_text_ai(123), (True, ""))
        self.assertEqual(user.status, "expired")


class CourseTrialLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_trial_lesson_moves_trial_user_to_free(self):
        session = _Session()
        user = SimpleNamespace(
            status="trial",
            payment_status="none",
            end_date=None,
            trial_course_lesson_id=44,
            trial_course_completed_at=None,
        )
        await CourseTrialService(session).mark_trial_completed(user, 44)
        self.assertEqual(user.status, "free")
        self.assertIsNotNone(user.trial_course_completed_at)


class BotBlockStatusServiceTests(unittest.TestCase):
    def test_bot_blocked_is_separate_from_admin_block_status(self):
        now = datetime.now(timezone.utc)
        user = SimpleNamespace(status="active", bot_blocked_at=now, bot_unblocked_at=None)
        self.assertTrue(BotBlockStatusService.is_bot_blocked(user))
        self.assertEqual(user.status, "active")

        user.bot_unblocked_at = now + timedelta(seconds=1)
        self.assertFalse(BotBlockStatusService.is_bot_blocked(user))
