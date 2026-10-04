"""Subscription and limit notices go to the Android app first, Telegram second.

The phone must confirm it showed the notice. Without that confirmation within
ten minutes the stored Telegram message is sent, and a phone that looks the
notice up afterwards is told not to show it, so nobody gets it twice.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_push import create_android_push_router
from app.db.base import Base
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.user import User
from app.services.android_push_service import AndroidPushResult, AndroidPushService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.discount_notification_service import DiscountNotificationService
from app.services.expiry_reminder_service import ExpiryReminderService
from app.services.notification_delivery_service import (
    ANDROID_CONFIRM_TIMEOUT,
    APP_TITLE,
    PUSH_KIND,
    NotificationDeliveryService,
    TelegramNotice,
    phone_copy,
)

from tests.test_android_push import user


def settings(**overrides):
    values = dict(
        DESKTOP_AUTH_SIGNING_SECRET="android-notice-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
        ANDROID_FCM_PROJECT_ID="test-project",
        ANDROID_FCM_SERVICE_ACCOUNT_JSON="",
        ANDROID_PUSH_UPDATES_ENABLED=False,
        ANDROID_PUSH_STUDY_ENABLED=False,
        ANDROID_PUSH_NOTICES_ENABLED=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class _Bot:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []
        self.photos = []

    async def send_message(self, **kwargs):
        if self.fail:
            raise RuntimeError("telegram unavailable")
        self.messages.append(kwargs)

    async def send_photo(self, **kwargs):
        self.photos.append(kwargs)


class PhoneCopyTests(unittest.TestCase):
    def test_the_bold_headline_becomes_the_title(self):
        title, body = phone_copy(
            "trial_expiring",
            "uz",
            "👑 <b>Pro sinovi tugadi</b>\n\n<blockquote>Progress joyida.</blockquote>",
        )
        self.assertEqual("👑 Pro sinovi tugadi", title)
        self.assertEqual("Progress joyida.", body)

    def test_a_one_line_notice_uses_the_feed_title_for_its_key(self):
        title, body = phone_copy("subscription_expiring", "ru", "Завтра день окончания вашей подписки.")
        self.assertEqual("Подписка скоро закончится", title)
        self.assertEqual("Завтра день окончания вашей подписки.", body)

    def test_a_one_line_notice_without_a_feed_title_is_signed_by_the_app(self):
        title, body = phone_copy("daily_limit_renewed", "uz", "✅ Kunlik limitingiz yangilandi.")
        self.assertEqual(APP_TITLE, title)
        self.assertEqual("✅ Kunlik limitingiz yangilandi.", body)


class TelegramNoticeTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_delayed_copy_is_the_same_telegram_request(self):
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Obuna", web_app=WebAppInfo(url="https://example.test/sub")),
            InlineKeyboardButton(text="Keyinroq", callback_data="sub_churn:later"),
        ]])
        notice = TelegramNotice(text="<b>Salom</b>", reply_markup=markup, parse_mode="HTML")
        restored = TelegramNotice.from_payload(notice.to_payload())

        immediate, delayed = _Bot(), _Bot()
        await notice.send(immediate, 7)
        await restored.send(delayed, 7)
        self.assertEqual(immediate.messages, delayed.messages)
        self.assertEqual(
            "https://example.test/sub",
            delayed.messages[0]["reply_markup"].inline_keyboard[0][0].web_app.url,
        )

    async def test_only_the_arguments_the_notice_had_are_sent(self):
        bot = _Bot()
        await TelegramNotice(text="Ertaga obunangiz tugash kuni.").send(bot, 5)
        self.assertEqual([{"chat_id": 5, "text": "Ertaga obunangiz tugash kuni."}], bot.messages)

    async def test_campaign_media_survives_the_delay(self):
        notice = TelegramNotice(
            text="Chegirma", parse_mode="HTML", media_type="photo", media_file_id="file-1",
            disable_web_page_preview=None,
        )
        bot = _Bot()
        await TelegramNotice.from_payload(notice.to_payload()).send(bot, 9)
        self.assertEqual(
            [{"chat_id": 9, "photo": "file-1", "caption": "Chegirma", "parse_mode": "HTML"}],
            bot.photos,
        )


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
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
        app = FastAPI()
        app.include_router(create_android_push_router(
            session_factory=self.sessions, settings_obj=self.settings,
        ))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://test.local")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _link(self, session, telegram_id, installation_key):
        auth = DesktopAuthService(session, self.settings)
        started = await auth.start_link(
            platform="android", app_version="1.0.0", installation_key=installation_key,
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

    async def _register(self, token, *, allowed):
        await self.client.post(
            "/api/v3/android/push/register",
            json={"token": "fcm-token-" + token[:4] + "x" * 32},
            headers=self.bearer(token),
        )
        preferences = {"study_reminders_enabled": False, "timezone_name": "UTC"}
        if allowed is not None:
            preferences["notifications_allowed"] = allowed
        response = await self.client.post(
            "/api/v3/android/push/preferences", json=preferences, headers=self.bearer(token),
        )
        self.assertEqual(200, response.status_code)

    async def _deliver(self, bot, *, accepted=True, telegram_id=1001):
        async with self.sessions() as session:
            learner = (
                await session.execute(select(User).where(User.telegram_id == telegram_id))
            ).scalar_one()
            with patch.object(
                AndroidPushService,
                "send_batch",
                new_callable=AsyncMock,
                return_value=[AndroidPushResult(accepted)],
            ) as send:
                outcome = await NotificationDeliveryService(session, self.settings).deliver(
                    bot,
                    learner,
                    key="subscription_expiring",
                    lang="uz",
                    telegram=TelegramNotice(text="Ertaga obunangiz tugash kuni."),
                    reason="expiry_reminder",
                )
                await session.commit()
            return outcome, send

    async def _rows(self):
        async with self.sessions() as session:
            return (await session.execute(select(AccountNoticeDelivery))).scalars().all()

    async def _sweep(self, bot, *, now=None):
        async with self.sessions() as session:
            return await NotificationDeliveryService(session, self.settings).send_due_fallbacks(
                bot, now=now
            )

    async def test_a_phone_that_allows_notices_gets_it_instead_of_telegram(self):
        await self._register(self.token_a, allowed=True)
        bot = _Bot()
        outcome, send = await self._deliver(bot)

        self.assertEqual("android", outcome)
        self.assertEqual([], bot.messages)
        target = send.await_args.args[0][0]
        self.assertEqual(self.device_a, target.device_id)
        self.assertEqual(PUSH_KIND, target.data["kind"])
        [row] = await self._rows()
        self.assertEqual("android_pending", row.status)
        self.assertEqual(target.data["notice_id"], row.id)

    async def test_without_the_app_telegram_is_sent_at_once(self):
        bot = _Bot()
        outcome, send = await self._deliver(bot)
        self.assertEqual("telegram", outcome)
        self.assertEqual(1, len(bot.messages))
        send.assert_not_awaited()
        self.assertEqual([], await self._rows())

    async def test_an_older_build_that_never_reported_stays_on_telegram(self):
        await self._register(self.token_a, allowed=None)
        bot = _Bot()
        outcome, send = await self._deliver(bot)
        self.assertEqual("telegram", outcome)
        send.assert_not_awaited()

    async def test_a_phone_without_permission_stays_on_telegram(self):
        await self._register(self.token_a, allowed=False)
        bot = _Bot()
        outcome, _ = await self._deliver(bot)
        self.assertEqual("telegram", outcome)

    async def test_the_kill_switch_keeps_everything_on_telegram(self):
        await self._register(self.token_a, allowed=True)
        self.settings.ANDROID_PUSH_NOTICES_ENABLED = False
        bot = _Bot()
        outcome, send = await self._deliver(bot)
        self.assertEqual("telegram", outcome)
        send.assert_not_awaited()

    async def test_when_no_phone_accepts_the_push_telegram_goes_now(self):
        await self._register(self.token_a, allowed=True)
        bot = _Bot()
        outcome, _ = await self._deliver(bot, accepted=False)
        self.assertEqual("telegram", outcome)
        self.assertEqual(1, len(bot.messages))
        [row] = await self._rows()
        self.assertEqual("telegram_sent", row.status)

    async def test_a_confirmed_notice_never_reaches_telegram(self):
        await self._register(self.token_a, allowed=True)
        await self._deliver(_Bot())
        [row] = await self._rows()

        shown = await self.client.get(
            f"/api/v3/android/notices/{row.id}", headers=self.bearer(self.token_a),
        )
        self.assertEqual(200, shown.status_code)
        notice = shown.json()["notice"]
        self.assertTrue(notice["show"])
        self.assertEqual("Obuna tugayapti", notice["title"])
        self.assertEqual("Ertaga obunangiz tugash kuni.", notice["body"])
        self.assertEqual("subscription", notice["action"])

        ack = await self.client.post(
            f"/api/v3/android/notices/{row.id}/ack",
            json={"shown": True},
            headers=self.bearer(self.token_a),
        )
        self.assertEqual(200, ack.status_code)

        bot = _Bot()
        later = datetime.now(timezone.utc) + ANDROID_CONFIRM_TIMEOUT * 2
        self.assertEqual(0, await self._sweep(bot, now=later))
        self.assertEqual([], bot.messages)
        [row] = await self._rows()
        self.assertEqual("android_shown", row.status)

    async def test_silence_from_the_phone_sends_telegram_once_after_ten_minutes(self):
        await self._register(self.token_a, allowed=True)
        await self._deliver(_Bot())
        bot = _Bot()

        soon = datetime.now(timezone.utc) + timedelta(minutes=5)
        self.assertEqual(0, await self._sweep(bot, now=soon))
        later = datetime.now(timezone.utc) + ANDROID_CONFIRM_TIMEOUT + timedelta(minutes=1)
        self.assertEqual(1, await self._sweep(bot, now=later))
        self.assertEqual(0, await self._sweep(bot, now=later))
        self.assertEqual(
            [{"chat_id": 1001, "text": "Ertaga obunangiz tugash kuni."}], bot.messages
        )

        # A phone that wakes up now must not show it as well.
        [row] = await self._rows()
        late = await self.client.get(
            f"/api/v3/android/notices/{row.id}", headers=self.bearer(self.token_a),
        )
        self.assertEqual({"id": row.id, "show": False}, late.json()["notice"])

    async def test_a_phone_that_cannot_show_it_hands_over_at_the_next_tick(self):
        await self._register(self.token_a, allowed=True)
        await self._deliver(_Bot())
        [row] = await self._rows()

        ack = await self.client.post(
            f"/api/v3/android/notices/{row.id}/ack",
            json={"shown": False},
            headers=self.bearer(self.token_a),
        )
        self.assertEqual(200, ack.status_code)
        bot = _Bot()
        self.assertEqual(1, await self._sweep(bot))
        self.assertEqual(1, len(bot.messages))

        async with self.sessions() as session:
            token = await session.get(AndroidPushToken, self.device_a)
        self.assertFalse(token.notifications_allowed)

    async def test_a_phone_reading_the_notice_holds_telegram_back_briefly(self):
        await self._register(self.token_a, allowed=True)
        await self._deliver(_Bot())
        [row] = await self._rows()
        async with self.sessions() as session:
            stored = await session.get(AccountNoticeDelivery, row.id)
            stored.fallback_due_at = datetime.now(timezone.utc)
            await session.commit()

        await self.client.get(f"/api/v3/android/notices/{row.id}", headers=self.bearer(self.token_a))
        bot = _Bot()
        self.assertEqual(0, await self._sweep(bot))

    async def test_notices_are_private_to_their_account(self):
        await self._register(self.token_a, allowed=True)
        await self._deliver(_Bot())
        [row] = await self._rows()
        other = await self.client.get(
            f"/api/v3/android/notices/{row.id}", headers=self.bearer(self.token_b),
        )
        self.assertEqual(404, other.status_code)
        other_ack = await self.client.post(
            f"/api/v3/android/notices/{row.id}/ack",
            json={"shown": False},
            headers=self.bearer(self.token_b),
        )
        self.assertEqual(404, other_ack.status_code)
        anonymous = await self.client.get(f"/api/v3/android/notices/{row.id}")
        self.assertEqual(401, anonymous.status_code)

    async def test_a_learner_who_blocked_the_bot_is_still_reached_in_the_app(self):
        await self._register(self.token_a, allowed=True)
        async with self.sessions() as session:
            learner = await session.get(User, 1)
            learner.bot_blocked_at = datetime.now(timezone.utc)
            await session.commit()
            delivery = NotificationDeliveryService(session, self.settings)
            self.assertTrue(await delivery.reachable(learner))
            unreached = await session.get(User, 2)
            unreached.bot_blocked_at = datetime.now(timezone.utc)
            self.assertFalse(await delivery.reachable(unreached))

        bot = _Bot()
        outcome, _ = await self._deliver(bot)
        self.assertEqual("android", outcome)
        # If the phone stays silent, the blocked chat is not written to.
        later = datetime.now(timezone.utc) + ANDROID_CONFIRM_TIMEOUT * 2
        self.assertEqual(0, await self._sweep(bot, now=later))
        self.assertEqual([], bot.messages)
        [row] = await self._rows()
        self.assertEqual("telegram_failed", row.status)


    async def test_the_expiry_reminder_reaches_the_app_and_is_recorded_once(self):
        await self._register(self.token_a, allowed=True)
        async with self.sessions() as session:
            learner = await session.get(User, 1)
            learner.status = "active"
            learner.payment_status = "approved"
            learner.end_date = datetime.now(timezone.utc) + timedelta(days=1)
            await session.commit()

        bot = _Bot()
        with (
            patch.object(
                NotificationDeliveryService, "android_enabled",
                new_callable=PropertyMock, return_value=True,
            ),
            patch.object(
                AndroidPushService, "send_batch",
                new_callable=AsyncMock, return_value=[AndroidPushResult(True)],
            ),
        ):
            async with self.sessions() as session:
                self.assertEqual(1, await ExpiryReminderService(session).send_expiry_reminders(bot))
            async with self.sessions() as session:
                self.assertEqual(0, await ExpiryReminderService(session).send_expiry_reminders(bot))

        self.assertEqual([], bot.messages)
        [row] = await self._rows()
        self.assertEqual(("Obuna tugayapti", "Obunangiz ertaga tugaydi."), (row.title, row.body))
        async with self.sessions() as session:
            feed = (await session.execute(select(CourseUserNotification))).scalars().all()
        self.assertEqual(["subscription_expiring"], [item.key for item in feed])

    async def test_a_campaign_goes_to_the_app_and_keeps_its_media_for_telegram(self):
        await self._register(self.token_a, allowed=True)
        campaign = SimpleNamespace(
            id=7, title="Kuz", title_uz="Kuzgi chegirma", reason=None, reason_uz=None,
            percent=30, notify_media_type="photo", notify_media_file_id="photo-1",
        )
        async with self.sessions() as session:
            learners = [await session.get(User, 1), await session.get(User, 2)]
            service = DiscountNotificationService(session)
            bot = _Bot()
            with (
                patch.object(service, "_target_users", new=AsyncMock(return_value=learners)),
                patch.object(
                    NotificationDeliveryService, "android_enabled",
                    new_callable=PropertyMock, return_value=True,
                ),
                patch.object(
                    AndroidPushService, "send_batch",
                    new_callable=AsyncMock, return_value=[AndroidPushResult(True)],
                ),
            ):
                result = await service.send_campaign_notification(bot, campaign)
            await session.commit()

        self.assertEqual((2, 2, 0), (result.total, result.sent, result.failed))
        # Learner 2 has no app: Telegram, with the campaign photo.
        self.assertEqual([1002], [photo["chat_id"] for photo in bot.photos])
        [row] = await self._rows()
        self.assertEqual(1001, row.telegram_id)
        self.assertEqual("🎁 Maxsus chegirma tayyor", row.title)
        self.assertEqual("Kuzgi chegirma\nChegirma: 30%", row.body)
        self.assertEqual("photo-1", row.telegram_payload["media_file_id"])


class DiscountPhoneCopyTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_phone_copy_drops_the_headline_and_the_mini_app_line(self):
        campaign = SimpleNamespace(
            title="Kuz", title_uz="Kuzgi chegirma", reason=None, reason_uz="Faqat bugun",
            percent=30,
        )
        service = DiscountNotificationService(SimpleNamespace())
        telegram = await service._notification_text(campaign, "uz", None)
        phone = await service._notification_text(campaign, "uz", None, for_phone=True)

        self.assertEqual(
            "🎁 <b>Maxsus chegirma tayyor</b>\n\n<b>Kuzgi chegirma</b>\n"
            "Chegirma: <b>30%</b>\n\nFaqat bugun\n\nTarif va to'lov Mini App ichida ochiladi.",
            telegram,
        )
        self.assertEqual(
            "<b>Kuzgi chegirma</b>\nChegirma: <b>30%</b>\n\nFaqat bugun", phone
        )


if __name__ == "__main__":
    unittest.main()
