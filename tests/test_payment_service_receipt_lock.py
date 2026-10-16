"""Bot receipt edits share canonical lock order with admin review."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.payment_repo import PaymentRepository
from app.services.payment_review_preview_service import PaymentReviewPreviewService
from app.services.payment_service import PaymentService


QUOTE = dict(final_amount=95, base_amount=95, currency="TJS", discount_source="none",
             discount_percent=0, discount_campaign_id=None, discount_title=None, discount_details=None)


class PaymentServiceReceiptLockTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([User(id=1, telegram_id=7001, selected_plan_type="1_month", payment_method="visa"),
                             User(id=2, telegram_id=None, selected_plan_type="1_month", payment_method="visa")])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_receipt_locks_owner_before_reads_and_scopes_both_update_paths(self):
        for status in ("draft", "pending"):
            async with self.sessions() as session:
                owner = await session.get(User, 1)
                payment = await PaymentRepository(session).create(owner, "1_month", 95, payment_status=status)
                await session.commit()
                service = PaymentService(session)
                service.get_checkout_info = AsyncMock(return_value=QUOTE)
                calls = []
                resolve = service.payment_repo.resolve_owner
                read_draft = service.payment_repo.get_latest_draft_by_user
                async def locked(actor, **kwargs):
                    calls.append(("owner", kwargs.get("lock", False)))
                    return await resolve(actor, **kwargs)
                async def draft(actor):
                    calls.append(("draft", actor.id))
                    return await read_draft(actor)
                service.payment_repo.resolve_owner = locked
                service.payment_repo.get_latest_draft_by_user = draft
                original = service.payment_repo.update_checkout if status == "draft" else service.payment_repo.update_screenshot
                guarded = AsyncMock(wraps=original)
                if status == "draft":
                    service.payment_repo.update_checkout = guarded
                else:
                    service.payment_repo.update_screenshot = guarded
                with self.subTest(status=status):
                    result, message = await service.attach_or_create_payment_screenshot(7001, "1_month", "receipt")
                    self.assertEqual((result.id, message), (payment.id, "updated"))
                    self.assertEqual(calls[0], ("owner", True))
                    self.assertEqual(guarded.await_args.kwargs["actor"].id, owner.id)
                await session.execute(update(Payment).values(payment_status="approved"))
                await session.commit()

    async def test_reviewed_cas_miss_never_claims_preview_or_returns_stale_pending(self):
        for original_status in ("draft", "pending"):
            for reviewed_status in ("approved", "rejected"):
                async with self.sessions() as session:
                    owner = await session.get(User, 1)
                    owner.payment_preview_available = True
                    owner.payment_preview_payment_id = None
                    payment = await PaymentRepository(session).create(owner, "1_month", 95, payment_status=original_status)
                    await session.execute(update(Payment).where(Payment.id == payment.id)
                        .values(payment_status=reviewed_status).execution_options(synchronize_session=False))
                    service = PaymentService(session)
                    service.get_checkout_info = AsyncMock(return_value=QUOTE)
                    service.payment_repo.get_latest_draft_by_user = AsyncMock(return_value=payment if original_status == "draft" else None)
                    service.payment_repo.get_latest_pending_by_user = AsyncMock(return_value=payment)
                    with patch.object(PaymentReviewPreviewService, "claim", new_callable=AsyncMock) as claim:
                        result = await service.attach_or_create_payment_screenshot(7001, "1_month", "late-receipt")
                        self.assertEqual(result, (None, "payment_already_reviewed"))
                        claim.assert_not_awaited()
                    actual = (await session.execute(select(Payment.payment_status, Payment.screenshot_file_id)
                        .where(Payment.id == payment.id))).one()
                    self.assertEqual(actual, (reviewed_status, None))
                    self.assertTrue(owner.payment_preview_available)
                    self.assertIsNone(owner.payment_preview_payment_id)
                    self.assertEqual((await session.execute(select(func.count(AIUsageBudget.id)))).scalar_one(), 0)
                    await session.rollback()

    async def test_create_fallback_requires_fresh_bot_intent_and_keeps_numeric_tg_semantics(self):
        async with self.sessions() as session:
            service = PaymentService(session)
            service.get_checkout_info = AsyncMock(return_value=QUOTE)
            self.assertEqual(await service.attach_or_create_payment_screenshot(1, "1_month", "bad"), (None, "access_start_first"))
            owner = await session.get(User, 1)
            owner.selected_plan_type = None
            await session.flush()
            self.assertEqual(await service.attach_or_create_payment_screenshot(7001, "1_month", "late"), (None, "payment_already_reviewed"))
            owner.selected_plan_type = "1_month"
            await session.flush()
            payment, state = await service.attach_or_create_payment_screenshot(7001, "1_month", "fresh")
            self.assertEqual((state, payment.user_id, payment.user_telegram_id), ("created", 1, 7001))

    async def test_draft_checkout_cas_miss_does_not_return_reviewed_payment_as_editable(self):
        async with self.sessions() as session:
            owner = await session.get(User, 1)
            payment = await PaymentRepository(session).create(owner, "1_month", 95, payment_status="draft")
            await session.execute(update(Payment).where(Payment.id == payment.id)
                .values(payment_status="approved").execution_options(synchronize_session=False))
            service = PaymentService(session)
            service.get_checkout_info = AsyncMock(return_value=QUOTE)
            service.payment_repo.get_latest_draft_by_user = AsyncMock(return_value=payment)
            result = await service.create_checkout_draft(7001, "1_month")
            self.assertEqual(result, (None, None, "payment_already_reviewed"))
            self.assertEqual((await session.execute(select(Payment.payment_status).where(Payment.id == payment.id))).scalar_one(), "approved")


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"), "requires isolated PostgreSQL test database")
class PaymentServiceReceiptConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
        self.schema = "receipt_lock_test_" + uuid4().hex
        self.admin = create_async_engine(url)
        async with self.admin.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(url, connect_args={"server_settings": {"search_path": self.schema + ",public"}})
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=7001, selected_plan_type="1_month"))
            session.add(Payment(id=1, user_id=1, user_telegram_id=7001, plan_type="1_month", amount=95))
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def test_admin_first_receipt_waits_without_holding_payment_and_creates_nothing(self):
        entered = asyncio.Event()
        async def receipt():
            async with self.sessions() as session:
                service = PaymentService(session)
                original = service.payment_repo.resolve_owner
                async def resolve(actor, **kwargs):
                    if kwargs.get("lock"):
                        entered.set()
                    return await original(actor, **kwargs)
                service.payment_repo.resolve_owner = resolve
                return await service.attach_or_create_payment_screenshot(7001, "1_month", "late-receipt")
        async with self.sessions() as reviewer:
            repo = PaymentRepository(reviewer)
            payment = await repo.get_by_id(1)
            owner = await repo.get_owner(payment, lock=True)
            pending = asyncio.create_task(receipt())
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                await asyncio.sleep(.1)
                self.assertFalse(pending.done())
                self.assertTrue(await asyncio.wait_for(repo.approve(payment), timeout=3))
                owner.selected_plan_type = None
                await reviewer.commit()
                self.assertEqual(await asyncio.wait_for(pending, timeout=5), (None, "payment_already_reviewed"))
            finally:
                if not pending.done():
                    pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(func.count(Payment.id)))).scalar_one(), 1)
            self.assertEqual((await session.execute(select(func.count(AIUsageBudget.id)))).scalar_one(), 0)
            user = await session.get(User, 1)
            self.assertTrue(user.payment_preview_available)
            self.assertIsNone(user.payment_preview_payment_id)

    async def test_receipt_first_admin_review_finishes_without_reverse_lock_deadlock(self):
        payment_written, release_receipt, review_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def receipt():
            async with self.sessions() as session:
                service = PaymentService(session)
                update_receipt = service.payment_repo.update_screenshot
                async def held(*args, **kwargs):
                    changed = await update_receipt(*args, **kwargs)
                    payment_written.set()
                    await release_receipt.wait()
                    return changed
                service.payment_repo.update_screenshot = held
                return await service.attach_or_create_payment_screenshot(7001, "1_month", "receipt")
        async def reject():
            async with self.sessions() as session:
                repo = PaymentRepository(session)
                payment = await repo.get_by_id(1)
                review_started.set()
                owner = await repo.get_owner(payment, lock=True)
                self.assertTrue(await repo.reject(payment))
                owner.selected_plan_type = None
                await PaymentReviewPreviewService(session).review(owner, payment, approved=False)
                await session.commit()
        first = asyncio.create_task(receipt())
        second = None
        try:
            await asyncio.wait_for(payment_written.wait(), timeout=5)
            second = asyncio.create_task(reject())
            await asyncio.wait_for(review_started.wait(), timeout=5)
            await asyncio.sleep(.1)
            self.assertFalse(second.done(), "review must wait for the receipt's User lock")
            release_receipt.set()
            result, _ = await asyncio.wait_for(asyncio.gather(first, second), timeout=8)
            self.assertEqual(result[1], "updated")
        finally:
            release_receipt.set()
            for task in (first, second):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(*(task for task in (first, second) if task is not None), return_exceptions=True)
        async with self.sessions() as session:
            self.assertEqual((await session.get(Payment, 1)).payment_status, "rejected")
            owner = await session.get(User, 1)
            self.assertFalse(owner.payment_preview_available)
            self.assertIsNone(owner.payment_preview_payment_id)
            self.assertEqual((await session.execute(select(AIUsageBudget.status))).scalar_one(), "expired")
