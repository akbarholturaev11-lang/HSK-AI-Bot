import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.ai_usage_budget_service import AIUsageBudgetService


class _Session:
    def __init__(self):
        self.add = MagicMock()
        self.flush = AsyncMock()


class RenewalBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_future_renewal_budget_does_not_displace_current_budget(self):
        now = datetime.now(timezone.utc)
        current = SimpleNamespace(
            starts_at=now - timedelta(days=15),
            ends_at=now + timedelta(days=15),
            status="active",
            updated_at=now,
        )
        scheduled = SimpleNamespace(
            starts_at=current.ends_at,
            ends_at=current.ends_at + timedelta(days=30),
            status="active",
            updated_at=now,
        )
        service = AIUsageBudgetService(_Session())
        service._list_active_budgets = AsyncMock(return_value=[scheduled, current])

        active = await service.get_active_budget(123)

        self.assertIs(active, current)
        self.assertEqual("active", current.status)
        self.assertEqual("active", scheduled.status)

    async def test_scheduled_payment_budget_preserves_existing_budget(self):
        session = _Session()
        service = AIUsageBudgetService(session)
        service._live_or_manual_usd_rates = AsyncMock(
            return_value={"tjs": 10.0, "cny": 7.0}
        )
        service.expire_active_budgets = AsyncMock()
        starts_at = datetime.now(timezone.utc) + timedelta(days=12)
        ends_at = starts_at + timedelta(days=30)
        payment = SimpleNamespace(
            id=7,
            user_telegram_id=123,
            plan_type="1_month",
            amount=100,
            currency="TJS",
            base_amount=None,
        )

        budget = await service.create_for_payment(
            payment,
            starts_at=starts_at,
            ends_at=ends_at,
            preserve_existing=True,
        )

        service.expire_active_budgets.assert_not_awaited()
        self.assertEqual(starts_at, budget.starts_at)
        self.assertEqual(ends_at, budget.ends_at)
        self.assertEqual("active", budget.status)
        session.add.assert_called_once_with(budget)


if __name__ == "__main__":
    unittest.main()
