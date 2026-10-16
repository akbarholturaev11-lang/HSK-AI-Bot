"""Canonical payment approval, paid budgets and delivery without Telegram."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.ai_usage_budget_service import AIUsageBudgetService, PAYMENT_PREVIEW_PLAN_TYPE
from app.services.android_payment_push_service import AndroidPaymentPushService
from app.services.payment_notify_service import PaymentNotifyService
from app.services.payment_review_preview_service import PaymentReviewPreviewService
from app.services.subscription_service import SubscriptionService
from app.services.desktop_auth_service import DesktopAuthService
from app.api.android_push import create_android_push_router
from app.services.user_access_state_service import UserAccessState, UserAccessStateService
from app.services.access_service import AccessService


class NativePaymentActivationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, full_name="Google learner", language="uz", status="free"),
                User(id=2, telegram_id=None, full_name="Apple learner", language="ru", status="free"),
                User(id=3, telegram_id=3003, full_name="Telegram learner", language="uz", status="free"),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _payment(self, session, uid=1, *, preview=True, telegram_id=None):
        payment = Payment(user_id=uid, user_telegram_id=telegram_id, plan_type="1_month",
                          amount=100, currency="TJS", payment_method="visa", payment_status="pending")
        session.add(payment)
        await session.flush()
        if preview:
            self.assertTrue(await PaymentReviewPreviewService(session).claim(await session.get(User, uid), payment))
        await session.commit()
        return payment

    async def _main_review(self, session, payment, action):
        from tests.test_main_imports import MainModuleImportTests
        main = MainModuleImportTests._import_main()
        with (
            patch.object(main, "async_session_maker", self.sessions),
            patch.object(main.ConversionFunnelService, "record", new=AsyncMock(return_value=True)),
            patch.object(main.CourseMiniAppAnalyticsService, "record_server_event", new=AsyncMock(return_value={"recorded": False})),
            patch.object(PaymentNotifyService, "_android_push", new=AsyncMock()),
            patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates", new=AsyncMock(return_value={"tjs": 10, "cny": 7})),
        ):
            return await main._review_admin_payment(session, payment_id=payment.id, action=action, reason=None)

    async def test_admin_approval_activates_only_canonical_owner_and_replay_does_not_renew(self):
        async with self.sessions() as session:
            payment = await self._payment(session)
            now = datetime.now(timezone.utc)
            other = await session.get(User, 2)
            other_budget = await AIUsageBudgetService(session).create_fixed_budget(
                telegram_id=other, plan_type="pro_trial_7_days", amount=2, currency="usd", total_budget_usd=2,
                starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(days=7),
            )
            await session.commit()
            self.assertEqual(await self._main_review(session, payment, "approve"), ({"ok": True, "status": "approved"}, 200))
            owner = await session.get(User, 1)
            self.assertEqual(UserAccessStateService.classify(owner), UserAccessState.PAID)
            self.assertEqual(owner.end_date - owner.start_date, timedelta(days=30))
            self.assertIsNone(owner.telegram_id)
            self.assertTrue(owner.payment_preview_available)
            self.assertIsNone(owner.payment_preview_payment_id)
            self.assertEqual((payment.user_id, payment.user_telegram_id), (1, None))
            budgets = list((await session.scalars(select(AIUsageBudget).where(AIUsageBudget.user_id == 1))).all())
            self.assertEqual({b.plan_type: b.status for b in budgets}, {PAYMENT_PREVIEW_PLAN_TYPE: "expired", "1_month": "active"})
            self.assertTrue(all(b.user_telegram_id is None for b in budgets))
            await session.refresh(other_budget)
            self.assertEqual(other_budget.status, "active")
            self.assertEqual(UserAccessStateService.classify(other), UserAccessState.FREE)
            expiry = owner.end_date
            self.assertEqual((await self._main_review(session, payment, "approve"))[1], 409)
            self.assertEqual(owner.end_date, expiry)

    async def test_admin_rejection_revokes_only_native_receipt_preview(self):
        async with self.sessions() as session:
            own = await self._payment(session)
            other = await self._payment(session, uid=2)
            self.assertEqual((await self._main_review(session, own, "reject"))[1], 200)
            owner, neighbour = await session.get(User, 1), await session.get(User, 2)
            self.assertIsNone(owner.payment_preview_payment_id)
            self.assertFalse(owner.payment_preview_available)
            self.assertEqual(UserAccessStateService.classify(owner), UserAccessState.FREE)
            self.assertEqual(neighbour.payment_preview_payment_id, other.id)
            self.assertEqual(UserAccessStateService.classify(neighbour), UserAccessState.TEMPORARY_TRIAL)

    async def test_receipt_approval_cannot_silently_unblock_a_canonical_account(self):
        async with self.sessions() as session:
            payment = await self._payment(session, preview=False)
            user = await session.get(User, 1)
            user.status = "blocked"
            await session.commit()
            result = await self._main_review(session, payment, "approve")
            self.assertEqual(result, ({"ok": False, "error": "subscription_activation_failed"}, 400))
            await session.refresh(user)
            await session.refresh(payment)
            self.assertEqual(user.status, "blocked")
            self.assertEqual(payment.payment_status, "pending")
            self.assertIsNone(user.end_date)
            self.assertEqual((await session.scalars(select(AIUsageBudget))).all(), [])

    async def test_bot_admin_can_approve_provider_payment_without_telegram_delivery(self):
        from app.bot.handlers import admin_payments
        async with self.sessions() as session:
            payment = await self._payment(session, uid=2)
            callback = SimpleNamespace(from_user=SimpleNamespace(id=99), data=f"admin_payment:approve:{payment.id}",
                answer=AsyncMock(), message=SimpleNamespace(edit_reply_markup=AsyncMock()),
                bot=SimpleNamespace(send_message=AsyncMock(), delete_message=AsyncMock()))
            with (
                patch.object(admin_payments, "_is_admin", return_value=True),
                patch.object(admin_payments.ConversionFunnelService, "record", new=AsyncMock(return_value=True)),
                patch.object(admin_payments.CourseMiniAppAnalyticsService, "record_server_event", new=AsyncMock(return_value={"recorded": False})),
                patch.object(PaymentNotifyService, "_android_push", new=AsyncMock()),
                patch.object(AIUsageBudgetService, "_live_or_manual_usd_rates", new=AsyncMock(return_value={"tjs": 10, "cny": 7})),
            ):
                await admin_payments.admin_payment_approve_handler(callback, session)
            self.assertEqual(payment.payment_status, "approved")
            self.assertEqual(UserAccessStateService.classify(await session.get(User, 2)), UserAccessState.PAID)
            self.assertEqual(UserAccessStateService.classify(await session.get(User, 1)), UserAccessState.FREE)
            callback.bot.send_message.assert_not_awaited()
            callback.bot.delete_message.assert_not_awaited()

    async def test_payment_cannot_activate_foreign_user_even_if_telegram_metadata_matches(self):
        async with self.sessions() as session:
            payment = await self._payment(session, uid=2, preview=False, telegram_id=3003)
            payment.payment_status = "approved"
            for uid in (1, 3):
                with self.subTest(uid=uid):
                    user = await session.get(User, uid)
                    self.assertFalse(await SubscriptionService(session).activate_plan(user, "1_month", payment=payment))
                    self.assertEqual(UserAccessStateService.classify(user), UserAccessState.FREE)
            self.assertEqual((await session.scalars(select(AIUsageBudget))).all(), [])

    async def test_native_payment_push_does_not_target_other_null_telegram_devices(self):
        async with self.sessions() as session:
            for key, uid, revoked in (("owner", 1, False), ("other", 2, False), ("revoked", 1, True)):
                session.add(DesktopDevice(id=key, user_id=uid, telegram_id=None, platform="android",
                    installation_key_hash=key.ljust(64, "x"), app_version="1.0",
                    revoked_at=datetime.now(timezone.utc) if revoked else None))
                session.add(AndroidPushToken(device_id=key, token="token-" + key))
            await session.commit()
            service = AndroidPaymentPushService(session, SimpleNamespace(ANDROID_FCM_PROJECT_ID="fixture-project"))
            with patch.object(service, "_send_one", new=AsyncMock(return_value=True)) as send:
                await service.notify(telegram_id=None, user_id=1, payment_id=7, status="approved")
                send.assert_awaited_once_with(token="token-owner", device_id="owner", payment_id=7, status="approved")
                await service.notify(telegram_id=None, payment_id=7, status="approved")
                self.assertEqual(send.await_count, 1)

    async def test_android_status_uses_bearer_owner_instead_of_null_telegram_equality(self):
        settings = SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="native-payment-status-" + "x" * 48,
                                   DESKTOP_AUTH_ACCESS_TTL_SECONDS=900, BOT_TOKEN="fixture")
        async with self.sessions() as session:
            own = await self._payment(session, preview=False)
            other = await self._payment(session, uid=2, preview=False)
            device = DesktopDevice(id="status-device", user_id=1, telegram_id=None, platform="android",
                installation_key_hash="s" * 64, app_version="1.0")
            auth = DesktopSession(id="status-session", device_id=device.id,
                refresh_token_hash="r" * 64, expires_at=datetime.now(timezone.utc) + timedelta(days=1))
            session.add_all([device, auth])
            await session.commit()
            token, _ = DesktopAuthService(session, settings)._access_token(desktop_session=auth, device=device)
        app = FastAPI()
        app.include_router(create_android_push_router(session_factory=self.sessions, settings_obj=settings))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://native.test",
                               headers={"Authorization": "Bearer " + token}) as client:
            response = await client.get(f"/api/v3/android/subscription/payments/{own.id}/status")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["payment_id"], own.id)
            response = await client.get(f"/api/v3/android/subscription/payments/{other.id}/status")
            self.assertEqual(response.status_code, 404, response.text)
            response = await client.get(f"/api/v3/android/subscription/payments/{other.id}/status?user_id=2")
            self.assertEqual(response.status_code, 422, response.text)

    async def test_paid_native_expiry_keeps_canonical_notice_target_and_other_paid_account(self):
        from tests.test_main_imports import MainModuleImportTests
        main = MainModuleImportTests._import_main()
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            owner, other = await session.get(User, 1), await session.get(User, 2)
            for user in (owner, other):
                user.status, user.payment_status = "active", "approved"
            owner.end_date, other.end_date = now - timedelta(seconds=1), now + timedelta(days=1)
            await session.commit()
            changed, actors = await AccessService(session).downgrade_expired_active_users()
            self.assertEqual(changed, 1)
            self.assertEqual([user.id for user in actors], [1])
            self.assertEqual(owner.status, "expired")
            self.assertEqual(other.status, "active")
            with patch.object(main.NotificationDeliveryService, "deliver", new=AsyncMock(return_value="android")) as deliver:
                await main._send_subscription_expired_offer(session, actors[0])
            self.assertEqual(deliver.await_args.args[1].id, 1)
            self.assertIsNotNone(owner.subscription_expired_offer_sent_at)
            self.assertIsNone(other.subscription_expired_offer_sent_at)


if __name__ == "__main__":
    unittest.main()
