"""lava.top second checkout path: verified, idempotent money handling."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.lava import LavaInvoice, LavaWebhookEvent
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.lava import events, ledger
from app.services.lava.checkout import LavaCheckoutError, LavaCheckoutService
from app.services.lava.config import LavaConfigService, config_from_dict, effective_mode
from app.services.lava.reconcile import LavaReconcileWorker
from app.services.subscription_service import PLAN_DURATIONS, SUBSCRIPTION_PLAN_DURATIONS
from tests.lava_fakes import (
    OFFER_ID, WEBHOOK_SECRET, FakeLava, lava_settings, make_runtime, payment_webhook, refund_webhook,
)


def _config(mode="both", *, enabled=("1_month", "3_months", "6_months", "12_months"), currency="USD"):
    return config_from_dict({
        "checkout_mode": mode, "currency": currency,
        "plans": {plan: {"enabled": plan in enabled, "offer_id": OFFER_ID} for plan in
                  ("1_month", "3_months", "6_months", "12_months")},
    })


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class LavaPaymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=1001, full_name="Learner", language="uz", status="free"),
                User(id=2, telegram_id=None, full_name="Google learner", language="ru", status="free"),
            ])
            await LavaConfigService(session).save(_config())
            await session.commit()
        self.fake = FakeLava()
        self.runtime = make_runtime(self.sessions, self.fake)
        self.approved = []

        async def on_approved(session, result):
            self.approved.append(result.payment.id)

        self.runtime.on_approved = on_approved
        self.checkout = LavaCheckoutService(self.runtime)
        patcher = patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                               new=AsyncMock(return_value={"tjs": 10, "cny": 7}))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _start(self, user_id=1, plan="1_month", email="Buyer@Example.com", source="miniapp"):
        return await self.checkout.start(self.sessions, user_id=user_id, plan_type=plan, email=email,
                                         source=source, language="uz")

    async def _ingest(self, raw, key=WEBHOOK_SECRET):
        return await events.ingest(self.runtime, raw, api_key_header=key, client_ip="158.160.60.174")

    async def _contract(self, checkout_id):
        async with self.sessions() as session:
            return (await session.get(LavaInvoice, checkout_id)).contract_id

    async def _user(self, user_id=1):
        async with self.sessions() as session:
            return await session.get(User, user_id)

    async def _payments(self, user_id=1):
        async with self.sessions() as session:
            return list((await session.execute(select(Payment).where(Payment.user_id == user_id)
                                               .order_by(Payment.id))).scalars())

    async def _paid_first(self, plan="1_month"):
        started = await self._start(plan=plan)
        contract = await self._contract(started["checkout_id"])
        self.fake.complete(contract)
        amount = self.fake.invoices[contract]["amount"]
        self.assertEqual(await self._ingest(payment_webhook("payment.success", contract, amount=amount)),
                         (200, {"ok": True, "result": "applied"}))
        return started["checkout_id"], contract

    # -- mode and terms ---------------------------------------------------
    async def test_manual_only_mode_keeps_overview_unchanged(self):
        async with self.sessions() as session:
            await LavaConfigService(session).save(_config("manual_only"))
            await session.commit()
            user = await session.get(User, 1)
            self.assertIsNone(await self.checkout.overview_block(session, user, supports_lava=True))
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start()
        self.assertEqual(ctx.exception.code, "lava_unavailable")

    async def test_effective_mode_falls_back_to_manual_when_unsafe(self):
        config = _config("lava_only")
        self.assertEqual(effective_mode(config, lava_settings(), client_supports_lava=True), "lava_only")
        self.assertEqual(effective_mode(config, lava_settings(), client_supports_lava=False), "manual_only")
        self.assertEqual(effective_mode(config, lava_settings(LAVA_ENABLED=False), client_supports_lava=True),
                         "manual_only")
        self.assertEqual(effective_mode(config, lava_settings(LAVA_API_KEY=""), client_supports_lava=True),
                         "manual_only")
        self.assertEqual(effective_mode(_config("both", enabled=()), lava_settings(), client_supports_lava=True),
                         "manual_only")

    async def test_disabled_term_is_hidden_and_rejected_then_visible_again(self):
        async with self.sessions() as session:
            await LavaConfigService(session).save(_config(enabled=("1_month", "6_months")))
            await session.commit()
            block = await self.checkout.overview_block(session, await session.get(User, 1), supports_lava=True)
        self.assertEqual([plan["plan_type"] for plan in block["plans"]], ["1_month", "6_months"])
        self.assertEqual(block["mode"], "both")
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start(plan="3_months")
        self.assertEqual(ctx.exception.code, "plan_unavailable")
        async with self.sessions() as session:
            await LavaConfigService(session).save(_config())
            await session.commit()
            block = await self.checkout.overview_block(session, await session.get(User, 1), supports_lava=True)
        self.assertIn("3_months", [plan["plan_type"] for plan in block["plans"]])

    def test_manual_allowlist_does_not_gain_lava_terms(self):
        self.assertEqual(set(PLAN_DURATIONS), {"10_days", "1_month", "3_months"})
        self.assertEqual(SUBSCRIPTION_PLAN_DURATIONS["6_months"], 180)
        self.assertEqual(SUBSCRIPTION_PLAN_DURATIONS["12_months"], 365)

    # -- activation -------------------------------------------------------
    async def test_verified_payment_activates_once_despite_duplicate_webhooks(self):
        checkout_id, contract = await self._paid_first()
        user = await self._user()
        self.assertEqual(user.status, "active")
        self.assertEqual(user.payment_status, "approved")
        self.assertAlmostEqual((_utc(user.end_date) - datetime.now(timezone.utc)).days, 29, delta=1)
        first_end = user.end_date
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract)))[1]["result"],
                         "duplicate")
        await events.verify_and_apply(self.runtime, contract)  # admin recheck / reconcile race
        payments = await self._payments()
        self.assertEqual(len(payments), 1)
        self.assertEqual((payments[0].payment_method, payments[0].payment_status, payments[0].currency,
                          payments[0].local_amount), ("lava", "approved", "USD", "10.00"))
        self.assertEqual((await self._user()).end_date, first_end)
        self.assertEqual(self.approved, [payments[0].id])
        status = await self.checkout.status(self.sessions, user_id=1, checkout_id=checkout_id)
        self.assertEqual(status["status"], "paid")
        async with self.sessions() as session:
            row = await session.get(LavaInvoice, checkout_id)
            self.assertEqual((row.status, row.granted_days, row.buyer_email, row.subscription_status),
                             ("paid", 30, "buyer@example.com", "active"))
            # Lava pre-payment state never became a reviewable pending receipt.
            self.assertEqual(await session.scalar(select(func.count(Payment.id)).where(
                Payment.payment_status == "pending")), 0)

    async def test_webhook_without_api_completion_is_not_granted_and_retries(self):
        started = await self._start()
        contract = await self._contract(started["checkout_id"])
        status, body = await self._ingest(payment_webhook("payment.success", contract))
        self.assertEqual((status, body["result"]), (503, "retry"))
        self.assertEqual(await self._payments(), [])
        self.assertEqual((await self._user()).status, "free")

    async def test_forged_webhook_is_rejected_without_recording(self):
        started = await self._start()
        contract = await self._contract(started["checkout_id"])
        self.fake.complete(contract)
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract), key="wrong"))[0], 401)
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract), key=None))[0], 401)
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count(LavaWebhookEvent.id))), 0)
        self.assertEqual(await self._payments(), [])

    async def test_unknown_contract_is_unmatched_not_granted_by_email(self):
        external = self.fake.add_external(email="buyer@example.com")
        status, body = await self._ingest(payment_webhook("payment.success", external))
        self.assertEqual((status, body["result"]), (200, "unmatched"))
        self.assertEqual(await self._payments(), [])
        self.assertIn("unmatched", [code for code, _ in self.runtime.notifier.alerts])

    async def test_renewal_extends_from_current_end(self):
        _, parent = await self._paid_first()
        first_end = _utc((await self._user()).end_date)
        renewal = self.fake.add_renewal(parent)
        result = await self._ingest(payment_webhook("subscription.recurring.payment.success", renewal,
                                                    parent=parent))
        self.assertEqual(result[1]["result"], "applied")
        self.assertEqual(_utc((await self._user()).end_date) - first_end, timedelta(days=30))
        self.assertEqual(len(await self._payments()), 2)

    async def test_twelve_month_term_grants_365_days(self):
        await self._paid_first(plan="12_months")
        user = await self._user()
        self.assertAlmostEqual((_utc(user.end_date) - datetime.now(timezone.utc)).days, 364, delta=1)
        self.assertEqual((await self._payments())[0].plan_type, "12_months")

    # -- start guards -----------------------------------------------------
    async def test_start_refuses_second_subscription_and_pending_receipt(self):
        await self._paid_first()
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start()
        self.assertEqual(ctx.exception.code, "subscription_active")
        async with self.sessions() as session:
            session.add(Payment(user_id=2, plan_type="1_month", amount=29, currency="TJS",
                                payment_method="visa", payment_status="pending"))
            await session.commit()
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start(user_id=2)
        self.assertEqual(ctx.exception.code, "payment_pending")

    async def test_invalid_email_rejected(self):
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start(email="not-an-email")
        self.assertEqual(ctx.exception.code, "invalid_email")

    # -- cancellation keeps the paid term ----------------------------------
    async def test_cancellation_paths_keep_end_date(self):
        _, contract = await self._paid_first()
        end = (await self._user()).end_date
        result = await self.checkout.cancel(self.sessions, user_id=1)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual((await self._user()).end_date, end)
        cancel_event = payment_webhook("subscription.cancelled", contract)
        self.assertEqual((await self._ingest(cancel_event))[1]["result"], "applied")
        self.assertEqual((await self._user()).end_date, end)
        failed = payment_webhook("subscription.recurring.payment.failed", self.fake.add_renewal(contract, status="FAILED"),
                                 parent=contract)
        await self._ingest(failed)
        user = await self._user()
        self.assertEqual((user.end_date, user.status), (end, "active"))
        self.assertEqual([p.payment_status for p in await self._payments()], ["approved"])

    # -- refund / chargeback ---------------------------------------------
    async def test_full_refund_revokes_exactly_the_paid_days(self):
        await self._paid_first()
        payment = (await self._payments())[0]
        status, body = await self._ingest(refund_webhook())
        self.assertEqual((status, body["result"]), (200, "applied"))
        user = await self._user()
        self.assertEqual(user.status, "expired")
        self.assertLessEqual(_utc(user.end_date), datetime.now(timezone.utc) + timedelta(minutes=1))
        refunded = (await self._payments())[0]
        self.assertEqual((refunded.id, refunded.payment_status), (payment.id, "refunded"))
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count(PortfolioTransaction.id)).where(
                PortfolioTransaction.payment_id == payment.id)), 0)
        self.assertIn((1, "refund_revoked"), self.runtime.notifier.notices)

    async def test_refund_keeps_later_renewal_days(self):
        _, parent = await self._paid_first()
        renewal = self.fake.add_renewal(parent)
        await self._ingest(payment_webhook("subscription.recurring.payment.success", renewal, parent=parent))
        end_two_periods = _utc((await self._user()).end_date)
        await self._ingest(refund_webhook())
        self.assertEqual(end_two_periods - _utc((await self._user()).end_date), timedelta(days=30))
        self.assertEqual((await self._user()).status, "active")

    async def test_partial_or_unmatched_refund_needs_review_without_access_change(self):
        await self._paid_first()
        end = (await self._user()).end_date
        self.assertEqual((await self._ingest(refund_webhook(refund_type="partial", amount="3.00")))[1]["result"],
                         "needs_review")
        self.assertEqual((await self._ingest(refund_webhook(email="other@example.com")))[1]["result"],
                         "needs_review")
        self.assertEqual((await self._user()).end_date, end)

    async def test_chargeback_open_blocks_lava_and_won_restores_days(self):
        checkout_id, _ = await self._paid_first()
        end = _utc((await self._user()).end_date)
        await self._ingest(refund_webhook(event_type="chargeback.initiated"))
        self.assertEqual((await self._payments())[0].payment_status, "chargeback")
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start()
        self.assertEqual(ctx.exception.code, "chargeback_open")
        outcome = await ledger.close_chargeback(self.sessions, checkout_id, won=True)
        self.assertEqual(outcome.outcome, "restored")
        user = await self._user()
        self.assertEqual(user.status, "active")
        self.assertAlmostEqual((_utc(user.end_date) - end).total_seconds(), 0, delta=120)
        self.assertEqual((await self._payments())[0].payment_status, "approved")

    # -- kill switch / pause / reconciliation -----------------------------
    async def test_sales_disabled_still_processes_existing_invoice(self):
        started = await self._start()
        contract = await self._contract(started["checkout_id"])
        self.runtime.settings.LAVA_ENABLED = False
        with self.assertRaises(LavaCheckoutError):
            await self._start(user_id=2)
        self.fake.complete(contract)
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract)))[1]["result"], "applied")
        self.assertEqual((await self._user()).status, "active")

    async def test_paused_processing_queues_and_drains_once(self):
        started = await self._start()
        contract = await self._contract(started["checkout_id"])
        self.fake.complete(contract)
        self.runtime.settings.LAVA_PROCESSING_PAUSED = True
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract)))[1]["result"], "queued")
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract)))[1]["result"], "queued")
        self.assertEqual(await self._payments(), [])
        self.runtime.settings.LAVA_PROCESSING_PAUSED = False
        worker = LavaReconcileWorker(self.runtime, instance_id="t")
        await worker.tick(force=True)
        await worker.tick(force=True)
        self.assertEqual(len(await self._payments()), 1)

    async def test_reconcile_repairs_lost_webhook(self):
        started = await self._start()
        contract = await self._contract(started["checkout_id"])
        self.fake.complete(contract)  # paid, but the webhook never arrived
        worker = LavaReconcileWorker(self.runtime, instance_id="t")
        summary = await worker.tick(force=True)
        self.assertEqual(summary["invoices"], 1)
        self.assertEqual(len(await self._payments()), 1)
        self.assertEqual((await self._user()).status, "active")
        # A late webhook afterwards is a duplicate.
        self.assertEqual((await self._ingest(payment_webhook("payment.success", contract)))[1]["result"],
                         "duplicate")

    async def test_reconcile_applies_missed_renewal(self):
        _, parent = await self._paid_first()
        self.fake.add_renewal(parent)
        worker = LavaReconcileWorker(self.runtime, instance_id="t")
        summary = await worker.tick(force=True)
        self.assertEqual(summary["renewals"], 1)
        self.assertEqual(len(await self._payments()), 2)

    async def test_account_purge_keeps_lava_money_facts_and_drops_email(self):
        from app.repositories.user_repo import UserRepository
        await self._paid_first()
        renewal_parent = await self._contract(1)
        self.fake.add_renewal(renewal_parent)
        await self._ingest(refund_webhook())  # first payment becomes 'refunded'
        async with self.sessions() as session:
            self.assertTrue(await UserRepository(session).delete_by_user_id(1))
            await session.commit()
        async with self.sessions() as session:
            payments = list((await session.execute(select(Payment))).scalars())
            invoices = list((await session.execute(select(LavaInvoice))).scalars())
        self.assertEqual([p.payment_status for p in payments], ["refunded"])
        self.assertTrue(all(p.user_id is None for p in payments))
        self.assertTrue(all(row.user_id is None and row.buyer_email is None for row in invoices))

    async def test_provider_outage_on_create_marks_reservation_failed(self):
        self.fake.unavailable = True
        with self.assertRaises(LavaCheckoutError) as ctx:
            await self._start()
        self.assertEqual(ctx.exception.code, "provider_unavailable")
        self.fake.unavailable = False
        started = await self._start()  # a failed reservation does not block a retry
        self.assertTrue(started["payment_url"].startswith("https://pay.lava.top/"))


if __name__ == "__main__":
    unittest.main()
