"""Android payment push is bound to the current native account and device."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, call, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_push import create_android_push_router
from app.db.base import Base
from app.db.models.android_push import AndroidPushToken
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.android_payment_push_service import AndroidPaymentPushService
from app.services.android_push_service import AndroidPushResult
from app.services.android_realtime_push_service import AndroidRealtimePushService
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.payment_notify_service import PaymentNotifyService


def settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="android-push-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
        ANDROID_FCM_PROJECT_ID="test-project",
        ANDROID_FCM_SERVICE_ACCOUNT_JSON="",
        ANDROID_PUSH_UPDATES_ENABLED=True,
        ANDROID_PUSH_STUDY_ENABLED=True,
    )


def user(user_id: int, telegram_id: int) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=f"User {user_id}",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class AndroidPushTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = settings()
        async with self.sessions() as session:
            session.add_all([user(1, 1001), user(2, 1002)])
            await session.commit()
            self.token_a, self.device_a = await self._link(session, 1001, "a" * 48)
            self.token_b, self.device_b = await self._link(session, 1002, "b" * 48)
            self.desktop_token, _ = await self._link(session, 1001, "c" * 48, platform="macos")
            session.add_all([
                Payment(id=11, user_telegram_id=1001, plan_type="1_month", amount=89,
                        currency="TJS", payment_status="approved", source="android"),
                Payment(id=12, user_telegram_id=1001, plan_type="1_month", amount=89,
                        currency="TJS", payment_status="rejected", source="telegram_miniapp"),
            ])
            await session.commit()
        app = FastAPI()
        app.include_router(create_android_push_router(
            session_factory=self.sessions, settings_obj=self.settings,
        ))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://test.local")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _link(self, session, telegram_id, installation_key, platform="android"):
        auth = DesktopAuthService(session, self.settings)
        started = await auth.start_link(
            platform=platform, app_version="1.0.0", installation_key=installation_key,
        )
        await auth.approve_link(display_code=started["display_code"], telegram_id=telegram_id)
        linked = await auth.poll_link(
            link_request_id=started["link_request_id"],
            polling_secret=started["polling_secret"],
        )
        context = await auth.authenticate(linked["access_token"])
        return linked["access_token"], context.device.id

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    async def test_registration_requires_android_bearer_and_moves_rotated_token(self):
        path = "/api/v3/android/push/register"
        payload = {"token": "fcm-token-" + "x" * 32}
        anonymous = await self.client.post(path, json=payload)
        self.assertEqual(401, anonymous.status_code)
        desktop = await self.client.post(
            path, json=payload, headers=self.bearer(self.desktop_token),
        )
        self.assertEqual(403, desktop.status_code)
        first = await self.client.post(path, json=payload, headers=self.bearer(self.token_a))
        self.assertEqual(200, first.status_code)
        second = await self.client.post(path, json=payload, headers=self.bearer(self.token_b))
        self.assertEqual(200, second.status_code)
        async with self.sessions() as session:
            rows = (await session.execute(select(AndroidPushToken))).scalars().all()
        self.assertEqual(1, len(rows))
        self.assertEqual(self.device_b, rows[0].device_id)

    async def test_preferences_are_device_bound_and_timezone_is_validated(self):
        token = "fcm-token-" + "p" * 32
        registered = await self.client.post(
            "/api/v3/android/push/register",
            json={"token": token},
            headers=self.bearer(self.token_a),
        )
        self.assertEqual(200, registered.status_code)

        updated = await self.client.post(
            "/api/v3/android/push/preferences",
            json={
                "study_reminders_enabled": True,
                "timezone_name": "Asia/Shanghai",
            },
            headers=self.bearer(self.token_a),
        )
        self.assertEqual(200, updated.status_code)
        async with self.sessions() as session:
            row = await session.get(AndroidPushToken, self.device_a)
            self.assertTrue(row.study_reminders_enabled)
            self.assertEqual("Asia/Shanghai", row.timezone_name)

        invalid = await self.client.post(
            "/api/v3/android/push/preferences",
            json={
                "study_reminders_enabled": True,
                "timezone_name": "Not/A_Real_Zone",
            },
            headers=self.bearer(self.token_a),
        )
        self.assertEqual(422, invalid.status_code)

    async def test_study_push_is_once_per_local_day(self):
        token = "fcm-token-" + "s" * 32
        await self.client.post(
            "/api/v3/android/push/register",
            json={"token": token},
            headers=self.bearer(self.token_a),
        )
        await self.client.post(
            "/api/v3/android/push/preferences",
            json={
                "study_reminders_enabled": True,
                "timezone_name": "UTC",
            },
            headers=self.bearer(self.token_a),
        )

        async with self.sessions() as session:
            service = AndroidRealtimePushService(session, self.settings)
            with patch.object(
                service.push,
                "send_batch",
                new_callable=AsyncMock,
                return_value=[AndroidPushResult(True)],
            ) as send:
                now = datetime(2026, 9, 28, 20, 5, tzinfo=timezone.utc)
                self.assertEqual(1, await service.send_due_study(now))
                self.assertEqual(0, await service.send_due_study(now))
                self.assertEqual(1, send.await_count)

            row = await session.get(AndroidPushToken, self.device_a)
            self.assertEqual("2026-09-28", row.last_study_push_day)
    async def test_payment_status_is_owner_only_for_android_and_miniapp_receipts(self):
        for payment_id, expected in [(11, "approved"), (12, "rejected")]:
            path = f"/api/v3/android/subscription/payments/{payment_id}/status"
            response = await self.client.get(path, headers=self.bearer(self.token_a))
            self.assertEqual(200, response.status_code)
            self.assertEqual(expected, response.json()["status"])
            other = await self.client.get(path, headers=self.bearer(self.token_b))
            self.assertEqual(404, other.status_code)
            anonymous = await self.client.get(path)
            self.assertEqual(401, anonymous.status_code)

    async def test_revoking_session_removes_push_registration(self):
        payload = {"token": "fcm-token-" + "y" * 32}
        await self.client.post(
            "/api/v3/android/push/register", json=payload,
            headers=self.bearer(self.token_a),
        )
        async with self.sessions() as session:
            await DesktopAuthService(session, self.settings).revoke(
                self.token_a, revoke_device=False,
            )
            row = await session.get(AndroidPushToken, self.device_a)
        self.assertIsNone(row)

    async def test_only_current_android_device_receives_committed_decision(self):
        payload = {"token": "fcm-token-" + "z" * 32}
        await self.client.post(
            "/api/v3/android/push/register", json=payload,
            headers=self.bearer(self.token_a),
        )
        async with self.sessions() as session:
            service = AndroidPaymentPushService(session, self.settings)
            with patch.object(service, "_send_one", new_callable=AsyncMock, return_value=True) as send:
                await service.notify(telegram_id=1001, payment_id=11, status="approved")
                send.assert_awaited_once_with(
                    token=payload["token"], device_id=self.device_a,
                    payment_id=11, status="approved",
                )
                await service.notify(telegram_id=1002, payment_id=11, status="approved")
                await service.notify(telegram_id=1001, payment_id=11, status="pending")
                self.assertEqual(1, send.await_count)

    async def test_bot_delivery_failure_does_not_suppress_android_decision(self):
        async with self.sessions() as session:
            current_user = await session.get(User, 1)
            payment = await session.get(Payment, 11)
            bot = SimpleNamespace(send_message=AsyncMock(side_effect=RuntimeError("bot unavailable")))
            with (
                patch.object(BotBlockStatusService, "is_bot_blocked", return_value=False),
                patch.object(PaymentNotifyService, "_failure", new_callable=AsyncMock),
                patch.object(AndroidPaymentPushService, "notify", new_callable=AsyncMock) as push,
            ):
                notifier = PaymentNotifyService(session)
                await notifier.notify_payment_approved(bot, current_user, payment)
                await notifier.notify_payment_rejected(bot, current_user, payment=payment)

            self.assertEqual(
                [
                    call(telegram_id=1001, payment_id=11, status="approved"),
                    call(telegram_id=1001, payment_id=11, status="rejected"),
                ],
                push.await_args_list,
            )
