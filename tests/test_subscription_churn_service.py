import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.subscription_churn_service import SubscriptionChurnService


class _Scalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return _Scalars(self.rows)


class _Session:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.added = []
        self.flush_count = 0
        self.commit_count = 0

    async def execute(self, _stmt):
        return _Result(self.rows)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1


class SubscriptionChurnServiceTests(unittest.IsolatedAsyncioTestCase):
    def _user(self, **overrides):
        values = {
            "id": 1,
            "telegram_id": 123,
            "language": "uz",
            "subscription_expired_offer_sent_at": None,
            "subscription_churn_followup_sent_at": None,
            "subscription_churn_responded_at": None,
            "subscription_churn_reason": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    async def test_budget_reason_creates_immediate_feedback_discount(self):
        user = self._user()
        session = _Session()
        feedback, discount_available = await SubscriptionChurnService(session).record_reason(user, "budget")

        self.assertTrue(discount_available)
        self.assertEqual(feedback.disliked_code, "price")
        self.assertIsNotNone(feedback.price_offer_sent_at)
        self.assertEqual(user.subscription_churn_reason, "budget")
        self.assertIsNotNone(user.subscription_churn_responded_at)
        self.assertEqual(session.added, [feedback])

    async def test_ai_quality_reason_notifies_without_discount(self):
        user = self._user()
        session = _Session()
        feedback, discount_available = await SubscriptionChurnService(session).record_reason(user, "ai_quality")

        self.assertFalse(discount_available)
        self.assertEqual(feedback.disliked_code, "unclear")
        self.assertIsNone(feedback.price_offer_sent_at)
        self.assertEqual(user.subscription_churn_reason, "ai_quality")

    async def test_due_followup_is_sent_once_and_marked(self):
        user = self._user(
            subscription_expired_offer_sent_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        session = _Session(rows=[user])
        bot = SimpleNamespace(send_message=AsyncMock())

        sent = await SubscriptionChurnService(session).send_due_followups(bot)

        self.assertEqual(sent, 1)
        self.assertIsNotNone(user.subscription_churn_followup_sent_at)
        self.assertEqual(session.commit_count, 1)
        bot.send_message.assert_awaited_once()
