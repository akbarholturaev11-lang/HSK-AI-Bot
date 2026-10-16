"""Pending-receipt Pro preview: one opportunity, replenished by real approval."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.ai_usage_budget_service import (
    AIUsageBudgetService,
    PAYMENT_PREVIEW_AI_CAP_USD,
    PAYMENT_PREVIEW_PLAN_TYPE,
)
from app.services.entitlements.state import (
    EntitlementState, has_full_access, is_billing_paid, resolve_state,
)
from app.services.payment_review_preview_service import PaymentReviewPreviewService
from app.services.subscription_service import SubscriptionService
from app.services.user_access_state_service import UserAccessStateService, UserAccessState


class PaymentReviewPreviewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(
                telegram_id=954001, full_name="Receipt Preview",
                language="uz", level="hsk1", learning_mode="course",
                voice_mode="none", status="free", payment_status="none",
            ))
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _new_payment(self, session, plan="1_month"):
        payment = Payment(
            user_telegram_id=954001, plan_type=plan, amount=100,
            currency="TJS", payment_status="pending", payment_method="visa",
        )
        session.add(payment)
        await session.flush()
        return payment

    async def _user(self, session):
        return (await session.execute(
            select(User).where(User.telegram_id == 954001)
        )).scalar_one()

    async def test_receipt_opens_unpaid_preview_only_once(self):
        async with self.sessions() as session:
            user = await self._user(session)
            payment = await self._new_payment(session)
            preview = PaymentReviewPreviewService(session)

            self.assertTrue(await preview.claim(user, payment))
            self.assertFalse(await preview.claim(user, payment))
            self.assertFalse(user.payment_preview_available)
            self.assertEqual(user.payment_preview_payment_id, payment.id)
            self.assertEqual(
                UserAccessStateService.classify(user), UserAccessState.TEMPORARY_TRIAL
            )
            self.assertFalse(UserAccessStateService.is_paid(user))
            self.assertEqual(resolve_state(user), EntitlementState.TEMP_ACCESS)
            self.assertTrue(has_full_access(resolve_state(user)))
            self.assertFalse(is_billing_paid(resolve_state(user)))
            self.assertEqual(user.payment_status, "none")
            self.assertIsNone(user.end_date)
            budgets = (await session.execute(select(AIUsageBudget))).scalars().all()
            self.assertEqual(len(budgets), 1)
            self.assertEqual(budgets[0].payment_id, payment.id)
            self.assertEqual(budgets[0].plan_type, PAYMENT_PREVIEW_PLAN_TYPE)
            self.assertEqual(budgets[0].total_budget_usd, PAYMENT_PREVIEW_AI_CAP_USD)
            self.assertTrue((await AIUsageBudgetService(session).can_use_payment_preview_ai(
                user.telegram_id, payment.id
            )).allowed)

    async def test_reject_removes_access_without_refunding_ticket(self):
        async with self.sessions() as session:
            user = await self._user(session)
            first = await self._new_payment(session)
            preview = PaymentReviewPreviewService(session)
            self.assertTrue(await preview.claim(user, first))
            first.payment_status = "rejected"
            await preview.review(user, first, approved=False)

            self.assertIsNone(user.payment_preview_payment_id)
            self.assertFalse(user.payment_preview_available)
            self.assertEqual(UserAccessStateService.classify(user), UserAccessState.FREE)
            self.assertFalse((await AIUsageBudgetService(session).can_use_payment_preview_ai(
                user.telegram_id, first.id
            )).allowed)
            second = await self._new_payment(session)
            self.assertFalse(await preview.claim(user, second))
            self.assertEqual(user.payment_status, "none")
            self.assertEqual(second.payment_status, "pending")

            # An admin-approved real subscription, not the rejected screenshot,
            # replenishes exactly one opportunity.
            second.payment_status = "approved"
            await preview.review(user, second, approved=True)
            self.assertTrue(user.payment_preview_available)
            third = await self._new_payment(session)
            self.assertTrue(await preview.claim(user, third))
            self.assertFalse(user.payment_preview_available)
            self.assertEqual(user.payment_preview_payment_id, third.id)

    async def test_approval_activates_real_plan_and_replenishes_once(self):
        async with self.sessions() as session:
            user = await self._user(session)
            payment = await self._new_payment(session)
            self.assertTrue(await PaymentReviewPreviewService(session).claim(user, payment))
            payment.payment_status = "approved"
            with (
                patch(
                    "app.services.ai_usage_budget_service.AIUsageBudgetService.create_for_payment",
                    new_callable=AsyncMock,
                ),
                patch(
                    "app.services.portfolio_service.PortfolioService.record_subscription_profit",
                    new_callable=AsyncMock,
                ),
                patch(
                    "app.services.subscription_churn_service.SubscriptionChurnService.reset_after_paid_activation",
                    new_callable=AsyncMock,
                ),
            ):
                self.assertTrue(await SubscriptionService(session).activate_plan(
                    telegram_id=user.telegram_id, plan_type=payment.plan_type, payment=payment
                ))
            self.assertEqual(UserAccessStateService.classify(user), UserAccessState.PAID)
            self.assertTrue(user.payment_preview_available)
            self.assertIsNone(user.payment_preview_payment_id)
            self.assertGreater(AIUsageBudgetService(session)._as_utc(user.end_date), datetime.now(timezone.utc))
            self.assertEqual(
                (await session.execute(
                    select(AIUsageBudget).where(AIUsageBudget.payment_id == payment.id)
                )).scalar_one().status, "expired"
            )

    async def test_real_paid_access_survives_rejected_renewal(self):
        async with self.sessions() as session:
            user = await self._user(session)
            user.status = "active"
            user.payment_status = "approved"
            user.start_date = datetime.now(timezone.utc)
            user.end_date = datetime.now(timezone.utc) + timedelta(days=8)
            payment = await self._new_payment(session)
            preview = PaymentReviewPreviewService(session)
            self.assertTrue(await preview.claim(user, payment))
            budget = (await session.execute(
                select(AIUsageBudget).where(AIUsageBudget.payment_id == payment.id)
            )).scalar_one()
            self.assertGreaterEqual(
                AIUsageBudgetService(session)._as_utc(budget.starts_at),
                AIUsageBudgetService(session)._as_utc(user.end_date),
            )
            payment.payment_status = "rejected"
            await preview.review(user, payment, approved=False)
            self.assertEqual(UserAccessStateService.classify(user), UserAccessState.PAID)
            self.assertEqual(user.payment_status, "approved")
            self.assertGreater(AIUsageBudgetService(session)._as_utc(user.end_date), datetime.now(timezone.utc))

    async def test_preview_budget_is_not_unlimited_after_exhaustion(self):
        async with self.sessions() as session:
            user = await self._user(session)
            payment = await self._new_payment(session)
            self.assertTrue(await PaymentReviewPreviewService(session).claim(user, payment))
            budget = (await session.execute(select(AIUsageBudget))).scalar_one()
            budget.segment_1_spent_usd = PAYMENT_PREVIEW_AI_CAP_USD
            self.assertFalse((await AIUsageBudgetService(session).can_use_payment_preview_ai(
                user.telegram_id, payment.id
            )).allowed)
            self.assertEqual(resolve_state(user), EntitlementState.TEMP_ACCESS)

    async def test_hsk30_unlock_and_blocked_accounts_do_not_spend_ticket(self):
        async with self.sessions() as session:
            user = await self._user(session)
            preview = PaymentReviewPreviewService(session)
            unlock = await self._new_payment(session, "hsk30_unlock")
            self.assertFalse(await preview.claim(user, unlock))
            self.assertTrue(user.payment_preview_available)
            user.status = "blocked"
            payment = await self._new_payment(session)
            self.assertFalse(await preview.claim(user, payment))
            self.assertTrue(user.payment_preview_available)
            self.assertEqual(UserAccessStateService.classify(user), UserAccessState.BLOCKED)


if __name__ == "__main__":
    unittest.main()
