"""Manual access preserves paid terms, preview/budget rules and atomic proof/audit."""
import base64
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api.pwa_access_grants import (
    AccessGrantCommand, CommandError, ExecuteAccessGrant, PrepareAccessGrant,
    create_admin_pwa_access_grant_router, execute_access_grant, prepare_access_grant,
)
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import begin_step_up, operation_digest, verify_step_up
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, make_assertion


class AccessGrantFixtures:
    async def grant_command(self, days=30, user_id=1):
        async with self.sessions() as db:
            result = await prepare_access_grant(db, session_cookie=fixtures.COOKIE,
                request=PrepareAccessGrant(user_id=user_id, duration_days=days), settings_obj=self.settings)
        return AccessGrantCommand.model_validate(result["payload"])

    async def grant_proof(self, command, *, signed=False):
        now = datetime.now(timezone.utc)
        if signed:
            async with self.sessions() as db:
                started = await begin_step_up(db, session_cookie=fixtures.COOKIE,
                    settings_obj=self.settings, **command.operation())
            challenge = started.options["challenge"]
            challenge = base64.urlsafe_b64decode(challenge + "=" * (-len(challenge) % 4))
            async with self.sessions() as db:
                self.assertTrue(await verify_step_up(db, session_cookie=fixtures.COOKIE,
                    step_up_id=started.step_up_id, credential=make_assertion(self.key, challenge=challenge), settings_obj=self.settings))
            return started.step_up_id
        step_id = str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id, session_id=self.session_id, user_id=101,
                action="users.grant_access", target=str(command.user_id),
                payload_hash=operation_digest(**command.operation()), challenge=b"G"*32,
                status="verified", credential_id=CRED_ID, verified_at=now,
                created_at=now, expires_at=now+timedelta(seconds=50)))
            await db.commit()
        return step_id

    async def grant_execute(self, command, proof, **changes):
        async with self.sessions() as db:
            return await execute_access_grant(db, session_cookie=fixtures.COOKIE,
                request=ExecuteAccessGrant(**{**command.model_dump(), **changes}, step_up_id=proof), settings_obj=self.settings)


