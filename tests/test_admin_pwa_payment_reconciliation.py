"""Isolated reconciliation contract: human evidence never mutates payment or resends."""
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.admin_api.pwa_access_grants import CommandError
from app.admin_api.pwa_payment_reconciliation import (
    PrepareReconciliation, ReconciliationCommand, ExecuteReconciliation,
    prepare_reconciliation, execute_reconciliation,
    create_admin_pwa_payment_reconciliation_router,
)
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import begin_step_up, verify_step_up
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentOutbox
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.payment import Payment
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import make_assertion


class ReconciliationTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed_uncertain(self):
        payment = await self.command()
        signed = await self.receipt(payment, signed=True)
        result = await self.execute(payment, signed)
        review_id = result["review_id"]
        async with self.sessions() as db:
            outbox = await db.get(AdminPwaPaymentOutbox, review_id)
            outbox.status = "uncertain"
            outbox.attempted_at = datetime.now(timezone.utc)
            outbox.finished_at = datetime.now(timezone.utc)
            await db.commit()
        return review_id

    async def prepared(self, review_id, resolution="no_retry", reason="Verified external case"):
        async with self.sessions() as db:
            result = await prepare_reconciliation(db, session_cookie=fixtures.COOKIE,
                request=PrepareReconciliation(review_id=review_id, resolution=resolution, reason=reason),
                settings_obj=self.settings)
        return ReconciliationCommand.model_validate(result["operation"]["payload"])

    async def signed(self, command):
        async with self.sessions() as db:
            started = await begin_step_up(db, session_cookie=fixtures.COOKIE,
                settings_obj=self.settings, **command.operation())
        async with self.sessions() as db:
            step = await db.get(AdminPwaStepUp, started.step_up_id)
            challenge = bytes(step.challenge)
        # This fixture already signed the original financial approval.
        # The authenticator must increment its monotonic counter; replaying
        # count=1 here is intentionally rejected by production WebAuthn.
        async with self.sessions() as db:
            credential = (await db.execute(select(AdminPwaCredential))).scalar_one()
            next_count = credential.sign_count + 1
        async with self.sessions() as db:
            self.assertTrue(await verify_step_up(db, session_cookie=fixtures.COOKIE,
                step_up_id=started.step_up_id,
                credential=make_assertion(self.key, challenge=challenge,
                                         sign_count=next_count), settings_obj=self.settings))
        return started.step_up_id

    async def run_command(self, command, step_id):
        async with self.sessions() as db:
            return await execute_reconciliation(db, session_cookie=fixtures.COOKIE,
                request=ExecuteReconciliation(**command.model_dump(), step_up_id=step_id),
                settings_obj=self.settings)

    async def test_signed_operator_note_is_atomic_without_financial_change_or_resend(self):
        review_id = await self.seed_uncertain()
        command = await self.prepared(review_id, reason="Externally reviewed by operator")
        proof = await self.signed(command)
        result = await self.run_command(command, proof)
        self.assertEqual(result["delivery"]["resolution"], "no_retry")
        self.assertIsNotNone(result["delivery"]["reconciled_at"])
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "approved")
            self.assertEqual((await db.get(AdminPwaPaymentOutbox, review_id)).status, "uncertain")
            entries = (await db.execute(select(AdminPwaCommandAudit).where(
                AdminPwaCommandAudit.action == "payments.delivery_reconcile"))).scalars().all()
            self.assertEqual(len(entries), 1)
            self.assertNotIn("Externally reviewed by operator", entries[0].result_json)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "consumed")
        with self.assertRaises(CommandError) as denied:
            await self.run_command(command, proof)
        self.assertEqual(denied.exception.status, 403)
        with self.assertRaises(CommandError) as denied:
            await self.prepared(review_id)
        self.assertEqual(denied.exception.status, 409)

    async def test_changed_outbox_and_tampered_resolution_never_consume_proof(self):
        review_id = await self.seed_uncertain()
        command = await self.prepared(review_id)
        proof = await self.signed(command)
        with self.assertRaises(CommandError) as denied:
            await self.run_command(ReconciliationCommand(
                **{**command.model_dump(), "resolution": "observed"}), proof)
        self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            outbox = await db.get(AdminPwaPaymentOutbox, review_id)
            outbox.status = "attempted"
            await db.commit()
        with self.assertRaises(CommandError) as denied:
            await self.run_command(command, proof)
        self.assertEqual(denied.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_prepare_rejects_pending_and_http_guards_are_default_off(self):
        command = await self.command()
        result = await self.execute(command, await self.receipt(command, signed=True))
        with self.assertRaises(CommandError) as denied:
            await self.prepared(result["review_id"])
        self.assertEqual(denied.exception.status, 409)
        app = FastAPI()
        app.include_router(create_admin_pwa_payment_reconciliation_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),
            base_url="https://hskai.app", headers={"origin":"https://hskai.app"}) as client:
            payload = {"review_id":result["review_id"]}
            self.assertEqual((await client.post("/api/admin/v1/payment-deliveries/read",
                json=payload)).status_code, 401)
            client.cookies.set(ADMIN_PWA_COOKIE_NAME, fixtures.COOKIE)
            self.assertEqual((await client.post("/api/admin/v1/payment-deliveries/read",
                json=payload, headers={"origin":"https://foreign.invalid"})).status_code, 403)
            self.settings.ADMIN_PWA_ENABLED = False
            for endpoint in ("read", "prepare", "save"):
                self.assertEqual((await client.post("/api/admin/v1/payment-deliveries/"+endpoint,
                    json=payload)).status_code, 404)


if __name__ == "__main__":
    unittest.main()
