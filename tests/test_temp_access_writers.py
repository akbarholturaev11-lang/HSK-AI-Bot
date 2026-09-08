"""Kim `users` qatoriga vaqtinchalik yoki doimiy kirish yozadi.

`SubscriptionService.activate_plan` yagona PULLIK yo'l bo'lsa-da, `status` va
`end_date` ga yozadigan yana uchta joy bor. Ular obuna emas, lekin
`UserAccessStateService.classify()` javobini o'zgartiradi:

* `admin_access.ensure_admin_active` — `status` VA `payment_status` ni qo'yadi
  → `PAID`;
* `bot_feedback_service.grant_feedback_reward` — faqat `status` ni qo'yadi
  → `TEMPORARY_TRIAL` (30 daqiqa);
* `release_feedback_service` "Sinab ko'rish" — xuddi shunday.

Markaziy entitlement dvigateli qurilayotganda bu farq yo'qolib ketmasligi
kerak: TEMP_ACCESS pullik emas, lekin kontentni ochadi. Shu fayl o'sha
chegarani qotiradi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import admin_access
from app.services.admin_access import ADMIN_ACTIVE_UNTIL, ensure_admin_active
from app.services.bot_feedback_service import (
    FEEDBACK_REWARD_DURATION,
    BotFeedbackService,
)
from app.services.user_access_state_service import (
    UserAccessState,
    UserAccessStateService,
)


def _free_user(telegram_id: int = 900) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        telegram_id=telegram_id,
        status="free",
        payment_status="none",
        start_date=None,
        end_date=None,
        questions_used=4,
        last_limit_reset_at=None,
        expiry_reminder_sent_at=datetime.now(timezone.utc),
        selected_plan_type="1_month",
        pending_checkout_msg_id=42,
    )


class AdminAccessWriterTests(unittest.IsolatedAsyncioTestCase):
    async def test_an_admin_is_pushed_to_paid_until_2099(self):
        user = _free_user(telegram_id=777)
        session = SimpleNamespace(flush=AsyncMock())

        with patch.object(admin_access, "is_admin_user", lambda _tid: True):
            changed = await ensure_admin_active(session, user)

        self.assertTrue(changed)
        self.assertEqual("active", user.status)
        self.assertEqual("approved", user.payment_status)
        self.assertEqual(ADMIN_ACTIVE_UNTIL, user.end_date)
        # Admin PULLIK deb ko'rinadi — vaqtinchalik kirish emas.
        self.assertEqual(UserAccessState.PAID, UserAccessStateService.classify(user))

    async def test_a_normal_user_is_left_untouched(self):
        user = _free_user()
        session = SimpleNamespace(flush=AsyncMock())

        with patch.object(admin_access, "is_admin_user", lambda _tid: False):
            changed = await ensure_admin_active(session, user)

        self.assertFalse(changed)
        self.assertEqual("free", user.status)
        self.assertEqual("none", user.payment_status)
        session.flush.assert_not_awaited()


class FeedbackRewardWriterTests(unittest.IsolatedAsyncioTestCase):
    def _service(self):
        service = BotFeedbackService(SimpleNamespace(flush=AsyncMock()))
        service.feedback_repo = SimpleNamespace(mark_reward_granted=AsyncMock())
        return service

    async def test_the_reward_grants_temporary_access_not_a_subscription(self):
        user = _free_user()
        feedback = SimpleNamespace(reward_granted_at=None)
        before = datetime.now(timezone.utc)

        await self._service().grant_feedback_reward(user=user, feedback=feedback)

        # `status` qo'yiladi, `payment_status` TEGILMAYDI — TEMP_ACCESS shartnomasi.
        self.assertEqual("active", user.status)
        self.assertEqual("none", user.payment_status)
        self.assertEqual(
            UserAccessState.TEMPORARY_TRIAL,
            UserAccessStateService.classify(user),
        )
        self.assertFalse(UserAccessStateService.is_paid(user))
        self.assertTrue(UserAccessStateService.has_unlimited_course_access(user))

        expected_end = before + FEEDBACK_REWARD_DURATION
        self.assertLess(abs((user.end_date - expected_end).total_seconds()), 60)
        # Kutayotgan checkout tozalanadi, limit hisoblagichi nolga tushadi.
        self.assertEqual(0, user.questions_used)
        self.assertIsNone(user.selected_plan_type)
        self.assertIsNone(user.pending_checkout_msg_id)
        self.assertIsNone(user.expiry_reminder_sent_at)

    async def test_a_paid_user_is_never_touched_by_the_reward(self):
        # Obunachida limit yo'q: 30 daqiqalik bonus faqat end_date'ni buzardi.
        end = datetime.now(timezone.utc) + timedelta(days=20)
        user = _free_user()
        user.status = "active"
        user.payment_status = "approved"
        user.end_date = end
        user.selected_plan_type = "3_months"

        await self._service().grant_feedback_reward(
            user=user, feedback=SimpleNamespace(reward_granted_at=None)
        )

        self.assertEqual(end, user.end_date)
        self.assertEqual("3_months", user.selected_plan_type)
        self.assertEqual(UserAccessState.PAID, UserAccessStateService.classify(user))

    async def test_an_already_rewarded_feedback_does_not_grant_twice(self):
        user = _free_user()

        await self._service().grant_feedback_reward(
            user=user,
            feedback=SimpleNamespace(reward_granted_at=datetime.now(timezone.utc)),
        )

        self.assertEqual("free", user.status)
        self.assertIsNone(user.end_date)

    async def test_an_existing_longer_window_is_extended_not_replaced(self):
        # Allaqachon faol vaqtinchalik kirish bo'lsa, 30 daqiqa uning USTIGA
        # qo'shiladi — mukofot mavjud muddatni qisqartirmasligi kerak.
        current_end = datetime.now(timezone.utc) + timedelta(hours=2)
        user = _free_user()
        user.status = "active"
        user.end_date = current_end

        await self._service().grant_feedback_reward(
            user=user, feedback=SimpleNamespace(reward_granted_at=None)
        )

        self.assertEqual(current_end + FEEDBACK_REWARD_DURATION, user.end_date)
        self.assertEqual(
            UserAccessState.TEMPORARY_TRIAL,
            UserAccessStateService.classify(user),
        )


if __name__ == "__main__":
    unittest.main()