class AccessGrantTests(AccessGrantFixtures, fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def test_real_signature_grants_canonical_native_user_once_without_financial_side_effects(self):
        command = await self.grant_command()
        proof = await self.grant_proof(command, signed=True)
        now = datetime.now(timezone.utc)
        result = await self.grant_execute(command, proof)
        self.assertFalse(result["extended"])
        async with self.sessions() as db:
            user = await db.get(User, 1)
            self.assertIsNone(user.telegram_id)
            self.assertEqual(user.payment_status, "approved")
            self.assertAlmostEqual((user.end_date.replace(tzinfo=timezone.utc)-now).total_seconds(), 30*86400, delta=2)
            self.assertEqual(user.payment_preview_available, command.expected.payment_preview_available)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Payment)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AIUsageBudget)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)), 0)
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
            self.assertEqual(audit.actor_user_id, 101)
            self.assertEqual(audit.target_user_id, 1)
            self.assertEqual(audit.payload_hash, operation_digest(**command.operation()))
            self.assertEqual(json.loads(audit.result_json)["duration_days"], 30)
        with self.assertRaises(CommandError) as denied:
            await self.grant_execute(command, proof)
        self.assertEqual(denied.exception.status, 403)

    async def test_existing_paid_term_is_extended_and_spent_preview_is_not_replenished(self):
        end = datetime.now(timezone.utc)+timedelta(days=7)
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.status = "active";user.payment_status = "approved";user.end_date = end
            user.payment_preview_available = False
            await db.commit()
        command = await self.grant_command(10)
        result = await self.grant_execute(command, await self.grant_proof(command))
        self.assertTrue(result["extended"])
        self.assertEqual(datetime.fromisoformat(result["after"]["end_date"]), end+timedelta(days=10))
        self.assertFalse(result["after"]["payment_preview_available"])

    async def test_target_days_and_expected_snapshot_tampering_deny_without_consumption(self):
        command = await self.grant_command()
        proof = await self.grant_proof(command)
        for changes in ({"user_id": 2}, {"duration_days": 31},
                        {"expected": {**command.expected.model_dump(), "status": "active"}}):
            with self.assertRaises(CommandError) as denied:
                await self.grant_execute(command, proof, **changes)
            self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_concurrent_state_change_and_blocked_target_require_new_confirmation(self):
        command = await self.grant_command()
        proof = await self.grant_proof(command)
        async with self.sessions() as db:
            (await db.get(User, 1)).payment_status = "rejected"
            await db.commit()
        with self.assertRaises(CommandError) as denied:
            await self.grant_execute(command, proof)
        self.assertEqual(denied.exception.status, 409)
        async with self.sessions() as db:
            (await db.get(User, 1)).status = "blocked"
            await db.commit()
        with self.assertRaisesRegex(CommandError, "target_blocked"):
            await self.grant_command()
        with self.assertRaisesRegex(CommandError, "target_blocked"):
            await self.grant_execute(command, proof)

    async def test_audit_failure_rolls_back_entitlement_and_proof(self):
        command = await self.grant_command()
        proof = await self.grant_proof(command)
        def fail(mapper, connection, target):
            raise RuntimeError("synthetic audit failure")
        event.listen(AdminPwaCommandAudit, "before_insert", fail)
        try:
            with self.assertRaises(RuntimeError):
                await self.grant_execute(command, proof)
        finally:
            event.remove(AdminPwaCommandAudit, "before_insert", fail)
        async with self.sessions() as db:
            self.assertIsNone((await db.get(User, 1)).end_date)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
        self.assertTrue((await self.grant_execute(command, proof))["command_id"])

    async def test_current_session_and_privilege_rechecks_deny_signed_proof(self):
        for field, value in (("revoked_at", datetime.now(timezone.utc)),
                             ("expires_at", datetime.now(timezone.utc)-timedelta(seconds=1)),
                             ("auth_method", "google_telegram")):
            command = await self.grant_command()
            proof = await self.grant_proof(command)
            async with self.sessions() as db:
                row = await db.get(AdminPwaSession, self.session_id)
                old = getattr(row, field);setattr(row, field, value)
                await db.commit()
            with self.assertRaises(CommandError):
                await self.grant_execute(command, proof)
            async with self.sessions() as db:
                setattr(await db.get(AdminPwaSession, self.session_id), field, old)
                await db.commit()
        self.settings.admin_id_list = []
        with self.assertRaises(CommandError):
            await self.grant_execute(command, proof)

    async def test_route_is_cookie_only_same_origin_strict_bounded_and_default_off(self):
        app = FastAPI()
        app.include_router(create_admin_pwa_access_grant_router(settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
                headers={"origin": "https://hskai.app"}, cookies={ADMIN_PWA_COOKIE_NAME: fixtures.COOKIE}) as client:
            for body in ({"user_id": True, "duration_days": 30}, {"user_id": 1, "duration_days": "30"},
                         {"user_id": 1, "duration_days": 0}, {"user_id": 1, "duration_days": 36501},
                         {"user_id": 1, "duration_days": 1, "telegram_id": 1001}):
                self.assertEqual((await client.post("/api/admin/v1/users/prepare-access", json=body)).status_code, 400)
            payload = {"user_id": 1, "duration_days": 30}
            response = await client.post("/api/admin/v1/users/prepare-access", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual((await client.post("/api/admin/v1/users/prepare-access", json=payload,
                headers={"origin": "https://evil.invalid"})).status_code, 403)
            client.cookies.clear();client.headers["authorization"] = "Bearer "+fixtures.COOKIE
            self.assertEqual((await client.post("/api/admin/v1/users/prepare-access", json=payload)).status_code, 401)
            self.settings.ADMIN_PWA_ENABLED = False
            self.assertEqual((await client.post("/api/admin/v1/users/prepare-access", json=payload)).status_code, 404)

    async def test_expiry_crossing_paid_term_boundary_rejects_stale_confirmation(self):
        end = datetime.now(timezone.utc)+timedelta(seconds=10)
        async with self.sessions() as db:
            user = await db.get(User, 1);user.payment_status = "approved";user.end_date = end
            await db.commit()
        command = await self.grant_command()
        proof = await self.grant_proof(command)
        with patch("app.admin_api.pwa_access_grants.datetime") as clock:
            clock.now.return_value = end+timedelta(seconds=1)
            with self.assertRaisesRegex(CommandError, "confirmation_changed"):
                await self.grant_execute(command, proof)
