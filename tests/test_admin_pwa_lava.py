"""Admin PWA lava.top control: exact passkey proofs, CAS, safe mode rules."""
import unittest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import func, select

from app.admin_api.pwa_lava import (
    CommandError, ExecuteLavaAction, ExecuteLavaSettings, LavaActionCommand, LavaActionInput,
    LavaSettingsCommand, LavaSettingsInput, execute_lava_action, execute_lava_settings,
    prepare_lava_action, prepare_lava_settings, read_lava,
)
from app.admin_api.pwa_step_up import operation_digest
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.lava import LavaInvoice
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.lava.config import LavaConfigService
from app.repositories.bot_setting_repo import BotSettingRepository
from tests import test_admin_pwa_payment_review as fixtures
from tests.lava_fakes import API_KEY, OFFER_ID, WEBHOOK_SECRET, FakeLava, RecordingNotifier
from tests.test_admin_pwa_webauthn_crypto_vectors import CRED_ID
from app.services.lava.events import LavaRuntime

PLANS = ("1_month", "3_months", "6_months", "12_months")


def _settings_input(mode="both", enabled=("1_month", "3_months")):
    return LavaSettingsInput(checkout_mode=mode, currency="USD", plans={
        plan: {"enabled": plan in enabled, "offer_id": OFFER_ID if plan in enabled else ""} for plan in PLANS})


class AdminPwaLavaTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.AdminPwaPaymentReviewTests.asyncSetUp(self)
        for key, value in dict(LAVA_ENABLED=True, LAVA_API_KEY=API_KEY, LAVA_WEBHOOK_SECRET=WEBHOOK_SECRET,
                               LAVA_PROCESSING_PAUSED=False, PUBLIC_SITE_URL="https://hsk.example").items():
            setattr(self.settings, key, value)
        self.fake = FakeLava()
        self.runtime = LavaRuntime(settings=self.settings, session_factory=self.sessions,
                                   notifier=RecordingNotifier(), client_factory=self.fake.client)
        patcher = patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                               new=AsyncMock(return_value={"tjs": 10, "cny": 7}))
        patcher.start()
        self.addCleanup(patcher.stop)

    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def proof(self, operation):
        stamp = datetime.now(timezone.utc)
        step_id = str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(id=step_id, session_id=self.session_id, user_id=101,
                                  action=operation["action"], target=operation["target"],
                                  payload_hash=operation_digest(**operation), challenge=b"L" * 32,
                                  status="verified", credential_id=CRED_ID, verified_at=stamp,
                                  created_at=stamp, expires_at=stamp + timedelta(seconds=40)))
            await db.commit()
        return step_id

    async def prepare_settings(self, request):
        async with self.sessions() as db:
            result = await prepare_lava_settings(db, session_cookie=fixtures.COOKIE, request=request,
                                                 settings_obj=self.settings, runtime_getter=lambda: self.runtime)
        return LavaSettingsCommand.model_validate(result["operation"]["payload"])

    async def save_settings(self, command, proof):
        async with self.sessions() as db:
            return await execute_lava_settings(
                db, session_cookie=fixtures.COOKIE, request=ExecuteLavaSettings(**command.model_dump(), step_up_id=proof),
                settings_obj=self.settings, runtime_getter=lambda: self.runtime)

    async def test_settings_save_snapshots_live_prices_and_is_one_use(self):
        command = await self.prepare_settings(_settings_input())
        self.assertEqual(command.prices, {"1_month": "10.00", "3_months": "27.00"})
        proof = await self.proof(command.operation())
        result = await self.save_settings(command, proof)
        self.assertEqual(result["config"]["checkout_mode"], "both")
        async with self.sessions() as db:
            config = await LavaConfigService(db).load()
            self.assertEqual(str(config.terms["3_months"].price_amount), "27.00")
            self.assertFalse(config.terms["6_months"].enabled)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "consumed")
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
            self.assertEqual((audit.action, audit.target), ("lava.settings", "global"))
            self.assertNotIn(API_KEY, audit.result_json)
        with self.assertRaises(CommandError):
            await self.save_settings(command, proof)

    async def test_promo_codes_are_signed_saved_and_audited_by_key_only(self):
        request = _settings_input()
        request = LavaSettingsInput(**{**request.model_dump(), "promo_codes": {
            "referral:20": "HSKREF20", "admin_campaign:30": "SPRING-30"}})
        command = await self.prepare_settings(request)
        self.assertEqual(command.promo_codes, {"referral:20": "HSKREF20", "admin_campaign:30": "SPRING-30"})
        result = await self.save_settings(command, await self.proof(command.operation()))
        self.assertEqual(result["config"]["promo_codes"]["admin_campaign:30"], "SPRING-30")
        async with self.sessions() as db:
            audit = await db.get(AdminPwaCommandAudit, result["command_id"])
        self.assertIn("admin_campaign:30", audit.result_json)
        self.assertNotIn("SPRING-30", audit.result_json)
        bad = LavaSettingsInput(**{**request.model_dump(), "promo_codes": {"referral:20": "no spaces!"}})
        with self.assertRaises(CommandError) as ctx:
            await self.prepare_settings(bad)
        self.assertEqual(str(ctx.exception), "invalid_promo_code")

    async def test_unsafe_modes_are_refused_but_manual_only_always_saves(self):
        self.settings.LAVA_ENABLED = False
        with self.assertRaises(CommandError) as ctx:
            await self.prepare_settings(_settings_input("lava_only"))
        self.assertEqual(ctx.exception.status, 409)
        self.settings.LAVA_ENABLED = True
        with self.assertRaises(CommandError):
            await self.prepare_settings(_settings_input("both", enabled=()))
        self.fake.product_type = "DIGITAL_PRODUCT"
        with self.assertRaises(CommandError) as ctx:
            await self.prepare_settings(_settings_input("both"))
        self.assertEqual(str(ctx.exception), "lava_offer_invalid")
        self.fake.unavailable = True
        command = await self.prepare_settings(_settings_input("manual_only"))
        result = await self.save_settings(command, await self.proof(command.operation()))
        self.assertEqual(result["config"]["checkout_mode"], "manual_only")

    async def test_tampered_or_stale_settings_are_rejected(self):
        command = await self.prepare_settings(_settings_input())
        proof = await self.proof(command.operation())
        tampered = LavaSettingsCommand(**{**command.model_dump(), "checkout_mode": "lava_only"})
        with self.assertRaises(CommandError) as ctx:
            await self.save_settings(tampered, proof)
        self.assertEqual(ctx.exception.status, 403)
        self.fake.prices["MONTHLY"] = "12.00"  # lava price changed after preparation
        with self.assertRaises(CommandError) as ctx:
            await self.save_settings(command, proof)
        self.assertEqual(ctx.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def _action(self, **fields):
        async with self.sessions() as db:
            prepared = await prepare_lava_action(db, session_cookie=fixtures.COOKIE,
                                                 request=LavaActionInput(**fields), settings_obj=self.settings,
                                                 runtime_getter=lambda: self.runtime)
        command = LavaActionCommand.model_validate(prepared["operation"]["payload"])
        proof = await self.proof(command.operation())
        async with self.sessions() as db:
            return await execute_lava_action(db, session_cookie=fixtures.COOKIE,
                                             request=ExecuteLavaAction(**command.model_dump(), step_up_id=proof),
                                             settings_obj=self.settings, runtime_getter=lambda: self.runtime)

    async def test_link_unmatched_contract_grants_after_api_verification(self):
        contract = self.fake.add_external(amount="27.00")
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(LavaInvoice(contract_id=contract, kind="external", currency="USD", source="admin_link",
                               status="unmatched", created_at=now, updated_at=now))
            await db.commit()
            invoice_id = (await db.execute(select(LavaInvoice.id))).scalar_one()
        result = await self._action(kind="link", invoice_id=invoice_id, user_id=2, plan_type="3_months")
        self.assertEqual(result["outcome"], "applied")
        async with self.sessions() as db:
            user = await db.get(User, 2)
            self.assertEqual(user.status, "active")
            payment = (await db.execute(select(Payment).where(Payment.user_id == 2))).scalar_one()
            self.assertEqual((payment.plan_type, payment.payment_method), ("3_months", "lava"))
        async with self.sessions() as db:
            reading = await read_lava(db, session_cookie=fixtures.COOKIE, settings_obj=self.settings)
        self.assertEqual(reading["lava"]["counts"]["paid_30d"], 1)
        with self.assertRaises(CommandError) as ctx:  # already linked
            await self._action(kind="link", invoice_id=invoice_id, user_id=2, plan_type="3_months")
        self.assertEqual(ctx.exception.status, 409)

    async def test_read_separates_buyer_non_payment_from_technical_incidents(self):
        now = datetime.now(timezone.utc)
        def invoice(*, status, review_reason=None):
            return LavaInvoice(
                contract_id=str(uuid4()), kind="first", user_id=2,
                plan_type="1_month", currency="USD", expected_amount=Decimal("7.90"),
                buyer_email="buyer@example.com", source="pwa", status=status,
                review_reason=review_reason, created_at=now, updated_at=now,
            )
        async with self.sessions() as db:
            db.add_all([
                invoice(status="created"),
                invoice(status="failed"),
                invoice(status="expired"),
                invoice(status="failed", review_reason="create_rejected"),
            ])
            await BotSettingRepository(db).set("lava_last_webhook_auth_failure_at", now.isoformat())
            await BotSettingRepository(db).set("lava_last_webhook_auth_failure_reason", "key_mismatch")
            await db.commit()
        async with self.sessions() as db:
            result = (await read_lava(db, session_cookie=fixtures.COOKIE,
                                      settings_obj=self.settings))["lava"]
        self.assertEqual(result["counts"]["awaiting_payment"], 1)
        self.assertEqual(result["counts"]["unsuccessful_payments"], 2)
        self.assertEqual(len(result["awaiting"]), 1)
        self.assertEqual(result["awaiting"][0]["amount"], "7.90")
        self.assertEqual({row["status"] for row in result["unsuccessful"]},
                         {"failed", "expired"})
        self.assertEqual(len(result["attention"]), 1)
        self.assertEqual(result["attention"][0]["review_reason"], "create_rejected")
        self.assertEqual(result["status"]["last_auth_failure_reason"], "key_mismatch")
        self.assertNotIn("buyer@example.com", str(result))

    async def test_action_payload_must_match_kind(self):
        with self.assertRaises(CommandError):
            await self._action(kind="cancel", user_id=2, invoice_id=5)
        with self.assertRaises(CommandError):
            await self._action(kind="chargeback", invoice_id=1)


if __name__ == "__main__":
    unittest.main()
