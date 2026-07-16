import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.subscription_service import (
    MANUAL_SUBSCRIPTION_MAX_DAYS,
    SubscriptionService,
    normalize_manual_subscription_days,
)


class _Session:
    def __init__(self):
        self.flush_count = 0

    async def flush(self):
        self.flush_count += 1


class _UserRepo:
    def __init__(self, user):
        self.user = user
        self.locked_lookups = 0

    async def get_by_telegram_id(self, _telegram_id):
        return self.user

    async def get_by_telegram_id_for_update(self, _telegram_id):
        self.locked_lookups += 1
        return self.user


class ManualSubscriptionDurationTests(unittest.TestCase):
    def test_duration_normalizer_accepts_integer_days_in_bounds(self):
        self.assertEqual(normalize_manual_subscription_days(1), 1)
        self.assertEqual(normalize_manual_subscription_days(" 45 "), 45)
        self.assertEqual(normalize_manual_subscription_days(MANUAL_SUBSCRIPTION_MAX_DAYS), 36_500)

    def test_duration_normalizer_rejects_invalid_values(self):
        for value in (
            None,
            True,
            0,
            -1,
            1.5,
            "1.5",
            "-2",
            "",
            "²",
            "9" * 5_000,
            MANUAL_SUBSCRIPTION_MAX_DAYS + 1,
        ):
            with self.subTest(value=value):
                self.assertIsNone(normalize_manual_subscription_days(value))


class SubscriptionServiceManualGrantTests(unittest.IsolatedAsyncioTestCase):
    def _user(self, **overrides):
        values = {
            "telegram_id": 123,
            "status": "free",
            "payment_status": "none",
            "start_date": None,
            "end_date": None,
            "selected_plan_type": "1_month",
            "expiry_reminder_sent_at": datetime.now(timezone.utc),
            "subscription_expired_offer_sent_at": datetime.now(timezone.utc),
            "subscription_churn_followup_sent_at": datetime.now(timezone.utc),
            "subscription_churn_responded_at": datetime.now(timezone.utc),
            "subscription_churn_reason": "price",
            "discount_eligible": False,
            "discount_used": False,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def _service(self, user):
        session = _Session()
        service = SubscriptionService(session)
        repo = _UserRepo(user)
        service.user_repo = repo
        return service, session, repo

    async def test_custom_duration_makes_free_user_paid_active_from_now(self):
        user = self._user()
        service, session, repo = self._service(user)

        grant = await service.grant_manual_paid_access(123, 45)

        self.assertIsNotNone(grant)
        granted_user, extended = grant
        self.assertIs(granted_user, user)
        self.assertFalse(extended)
        self.assertEqual(user.status, "active")
        self.assertEqual(user.payment_status, "approved")
        self.assertEqual(user.end_date - user.start_date, timedelta(days=45))
        self.assertIsNone(user.selected_plan_type)
        self.assertIsNone(user.expiry_reminder_sent_at)
        self.assertIsNone(user.subscription_expired_offer_sent_at)
        self.assertIsNone(user.subscription_churn_followup_sent_at)
        self.assertIsNone(user.subscription_churn_responded_at)
        self.assertIsNone(user.subscription_churn_reason)
        self.assertEqual(repo.locked_lookups, 1)
        self.assertGreaterEqual(session.flush_count, 2)

    async def test_custom_duration_extends_existing_paid_expiry(self):
        original_start = datetime.now(timezone.utc) - timedelta(days=20)
        original_end = datetime.now(timezone.utc) + timedelta(days=5)
        user = self._user(
            status="active",
            payment_status="approved",
            start_date=original_start,
            end_date=original_end,
        )
        service, _, _ = self._service(user)

        _, extended = await service.grant_manual_paid_access(123, "17")

        self.assertTrue(extended)
        self.assertEqual(user.start_date, original_start)
        self.assertEqual(user.end_date, original_end + timedelta(days=17))

    async def test_blocked_user_with_remaining_paid_time_is_unblocked_without_losing_days(self):
        original_end = datetime.now(timezone.utc) + timedelta(days=12)
        user = self._user(
            status="blocked",
            payment_status="approved",
            start_date=datetime.now(timezone.utc) - timedelta(days=3),
            end_date=original_end,
        )
        service, _, _ = self._service(user)

        _, extended = await service.grant_manual_paid_access(123, 8)

        self.assertTrue(extended)
        self.assertEqual(user.status, "active")
        self.assertEqual(user.end_date, original_end + timedelta(days=8))

    async def test_future_non_paid_trial_is_replaced_by_exact_paid_duration(self):
        user = self._user(
            status="active",
            payment_status="none",
            start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            end_date=datetime.now(timezone.utc) + timedelta(days=3),
        )
        service, _, _ = self._service(user)

        _, extended = await service.grant_manual_paid_access(123, 7)

        self.assertFalse(extended)
        self.assertEqual(user.end_date - user.start_date, timedelta(days=7))

    async def test_invalid_duration_or_missing_user_is_not_granted(self):
        user = self._user()
        service, _, repo = self._service(user)

        self.assertIsNone(await service.grant_manual_paid_access(123, 0))
        self.assertEqual(repo.locked_lookups, 0)

        service.user_repo = _UserRepo(None)
        self.assertIsNone(await service.grant_manual_paid_access(999, 30))

    async def test_fixed_payment_plan_activation_keeps_existing_reset_semantics(self):
        user = self._user(
            status="active",
            payment_status="approved",
            start_date=datetime.now(timezone.utc) - timedelta(days=2),
            end_date=datetime.now(timezone.utc) + timedelta(days=50),
        )
        service, _, _ = self._service(user)

        self.assertTrue(await service.activate_plan(123, "10_days"))
        self.assertEqual(user.end_date - user.start_date, timedelta(days=10))


if __name__ == "__main__":
    unittest.main()
