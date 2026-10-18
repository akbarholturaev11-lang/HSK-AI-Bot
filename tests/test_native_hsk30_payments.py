"""HSK 3.0 one-time purchase belongs to the account, independently of Telegram."""
import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_features import create_android_features_router
from app.api.desktop_subscription import create_desktop_subscription_router
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget
from app.db.models.course_track_state import CourseTrackState
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_notify_service import AdminNotifyService
from app.services.course_track_service import CourseTrackService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.hsk30_feature_service import HSK30_ENABLED_SETTINGS_KEY
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE, HSK30_UNLOCK_PRICE_KEY, Hsk30UnlockService
from app.services.payment_notify_service import PaymentNotifyService
from app.services.subscription_miniapp_service import PAYMENT_DETAILS_KEY, SubscriptionMiniAppService
from tests.native_postgres_deadlines import postgres_timeout


PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
       "+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class NativeHsk30PaymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="native-hsk30-test-" + "x" * 48,
                                        BOT_USERNAME="fixture_bot")
        self.headers = {}
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, full_name="Google learner", status="free", language="uz"),
                User(id=2, telegram_id=None, full_name="Apple learner", status="free", language="ru"),
                User(id=3, telegram_id=1, full_name="Real Telegram learner", status="free", language="uz"),
                User(id=4, telegram_id=None, full_name="Windows learner", status="free", language="tj"),
            ])
            await session.flush()
            for uid, platform in ((1, "android"), (2, "macos"), (4, "windows")):
                device = DesktopDevice(id=f"hsk30-device-{uid}", user_id=uid, telegram_id=None,
                    platform=platform, app_version="1.4.3", installation_key_hash=f"hsk30-key-{uid}")
                session.add(device)
                await session.flush()
                auth = DesktopSession(id=f"hsk30-session-{uid}", device_id=device.id,
                    refresh_token_hash=f"hsk30-refresh-{uid}", expires_at=datetime.now(timezone.utc) + timedelta(days=1))
                session.add(auth)
                await session.flush()
                token, _ = DesktopAuthService(session, self.settings)._access_token(desktop_session=auth, device=device)
                self.headers[uid] = {"Authorization": "Bearer " + token}
            settings = BotSettingRepository(session)
            await settings.set(HSK30_ENABLED_SETTINGS_KEY, "1")
            await settings.set(PAYMENT_DETAILS_KEY, "HSK30 TEST BANK DETAILS")
            await session.commit()
        self.bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="fixture_bot")))
        app = FastAPI()
        common = dict(session_factory=self.sessions, settings_obj=self.settings, bot=self.bot)
        app.include_router(create_android_features_router(**common))
        app.include_router(create_desktop_subscription_router(**common))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://native.test")
        self.funnel = patch("app.services.conversion_funnel_service.async_session_maker", self.sessions)
        self.funnel.start()

    async def asyncTearDown(self):
        await self.client.aclose()
        self.funnel.stop()
        await self.engine.dispose()

    async def _pending(self, session, uid):
        user = await session.get(User, uid)
        payment = await PaymentRepository(session).create(user, HSK30_UNLOCK_PLAN_TYPE, 10, currency="TJS")
        await session.commit()
        return payment

    async def _review(self, session, payment, action):
        from tests.test_main_imports import MainModuleImportTests
        main = MainModuleImportTests._import_main()
        with (patch.object(main, "async_session_maker", self.sessions),
              patch.object(main.ConversionFunnelService, "record", new=AsyncMock(return_value=True)),
              patch.object(main.CourseMiniAppAnalyticsService, "record_server_event", new=AsyncMock(return_value={"recorded": False})),
              patch.object(PaymentNotifyService, "_android_push", new=AsyncMock())):
            return await main._review_admin_payment(session, payment_id=payment.id, action=action, reason=None)

    async def _bot_review(self, session, payment_id, action):
        from app.bot.handlers import admin_payments
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=99), data=f"admin_payment:{action}:{payment_id}",
            answer=AsyncMock(), message=SimpleNamespace(edit_reply_markup=AsyncMock()),
            bot=SimpleNamespace(send_message=AsyncMock(), delete_message=AsyncMock()),
        )
        with (
            patch.object(admin_payments, "_is_admin", return_value=True),
            patch.object(admin_payments.ConversionFunnelService, "record", new=AsyncMock(return_value=True)),
            patch.object(admin_payments.CourseMiniAppAnalyticsService, "record_server_event", new=AsyncMock(return_value={"recorded": False})),
            patch.object(PaymentNotifyService, "_android_push", new=AsyncMock()),
        ):
            handler = (admin_payments.admin_payment_approve_handler if action == "approve"
                       else admin_payments.admin_payment_reject_handler)
            await handler(callback, session)
        callback.bot.send_message.assert_not_awaited()
        callback.bot.delete_message.assert_not_awaited()
        return callback

    async def test_direct_macos_windows_checkout_isolated_at_unchanged_one_time_price(self):
        ids = {}
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock(return_value="HSK30_RECEIPT")) as delivery:
            for uid in (1, 2, 4):
                with self.subTest(user_id=uid):
                    base = "/api/v3/android/subscription/checkout" if uid == 1 else "/api/v3/desktop/subscription"
                    query = "?origin=hsk30_content" if uid == 1 else "?mode=hsk30_unlock"
                    overview = await self.client.get(base + "/overview" + query, headers=self.headers[uid])
                    self.assertEqual(overview.status_code, 200, overview.text)
                    self.assertEqual(overview.json()["mode"], "hsk30_unlock")
                    self.assertTrue(overview.json()["checkout_allowed"])
                    self.assertEqual(set(overview.json()["prices"]["visa"]), {HSK30_UNLOCK_PLAN_TYPE})
                    body = dict(plan_type=HSK30_UNLOCK_PLAN_TYPE, payment_method="visa", card_country="tj")
                    quote = await self.client.post(base + "/quote", headers=self.headers[uid], json=body)
                    self.assertEqual(quote.status_code, 200, quote.text)
                    self.assertEqual((quote.json()["quote"]["final_amount"], quote.json()["quote"]["final_currency"]), (10, "TJS"))
                    self.assertFalse(quote.json()["quote"]["discount_applied"])
                    body.update(screenshot_data_url=PNG, attempt_id=overview.json()["attempt_id"])
                    submitted = await self.client.post(base + "/submit", headers=self.headers[uid], json=body)
                    self.assertEqual(submitted.status_code, 200, submitted.text)
                    self.assertTrue(submitted.json()["provisional_access"])
                    ids[uid] = submitted.json()["payment_id"]
                    duplicate = await self.client.post(base + "/submit", headers=self.headers[uid], json=body)
                    self.assertEqual(duplicate.status_code, 200, duplicate.text)
                    self.assertEqual(duplicate.json()["payment_id"], ids[uid])
                    self.assertTrue(duplicate.json()["already_pending"])
            self.assertEqual(delivery.await_count, 3)
        async with self.sessions() as session:
            self.assertEqual(len(set(ids.values())), 3)
            for uid, pid in ids.items():
                payment, user = await session.get(Payment, pid), await session.get(User, uid)
                self.assertEqual((payment.user_id, payment.user_telegram_id, payment.amount), (uid, None, 10))
                self.assertTrue((await CourseTrackService(session).hsk30_access(user)).provisional_access)
                self.assertTrue(user.payment_preview_available)
                self.assertIsNone(user.payment_preview_payment_id)
                self.assertEqual(user.payment_status, "none")
            legacy = await session.get(User, 3)
            self.assertFalse((await CourseTrackService(session).hsk30_access(legacy)).allowed)
            self.assertIsNone((await SubscriptionMiniAppService(session).overview(1))["pending_payment"])
            self.assertEqual(await session.scalar(select(func.count()).select_from(AIUsageBudget)), 0)

    async def test_admin_approval_grants_only_permanent_track_without_pro_or_preview_refill(self):
        async with self.sessions() as session:
            payment = await self._pending(session, 1)
            user = await session.get(User, 1)
            user.payment_preview_available = False
            await session.commit()
            self.assertEqual(await self._review(session, payment, "approve"),
                ({"ok": True, "status": "approved", "product": HSK30_UNLOCK_PLAN_TYPE}, 200))
            state = await session.scalar(select(CourseTrackState).where(CourseTrackState.user_id == 1))
            self.assertEqual(state.unlock_payment_id, payment.id)
            self.assertIsNotNone(state.unlocked_at)
            self.assertEqual((user.status, user.payment_status, user.end_date, user.payment_preview_available),
                             ("free", "none", None, False))
            self.assertIsNone(await session.scalar(select(CourseTrackState).where(CourseTrackState.user_id == 2)))
            self.assertEqual(await session.scalar(select(func.count()).select_from(AIUsageBudget)), 0)
            self.assertEqual((await self._review(session, payment, "approve"))[1], 409)

    async def test_rejected_retry_and_blocked_pending_do_not_open_another_account(self):
        async with self.sessions() as session:
            own, other = await self._pending(session, 1), await self._pending(session, 2)
            self.assertEqual((await self._review(session, own, "reject"))[1], 200)
            owner, neighbour = await session.get(User, 1), await session.get(User, 2)
            self.assertFalse((await CourseTrackService(session).hsk30_access(owner)).allowed)
            self.assertTrue((await CourseTrackService(session).hsk30_access(neighbour)).provisional_access)
            retry = await self._pending(session, 1)
            self.assertFalse(await Hsk30UnlockService(session).is_provisional_payment(owner, retry))
            self.assertFalse(await Hsk30UnlockService(session).is_provisional_payment(owner, other))
            owner.status = "blocked"
            await session.commit()
            self.assertFalse((await CourseTrackService(session).hsk30_access(owner)).allowed)
            self.assertEqual(await self._review(session, retry, "approve"),
                ({"ok": False, "error": "hsk30_unlock_failed"}, 400))
            await session.refresh(owner)
            await session.refresh(retry)
            self.assertEqual((owner.status, retry.payment_status), ("blocked", "pending"))

    async def test_canonical_owner_overrides_null_or_conflicting_telegram_metadata(self):
        async with self.sessions() as session:
            payment = await self._pending(session, 2)
            payment.payment_status = "approved"
            payment.user_telegram_id = 1
            service = Hsk30UnlockService(session)
            self.assertFalse(await service.grant(user=await session.get(User, 1), payment=payment))
            self.assertFalse(await service.grant(user=await session.get(User, 3), payment=payment))
            self.assertTrue(await service.grant(user=await session.get(User, 2), payment=payment))
            self.assertEqual([(state.user_id, state.unlock_payment_id) for state in
                (await session.scalars(select(CourseTrackState))).all()], [(2, payment.id)])

    async def test_bot_admin_approval_and_replay_keep_native_purchase_separate_from_pro(self):
        async with self.sessions() as session:
            payment = await self._pending(session, 2)
            payment_id = payment.id
            user = await session.get(User, 2)
            user.payment_preview_available = False
            user.selected_plan_type = "3_months"
            await session.commit()
            callback = await self._bot_review(session, payment_id, "approve")
            callback.answer.assert_awaited_with("✅ HSK 3.0 ochildi!", show_alert=True)
            await session.refresh(payment)
            self.assertEqual(payment.payment_status, "approved")
            access = await CourseTrackService(session).hsk30_access(user)
            self.assertTrue(access.permanently_unlocked)
            self.assertFalse(access.paid_access)
            self.assertEqual((user.status, user.payment_status, user.end_date, user.payment_preview_available,
                              user.payment_preview_payment_id, user.selected_plan_type),
                             ("free", "none", None, False, None, "3_months"))
            state = await session.scalar(select(CourseTrackState).where(CourseTrackState.user_id == 2))
            unlocked_at = state.unlocked_at
            for action in ("approve", "reject"):
                callback = await self._bot_review(session, payment_id, action)
                callback.answer.assert_awaited_with("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)
            await session.refresh(state)
            self.assertEqual(state.unlocked_at, unlocked_at)
            self.assertEqual(await session.scalar(select(func.count()).select_from(CourseTrackState)), 1)
            self.assertEqual(await session.scalar(select(func.count()).select_from(AIUsageBudget)), 0)

    async def test_bot_admin_rejection_revokes_only_owner_hsk30_and_replay_cannot_grant(self):
        async with self.sessions() as session:
            own, other = await self._pending(session, 2), await self._pending(session, 4)
            owner = await session.get(User, 2)
            callback = await self._bot_review(session, own.id, "reject")
            callback.answer.assert_awaited_with("❌ Rad etildi", show_alert=True)
            self.assertFalse((await CourseTrackService(session).hsk30_access(owner)).allowed)
            self.assertTrue((await CourseTrackService(session).hsk30_access(await session.get(User, 4))).provisional_access)
            callback = await self._bot_review(session, own.id, "approve")
            callback.answer.assert_awaited_with("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)
            self.assertTrue(owner.payment_preview_available)
            self.assertIsNone(owner.payment_preview_payment_id)
            self.assertIsNone(await session.scalar(select(CourseTrackState)))
            self.assertEqual(other.payment_status, "pending")

    async def test_bot_review_cannot_unblock_native_owner(self):
        async with self.sessions() as session:
            payment = await self._pending(session, 2)
            payment_id = payment.id
            owner = await session.get(User, 2)
            owner.status = "blocked"
            await session.commit()
            callback = await self._bot_review(session, payment_id, "approve")
            callback.answer.assert_awaited_with("HSK 3.0 ni ochib bo'lmadi", show_alert=True)
            await session.refresh(owner)
            await session.refresh(payment)
            self.assertEqual((owner.status, payment.payment_status), ("blocked", "pending"))
            self.assertIsNone(await session.scalar(select(CourseTrackState)))

    async def test_provider_quote_respects_admin_price_without_subscription_discount(self):
        async with self.sessions() as session:
            await BotSettingRepository(session).set(HSK30_UNLOCK_PRICE_KEY, "17")
            await session.commit()
        for uid in (1, 2, 4):
            base = "/api/v3/android/subscription/checkout" if uid == 1 else "/api/v3/desktop/subscription"
            response = await self.client.post(base + "/quote", headers=self.headers[uid], json={
                "plan_type": HSK30_UNLOCK_PLAN_TYPE, "payment_method": "visa", "card_country": "tj",
            })
            self.assertEqual(response.status_code, 200, response.text)
            quote = response.json()["quote"]
            self.assertEqual((quote["base_amount"], quote["final_amount"], quote["final_currency"]), (17, 17, "TJS"))
            self.assertFalse(quote["discount_applied"])

    async def test_failed_admin_delivery_rolls_back_native_payment_and_provisional_access(self):
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock(side_effect=RuntimeError("fixture failure"))):
            response = await self.client.post("/api/v3/android/subscription/checkout/submit", headers=self.headers[1], json={
                "plan_type": HSK30_UNLOCK_PLAN_TYPE, "payment_method": "visa", "card_country": "tj",
                "screenshot_data_url": PNG,
            })
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["error"], "admin_notification_failed")
        async with self.sessions() as session:
            owner = await session.get(User, 1)
            self.assertFalse((await CourseTrackService(session).hsk30_access(owner)).allowed)
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 0)
            self.assertEqual(await session.scalar(select(func.count()).select_from(AIUsageBudget)), 0)
            self.assertTrue(owner.payment_preview_available)

    async def test_blocked_provider_cannot_create_checkout_with_an_existing_native_session(self):
        async with self.sessions() as session:
            for uid in (1, 2, 4):
                (await session.get(User, uid)).status = "blocked"
            await session.commit()
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock()) as deliver:
            for uid in (1, 2, 4):
                base = "/api/v3/android/subscription/checkout" if uid == 1 else "/api/v3/desktop/subscription"
                for action in ("quote", "submit"):
                    body = {"plan_type": HSK30_UNLOCK_PLAN_TYPE, "payment_method": "visa", "card_country": "tj"}
                    if action == "submit":
                        body["screenshot_data_url"] = PNG
                    response = await self.client.post(base + "/" + action, headers=self.headers[uid], json=body)
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertIn(response.json()["error"], {"user_blocked", "desktop_subscription_blocked"})
            deliver.assert_not_awaited()
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(Payment)), 0)

    async def test_native_hsk30_purge_keeps_anonymous_approved_financial_fact(self):
        async with self.sessions() as session:
            approved = await self._pending(session, 1)
            approved_id = approved.id
            self.assertEqual((await self._review(session, approved, "approve"))[1], 200)
            approved.screenshot_file_id, approved.admin_comment = "private-receipt", "private-name"
            pending, other = await self._pending(session, 1), await self._pending(session, 2)
            pending_id, other_id = pending.id, other.id
            self.assertTrue(await UserRepository(session).delete_by_user_id(1))
            await session.commit()
            retained = await session.get(Payment, approved_id)
            await session.refresh(retained)
            self.assertEqual((retained.user_id, retained.user_telegram_id, retained.plan_type,
                              retained.payment_status, retained.amount, retained.currency),
                             (None, -1, HSK30_UNLOCK_PLAN_TYPE, "approved", 10, "TJS"))
            self.assertIsNone(retained.screenshot_file_id)
            self.assertIsNone(retained.admin_comment)
            self.assertIsNone(await session.get(Payment, pending_id, populate_existing=True))
            self.assertEqual((await session.get(Payment, other_id)).user_id, 2)
            self.assertIsNone(await session.scalar(select(CourseTrackState).where(CourseTrackState.user_id == 1)))


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"), "requires isolated PostgreSQL test database")
class NativeHsk30ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "native_hsk30_test_" + uuid4().hex
        self.admin = create_async_engine(os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"],
            connect_args={"timeout": postgres_timeout(60)})
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"],
            connect_args={"timeout": postgres_timeout(60), "server_settings": {"search_path": self.schema + ",public"}})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([User(id=1, telegram_id=None, status="free"), User(id=2, telegram_id=None, status="free")])
            await BotSettingRepository(session).set(HSK30_ENABLED_SETTINGS_KEY, "1")
            await BotSettingRepository(session).set(PAYMENT_DETAILS_KEY, "HSK30 TEST BANK DETAILS")
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def test_simultaneous_hsk30_receipts_create_one_pending_per_canonical_account(self):
        async def submit(uid):
            async with self.sessions() as session:
                result = await SubscriptionMiniAppService(session).submit(
                    telegram_id=await session.get(User, uid), plan_type=HSK30_UNLOCK_PLAN_TYPE,
                    payment_method="visa", card_country="tj", screenshot_data_url=PNG,
                    bot=SimpleNamespace(), source="android_subscription",
                )
                self.assertTrue(result["ok"], result)
                return uid, result["payment_id"]
        with patch.object(AdminNotifyService, "notify_payment_review", new=AsyncMock(return_value="HSK30_RECEIPT")) as deliver:
            results = await asyncio.wait_for(asyncio.gather(*(submit(uid) for uid in (1, 1, 1, 1, 2, 2))), timeout=postgres_timeout(15))
            self.assertEqual(deliver.await_count, 2)
        for uid in (1, 2):
            self.assertEqual(len({pid for actual, pid in results if actual == uid}), 1)
        self.assertEqual(len({pid for _, pid in results}), 2)
        async with self.sessions() as session:
            rows = list((await session.scalars(select(Payment))).all())
            self.assertCountEqual([(row.user_id, row.user_telegram_id, row.amount, row.payment_status) for row in rows],
                                  [(1, None, 10, "pending"), (2, None, 10, "pending")])
            self.assertEqual(await session.scalar(select(func.count()).select_from(AIUsageBudget)), 0)

    async def test_simultaneous_native_grants_create_one_track_state_under_user_lock(self):
        async with self.sessions() as session:
            owner = await session.get(User, 1)
            ids = []
            for _ in range(2):
                payment = await PaymentRepository(session).create(owner, HSK30_UNLOCK_PLAN_TYPE, 10,
                    currency="TJS", payment_status="approved")
                ids.append(payment.id)
            await session.commit()
        async def grant(payment_id):
            async with self.sessions() as session:
                user, payment = await session.get(User, 1), await session.get(Payment, payment_id)
                result = await Hsk30UnlockService(session).grant(user=user, payment=payment)
                await session.commit()
                return result
        self.assertEqual(await asyncio.wait_for(asyncio.gather(*(grant(pid) for pid in ids)), timeout=postgres_timeout(15)), [True, True])
        async with self.sessions() as session:
            rows = list((await session.scalars(select(CourseTrackState))).all())
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].user_id, 1)
            self.assertIn(rows[0].unlock_payment_id, ids)
            self.assertIsNotNone(rows[0].unlocked_at)
            self.assertEqual((await session.get(User, 1)).payment_status, "none")

    async def test_course_switch_and_admin_grant_share_user_before_track_lock_order(self):
        from app.db.models.course_progress import CourseProgress
        for uid, existing_track in ((1, False), (2, True)):
            with self.subTest(existing_track=existing_track):
                async with self.sessions() as session:
                    owner = await session.get(User, uid)
                    owner.level = "hsk1"
                    session.add(CourseProgress(user_id=uid, level="hsk1"))
                    session.add(CourseTrackState(user_id=uid, track="hsk20", level="hsk1"))
                    if existing_track:
                        session.add(CourseTrackState(user_id=uid, track="hsk30", level="nhsk1"))
                    payment = await PaymentRepository(session).create(owner, HSK30_UNLOCK_PLAN_TYPE, 10,
                        currency="TJS", payment_status="approved")
                    await session.commit()
                    payment_id = payment.id
                admin_has_user, switch_has_track = asyncio.Event(), asyncio.Event()

                async def approve():
                    async with self.sessions() as session:
                        owner = await PaymentRepository(session).resolve_owner(await session.get(User, uid), lock=True)
                        admin_has_user.set()
                        try:
                            await asyncio.wait_for(switch_has_track.wait(), timeout=0.5)
                        except asyncio.TimeoutError:
                            pass
                        self.assertTrue(await Hsk30UnlockService(session).grant(
                            user=owner, payment=await session.get(Payment, payment_id)))
                        await session.commit()

                async def switch():
                    await admin_has_user.wait()
                    async with self.sessions() as session:
                        service = CourseTrackService(session)
                        original = service.state_repo.get
                        async def read_state(user_id, track, *, for_update=False):
                            state = await original(user_id, track, for_update=for_update)
                            if track == "hsk30" and for_update:
                                switch_has_track.set()
                            return state
                        service.state_repo.get = read_state
                        await service.switch(await session.get(User, uid), target_track="hsk30", allow_locked_hsk30=True)
                        await session.commit()

                await asyncio.wait_for(asyncio.gather(approve(), switch()), timeout=postgres_timeout(15))
                async with self.sessions() as session:
                    state = await session.scalar(select(CourseTrackState).where(
                        CourseTrackState.user_id == uid, CourseTrackState.track == "hsk30"))
                    self.assertIsNotNone(state.unlocked_at)
                    self.assertEqual(state.unlock_payment_id, payment_id)
                    self.assertEqual((await session.get(User, uid)).level, "nhsk1")
