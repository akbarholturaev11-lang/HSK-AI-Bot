"""Admin PWA course access policy: atomic, confirmed, auditable, no broadcast."""
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import func, select

from app.admin_api.pwa_course_access import (
    CoursePolicyInput, CoursePolicyCommand, ExecuteCoursePolicy,
    CommandError, prepare_course_policy, execute_course_policy, read_course_policy,
)
from app.admin_api.pwa_step_up import operation_digest
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.bot_setting import BotSetting
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID


class CoursePolicyTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self, mode="subscription", free_until=None):
        async with self.sessions() as db:
            data = await prepare_course_policy(
                db, session_cookie=fixtures.COOKIE,
                request=CoursePolicyInput(mode=mode, free_until=free_until),
                settings_obj=self.settings)
        return CoursePolicyCommand.model_validate(data["operation"]["payload"])

    async def proof(self, command):
        now = datetime.now(timezone.utc)
        step_id = str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id, session_id=self.session_id, user_id=101,
                action="course.access_policy", target="global",
                payload_hash=operation_digest(**command.operation()), challenge=b"P"*32,
                status="verified", credential_id=CRED_ID, verified_at=now,
                created_at=now, expires_at=now+timedelta(seconds=50)))
            await db.commit()
        return step_id

    async def execute(self, command, proof):
        async with self.sessions() as db:
            return await execute_course_policy(
                db, session_cookie=fixtures.COOKIE,
                request=ExecuteCoursePolicy(**command.model_dump(),step_up_id=proof),
                settings_obj=self.settings)

    async def test_explicit_global_policy_change_consumes_exact_proof_and_audits(self):
        date = (datetime.now(timezone.utc)+timedelta(days=3)).replace(microsecond=0).isoformat()
        command = await self.prepare("free_until", date)
        proof = await self.proof(command)
        result = await self.execute(command, proof)
        self.assertEqual(result["course_access"]["mode"], "free_until")
        self.assertTrue(result["course_access"]["free_active"])
        async with self.sessions() as db:
            row=await db.get(BotSetting, "course_lesson_access_policy")
            self.assertIsNotNone(row)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,"consumed")
            audit=await db.get(AdminPwaCommandAudit,result["command_id"])
            self.assertEqual(audit.action,"course.access_policy")
            self.assertEqual(audit.target,"global")
            self.assertEqual(audit.target_user_id,None)
        with self.assertRaises(CommandError):
            await self.execute(command,proof)

    async def test_cross_command_tamper_and_stale_policy_block_without_write(self):
        command=await self.prepare()
        proof=await self.proof(command)
        changed=CoursePolicyCommand(mode="subscription",free_until=None,
                                    expected_hash="f"*64)
        with self.assertRaises(CommandError):
            await self.execute(changed,proof)
        async with self.sessions() as db:
            db.add(BotSetting(key="course_lesson_access_policy", value='{"mode":"free_until"}'))
            await db.commit()
        with self.assertRaises(CommandError) as ctx:
            await self.execute(command,proof)
        self.assertEqual(ctx.exception.status,409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,"verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)),0)

    async def test_read_is_private_and_does_not_issue_or_consume_proof(self):
        async with self.sessions() as db:
            result=await read_course_policy(db,session_cookie=fixtures.COOKIE,
                                             settings_obj=self.settings)
        self.assertEqual(result["course_access"]["mode"],"subscription")
        self.assertEqual(len(result["revision_hash"]),64)
        self.settings.ADMIN_PWA_ENABLED=False
        with self.assertRaises(CommandError):
            await self.prepare()
        self.settings.ADMIN_PWA_ENABLED=True

    async def test_policy_rejects_old_or_ambiguous_expiry_and_legacy_ads(self):
        with self.assertRaises(ValidationError):
            CoursePolicyInput(mode="ads")
        with self.assertRaises(ValidationError):
            CoursePolicyInput(mode="free_until",free_until="2026-10-25T10:00:00")
        with self.assertRaises(ValidationError):
            CoursePolicyInput(mode="subscription",free_until="2030-01-01T00:00:00Z")
        with self.assertRaises(ValidationError):
            CoursePolicyInput(mode="free_until",
                free_until=(datetime.now(timezone.utc)+timedelta(days=366)).isoformat())
