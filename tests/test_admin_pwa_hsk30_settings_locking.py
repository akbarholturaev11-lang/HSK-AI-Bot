"""HSK30 settings protect absent rows, raw timestamps and strict read inputs."""
import asyncio
import hashlib
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.admin_api import pwa_hsk30_settings as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.bot_setting import BotSetting
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.hsk30_feature_service import Hsk30FeatureService
from tests import test_admin_pwa_hsk30_settings as hsk_fixtures
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings_postgres as pg_fixtures


class Hsk30SettingLockTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    prepare = hsk_fixtures.Hsk30SettingsTests.prepare
    proof = hsk_fixtures.Hsk30SettingsTests.proof
    run_command = hsk_fixtures.Hsk30SettingsTests.run_command

    async def test_first_write_prelocks_all_four_keys_in_sorted_order_without_creating_rows(self):
        locked = []
        original = BotSettingRepository.lock_key
        async def capture(repo, key):
            locked.append(key)
            await original(repo, key)
        with patch.object(BotSettingRepository, "lock_key", capture):
            async with self.sessions() as db:
                async with db.begin():
                    digest = await api._snapshot(db, lock=True)
        self.assertEqual(locked, sorted(api._KEYS))
        self.assertEqual(len(digest), 64)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 0)

    async def test_identical_value_with_changed_timestamp_rejects_stale_confirmation(self):
        async with self.sessions() as db:
            db.add(BotSetting(key="hsk30_unlock_price_tjs", value="10"))
            await db.commit()
        command = await self.prepare()
        step_id = await self.proof(command)
        async with self.sessions() as db:
            row = await db.get(BotSetting, "hsk30_unlock_price_tjs")
            row.updated_at = datetime.now(timezone.utc)+timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(api.CommandError) as stale:
            await self.run_command(command, step_id)
        self.assertEqual(stale.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, step_id)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_read_requires_a_bounded_empty_object_and_does_not_write(self):
        app = FastAPI()
        app.include_router(api.create_admin_pwa_hsk30_settings_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
                headers={"origin":"https://hskai.app"}, cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            for body in ({"enabled":True}, {"arbitrary":"sql"}, []):
                self.assertEqual((await client.post("/api/admin/v1/hsk30/read", json=body)).status_code, 400)
            self.assertEqual((await client.post("/api/admin/v1/hsk30/read", content="{invalid",
                headers={"content-type":"application/json"})).status_code, 400)
            self.assertEqual((await client.post("/api/admin/v1/hsk30/read", content=" "*4097,
                headers={"content-type":"application/json"})).status_code, 400)
            response = await client.post("/api/admin/v1/hsk30/read", json={})
            self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)), 0)


@unittest.skipUnless(os.environ.get("ADMIN_PWA_TEST_DATABASE_URL"),
    "requires isolated ADMIN_PWA_TEST_DATABASE_URL (never production)")
class Hsk30SettingPostgresLockTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg_fixtures.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg_fixtures.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare = hsk_fixtures.Hsk30SettingsTests.prepare
    proof = hsk_fixtures.Hsk30SettingsTests.proof
    run_command = hsk_fixtures.Hsk30SettingsTests.run_command

    async def test_legacy_enable_decides_transition_after_concurrent_disable_commits(self):
        async with self.sessions() as db:
            await BotSettingRepository(db).set_bool('hsk30_enabled',True)
            await db.commit()
        waiting=asyncio.Event();task=None
        original_lock=BotSettingRepository.lock_key
        async def observe(repo,key):
            if asyncio.current_task().get_name()=='legacy-hsk-enable':
                waiting.set()
            await original_lock(repo,key)
        async def enable():
            async with self.sessions() as db:
                async with db.begin():
                    service=Hsk30FeatureService(db)
                    previous=await service.setting_repo.get_record('hsk30_enabled')
                    self.assertEqual(previous.value,'1')
                    await service.set_enabled(True)
                    return previous.value  # Keep the old identity-map row alive.
        try:
            async with self.sessions() as writer:
                async with writer.begin():
                    await BotSettingRepository(writer).set_bool('hsk30_enabled',False)
                    with patch.object(BotSettingRepository,'lock_key',observe):
                        task=asyncio.create_task(enable(),name='legacy-hsk-enable')
                        await asyncio.wait_for(waiting.wait(),5)
                        self.assertFalse(task.done())
            await asyncio.wait_for(task,5)
            async with self.sessions() as db:
                self.assertTrue(await Hsk30FeatureService(db).is_enabled())
        finally:
            if task is not None and not task.done():
                task.cancel();await asyncio.gather(task,return_exceptions=True)

    async def test_two_admins_cannot_overwrite_the_same_absent_hsk_settings(self):
        command = await self.prepare()
        first_proof = await self.proof(command)
        cookie, second_proof, session_id = "T"*64, str(uuid4()), str(uuid4())
        now = datetime.now(timezone.utc)
        self.settings.admin_id_list.append(9002)
        async with self.sessions() as db:
            db.add(User(id=202, telegram_id=9002, status="active"))
            await db.flush()
            db.add(AdminPwaSession(id=session_id, user_id=202,
                token_hash=hashlib.sha256(cookie.encode()).hexdigest(), auth_method="webauthn",
                created_at=now, expires_at=now+timedelta(hours=1)))
            db.add(AdminPwaCredential(id=str(uuid4()), user_id=202, credential_id=b"second-hsk-admin",
                public_key=b"verified-fixture-key", user_handle=b"second-hsk-handle", sign_count=0,
                device_type="single_device", backed_up=False, created_at=now))
            await db.flush()
            db.add(AdminPwaStepUp(id=second_proof, session_id=session_id, user_id=202,
                action="hsk30.settings", target="global", payload_hash=api.operation_digest(**command.operation()),
                challenge=b"Q"*32, status="verified", credential_id=b"second-hsk-admin",
                verified_at=now, created_at=now, expires_at=now+timedelta(seconds=50)))
            await db.commit()
        async def second_execute():
            async with self.sessions() as db:
                return await api.execute_hsk30_settings(db, session_cookie=cookie,
                    request=api.ExecuteHsk30Settings(**command.model_dump(), step_up_id=second_proof),
                    settings_obj=self.settings)
        saving, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_save, original_lock = Hsk30FeatureService.set_enabled, BotSettingRepository.lock_key
        async def hold_save(service, enabled):
            saving.set()
            await asyncio.wait_for(release.wait(), 5)
            return await original_save(service, enabled)
        async def observe_lock(repo, key):
            if asyncio.current_task().get_name() == "second-hsk-setting-command":
                waiting.set()
            return await original_lock(repo, key)
        tasks = []
        try:
            with patch.object(Hsk30FeatureService, "set_enabled", hold_save), \
                 patch.object(BotSettingRepository, "lock_key", observe_lock):
                first = asyncio.create_task(self.run_command(command, first_proof))
                tasks.append(first)
                await asyncio.wait_for(saving.wait(), 5)
                second = asyncio.create_task(second_execute(), name="second-hsk-setting-command")
                tasks.append(second)
                await asyncio.wait_for(waiting.wait(), 5)
                self.assertFalse(second.done())
                release.set()
                results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 10)
            self.assertIsInstance(results[0], dict)
            self.assertIsInstance(results[1], api.CommandError)
            self.assertEqual(str(results[1]), "confirmation_changed")
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
