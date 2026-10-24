"""Real setting-key contention, including absent rows and proof expiry.

Opt in only with a disposable ADMIN_PWA_TEST_DATABASE_URL. Every test owns a
random schema; no public learner/admin data is read, modified or deleted.
"""
import asyncio
import hashlib
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api import pwa_course_access as course
from app.admin_api import pwa_subscription_prices as prices
from app.db.base import Base
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.bot_setting import BotSetting
from app.db.models.subscription_price import SubscriptionPrice
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_access_policy_service import (
    COURSE_ACCESS_POLICY_KEY, CourseAccessPolicyService,
)
from app.services.subscription_price_service import SubscriptionPriceService
from tests import test_admin_pwa_course_access as course_fixtures
from tests import test_admin_pwa_payment_review as payment_fixtures


@unittest.skipUnless(os.environ.get("ADMIN_PWA_TEST_DATABASE_URL"),
                     "requires isolated ADMIN_PWA_TEST_DATABASE_URL (never production)")
class AdminPwaSettingsPostgresTests(payment_fixtures.PaymentFixtures,
                                    unittest.IsolatedAsyncioTestCase):
    prepare = course_fixtures.CoursePolicyTests.prepare
    proof = course_fixtures.CoursePolicyTests.proof
    execute = course_fixtures.CoursePolicyTests.execute

    async def asyncSetUp(self):
        self.schema = "adminpwa_settings_" + uuid4().hex
        url = os.environ["ADMIN_PWA_TEST_DATABASE_URL"]
        self.admin_engine = create_async_engine(url)
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(url, connect_args={"server_settings": {
            "search_path": self.schema + ",public", "statement_timeout": "15000",
            "lock_timeout": "10000",
        }})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        await self.seed_payment()

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin_engine.dispose()

    async def _second_admin(self, command):
        now = datetime.now(timezone.utc)
        cookie = "T" * 64
        step_id, session_id = str(uuid4()), str(uuid4())
        self.settings.admin_id_list.append(9002)
        async with self.sessions() as db:
            db.add(User(id=202, telegram_id=9002, status="active"))
            await db.flush()
            db.add(AdminPwaSession(id=session_id, user_id=202,
                token_hash=hashlib.sha256(cookie.encode()).hexdigest(), auth_method="webauthn",
                created_at=now, expires_at=now + timedelta(hours=1)))
            db.add(AdminPwaCredential(id=str(uuid4()), user_id=202,
                credential_id=b"second-setting-admin", public_key=b"verified-fixture-key",
                user_handle=b"second-setting-admin-handle", sign_count=0,
                device_type="single_device", backed_up=False, created_at=now))
            await db.flush()
            db.add(AdminPwaStepUp(id=step_id, session_id=session_id, user_id=202,
                action="course.access_policy", target="global",
                payload_hash=course.operation_digest(**command.operation()), challenge=b"Q" * 32,
                status="verified", credential_id=b"second-setting-admin", verified_at=now,
                created_at=now, expires_at=now + timedelta(seconds=50)))
            await db.commit()

        async def execute():
            async with self.sessions() as db:
                return await course.execute_course_policy(db, session_cookie=cookie,
                    request=course.ExecuteCoursePolicy(**command.model_dump(), step_up_id=step_id),
                    settings_obj=self.settings)
        return execute, step_id

    async def test_two_admins_cannot_overwrite_the_same_absent_setting_snapshot(self):
        command = await self.prepare()
        first_proof = await self.proof(command)
        second_execute, second_proof = await self._second_admin(command)
        saving, release, second_waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_save = CourseAccessPolicyService.save_policy
        original_lock = BotSettingRepository.lock_key

        async def hold_first_save(service, **kwargs):
            saving.set()
            await asyncio.wait_for(release.wait(), 5)
            return await original_save(service, **kwargs)

        async def observe_key_wait(repo, key):
            if asyncio.current_task().get_name() == "second-setting-command":
                second_waiting.set()
            return await original_lock(repo, key)

        tasks = []
        try:
            with patch.object(CourseAccessPolicyService, "save_policy", hold_first_save), \
                 patch.object(BotSettingRepository, "lock_key", observe_key_wait):
                first = asyncio.create_task(self.execute(command, first_proof))
                tasks.append(first)
                await asyncio.wait_for(saving.wait(), 5)
                second = asyncio.create_task(second_execute(), name="second-setting-command")
                tasks.append(second)
                await asyncio.wait_for(second_waiting.wait(), 5)
                self.assertFalse(second.done())
                release.set()
                result = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 10)
            self.assertIsInstance(result[0], dict)
            self.assertIsInstance(result[1], course.CommandError)
            self.assertEqual(str(result[1]), "confirmation_changed")
            self.assertEqual(result[1].status, 409)
            async with self.sessions() as db:
                self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 1)
                self.assertEqual((await db.get(AdminPwaStepUp, first_proof)).status, "consumed")
                self.assertEqual((await db.get(AdminPwaStepUp, second_proof)).status, "verified")
        finally:
            release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def test_shared_service_writer_serializes_with_absent_pwa_setting(self):
        command = await self.prepare()
        proof = await self.proof(command)
        waiting = asyncio.Event()
        original_lock = BotSettingRepository.lock_key

        async def observe_lock(repo, key):
            if asyncio.current_task().get_name() == "waiting-pwa-command":
                waiting.set()
            return await original_lock(repo, key)

        task = None
        try:
            async with self.sessions() as legacy:
                async with legacy.begin():
                    # The real shared service, also called by Telegram admin,
                    # creates an uncommitted first row and owns its key lock.
                    policy = await CourseAccessPolicyService(legacy).save_policy(
                        mode="free_until", duration_days=2, updated_by_telegram_id=9001)
                    with patch.object(BotSettingRepository, "lock_key", observe_lock):
                        task = asyncio.create_task(self.execute(command, proof), name="waiting-pwa-command")
                        await asyncio.wait_for(waiting.wait(), 5)
                        self.assertFalse(task.done())
                with self.assertRaisesRegex(course.CommandError, "confirmation_changed"):
                    await asyncio.wait_for(task, 10)
            async with self.sessions() as db:
                self.assertEqual((await CourseAccessPolicyService(db).get_policy()).free_until, policy.free_until)
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
                self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)
        finally:
            if task is not None:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_setting_lock_wait_cannot_outlive_the_verified_proof(self):
        command = await self.prepare()
        proof = await self.proof(command)
        waiting = asyncio.Event()
        original_lock = BotSettingRepository.lock_key
        future = datetime.now(timezone.utc) + timedelta(minutes=2)

        class AfterWaitDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return future.astimezone(tz) if tz else future.replace(tzinfo=None)

        async def observe_lock(repo, key):
            if asyncio.current_task().get_name() == "expiring-pwa-command":
                waiting.set()
            return await original_lock(repo, key)

        task = None
        final_clock = patch.object(course, "datetime", AfterWaitDateTime)
        try:
            async with self.sessions() as blocker:
                async with blocker.begin():
                    await BotSettingRepository(blocker).lock_key(COURSE_ACCESS_POLICY_KEY)
                    with patch.object(BotSettingRepository, "lock_key", observe_lock):
                        task = asyncio.create_task(self.execute(command, proof), name="expiring-pwa-command")
                        await asyncio.wait_for(waiting.wait(), 5)
                        self.assertFalse(task.done())
                        final_clock.start()
                # Move only the command's final authorization clock. The
                # shared proof consumer already verified a currently valid
                # proof before waiting for the actual PostgreSQL key lock.
                with self.assertRaisesRegex(course.CommandError, "step_up_denied") as caught:
                    await asyncio.wait_for(task, 10)
                self.assertEqual(caught.exception.status, 403)
            async with self.sessions() as db:
                self.assertIsNone(await db.get(BotSetting, COURSE_ACCESS_POLICY_KEY))
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
                self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)
        finally:
            final_clock.stop()
            if task is not None:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_first_price_insert_waits_for_legacy_writer_and_rejects_old_snapshot(self):
        async with self.sessions() as db:
            prepared = await prices.prepare_subscription_price(db,
                session_cookie=payment_fixtures.COOKIE, settings_obj=self.settings,
                request=prices.PrepareSubscriptionPrice(method="visa", plan="1_month", amount=120))
        command = prices.SubscriptionPriceCommand.model_validate(prepared["operation"]["payload"])
        now, proof = datetime.now(timezone.utc), str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=proof, session_id=self.session_id, user_id=101,
                action="subscription.prices", target=command.operation()["target"],
                payload_hash=course.operation_digest(**command.operation()), challenge=b"V" * 32,
                status="verified", credential_id=course_fixtures.CRED_ID, verified_at=now,
                created_at=now, expires_at=now + timedelta(seconds=50)))
            await db.commit()
        waiting = asyncio.Event()
        original_lock = BotSettingRepository.lock_key

        async def observe_lock(repo, key):
            if asyncio.current_task().get_name() == "waiting-price-command":
                waiting.set()
            return await original_lock(repo, key)

        async def execute():
            async with self.sessions() as db:
                return await prices.execute_subscription_price(db,
                    session_cookie=payment_fixtures.COOKIE, settings_obj=self.settings,
                    request=prices.ExecuteSubscriptionPrice(**command.model_dump(), step_up_id=proof))

        task = None
        try:
            async with self.sessions() as legacy:
                async with legacy.begin():
                    # No price existed at prepare time. The canonical legacy
                    # writer now inserts its first row and keeps it uncommitted.
                    await SubscriptionPriceService(legacy).set_price(
                        payment_method="visa", plan_type="1_month", amount=130,
                        updated_by_telegram_id=9001)
                    with patch.object(BotSettingRepository, "lock_key", observe_lock):
                        task = asyncio.create_task(execute(), name="waiting-price-command")
                        await asyncio.wait_for(waiting.wait(), 5)
                        self.assertFalse(task.done())
                with self.assertRaisesRegex(prices.CommandError, "confirmation_changed") as caught:
                    await asyncio.wait_for(task, 10)
                self.assertEqual(caught.exception.status, 409)
            async with self.sessions() as db:
                price = await db.scalar(select(SubscriptionPrice))
                self.assertEqual((price.amount, price.currency), (130, "TJS"))
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
                self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)
        finally:
            if task is not None:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
