"""Trials, abuse signals, ad caps and notices retain canonical ownership."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_ad import CourseAdCreative, CourseAdView
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.referral import Referral
from app.db.models.trial_risk_event import TrialRiskEvent
from app.db.models.user import User
from app.services.ad_placement_service import AdPlacementService, PLACEMENT_SCREEN_CENTER
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.android_push_service import AndroidPushResult
from app.api.android_auth import create_android_auth_router
from app.api.android_features import create_android_features_router
from app.repositories.user_repo import UserRepository
from app.services.desktop_auth_service import DesktopAuthService
from app.services.entitlements.limits_config import LimitConfigService
from app.services.notification_delivery_service import (
    NotificationDeliveryService, TelegramNotice, STATUS_FAILED, STATUS_SHOWN,
)
from app.services.pro_trial_service import ProTrialService, REASON_ACTIVE_BUDGET, REASON_ALREADY_USED
from app.services.onboarding_service import OnboardingService
from app.services.trial_risk_service import TrialRiskService


class NativeAccountLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="native-lifecycle-test-" + "x" * 48,
            ANDROID_PUSH_NOTICES_ENABLED=True, ANDROID_FCM_PROJECT_ID="test-project", BOT_USERNAME="pomp_test_bot")
        self.funnel_patch = patch("app.services.conversion_funnel_service.async_session_maker", self.sessions)
        self.funnel_patch.start()
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            session.add_all([
                User(id=uid, telegram_id=tid, full_name=f"Learner {uid}", language="uz", level="hsk1",
                     status="free", payment_status="none", created_at=now - timedelta(days=10), last_active_at=now)
                for uid, tid in ((1, None), (2, None), (3, 3003))
            ])
            config = LimitConfigService(session)
            payload = (await config.get_config()).public_payload()
            payload["trial"].update(enabled=True, min_account_age_hours=0, ai_budget_usd=2, days=7)
            await config.save_config(payload)
            await session.commit()

    async def asyncTearDown(self):
        self.funnel_patch.stop()
        await self.engine.dispose()

    async def test_trial_preserves_billing_dates_and_existing_budget_and_cannot_repeat(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            now = datetime.now(timezone.utc)
            existing = await AIUsageBudgetService(session).create_fixed_budget(
                telegram_id=bob, plan_type="existing_grant", amount=2, currency="usd", total_budget_usd=2,
                starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(days=2),
            )
            await session.commit()
            refused = await ProTrialService(session).start(bob, source="android_trial", client="android")
            self.assertEqual(refused["error"], REASON_ACTIVE_BUDGET)
            self.assertEqual(existing.status, "active")
            self.assertFalse(bob.trial_used)
            before = (alice.status, alice.payment_status, alice.start_date, alice.end_date)
            granted = await ProTrialService(session).start(alice, source="android_trial", client="android")
            self.assertTrue(granted["ok"], granted)
            self.assertEqual((alice.status, alice.payment_status, alice.start_date, alice.end_date), before)
            repeated = await ProTrialService(session).start(alice, source="android_trial", client="android")
            self.assertEqual(repeated["error"], REASON_ALREADY_USED)
            budgets = (await session.execute(select(AIUsageBudget).order_by(AIUsageBudget.id))).scalars().all()
            self.assertEqual(len(budgets), 2)
            self.assertEqual({row.user_id for row in budgets}, {1, 2})
            self.assertTrue(all(row.user_telegram_id is None for row in budgets))

    async def test_reused_device_and_ip_count_distinct_internal_accounts(self):
        async with self.sessions() as session:
            service = TrialRiskService(session, self.settings)
            args = dict(client="android", source="android_trial", installation_key_hash="a" * 64,
                        remote_ip="203.0.113.5")
            alice, bob, legacy = [await session.get(User, uid) for uid in (1, 2, 3)]
            first = await service.analyze(alice, **args)
            self.assertEqual(first.prior_device_trial_users, 0)
            self.assertTrue(await service.record_started(alice, first))
            self.assertTrue(await service.record_started(alice, first))
            second = await service.analyze(bob, **args)
            self.assertEqual((second.prior_device_trial_users, second.prior_ip_trial_users_24h,
                              second.prior_ip_trial_users_7d), (1, 1, 1))
            self.assertIn("device_used_for_other_trial", second.signals)
            self.assertTrue(await service.record_started(bob, second))
            third = await service.analyze(legacy, **args)
            self.assertEqual((third.prior_device_trial_users, third.prior_ip_trial_users_24h), (2, 2))
            own = await service.analyze(alice, **args)
            self.assertEqual(own.prior_device_trial_users, 1)
            rows = (await session.execute(select(TrialRiskEvent))).scalars().all()
            self.assertEqual({row.user_id for row in rows}, {1, 2})
            self.assertTrue(all(row.telegram_id is None for row in rows))
            self.assertTrue(all(row.ip_hash and row.ip_hash != args["remote_ip"] for row in rows))

    async def test_ads_count_native_accounts_separately_and_keep_shared_per_account_cap(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            session.add(CourseAdCreative(id=1, title="Course notice", media_path="unused.mp4", media_type="video",
                placements=PLACEMENT_SCREEN_CENTER, duration_seconds=7, language="all", is_active=True))
            await session.flush()
            ads = AdPlacementService(session)
            await ads.save_settings({"placements": {PLACEMENT_SCREEN_CENTER: {"enabled": True, "daily_cap": 1}}})
            seen = await ads.record_view(alice, placement=PLACEMENT_SCREEN_CENTER, ad_id=1, watched_seconds=7)
            self.assertTrue(seen["ok"], seen)
            a = await ads.status(alice, placement=PLACEMENT_SCREEN_CENTER, client="android")
            b = await ads.status(bob, placement=PLACEMENT_SCREEN_CENTER, client="desktop")
            self.assertEqual((a["used"], a["remaining"]), (1, 0))
            self.assertEqual((b["used"], b["remaining"]), (0, 1))
            row = (await session.execute(select(CourseAdView))).scalars().one()
            self.assertEqual((row.user_id, row.user_telegram_id), (1, None))

    async def _devices(self, session):
        for uid in (1, 2):
            device = DesktopDevice(id=f"native-device-{uid}", user_id=uid, telegram_id=None,
                installation_key_hash=str(uid) * 64, platform="android", app_version="1.0")
            session.add(device)
            session.add(AndroidPushToken(device_id=device.id, token=f"test-fcm-{uid}", notifications_allowed=True))
        await session.commit()

    async def test_notices_target_claim_and_ack_only_the_canonical_owner(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            await self._devices(session)
            service = NotificationDeliveryService(session, self.settings)
            service.push.send_batch = AsyncMock(return_value=[AndroidPushResult(accepted=True)])
            bot = SimpleNamespace(send_message=AsyncMock())
            self.assertTrue(await service.reachable(alice))
            self.assertEqual(await service._android_targets(alice), [("test-fcm-1", "native-device-1")])
            result = await service.deliver(bot, alice, key="limit_daily_spent", lang="uz",
                telegram=TelegramNotice(text="Kunlik limit"), reason="native_test")
            self.assertEqual(result, "android")
            sent = service.push.send_batch.await_args.args[0]
            self.assertEqual([(target.token, target.device_id) for target in sent], [("test-fcm-1", "native-device-1")])
            notice = (await session.execute(select(AccountNoticeDelivery))).scalars().one()
            self.assertEqual((notice.user_id, notice.telegram_id), (1, None))
            self.assertIsNone(await service.claim(notice.id, telegram_id=bob))
            self.assertFalse(await service.acknowledge(notice.id, telegram_id=bob, device_id="native-device-2", shown=False))
            self.assertTrue((await session.get(AndroidPushToken, "native-device-2")).notifications_allowed)
            self.assertFalse(await service.acknowledge(notice.id, telegram_id=alice, device_id="native-device-2", shown=False))
            self.assertTrue((await session.get(AndroidPushToken, "native-device-2")).notifications_allowed)
            own = await service.claim(notice.id, telegram_id=alice)
            self.assertTrue(own["show"])
            self.assertTrue(await service.acknowledge(notice.id, telegram_id=alice, device_id="native-device-1", shown=True))
            self.assertEqual(notice.status, STATUS_SHOWN)
            self.assertIsNone(notice.fallback_due_at)
            bot.send_message.assert_not_awaited()

    async def test_unshown_notice_never_falls_back_to_a_fabricated_telegram_id(self):
        async with self.sessions() as session:
            alice = await session.get(User, 1)
            await self._devices(session)
            service = NotificationDeliveryService(session, self.settings)
            service.push.send_batch = AsyncMock(return_value=[AndroidPushResult(accepted=True)])
            bot = SimpleNamespace(send_message=AsyncMock())
            await service.deliver(bot, alice, key="limit_daily_spent", lang="uz",
                telegram=TelegramNotice(text="Limit"), reason="native_test")
            notice = (await session.execute(select(AccountNoticeDelivery))).scalars().one()
            notice.fallback_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            self.assertEqual(await service.send_due_fallbacks(bot), 0)
            self.assertEqual(notice.status, STATUS_FAILED)
            self.assertIsNone(notice.telegram_sent_at)
            bot.send_message.assert_not_awaited()

    async def test_provider_referral_attributes_new_telegram_onboarding_canonically(self):
        async with self.sessions() as session:
            provider = await session.get(User, 1)
            await UserRepository(session).ensure_referral_code(provider)
            self.assertTrue(provider.referral_code)
            provider.referral_code = "a1b2c3d4"
            await session.commit()
            newcomer, created = await OnboardingService(session).get_or_create_user(
                telegram_id=7007, full_name="New Telegram learner", referral_code=provider.referral_code,
            )
            self.assertTrue(created)
            self.assertEqual(newcomer.telegram_id, 7007)
            self.assertIsNone(newcomer.referred_by_telegram_id)
            self.assertEqual((await session.scalar(select(Referral))).referrer_user_id, provider.id)
            self.assertEqual(newcomer.referrer_id, provider.id)
            self.assertIsNone(provider.telegram_id)
            self.assertNotEqual(provider.id, newcomer.id)

    async def test_android_bearer_http_bootstrap_profile_trial_and_telegram_only_guards(self):
        async with self.sessions() as session:
            await self._devices(session)
            device = await session.get(DesktopDevice, "native-device-1")
            native_session = DesktopSession(id="native-http-session", device_id=device.id,
                refresh_token_hash="r" * 64, expires_at=datetime.now(timezone.utc) + timedelta(days=1))
            session.add(native_session)
            await session.commit()
            token, _ = DesktopAuthService(session, self.settings)._access_token(
                desktop_session=native_session, device=device,
            )
        bot = SimpleNamespace(send_message=AsyncMock())
        app = FastAPI()
        app.include_router(create_android_auth_router(session_factory=self.sessions, settings_obj=self.settings))
        app.include_router(create_android_features_router(session_factory=self.sessions, settings_obj=self.settings, bot=bot))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://native.test",
                               headers={"Authorization": "Bearer " + token}) as client:
            for path in ("/api/v3/android/bootstrap", "/api/v3/android/profile", "/api/v3/android/subscription/overview"):
                response = await client.get(path)
                self.assertEqual(response.status_code, 200, (path, response.text))
                self.assertTrue(response.json()["ok"])
            before = await client.get("/api/v3/android/trial/status")
            self.assertEqual(before.status_code, 200, before.text)
            self.assertTrue(before.json()["trial"]["eligible"])
            started = await client.post("/api/v3/android/trial/start")
            self.assertEqual(started.status_code, 200, started.text)
            after = await client.get("/api/v3/android/trial/status")
            self.assertFalse(after.json()["trial"]["eligible"])
            referral = await client.get("/api/v3/android/referral/overview")
            self.assertEqual(referral.status_code, 200, referral.text)
            self.assertIn("&mode=trial", referral.json()["link"])
            payment = await client.post("/api/v3/android/subscription/open")
            # This compatibility endpoint opens the Telegram checkout. Native
            # Direct checkout uses the dedicated quote/receipt endpoints.
            self.assertEqual(payment.status_code, 409, payment.text)
            self.assertEqual(payment.json()["error"], "payment_telegram_required")
            currency = await client.put("/api/v3/android/subscription/currency-preference", json={"currency": "USD"})
            self.assertEqual(currency.status_code, 200, currency.text)
            self.assertEqual(currency.json()["currency"], "USD")
        async with self.sessions() as session:
            provider = await session.get(User, 1)
            other = await session.get(User, 2)
            self.assertIsNone(provider.telegram_id)
            self.assertTrue(provider.referral_code)
            self.assertFalse(other.trial_used)
            self.assertEqual(provider.subscription_currency, "USD")
        bot.send_message.assert_not_awaited()
