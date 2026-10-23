"""Canonical manual-payment ownership and immutable reviewed receipts."""
import asyncio
import os
import unittest
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.payment_repo import PaymentRepository


class NativePaymentRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, full_name="Native A"),
                User(id=2, telegram_id=None, full_name="Native B"),
                User(id=3, telegram_id=1001, full_name="Telegram A"),
                User(id=4, telegram_id=1002, full_name="Telegram B"),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_create_records_canonical_owner_without_fabricating_telegram_identity(self):
        async with self.sessions() as session:
            repo = PaymentRepository(session)
            native = await session.get(User, 1)
            first = await repo.create(native, "1_month", 95, source="desktop_subscription")
            second = await repo.create(1001, "1_month", 95)
            self.assertEqual((first.user_id, first.user_telegram_id), (1, None))
            self.assertEqual((second.user_id, second.user_telegram_id), (3, 1001))
            self.assertEqual((await repo.resolve_owner(native, lock=True)).id, 1)
            self.assertEqual((await repo.get_owner(first, lock=True)).id, 1)
            # A bare numeric canonical ID is never interpreted as an account.
            for invalid in (None, 0, -1, 1, 9999):
                with self.subTest(actor=invalid):
                    with self.assertRaisesRegex(ValueError, "payment_owner_not_found"):
                        await repo.create(invalid, "1_month", 95)

    async def test_all_owner_queries_keep_two_null_telegram_accounts_separate(self):
        async with self.sessions() as session:
            repo = PaymentRepository(session)
            first, second = await session.get(User, 1), await session.get(User, 2)
            draft = await repo.create(first, "1_month", 95, payment_status="draft")
            pending = await repo.create(first, "1_month", 95)
            rejected = await repo.create(second, "3_months", 250, payment_status="rejected")
            other_pending = await repo.create(second, "3_months", 250)
            self.assertEqual((await repo.get_latest_draft_by_user(first)).id, draft.id)
            self.assertIsNone(await repo.get_latest_draft_by_user(second))
            self.assertEqual((await repo.get_latest_pending_by_user(first)).id, pending.id)
            self.assertEqual((await repo.get_latest_pending_by_user(second)).id, other_pending.id)
            self.assertIsNone(await repo.get_latest_pending_by_user_and_plan(first, "3_months"))
            self.assertTrue(await repo.has_rejected_by_user_and_plan(second, "3_months"))
            self.assertFalse(await repo.has_rejected_by_user_and_plan(first, "3_months"))
            self.assertEqual({p.id for p in await repo.list_by_user(second)}, {rejected.id, other_pending.id})
            for invalid in (None, 0, -1):
                with self.subTest(actor=invalid):
                    self.assertEqual(await repo.list_by_user(invalid), [])
                    self.assertIsNone(await repo.get_latest_pending_by_user(invalid))
                    self.assertIsNone(await repo.get_latest_draft_by_user(invalid))
                    self.assertFalse(await repo.has_pending_by_user(invalid))
                    self.assertFalse(await repo.has_rejected_by_user_and_plan(invalid, "3_months"))

    async def test_canonical_owner_wins_over_conflicting_or_deleted_telegram_metadata(self):
        async with self.sessions() as session:
            repo = PaymentRepository(session)
            native = await session.get(User, 2)
            telegram = await session.get(User, 3)
            rows = [
                Payment(id=10, user_id=2, user_telegram_id=1001, plan_type="1_month", amount=95),
                Payment(id=11, user_id=None, user_telegram_id=1001, plan_type="1_month", amount=95),
                Payment(id=12, user_id=999, user_telegram_id=1001, plan_type="1_month", amount=95),
                Payment(id=13, user_id=None, user_telegram_id=9009, plan_type="1_month", amount=95),
                Payment(id=14, user_id=None, user_telegram_id=None, plan_type="1_month", amount=95),
            ]
            session.add_all(rows)
            await session.flush()
            self.assertEqual({p.id for p in await repo.list_by_user(telegram)}, {11})
            self.assertEqual({p.id for p in await repo.list_by_user(1001)}, {11})
            self.assertEqual({p.id for p in await repo.list_by_user(native)}, {10})
            self.assertEqual({p.id for p in await repo.list_by_user(9009)}, {13})
            self.assertEqual((await repo.get_owner(rows[0])).id, 2)
            self.assertEqual((await repo.get_owner(rows[1])).id, 3)
            self.assertIsNone(await repo.get_owner(rows[2]))
            self.assertIsNone(await repo.get_owner(rows[4]))
            self.assertFalse(repo.is_owned_by(rows[0], telegram))
            self.assertTrue(repo.is_owned_by(rows[0], native))
            self.assertFalse(repo.is_owned_by(rows[2], telegram))

    async def test_owner_guard_and_status_cas_prevent_foreign_or_reviewed_receipt_mutation(self):
        async with self.sessions() as session:
            repo = PaymentRepository(session)
            owner, other = await session.get(User, 1), await session.get(User, 2)
            payment = await repo.create(owner, "1_month", 95)
            changes = dict(plan_type="3_months", amount=250, currency="TJS",
                           payment_method="visa", base_amount=250, payment_status="pending")
            self.assertIsNone(await repo.get_by_id(payment.id, actor=other))
            self.assertIsNone(await repo.get_by_id(payment.id, actor=None))
            self.assertFalse(await repo.update_screenshot(payment, "foreign", actor=other))
            self.assertFalse(await repo.update_checkout(payment, actor=other, **changes))
            self.assertFalse(await repo.approve(payment, actor=other))
            self.assertFalse(await repo.reject(payment, actor=None))
            self.assertTrue(await repo.update_screenshot(payment, "owner-receipt", actor=owner))
            self.assertTrue(await repo.approve(payment, actor=owner))
            self.assertFalse(await repo.reject(payment, actor=owner))
            self.assertFalse(await repo.approve(payment))
            self.assertFalse(await repo.update_screenshot(payment, "late-receipt", actor=owner))
            self.assertFalse(await repo.update_checkout(payment, actor=owner, **changes))
            await session.refresh(payment)
            self.assertEqual((payment.payment_status, payment.amount, payment.screenshot_file_id),
                             ("approved", 95, "owner-receipt"))
            self.assertEqual((await repo.get_by_id(payment.id)).id, payment.id)

    async def test_creation_leaves_commit_and_rollback_to_the_caller(self):
        async with self.sessions() as session:
            await PaymentRepository(session).create(await session.get(User, 1), "1_month", 95)
            await session.rollback()
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count(Payment.id))), 0)


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"), "requires isolated PostgreSQL test database")
class NativePaymentConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "native_payment_test_" + uuid4().hex
        self.admin = create_async_engine(os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"])
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"],
            connect_args={"server_settings": {"search_path": self.schema + ",public"}})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([User(id=1, telegram_id=None), User(id=2, telegram_id=None)])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def test_parallel_pending_checks_share_one_payment_per_canonical_user(self):
        async def submit(uid):
            async with self.sessions() as session:
                repo = PaymentRepository(session)
                user = await repo.resolve_owner(await session.get(User, uid), lock=True)
                payment = await repo.get_latest_pending_by_user(user)
                if payment is None:
                    payment = await repo.create(user, "1_month", 95)
                await session.commit()
                return uid, payment.id
        results = await asyncio.wait_for(asyncio.gather(*(submit(uid) for uid in (1, 1, 1, 1, 2, 2))), timeout=15)
        for uid in (1, 2):
            self.assertEqual(len({pid for owner, pid in results if owner == uid}), 1)
        self.assertEqual(len({pid for _, pid in results}), 2)
        async with self.sessions() as session:
            rows = list((await session.execute(select(Payment))).scalars())
            self.assertCountEqual([(p.user_id, p.user_telegram_id, p.payment_status) for p in rows],
                                  [(1, None, "pending"), (2, None, "pending")])

    async def test_create_waits_for_its_owner_lock_without_blocking_another_account(self):
        async def create(uid):
            async with self.sessions() as session:
                payment = await PaymentRepository(session).create(await session.get(User, uid), "1_month", 95)
                await session.commit()
                return payment.user_id
        async with self.sessions() as blocker:
            await PaymentRepository(blocker).resolve_owner(await blocker.get(User, 1), lock=True)
            waiting = asyncio.create_task(create(1))
            try:
                await asyncio.sleep(0.1)
                self.assertFalse(waiting.done(), "creation must wait for the canonical account lock")
                self.assertEqual(await asyncio.wait_for(create(2), timeout=5), 2)
            finally:
                await blocker.commit()
            self.assertEqual(await asyncio.wait_for(waiting, timeout=5), 1)
