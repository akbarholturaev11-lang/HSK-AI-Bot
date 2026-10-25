"""PWA limits: numeric windows, exact passkey proof, CAS and trial integrity."""
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select

from app.admin_api.pwa_limits import (
    CommandError, LimitsUpdateInput, LimitsCommand, ExecuteLimits,
    read_limits, prepare_limits, save_limits,
)
from app.admin_api.pwa_step_up import operation_digest
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.services.entitlements.limits_config import ENTITLEMENT_LIMITS_KEY, LimitConfigService
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID


class PwaLimitsTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self, **changes):
        async with self.sessions() as db:
            result = await prepare_limits(db, session_cookie=fixtures.COOKIE,
                request=LimitsUpdateInput(**changes), settings_obj=self.settings)
        return LimitsCommand.model_validate(result["operation"]["payload"])

    async def proof(self, command):
        stamp = datetime.now(timezone.utc)
        step_id = str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id, session_id=self.session_id, user_id=101,
                action="limits.update", target="global",
                payload_hash=operation_digest(**command.operation()),
                challenge=b"L"*32, status="verified", credential_id=CRED_ID,
                verified_at=stamp, created_at=stamp,
                expires_at=stamp+timedelta(seconds=40)))
            await db.commit()
        return step_id

    async def execute(self, command, step_id):
        async with self.sessions() as db:
            return await save_limits(db, session_cookie=fixtures.COOKIE,
                request=ExecuteLimits(**command.model_dump(), step_up_id=step_id),
                settings_obj=self.settings)

    async def defaults(self):
        async with self.sessions() as db:
            return await read_limits(db, session_cookie=fixtures.COOKIE,
                settings_obj=self.settings)

    async def test_update_only_one_plan_and_preserve_trial_and_other_plans(self):
        before = (await self.defaults())["limits"]
        rules = dict(before["plans"]["FREE"])
        rules["ai.text"] = {"limit": 6, "window": "lifetime"}
        command = await self.prepare(plan="FREE", rules=rules)
        step_id = await self.proof(command)
        result = await self.execute(command, step_id)
        self.assertEqual(result["limits"]["plans"]["FREE"]["ai.text"],
                         {"limit": 6, "window": "lifetime"})
        self.assertEqual(result["limits"]["plans"]["TRIAL_ACTIVE"],
                         before["plans"]["TRIAL_ACTIVE"])
        self.assertEqual(result["limits"]["trial"]["ai_budget_usd"],
                         before["trial"]["ai_budget_usd"])
        async with self.sessions() as db:
            saved = await LimitConfigService(db).get_payload()
            self.assertEqual(saved["plans"]["FREE"]["ai.text"]["window"], "lifetime")
            self.assertEqual((await db.get(AdminPwaCommandAudit, result["command_id"])).action,
                             "limits.update")
            self.assertEqual((await db.get(AdminPwaStepUp,step_id)).status,"consumed")
        with self.assertRaises(CommandError):
            await self.execute(command,step_id)

    async def test_reject_changed_payload_and_stale_revision(self):
        before = (await self.defaults())["limits"]
        command = await self.prepare(plan="FREE",rules=before["plans"]["FREE"])
        proof = await self.proof(command)
        tampered = LimitsCommand(**{**command.model_dump(),
            "rules":{**command.rules, "ai.text":{"limit":99,"window":"daily"}}})
        with self.assertRaises(CommandError) as failure:
            await self.execute(tampered, proof)
        self.assertEqual(failure.exception.status,403)
        async with self.sessions() as db:
            db.add(BotSetting(key=ENTITLEMENT_LIMITS_KEY,value='{"other":"admin update"}'))
            await db.commit()
        with self.assertRaises(CommandError) as changed:
            await self.execute(command,proof)
        self.assertEqual(changed.exception.status,409)

    async def test_trial_settings_reuse_same_protected_path(self):
        previous = (await self.defaults())["limits"]
        command = await self.prepare(trial={"enabled":False,"days":5,"disabled_reason":"Scheduled"})
        result = await self.execute(command, await self.proof(command))
        self.assertFalse(result["limits"]["trial"]["enabled"])
        self.assertEqual(result["limits"]["trial"]["days"],5)
        self.assertEqual(result["limits"]["plans"]["FREE"],previous["plans"]["FREE"])

    async def test_only_daily_or_lifetime_are_accepted(self):
        before = (await self.defaults())["limits"]
        rules = dict(before["plans"]["FREE"])
        for rule in ({"limit":1,"window":"none"},{"limit":-1,"window":"daily"},
                     {"limit":10001,"window":"lifetime"},{"limit":"4","window":"daily"}):
            with self.subTest(rule=rule),self.assertRaises(ValidationError):
                LimitsUpdateInput(plan="FREE",rules={**rules,"ai.text":rule})
        for props in ({"plan":"FREE","rules":{}},{"trial":{"enabled":True,"days":100}},
                      {"plan":"FREE","rules":rules,"trial":{"enabled":True,"days":7}}):
            with self.subTest(props=props),self.assertRaises(ValidationError):
                LimitsUpdateInput(**props)
        with self.assertRaises(CommandError) as missing:
            await self.prepare(plan="FREE", rules={"ai.text":{"limit":5,"window":"daily"}})
        self.assertEqual(missing.exception.status,400)
