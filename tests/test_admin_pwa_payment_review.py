"""Real SQL financial rollback tests; synthetic fixtures never touch live data."""
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import ValidationError
from sqlalchemy import event, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview, AdminPwaPaymentOutbox
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.course_track_state import CourseTrackState
from app.db.models.partner import Partner, PartnerCredit, PartnerReferral
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.user import User
from app.admin_api.pwa_payment_review import (
    ExecutePaymentReview, PaymentReviewCommand, PreparePaymentReview,
    execute_payment_review, prepare_payment_review,
)
from app.admin_api.pwa_payment_outbox import dispatch_payment_review
from app.admin_api.pwa_step_up import begin_step_up, operation_digest, verify_step_up
from app.services.admin_payment_review_service import PaymentReviewError
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.payment_review_preview_service import PaymentReviewPreviewService
from tests.test_admin_pwa_webauthn_crypto_vectors import (
    CRED_ID, HANDLE, cose_es256_public_key, make_assertion,
)

COOKIE = "S" * 64


class PaymentFixtures:
    """Also used by disposable real PostgreSQL concurrency tests."""
    async def seed_payment(self, *, plan="1_month", legacy=False, partner=False):
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app", admin_id_list=[9001])
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.session_id = str(uuid4())
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([User(id=101, telegram_id=9001, status="active"),
                        User(id=1, telegram_id=1001 if legacy or partner else None, status="free"),
                        User(id=2, telegram_id=2002, status="free")])
            await db.flush()
            db.add(AdminPwaSession(id=self.session_id, user_id=101,
                token_hash=hashlib.sha256(COOKIE.encode()).hexdigest(), auth_method="webauthn",
                created_at=now, expires_at=now+timedelta(hours=1)))
            db.add(AdminPwaCredential(id=str(uuid4()), user_id=101, credential_id=CRED_ID,
                public_key=cose_es256_public_key(self.key), user_handle=HANDLE,
                sign_count=0, device_type="single_device", backed_up=False, created_at=now))
            payment = Payment(user_id=None if legacy else 1,
                user_telegram_id=1001 if legacy or partner else None,
                amount=100, currency="TJS", base_amount=100, plan_type=plan,
                payment_method="visa", payment_status="pending", screenshot_file_id="synthetic-receipt")
            db.add(payment)
            await db.flush()
            self.payment_id = payment.id
            if partner:
                db.add(Partner(id=1, user_telegram_id=3003, status="active", promotion_channel="fixture",
                    audience_size="1", contact_username="fixture"))
                await db.flush()
                db.add(PartnerReferral(partner_id=1, invited_user_telegram_id=1001))
                db.add(PartnerCredit(partner_id=1, credit_type="signup_bonus", amount_usd=1, is_locked=True))
            await db.commit()

    async def command(self, *, decision="approve", reason=None):
        async with self.sessions() as db:
            operation = await prepare_payment_review(db, session_cookie=COOKIE,
                request=PreparePaymentReview(payment_id=self.payment_id, decision=decision, reason=reason),
                settings_obj=self.settings)
        return PaymentReviewCommand.model_validate(operation["payload"])

    async def receipt(self, command, *, signed=False, **overrides):
        if signed:
            async with self.sessions() as db:
                started = await begin_step_up(db, session_cookie=COOKIE,
                    settings_obj=self.settings, **command.operation())
            async with self.sessions() as db:
                row = await db.get(AdminPwaStepUp, started.step_up_id)
                challenge = bytes(row.challenge)
            async with self.sessions() as db:
                passed = await verify_step_up(db, session_cookie=COOKIE, step_up_id=started.step_up_id,
                    credential=make_assertion(self.key, challenge=challenge), settings_obj=self.settings)
            assert passed
            return started.step_up_id
        now = datetime.now(timezone.utc)
        receipt_id = str(uuid4())
        values = dict(id=receipt_id, session_id=self.session_id, user_id=101,
            action="payments.review", target=str(command.payment_id),
            payload_hash=operation_digest(**command.operation()), challenge=b"C"*32,
            status="verified", credential_id=CRED_ID, created_at=now, verified_at=now,
            expires_at=now+timedelta(seconds=50))
        values.update(overrides)
        async with self.sessions() as db:
            db.add(AdminPwaStepUp(**values))
            await db.commit()
        return receipt_id

    async def execute(self, command, receipt, *, cookie=COOKIE):
        async with self.sessions() as db:
            return await execute_payment_review(db, session_cookie=cookie,
                request=ExecutePaymentReview(**command.model_dump(), step_up_id=receipt), settings_obj=self.settings)

    async def change(self, model, **values):
        async with self.sessions() as db:
            await db.execute(update(model).values(**values))
            await db.commit()


