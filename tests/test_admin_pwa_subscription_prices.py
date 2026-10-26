"""Real SQLite price command transactions and first-party HTTP guards."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import pwa_subscription_prices as prices
from app.admin_api.pwa_step_up import begin_step_up, operation_digest, verify_step_up
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.payment import Payment
from app.db.models.payment_qr_code import PaymentQrCode
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.subscription_price import SubscriptionPrice
from app.db.models.user import User
from app.services.subscription_price_service import SubscriptionPriceService
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID, make_assertion

ORIGIN = "https://hskai.app"


class AdminPwaSubscriptionPriceTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare_price(self, method="visa", plan="1_month", amount=100):
        async with self.sessions() as db:
            result = await prices.prepare_subscription_price(db, session_cookie=fixtures.COOKIE,
                request=prices.PrepareSubscriptionPrice(method=method, plan=plan, amount=amount),
                settings_obj=self.settings)
        return prices.SubscriptionPriceCommand.model_validate(result["operation"]["payload"])

    async def price_proof(self, command, *, signed=False, **overrides):
        if signed:
            async with self.sessions() as db:
                started = await begin_step_up(db, session_cookie=fixtures.COOKIE,
                    settings_obj=self.settings, **command.operation())
            self.assertIsNotNone(started)
            async with self.sessions() as db:
                challenge = bytes((await db.get(AdminPwaStepUp, started.step_up_id)).challenge)
            async with self.sessions() as db:
                self.assertTrue(await verify_step_up(db, session_cookie=fixtures.COOKIE,
                    step_up_id=started.step_up_id, settings_obj=self.settings,
                    credential=make_assertion(self.key, challenge=challenge)))
            return started.step_up_id
        now = datetime.now(timezone.utc)
        step_id = str(uuid4())
        values = dict(id=step_id, session_id=self.session_id, user_id=101,
            action="subscription.prices", target=command.operation()["target"],
            payload_hash=operation_digest(**command.operation()), challenge=b"Z" * 32,
            status="verified", credential_id=CRED_ID, verified_at=now,
            created_at=now, expires_at=now + timedelta(seconds=50))
        values.update(overrides)
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(**values))
            await db.commit()
        return step_id

    async def execute_price(self, command, proof, cookie=fixtures.COOKIE):
        async with self.sessions() as db:
            return await prices.execute_subscription_price(db, session_cookie=cookie,
                request=prices.ExecuteSubscriptionPrice(**command.model_dump(), step_up_id=proof),
                settings_obj=self.settings)

    async def test_read_returns_only_nine_canonical_targets_without_writes(self):
        async with self.sessions() as db:
            db.add(SubscriptionPrice(payment_method="unknown", plan_type="unknown",
                amount=1, currency="private-canary"))
            db.add(SubscriptionPrice(payment_method="visa", plan_type="1_month",
                amount=9, currency="USD"))
            await db.commit()
        async with self.sessions() as db:
            result = await prices.read_subscription_prices(db, session_cookie=fixtures.COOKIE,
                settings_obj=self.settings)
        self.assertEqual(len(result["prices"]), 9)
        visa = next(row for row in result["prices"] if row["target"] == "visa-1_month")
        self.assertEqual((visa["amount"], visa["currency"]), (89, "TJS"))
        for row in result["prices"]:
            self.assertEqual(set(row), {"method", "plan", "amount", "currency", "target", "revision_hash"})
            self.assertEqual(len(row["revision_hash"]), 64)
        self.assertNotIn("private-canary", json.dumps(result))
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(SubscriptionPrice)), 2)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaStepUp)), 0)

    async def test_genuine_passkey_changes_one_price_and_commits_atomic_audit(self):
        command = await self.prepare_price(amount=120)
        proof = await self.price_proof(command, signed=True)
        result = await self.execute_price(command, proof)
        self.assertEqual((result["price"]["amount"], result["price"]["currency"]), (120, "TJS"))
        self.assertEqual(result["price"]["target"], "visa-1_month")
        self.assertNotEqual(result["price"]["revision_hash"], command.expected_hash)
        async with self.sessions() as db:
            self.assertEqual((await SubscriptionPriceService(db).get_price("visa", "1_month")).amount, 120)
            self.assertEqual(await db.scalar(select(func.count()).select_from(SubscriptionPrice)), 1)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "consumed")
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
            self.assertEqual((audit.action, audit.target, audit.actor_user_id, audit.target_user_id),
                             ("subscription.prices", "visa-1_month", 101, None))
            self.assertEqual(audit.payload_hash, operation_digest(**command.operation()))
            self.assertEqual(json.loads(audit.result_json)["before"]["amount"], 89)
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")
            self.assertIsNone((await db.get(User, 1)).end_date)
        with self.assertRaisesRegex(prices.CommandError, "step_up_denied"):
            await self.execute_price(command, proof)

    async def test_alipay_wechat_use_existing_service_currency(self):
        for method in ("alipay", "wechat"):
            command = await self.prepare_price(method=method, plan="10_days", amount=35)
            proof = await self.price_proof(command)
            with self.assertRaisesRegex(prices.CommandError, 'payment_qr_required'):
                await self.execute_price(command, proof)
            async with self.sessions() as db:
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
                db.add(PaymentQrCode(scope='subscription',payment_method=method,plan_type='10_days',
                    amount=35,currency='¥',file_id='staged-future-price-qr'))
                await db.commit()
            with self.assertRaisesRegex(prices.CommandError, 'payment_qr_required'):
                await self.execute_price(command, proof)
            async with self.sessions() as db:
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
                db.add(PaymentQrCode(scope='subscription_20',payment_method=method,plan_type='10_days',
                    amount=28,currency='¥',file_id='staged-future-20-percent-qr'))
                await db.commit()
            result = await self.execute_price(command, proof)
            self.assertEqual((result["price"]["amount"], result["price"]["currency"]), (35, "¥"))

    async def test_active_discount_campaign_requires_new_price_specific_qr(self):
        command = await self.prepare_price(method="alipay", plan="10_days", amount=35)
        proof = await self.price_proof(command)
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            campaign = DiscountCampaign(title="Discount price QA", percent=25, is_active=True,
                starts_at=now-timedelta(minutes=1), ends_at=now+timedelta(hours=1),
                payment_method="alipay",plan_type="10_days")
            db.add(campaign)
            db.add(PaymentQrCode(scope="subscription",payment_method="alipay",
                plan_type="10_days",amount=35,currency="¥",file_id="full-price-qr"))
            db.add(PaymentQrCode(scope="subscription_20",payment_method="alipay",
                plan_type="10_days",amount=28,currency="¥",file_id="referral-qr"))
            await db.commit()
            campaign_id=campaign.id
        with self.assertRaisesRegex(prices.CommandError, "payment_qr_required"):
            await self.execute_price(command, proof)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status,"verified")
            db.add(PaymentQrCode(scope=f"admin_campaign:{campaign_id}",payment_method="alipay",
                plan_type="10_days",amount=26,currency="¥",file_id="campaign-qr"))
            await db.commit()
        saved=await self.execute_price(command, proof)
        self.assertEqual(saved["price"]["amount"],35)

    async def test_raw_legacy_revision_change_is_rejected_even_when_display_matches(self):
        async with self.sessions() as db:
            db.add(SubscriptionPrice(payment_method="visa", plan_type="1_month", amount=9, currency="USD"))
            await db.commit()
        command = await self.prepare_price()
        proof = await self.price_proof(command)
        # Both legacy amounts display the same canonical 89 TJS fallback.
        # CAS nevertheless binds the raw stored row, not the normalized UI.
        async with self.sessions() as db:
            row = await db.scalar(select(SubscriptionPrice))
            row.amount = 10
            await db.commit()
        with self.assertRaisesRegex(prices.CommandError, "confirmation_changed") as caught:
            await self.execute_price(command, proof)
        self.assertEqual(caught.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual((await db.scalar(select(SubscriptionPrice))).amount, 10)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_absent_snapshot_rejects_legacy_service_write(self):
        command = await self.prepare_price()
        proof = await self.price_proof(command)
        async with self.sessions() as db:
            await SubscriptionPriceService(db).set_price(payment_method="visa", plan_type="1_month", amount=130)
            await db.commit()
        with self.assertRaisesRegex(prices.CommandError, "confirmation_changed"):
            await self.execute_price(command, proof)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual((await db.scalar(select(SubscriptionPrice))).amount, 130)

    async def test_amount_target_and_action_tampering_cannot_reuse_price_proof(self):
        command = await self.prepare_price()
        proof = await self.price_proof(command)
        for changed in ({"amount": 101}, {"method": "wechat"}, {"plan": "10_days"}):
            altered = prices.SubscriptionPriceCommand.model_validate({**command.model_dump(), **changed})
            with self.assertRaisesRegex(prices.CommandError, "step_up_denied"):
                await self.execute_price(altered, proof)
        other_action_proof = await self.price_proof(command, action="course.access_policy")
        with self.assertRaisesRegex(prices.CommandError, "step_up_denied"):
            await self.execute_price(command, other_action_proof)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(SubscriptionPrice)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")

    async def test_expiry_after_target_lock_wait_rejects_and_rolls_back(self):
        command = await self.prepare_price()
        proof = await self.price_proof(command)
        original = prices._row
        future = datetime.now(timezone.utc) + timedelta(minutes=2)

        class AfterWaitDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return future.astimezone(tz) if tz else future.replace(tzinfo=None)

        async def after_wait(db, method, plan, *, lock=False):
            row = await original(db, method, plan, lock=lock)
            if lock:
                final_clock.start()
            return row

        final_clock = patch.object(prices, "datetime", AfterWaitDateTime)
        try:
            with patch.object(prices, "_row", after_wait):
                with self.assertRaisesRegex(prices.CommandError, "step_up_denied"):
                    await self.execute_price(command, proof)
        finally:
            final_clock.stop()
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(SubscriptionPrice)), 0)

    async def test_audit_failure_rolls_back_price_and_proof(self):
        command = await self.prepare_price()
        proof = await self.price_proof(command)
        original = AsyncSession.flush

        async def reject_audit(db, *args, **kwargs):
            if any(isinstance(row, AdminPwaCommandAudit) for row in db.new):
                raise RuntimeError("synthetic audit persistence failure")
            return await original(db, *args, **kwargs)

        with patch.object(AsyncSession, "flush", reject_audit):
            with self.assertRaisesRegex(RuntimeError, "audit persistence"):
                await self.execute_price(command, proof)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(SubscriptionPrice)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_current_authority_revocation_and_flag_block_commands(self):
        command = await self.prepare_price()
        proof = await self.price_proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaSession, self.session_id)).revoked_at = datetime.now(timezone.utc)
            await db.commit()
        with self.assertRaisesRegex(prices.CommandError, "step_up_denied"):
            await self.execute_price(command, proof)
        async with self.sessions() as db:
            with self.assertRaisesRegex(prices.CommandError, "unauthorized"):
                await prices.read_subscription_prices(db, session_cookie=fixtures.COOKIE, settings_obj=self.settings)
        self.settings.ADMIN_PWA_ENABLED = False
        with self.assertRaisesRegex(prices.CommandError, "not_found"):
            await self.prepare_price()

    async def test_strict_validation_rejects_invalid_amount_and_unknown_targets(self):
        for value in (True, 0, -1, 1_000_001, 1.5, "100", None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                prices.PrepareSubscriptionPrice(method="visa", plan="1_month", amount=value)
        for changed in ({"method": "Visa"}, {"plan": "hsk30_unlock"}, {"currency": "USD"}):
            with self.assertRaises(ValidationError):
                prices.PrepareSubscriptionPrice.model_validate(
                    {"method": "visa", "plan": "1_month", "amount": 100, **changed})

    async def test_http_security_and_bounded_payload_contract(self):
        app = FastAPI()
        app.include_router(prices.create_admin_pwa_subscription_prices_router(
            settings_obj=self.settings, session_factory=self.sessions))
        headers = {"origin": ORIGIN, "sec-fetch-site": "same-origin", "content-type": "application/json",
                   "cookie": "__Host-hskai_admin=" + fixtures.COOKIE}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as client:
            result = await client.post("/api/admin/v1/subscription-prices/read", headers=headers, json={})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.headers["cache-control"], "no-store")
            self.assertFalse(result.headers.get_list("set-cookie"))
            self.assertEqual(len(result.json()["prices"]), 9)
            for changed, status in (({"origin": "https://evil.example"}, 403),
                                    ({"sec-fetch-site": "cross-site"}, 403),
                                    ({"content-type": "text/plain"}, 415),
                                    ({"cookie": "", "authorization": "Bearer " + fixtures.COOKIE}, 401)):
                response = await client.post("/api/admin/v1/subscription-prices/read",
                    headers={**headers, **changed}, json={})
                self.assertEqual(response.status_code, status)
            for body in (b'{"method":"visa","method":"wechat","plan":"1_month","amount":100}',
                         b'[]', b'null', b'x' * 2049,
                         b'{"method":"visa","plan":"1_month","amount":100,"currency":"USD"}'):
                response = await client.post("/api/admin/v1/subscription-prices/prepare", headers=headers, content=body)
                self.assertEqual(response.status_code, 400)
            self.assertEqual((await client.post("/api/admin/v1/subscription-prices/read", headers=headers,
                                               json={"extra": 1})).status_code, 400)
            self.settings.ADMIN_PWA_ENABLED = False
            for route in ("read", "prepare", "save"):
                self.assertEqual((await client.post("/api/admin/v1/subscription-prices/" + route,
                                                   headers=headers, json={})).status_code, 404)
