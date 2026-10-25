"""Atomic first-party HSK 3.0 settings and exact one-use WebAuthn confirmation."""
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import func, select

from app.admin_api.pwa_hsk30_settings import (
    Hsk30SettingsInput, Hsk30SettingsCommand, ExecuteHsk30Settings,
    CommandError, read_hsk30_settings, prepare_hsk30_settings, execute_hsk30_settings,
)
from app.admin_api.pwa_step_up import operation_digest
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.bot_setting import BotSetting
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID


class Hsk30SettingsTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self, **overrides):
        props={"enabled":True,"unlock_payment_enabled":False,
               "unlock_price_tjs":10,"live_levels":["nhsk1","nhsk2"]}
        props.update(overrides)
        async with self.sessions() as db:
            result=await prepare_hsk30_settings(db, session_cookie=fixtures.COOKIE,
                request=Hsk30SettingsInput(**props), settings_obj=self.settings)
        return Hsk30SettingsCommand.model_validate(result["operation"]["payload"])

    async def proof(self, command):
        stamp=datetime.now(timezone.utc)
        step_id=str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id, session_id=self.session_id, user_id=101,
                action="hsk30.settings", target="global",
                payload_hash=operation_digest(**command.operation()), challenge=b"H"*32,
                status="verified", credential_id=CRED_ID, verified_at=stamp,
                created_at=stamp, expires_at=stamp+timedelta(seconds=40)))
            await db.commit()
        return step_id

    async def run_command(self,command,proof):
        async with self.sessions() as db:
            return await execute_hsk30_settings(db, session_cookie=fixtures.COOKIE,
                request=ExecuteHsk30Settings(**command.model_dump(),step_up_id=proof),
                settings_obj=self.settings)

    async def test_change_uses_shared_feature_and_unlock_services_atomically(self):
        command=await self.prepare()
        proof=await self.proof(command)
        result=await self.run_command(command,proof)
        self.assertTrue(result["hsk30"]["enabled"])
        self.assertFalse(result["hsk30"]["unlock_payment_enabled"])
        self.assertEqual(result["hsk30"]["unlock_price_tjs"],10)
        self.assertEqual(result["hsk30"]["live_levels"],["nhsk1","nhsk2"])
        async with self.sessions() as db:
            audit=await db.get(AdminPwaCommandAudit,result["command_id"])
            self.assertEqual(audit.action,"hsk30.settings")
            self.assertEqual(audit.target,"global")
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,"consumed")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),1)
        with self.assertRaises(CommandError):
            await self.run_command(command,proof)

    async def test_exact_payload_tampering_and_stale_shared_setting_rejected(self):
        command=await self.prepare()
        proof=await self.proof(command)
        changed=Hsk30SettingsCommand(**{**command.model_dump(),"unlock_price_tjs":100})
        with self.assertRaises(CommandError) as blocked:
            await self.run_command(changed,proof)
        self.assertEqual(blocked.exception.status,403)
        async with self.sessions() as db:
            db.add(BotSetting(key="hsk30_unlock_price_tjs",value="40"))
            await db.commit()
        with self.assertRaises(CommandError) as stale:
            await self.run_command(command,proof)
        self.assertEqual(stale.exception.status,409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,"verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),0)

    async def test_strict_bounds_and_read_without_any_update(self):
        for changes in ({"unlock_price_tjs":0},{"enabled":1},{"live_levels":["nhsk4"]},
                        {"live_levels":["nhsk2","nhsk1"]},{"live_levels":["nhsk1","nhsk1"]}):
            with self.assertRaises(ValidationError):
                Hsk30SettingsInput(**{**dict(enabled=True,unlock_payment_enabled=True,
                    unlock_price_tjs=10,live_levels=[]),**changes})
        async with self.sessions() as db:
            result=await read_hsk30_settings(db,session_cookie=fixtures.COOKIE,settings_obj=self.settings)
        self.assertIn("nhsk1",result["hsk30"]["available_levels"])
        self.assertFalse(result["hsk30"]["enabled"])
        self.assertEqual(result["hsk30"]["unlock_price_tjs"],10)
        self.assertTrue(result["hsk30"]["unlock_payment_enabled"])