class AdminPwaPaymentReviewTests(PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        @event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.rates = patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates",
                                 new=AsyncMock(return_value={"tjs": 10, "cny": 7}))
        self.rates.start()
        self.addCleanup(self.rates.stop)
        await self.seed_payment()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def assert_untouched(self, receipt):
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")
            self.assertEqual((await db.get(AdminPwaStepUp, receipt)).status, "verified")
            self.assertIsNone((await db.get(User, 1)).end_date)
            for model in (AdminPwaPaymentReview, AdminPwaPaymentOutbox, PortfolioTransaction):
                self.assertEqual(await db.scalar(select(func.count()).select_from(model)), 0)

    async def test_rejection_requires_a_reason_at_api_boundary(self):
        for reason in (None, "", "  "):
            with self.subTest(reason=reason), self.assertRaises(ValidationError):
                PreparePaymentReview(payment_id=self.payment_id, decision="reject", reason=reason)
        with self.assertRaises(ValidationError):
            PreparePaymentReview(payment_id=self.payment_id, decision="approve", reason="not allowed")

    async def test_genuine_es256_step_up_approval_and_replay(self):
        command = await self.command()
        receipt = await self.receipt(command, signed=True)
        funnel = AsyncMock()
        notify = AsyncMock()
        # No independent analytics/notifications inside financial transaction.
        with patch("app.services.conversion_funnel_service.ConversionFunnelService.record", funnel), \
             patch("app.services.payment_notify_service.PaymentNotifyService.notify_payment_approved", notify):
            result = await self.execute(command, receipt)
        self.assertEqual(result["status"], "approved")
        funnel.assert_not_awaited()
        notify.assert_not_awaited()
        async with self.sessions() as db:
            user = await db.get(User, 1)
            self.assertEqual(user.end_date-user.start_date, timedelta(days=30))
            self.assertEqual((await db.get(AdminPwaStepUp, receipt)).status, "consumed")
            audit = await db.get(AdminPwaPaymentReview, result["review_id"])
            self.assertEqual((audit.actor_user_id, audit.target_user_id, audit.payment_id), (101, 1, self.payment_id))
            self.assertEqual(audit.payload_hash, operation_digest(**command.operation()))
            self.assertEqual(json.loads(audit.payload_json), command.model_dump())
            self.assertEqual((await db.get(AdminPwaPaymentOutbox, audit.id)).status, "pending")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AIUsageBudget)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PortfolioTransaction)), 1)
        with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
            await self.execute(command, receipt)

    async def test_changed_server_financial_fields_roll_back_receipt(self):
        command = await self.command()
        receipt = await self.receipt(command)
        changes = {"amount": 99, "currency": "USD", "user_id": 2, "plan_type": "3_months",
                   "discount_source": "referral", "payment_method": "wechat", "screenshot_file_id": "another"}
        for name, value in changes.items():
            async with self.sessions() as db:
                original = getattr(await db.get(Payment, self.payment_id), name)
            await self.change(Payment, **{name: value})
            with self.subTest(field=name), self.assertRaisesRegex(PaymentReviewError, "confirmation_changed"):
                await self.execute(command, receipt)
            await self.change(Payment, **{name: original})
            await self.assert_untouched(receipt)

    async def test_invalid_real_signatures_cannot_authorize_payment(self):
        command = await self.command()
        stranger = ec.generate_private_key(ec.SECP256R1())
        for fields in ({"origin": "https://evil.example"}, {"rp_id": "evil.example"},
                       {"uv": False}, {"signature_valid": False}, {"key": stranger}):
            async with self.sessions() as db:
                started = await begin_step_up(db, session_cookie=COOKIE,
                    settings_obj=self.settings, **command.operation())
            async with self.sessions() as db:
                challenge = bytes((await db.get(AdminPwaStepUp, started.step_up_id)).challenge)
            parameters = {"key": self.key, "challenge": challenge, **fields}
            async with self.sessions() as db:
                self.assertFalse(await verify_step_up(db, session_cookie=COOKIE,
                    step_up_id=started.step_up_id, credential=make_assertion(**parameters), settings_obj=self.settings))
            with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
                await self.execute(command, started.step_up_id)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPaymentReview)), 0)

    async def test_changed_client_amount_owner_reason_and_target_cannot_reuse_proof(self):
        command = await self.command(decision="reject", reason="duplicate")
        receipt = await self.receipt(command)
        changes = [{"payment_id": self.payment_id+1}, {"reason": "other"}, {"decision": "approve", "reason": None},
                   {"expected": {**command.expected.model_dump(), "amount": 99}},
                   {"expected": {**command.expected.model_dump(), "user_id": 2}}]
        for change in changes:
            altered = PaymentReviewCommand.model_validate({**command.model_dump(), **change})
            with self.subTest(change=change), self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
                await self.execute(altered, receipt)
            await self.assert_untouched(receipt)

    async def test_wrong_action_target_pending_expired_and_counterfeit_credential(self):
        command = await self.command()
        for invalid in ({"action": "users.delete"}, {"target": "999"}, {"status": "pending", "verified_at": None},
                        {"expires_at": datetime.now(timezone.utc)-timedelta(seconds=1)},
                        {"credential_id": b"unregistered"}):
            receipt = await self.receipt(command, **invalid)
            with self.subTest(invalid=invalid), self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
                await self.execute(command, receipt)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")

    async def test_revoked_session_credential_admin_and_cross_browser_denied(self):
        command = await self.command()
        receipt = await self.receipt(command)
        with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
            await self.execute(command, receipt, cookie="T"*64)
        for model, field in ((AdminPwaSession, "revoked_at"), (AdminPwaCredential, "revoked_at")):
            await self.change(model, **{field: datetime.now(timezone.utc)})
            with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
                await self.execute(command, receipt)
            await self.change(model, **{field: None})
        self.settings.admin_id_list=[]
        with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
            await self.execute(command, receipt)
        self.settings.admin_id_list=[9001]
        await self.change(AdminPwaSession, expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
        with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
            await self.execute(command, receipt)
        await self.change(AdminPwaSession, expires_at=datetime.now(timezone.utc)+timedelta(hours=1))
        async with self.sessions() as db:
            (await db.get(User, 101)).status = " BLOCKED "
            await db.commit()
        with self.assertRaisesRegex(PaymentReviewError, "step_up_denied"):
            await self.execute(command, receipt)
        await self.assert_untouched(receipt)

    async def test_stale_pending_state_and_missing_canonical_owner_do_not_consume(self):
        command = await self.command()
        receipt = await self.receipt(command)
        await self.change(Payment, payment_status="approved")
        with self.assertRaisesRegex(PaymentReviewError, "already_reviewed"):
            await self.execute(command, receipt)
        await self.change(Payment, payment_status="pending", user_id=999, user_telegram_id=2002)
        with self.assertRaisesRegex(PaymentReviewError, "user_not_found"):
            await self.execute(command, receipt)
        await self.change(Payment, user_id=1, user_telegram_id=None)
        await self.assert_untouched(receipt)

    async def test_failure_after_entitlements_and_audit_insert_rolls_back_everything(self):
        command = await self.command()
        receipt = await self.receipt(command)
        @event.listens_for(AdminPwaPaymentOutbox, "before_insert")
        def fail(*_):
            raise RuntimeError("outbox disk failure")
        try:
            with self.assertRaisesRegex(RuntimeError, "outbox disk failure"):
                await self.execute(command, receipt)
        finally:
            event.remove(AdminPwaPaymentOutbox, "before_insert", fail)
        await self.assert_untouched(receipt)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AIUsageBudget)), 0)
        self.assertEqual((await self.execute(command, receipt))["status"], "approved")

    async def test_blocked_learner_activation_failure_keeps_receipt_and_payment_pending(self):
        command = await self.command()
        receipt = await self.receipt(command)
        async with self.sessions() as db:
            (await db.get(User, 1)).status="blocked"
            await db.commit()
        with self.assertRaisesRegex(PaymentReviewError, "subscription_activation_failed"):
            await self.execute(command, receipt)
        await self.assert_untouched(receipt)

    async def test_trial_analytics_deferred_and_preview_rejection_is_canonical(self):
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.trial_used=True
            await PaymentReviewPreviewService(db).claim(user, await db.get(Payment, self.payment_id))
            await db.commit()
        command=await self.command(decision="reject", reason="wrong_amount")
        receipt=await self.receipt(command)
        self.assertEqual((await self.execute(command, receipt))["status"], "rejected")
        async with self.sessions() as db:
            self.assertIsNone((await db.get(User, 1)).payment_preview_payment_id)
            self.assertFalse((await db.get(User, 1)).payment_preview_available)
            self.assertEqual((await db.scalar(select(AIUsageBudget))).status, "expired")
            self.assertEqual((await db.get(Payment, self.payment_id)).admin_comment, "wrong_amount")

    async def test_trial_conversion_never_escapes_rollback(self):
        async with self.sessions() as db:
            (await db.get(User, 1)).trial_used=True
            await db.commit()
        command=await self.command()
        receipt=await self.receipt(command)
        funnel=AsyncMock()
        with patch("app.services.conversion_funnel_service.ConversionFunnelService.record", funnel):
            result=await self.execute(command, receipt)
        funnel.assert_not_awaited()
        async with self.sessions() as db:
            outbox=await db.get(AdminPwaPaymentOutbox, result["review_id"])
            self.assertEqual(json.loads(outbox.effects_json)["deferred_events"][0]["event_name"], "trial_converted")

    async def test_hsk30_unlock_does_not_activate_pro(self):
        await self.change(Payment, plan_type="hsk30_unlock")
        command=await self.command()
        result=await self.execute(command, await self.receipt(command))
        self.assertEqual(result["product"], "hsk30_unlock")
        async with self.sessions() as db:
            track=await db.scalar(select(CourseTrackState))
            self.assertIsNotNone(track.unlocked_at)
            self.assertIsNone((await db.get(User, 1)).end_date)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AIUsageBudget)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PartnerCredit)), 0)

    async def test_hsk30_rejection_preserves_independent_subscription_and_saved_progress(self):
        await self.change(Payment, plan_type="hsk30_unlock")
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.status, user.payment_status = "active", "approved"
            user.end_date = datetime.now(timezone.utc)+timedelta(days=10)
            original_end = user.end_date
            db.add(CourseTrackState(user_id=1, track="hsk30", level="nhsk1", completed_lessons_count=3))
            await db.commit()
        command = await self.command(decision="reject", reason="wrong_amount")
        await self.execute(command, await self.receipt(command))
        async with self.sessions() as db:
            self.assertEqual((await db.get(User, 1)).end_date.replace(tzinfo=timezone.utc), original_end)
            self.assertEqual((await db.scalar(select(CourseTrackState))).completed_lessons_count, 3)

    async def test_rejection_outbox_failure_restores_preview_and_budget(self):
        async with self.sessions() as db:
            await PaymentReviewPreviewService(db).claim(await db.get(User, 1), await db.get(Payment, self.payment_id))
            await db.commit()
        command = await self.command(decision="reject", reason="wrong_amount")
        receipt = await self.receipt(command)
        @event.listens_for(AdminPwaPaymentOutbox, "before_insert")
        def fail(*_):
            raise RuntimeError("outbox unavailable")
        try:
            with self.assertRaises(RuntimeError):
                await self.execute(command, receipt)
        finally:
            event.remove(AdminPwaPaymentOutbox, "before_insert", fail)
        await self.assert_untouched(receipt)
        async with self.sessions() as db:
            self.assertEqual((await db.get(User, 1)).payment_preview_payment_id, self.payment_id)
            self.assertEqual((await db.scalar(select(AIUsageBudget))).status, "active")

    async def test_legacy_alias_is_bound_to_canonical_owner(self):
        await self.change(Payment, user_id=None, user_telegram_id=2002)
        command=await self.command()
        self.assertEqual(command.expected.user_id, 2)
        await self.execute(command, await self.receipt(command))
        async with self.sessions() as db:
            self.assertIsNone((await db.get(User, 1)).end_date)
            self.assertIsNotNone((await db.get(User, 2)).end_date)

    async def test_partner_commission_and_bonus_are_in_same_rollback(self):
        async with self.sessions() as db:
            (await db.get(User, 1)).telegram_id=1001
            db.add(Partner(id=1, user_telegram_id=3003, status="active", promotion_channel="fixture",
                audience_size="1", contact_username="fixture"))
            await db.flush()
            db.add(PartnerReferral(partner_id=1, invited_user_telegram_id=1001))
            db.add(PartnerCredit(partner_id=1, credit_type="signup_bonus", amount_usd=1, is_locked=True))
            await db.commit()
        command=await self.command()
        receipt=await self.receipt(command)
        @event.listens_for(AdminPwaPaymentOutbox, "before_insert")
        def fail(*_):
            raise RuntimeError("outbox unavailable")
        try:
            with self.assertRaises(RuntimeError):
                await self.execute(command, receipt)
        finally:
            event.remove(AdminPwaPaymentOutbox, "before_insert", fail)
        await self.assert_untouched(receipt)
        async with self.sessions() as db:
            self.assertTrue((await db.scalar(select(PartnerCredit))).is_locked)
            self.assertIsNone((await db.scalar(select(PartnerReferral))).first_paid_at)
        await self.execute(command, receipt)
        async with self.sessions() as db:
            credits=list((await db.scalars(select(PartnerCredit))).all())
            self.assertEqual(len(credits), 2)
            self.assertTrue(all(not credit.is_locked for credit in credits))
            self.assertIsNotNone((await db.scalar(select(PartnerReferral))).first_paid_at)

    async def test_outbox_attempted_once_after_commit_even_if_request_retried(self):
        command=await self.command()
        result=await self.execute(command, await self.receipt(command))
        async def emit(db, review):
            async with self.sessions() as other:
                self.assertEqual((await other.get(Payment, self.payment_id)).payment_status, "approved")
                self.assertIsNotNone(await other.get(AdminPwaPaymentReview, result["review_id"]))
        emitter=AsyncMock(side_effect=emit)
        options=dict(review_id=result["review_id"], session_factory=self.sessions, settings_obj=self.settings, emit=emitter)
        self.assertTrue(await dispatch_payment_review(**options))
        self.assertFalse(await dispatch_payment_review(**options))
        emitter.assert_awaited_once()

    async def test_uncertain_delivery_never_repeats_or_rolls_back_finance(self):
        command=await self.command()
        result=await self.execute(command, await self.receipt(command))
        emitter=AsyncMock(side_effect=RuntimeError("network timeout after send"))
        options=dict(review_id=result["review_id"], session_factory=self.sessions, settings_obj=self.settings, emit=emitter)
        self.assertFalse(await dispatch_payment_review(**options))
        self.assertFalse(await dispatch_payment_review(**options))
        emitter.assert_awaited_once()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "approved")
            self.assertEqual((await db.get(AdminPwaPaymentOutbox, result["review_id"])).status, "uncertain")

    async def test_strict_command_rejects_unknown_keys_coercions_and_truncation(self):
        data=(await self.command()).model_dump()
        for change in ({"payment_id": True}, {"payment_id": "1"}, {"digest": "ignored"},
                       {"reason": "x"}, {"expected": {**data["expected"], "amount": 100.0}},
                       {"expected": {**data["expected"], "amount": True}},
                       {"decision": "reject", "reason": " x "},
                       {"decision": "reject", "reason": "x"*301}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                PaymentReviewCommand.model_validate({**data, **change})
