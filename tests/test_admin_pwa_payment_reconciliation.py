"""Isolated reconciliation contract: human evidence never mutates payment or resends."""
import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from app.admin_api import pwa_payment_reconciliation as api

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
from tests import test_admin_pwa_settings_postgres as pg
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

    async def test_audit_failure_rolls_back_reconciliation_marker_and_proof(self):
        review_id=await self.seed_uncertain();command=await self.prepared(review_id);proof=await self.signed(command)
        def fail_audit(mapper,connection,row):
            if row.action==api.ACTION:raise RuntimeError('synthetic audit failure')
        event.listen(AdminPwaCommandAudit,'before_insert',fail_audit)
        try:
            with self.assertRaises(RuntimeError):await self.run_command(command,proof)
        finally:event.remove(AdminPwaCommandAudit,'before_insert',fail_audit)
        async with self.sessions() as db:
            self.assertIsNone((await db.get(AdminPwaPaymentOutbox,review_id)).reconciled_at)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')
            self.assertEqual((await db.get(Payment,self.payment_id)).payment_status,'approved')

    async def test_current_attempt_cannot_be_closed_before_the_stale_attempt_boundary(self):
        review_id=await self.seed_uncertain()
        async with self.sessions() as db:
            row=await db.get(AdminPwaPaymentOutbox,review_id);row.status='attempting'
            await db.commit()
        with self.assertRaises(CommandError):await self.prepared(review_id)
        async with self.sessions() as db:
            (await db.get(AdminPwaPaymentOutbox,review_id)).attempted_at=datetime.now(timezone.utc)-timedelta(minutes=11)
            await db.commit()
        self.assertEqual((await self.prepared(review_id)).review_id,review_id)

    async def test_queue_uses_two_bounded_index_pages_without_private_payloads_or_writes(self):
        from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview
        async with self.sessions() as db:
            for i in range(35):
                review_id=str(uuid4())
                db.add(AdminPwaPaymentReview(id=review_id,step_up_id=str(uuid4()),payment_id=10000+i,
                    actor_user_id=101,target_user_id=1,action='payments.review',decision='approve',
                    payload_hash='0'*64,payload_json='PRIVATE payload',status='applied'))
                await db.flush()
                db.add(AdminPwaPaymentOutbox(review_id=review_id,status='uncertain' if i%2 else 'attempting',
                    attempted_at=datetime.now(timezone.utc),effects_json='PRIVATE effects'))
            await db.commit()
        statements=[]
        def collect(conn,cursor,statement,params,context,many):statements.append(statement.lower())
        event.listen(self.engine.sync_engine,'before_cursor_execute',collect)
        try:
            async with self.sessions() as db:
                first=await api.read_reconciliation(db,session_cookie=fixtures.COOKIE,
                    request=api.ReconciliationRead(),settings_obj=self.settings)
            async with self.sessions() as db:
                second=await api.read_reconciliation(db,session_cookie=fixtures.COOKIE,
                    request=api.ReconciliationRead(before_id=first['next_before_id']),settings_obj=self.settings)
        finally:event.remove(self.engine.sync_engine,'before_cursor_execute',collect)
        self.assertEqual((len(first['items']),len(second['items'])),(30,5))
        self.assertFalse({r['review_id'] for r in first['items']} & {r['review_id'] for r in second['items']})
        self.assertNotIn('PRIVATE',str(first))
        self.assertFalse(any('effects_json' in q or 'payload_json' in q or 'count(' in q
            or q.lstrip().startswith(('insert ','update ','delete ')) for q in statements))


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class ReconciliationPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    seed_uncertain=ReconciliationTests.seed_uncertain
    prepared=ReconciliationTests.prepared
    signed=ReconciliationTests.signed
    run_command=ReconciliationTests.run_command

    async def test_two_distinct_proofs_cannot_record_two_operator_resolutions(self):
        review_id=await self.seed_uncertain();command=await self.prepared(review_id)
        proofs=[await self.signed(command),await self.signed(command)]
        result=await asyncio.gather(*(self.run_command(command,proof) for proof in proofs),return_exceptions=True)
        self.assertEqual(sum(isinstance(r,dict) for r in result),1)
        self.assertEqual(next(r for r in result if isinstance(r,CommandError)).status,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)
                .where(AdminPwaCommandAudit.action==api.ACTION)),1)

    async def test_actual_migration_refuses_erasing_nonempty_reconciliation_metadata(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        review_id=await self.seed_uncertain();command=await self.prepared(review_id)
        await self.run_command(command,await self.signed(command))
        path=Path(__file__).resolve().parents[1]/'alembic/versions/0128_admin_pwa_command_lookup.py'
        spec=importlib.util.spec_from_file_location('pwa_reconcile_migration',path)
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        async with self.engine.begin() as connection:
            def downgrade(sync):
                with Operations.context(MigrationContext.configure(sync)):migration.downgrade()
            with self.assertRaisesRegex(RuntimeError,'Archive operator reconciliation'):
                await connection.run_sync(downgrade)
        async with self.sessions() as db:
            self.assertIsNotNone((await db.get(AdminPwaPaymentOutbox,review_id)).reconciled_at)


if __name__ == "__main__":
    unittest.main()
