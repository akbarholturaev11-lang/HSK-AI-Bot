"""Regression coverage for the Android feature adapter.

The adapter owns no business logic of its own — it authenticates a bearer
token and forwards to the canonical services. These tests therefore protect
the two things that *are* the adapter's responsibility:

1. Nothing is reachable without a valid Android bearer token.
2. Subscription is never sold inside the Android app. The app is handed off to
   the Telegram bot, which offers the existing subscription Mini App, and the
   adapter never grants access by itself.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.desktop_rating import challenge_ref
from app.api.android_features import (
    _bot_url,
    _invite_link,
    _public_android_referral_item,
    _service_response,
    _subscription_payload,
    create_android_features_router,
)
from app.db.base import Base
from app.db.models.course_ad import CourseAdCreative
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.services.course_ad_service import CourseAdService
from app.services.course_miniapp_access_service import COURSE_AD_ATTEMPT_EVENT_NAME
from app.services.desktop_auth_service import DesktopAuthService
from app.services.referral_service import normalize_referral_code


def _settings(bot_username="pomp_test_bot"):
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="android-features-test-secret-" + "x" * 40,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME=bot_username,
    )


def _user(user_id: int, telegram_id: int, name: str) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=name,
        language="uz",
        level="hsk3",
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


class AndroidBotUrlTests(unittest.TestCase):
    def test_username_forms_resolve_to_one_link(self):
        self.assertEqual("https://t.me/pomp_bot", _bot_url(_settings("pomp_bot")))
        self.assertEqual("https://t.me/pomp_bot", _bot_url(_settings("@pomp_bot")))
        self.assertEqual("https://t.me/pomp_bot", _bot_url(_settings("  pomp_bot  ")))

    def test_missing_username_yields_no_link_instead_of_a_broken_one(self):
        # A "https://t.me/" button would dead-end the learner, so the absence
        # of a username has to stay visible to the caller.
        self.assertEqual("", _bot_url(_settings("")))
        self.assertEqual("", _bot_url(_settings(None)))
        self.assertEqual("", _bot_url(SimpleNamespace()))


class AndroidReferralPayloadTests(unittest.TestCase):
    def test_friend_row_keeps_miniapp_metrics_without_exposing_ids(self):
        secret = _settings().DESKTOP_AUTH_SIGNING_SECRET
        row = _public_android_referral_item(
            {
                "rank": 2,
                "name": "Li Friend",
                "username": "@li_friend",
                "telegram_id": 778,
                "user_id": 91,
                "status": "active",
                "xp": 45,
                "total_xp": 320,
                "course_level": "hsk3",
                "completed_lessons": 8,
                "is_paid": True,
            },
            secret=secret,
        )

        self.assertEqual(2, row["rank"])
        self.assertEqual("li_friend", row["username"])
        self.assertEqual(45, row["xp"])
        self.assertEqual(320, row["total_xp"])
        self.assertEqual(challenge_ref(778, secret), row["challenge_ref"])
        self.assertNotIn("telegram_id", row)
        self.assertNotIn("user_id", row)


class AndroidReferralRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 4242, "Referrer"))
            await session.commit()

        class FakeUserRepo:
            async def ensure_referral_code(self, user):
                user.referral_code = "invite42"
                return "invite42"

        class FakeReferralService:
            def __init__(self, session):
                self.user_repo = FakeUserRepo()

            async def list_miniapp_referrals(self, user, **_kwargs):
                return [
                    {
                        "rank": 1,
                        "name": "Li Friend",
                        "username": "li_friend",
                        "telegram_id": 778,
                        "status": "active",
                        "xp": 45,
                        "total_xp": 320,
                        "course_level": "hsk3",
                        "completed_lessons": 8,
                        "is_paid": True,
                    }
                ]

            async def get_trial_activation_progress(self, user):
                return 1

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                referral_service_factory=FakeReferralService,
            )
        )
        self.auth = patch.object(
            DesktopAuthService,
            "authenticate",
            AsyncMock(
                return_value=SimpleNamespace(user=SimpleNamespace(telegram_id=4242))
            ),
        )
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def test_overview_returns_the_invite_and_actionable_friend_rows(self):
        response = await self.client.get(
            "/api/v3/android/referral/overview?tz=180",
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("https://t.me/pomp_test_bot?start=invite42", payload["link"])
        self.assertEqual(1, payload["invited"])
        self.assertEqual(1, payload["activated"])
        self.assertEqual("Li Friend", payload["items"][0]["name"])
        self.assertTrue(payload["items"][0]["challenge_ref"])
        self.assertNotIn("telegram_id", payload["items"][0])


class AndroidInviteLinkTests(unittest.TestCase):
    def test_invite_payload_is_the_code_the_bot_looks_up(self):
        # `/start <payload>` resolves the payload against the stored referral
        # code with an exact match, so a decorated payload would reach the bot
        # and match nobody: the invite would be lost without any error.
        link = _invite_link("pomp_bot", "a1b2c3d4")

        self.assertEqual("https://t.me/pomp_bot?start=a1b2c3d4", link)
        payload = link.split("?start=", 1)[1]
        self.assertEqual("a1b2c3d4", normalize_referral_code(payload))

    def test_missing_parts_yield_no_link_instead_of_a_broken_one(self):
        self.assertEqual("", _invite_link("", "a1b2c3d4"))
        self.assertEqual("", _invite_link("pomp_bot", ""))


class AndroidLimitPassthroughTests(unittest.TestCase):
    """The client shows WHEN the limit reopens, so the instant must survive."""

    @staticmethod
    def _body(response):
        return json.loads(bytes(response.body).decode("utf-8"))

    def test_the_reset_instant_reaches_the_client(self):
        response = _service_response(
            {
                "ok": False,
                "error": "free_feature_limit_reached",
                "reset_at": "2026-09-16T00:00:00+00:00",
                "lifetime": False,
            }
        )
        self.assertEqual(403, response.status_code)
        body = self._body(response)
        self.assertEqual("2026-09-16T00:00:00+00:00", body["reset_at"])
        self.assertFalse(body["lifetime"])

    def test_a_lifetime_limit_reports_no_reset_instead_of_a_wrong_one(self):
        response = _service_response(
            {"ok": False, "error": "free_feature_limit_reached", "reset_at": None, "lifetime": True}
        )
        body = self._body(response)
        self.assertIsNone(body["reset_at"])
        self.assertTrue(body["lifetime"])

    def test_other_failures_are_unchanged(self):
        response = _service_response({"ok": False, "error": "mistake_review_empty"})
        self.assertEqual(404, response.status_code)
        self.assertEqual({"ok": False, "error": "mistake_review_empty"}, self._body(response))


class AndroidSubscriptionPayloadTests(unittest.TestCase):
    def test_checkout_is_never_offered_inside_the_app(self):
        payload = _subscription_payload(
            _user(1, 1001, "Account A"),
            {"subscription": {"until": None}},
            _settings(),
        )
        self.assertFalse(payload["checkout_allowed"])
        self.assertEqual("telegram_bot", payload["billing"]["provider"])
        self.assertEqual("https://t.me/pomp_test_bot", payload["billing"]["bot_url"])
        self.assertTrue(payload["billing"]["configured"])
        self.assertFalse(payload["access"]["is_paid"])

    def test_handoff_is_reported_unconfigured_without_a_bot_username(self):
        payload = _subscription_payload(
            _user(1, 1001, "Account A"),
            {"subscription": {}},
            _settings(""),
        )
        self.assertFalse(payload["billing"]["configured"])
        self.assertEqual("", payload["billing"]["bot_url"])
        self.assertIn("BOT_USERNAME", payload["billing"]["required_external_config"])


class AndroidSubscriptionHandoffApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Account A"))
            await session.commit()
        self.bot = SimpleNamespace(send_message=AsyncMock())

    async def asyncTearDown(self):
        await self.engine.dispose()

    def _client(self, settings_obj=None, bot=...):
        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=settings_obj or _settings(),
                bot=self.bot if bot is ... else bot,
            )
        )
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def _token(self, installation="i" * 48):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, _settings())
            started = await auth.start_link(
                platform="android",
                app_version="1.1.0",
                installation_key=installation,
            )
            await auth.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await auth.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            return linked["access_token"]

    async def test_handoff_sends_the_menu_and_returns_the_bot_link(self):
        token = await self._token()
        async with self._client() as client:
            with patch(
                "app.api.android_features.StudyMiniAppService.send_subscription_menu",
                AsyncMock(return_value=True),
            ) as send:
                response = await client.post(
                    "/api/v3/android/subscription/open",
                    headers={"Authorization": f"Bearer {token}"},
                )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["message_sent"])
        self.assertEqual("https://t.me/pomp_test_bot", body["bot_url"])
        self.assertEqual(1, send.await_count)
        # The adapter must not invent its own subscription copy or keyboard.
        self.assertEqual(1001, send.await_args.args[1])

    async def test_a_failed_message_still_hands_the_learner_the_bot_link(self):
        # Telegram can refuse the message (the user blocked the bot, a network
        # hiccup). Opening the bot chat still reaches the same menu, so the
        # button must not dead-end.
        token = await self._token()
        async with self._client() as client:
            with patch(
                "app.api.android_features.StudyMiniAppService.send_subscription_menu",
                AsyncMock(return_value=False),
            ):
                response = await client.post(
                    "/api/v3/android/subscription/open",
                    headers={"Authorization": f"Bearer {token}"},
                )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["message_sent"])
        self.assertEqual("https://t.me/pomp_test_bot", body["bot_url"])

    async def test_handoff_requires_a_bearer_token(self):
        async with self._client() as client:
            response = await client.post("/api/v3/android/subscription/open")
        self.assertEqual(401, response.status_code)
        self.assertFalse(response.json()["ok"])
        self.bot.send_message.assert_not_awaited()

    async def test_handoff_rejects_a_forged_token(self):
        async with self._client() as client:
            response = await client.post(
                "/api/v3/android/subscription/open",
                headers={"Authorization": "Bearer not-a-real-token"},
            )
        self.assertEqual(401, response.status_code)
        self.bot.send_message.assert_not_awaited()

    async def test_identity_is_never_taken_from_the_query_string(self):
        token = await self._token()
        async with self._client() as client:
            response = await client.post(
                "/api/v3/android/subscription/open?telegram_id=9999",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(422, response.status_code)
        self.bot.send_message.assert_not_awaited()

    async def test_handoff_fails_closed_without_a_bot_username(self):
        token = await self._token()
        async with self._client(settings_obj=_settings("")) as client:
            response = await client.post(
                "/api/v3/android/subscription/open",
                headers={"Authorization": f"Bearer {token}"},
            )
        # No link to send the learner to: say so rather than opening
        # "https://t.me/" and losing them.
        self.assertEqual(503, response.status_code)
        self.assertFalse(response.json()["ok"])

    async def test_a_missing_bot_still_returns_the_link(self):
        # The worker that serves the API may run without a bot instance; the
        # learner can still open the chat themselves.
        token = await self._token()
        async with self._client(bot=None) as client:
            response = await client.post(
                "/api/v3/android/subscription/open",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["message_sent"])
        self.assertEqual("https://t.me/pomp_test_bot", body["bot_url"])

    async def test_overview_reports_the_handoff_and_never_a_checkout(self):
        token = await self._token()
        async with self._client() as client:
            response = await client.get(
                "/api/v3/android/subscription/overview",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["checkout_allowed"])
        self.assertEqual("telegram_bot", body["billing"]["provider"])
        self.assertEqual("https://t.me/pomp_test_bot", body["billing"]["bot_url"])
        self.assertFalse(body["access"]["is_paid"])


class AndroidAdChannelTests(unittest.IsolatedAsyncioTestCase):
    """Which ads each distribution channel is allowed to receive.

    This is a policy boundary, not a preference: the Google Play build may not
    send a learner out of the app to pay, so the ad type that carries a
    subscription button must never reach it. The desktop-download promo never
    reaches Android at all — it is built for the Mini App layout and means
    nothing on a phone.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Account A"))
            for index, ad_type in enumerate(
                ("odiy", "hamkorlik", "bot", "dars_yakuni", "app")
            ):
                session.add(
                    CourseAdCreative(
                        title=f"{ad_type} creative",
                        media_path=f"{ad_type}.mp4",
                        media_type="video",
                        language="all",
                        ad_type=ad_type,
                        # Tur va JOY endi mustaqil: admin har reklamani
                        # ikkala joyga ham qo'yishi mumkin.
                        placements="lesson_end,screen_center",
                        duration_seconds=7,
                        is_active=True,
                        created_at=datetime(2026, 9, 1, 12, index, tzinfo=timezone.utc),
                    )
                )
            await session.commit()

        # The creatives have no file on disk; this test is about which types
        # are handed out, not about media storage.
        async def _always_available(self, ad):
            return True, False

        self.media = patch.object(
            CourseAdService,
            "ensure_media_available",
            _always_available,
        )
        self.media.start()
        self.addCleanup(self.media.stop)

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _token(self, installation="a" * 48):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, _settings())
            started = await auth.start_link(
                platform="android",
                app_version="1.1.0",
                installation_key=installation,
            )
            await auth.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await auth.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            return linked["access_token"]

    async def _ask(self, query=""):
        token = await self._token()
        response = await self.client.get(
            f"/api/v3/android/ad{query}",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response

    async def _types(self, query=""):
        # Mashq sloti endi reklama bermaydi, shuning uchun kanal filtri
        # dars yakuni sloti ustida tekshiriladi.
        if "slot=" not in query:
            query = (query + "&" if query else "?") + "slot=lesson_end"
        response = await self._ask(query)
        self.assertEqual(200, response.status_code, response.text)
        body = response.json()
        return {ad["ad_type"] for ad in body["ads"]}, body

    async def test_the_play_channel_never_gets_a_subscription_ad(self):
        """Play buildiga obuna CTA si bo'lgan reklama tushmasligi kerak.

        Ilgari buni JOY ta'minlardi: `lesson_end` slotida faqat `dars_yakuni`
        turi bo'lardi. Endi tur va joy mustaqil — bir joyda har xil tur
        bo'lishi mumkin — shuning uchun himoya TURga bog'langan.
        """
        types, _ = await self._types("?channel=play&slot=lesson_end")
        self.assertNotIn("dars_yakuni", types)

    async def test_the_play_channel_still_gets_the_ordinary_ads(self):
        # Xavfli turni chiqarib tashlash Play buildini reklamasiz qoldirmasin.
        types, _ = await self._types("?channel=play&slot=lesson_end")
        self.assertEqual({"odiy", "hamkorlik", "bot"}, types)

    async def test_the_practice_slot_no_longer_serves_ads(self):
        """Mashq sessiyalaridagi reklama olib tashlandi.

        Do'kondagi eski build hali "reklama ko'rib davom etish" tugmasini
        ko'rsatadi. Bo'sh javob unga "reklama yo'q" deydi va u obuna yo'liga
        o'tadi — xato ko'rsatmasdan. Aks holda u men o'chirgan `/ad/attempt`
        ga borib 404 olardi.
        """
        response = await self._ask("?slot=practice")

        self.assertEqual(404, response.status_code)
        self.assertEqual("course_ad_not_found", response.json()["error"])

    async def test_the_direct_channel_may_show_the_lesson_end_block(self):
        types, body = await self._types("?channel=direct&slot=lesson_end")
        self.assertIn("dars_yakuni", types)
        self.assertEqual("direct", body["channel"])

    async def test_the_desktop_promo_never_reaches_android(self):
        for query in ("?channel=play&slot=lesson_end", "?channel=direct&slot=lesson_end"):
            with self.subTest(query=query):
                types, _ = await self._types(query)
                self.assertNotIn("app", types)

    async def test_an_unknown_channel_falls_back_to_the_restricted_set(self):
        # Yo'q yoki g'alati qiymat ko'rsatiladigan narsani KENGAYTIRMASLIGI
        # kerak: obuna CTA si faqat aniq "direct" bilan ochiladi.
        for suffix in ("", "&channel=", "&channel=web"):
            with self.subTest(channel=suffix):
                types, _ = await self._types(f"?slot=lesson_end{suffix}")
                self.assertNotIn("dars_yakuni", types)

    async def test_the_channel_name_is_read_case_insensitively(self):
        types, body = await self._types("?channel=PLAY")
        self.assertEqual("play", body["channel"])
        self.assertNotIn("app", types)

    async def test_an_anonymous_caller_gets_no_ads(self):
        response = await self.client.get("/api/v3/android/ad")
        self.assertEqual(401, response.status_code)
        self.assertFalse(response.json()["ok"])

    async def _post(self, path, token, **body):
        return await self.client.post(
            path,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )

    async def _ad_view(self, token, *, ad_id=1, watched=9, placement="screen_center"):
        return await self._post(
            "/api/v3/android/ad/view",
            token,
            ad_id=ad_id,
            watched_seconds=watched,
            placement=placement,
        )

    async def test_a_watched_ad_is_recorded_but_opens_nothing(self):
        """Reklama ko'rib kirish ochish OLIB TASHLANDI.

        Ilgari to'liq ko'rilgan reklama bo'limni ochardi va buning uchun
        `/ad/attempt` tokeni va binding tarmog'i bor edi. Endi ko'rsatish
        faqat kunlik chegara uchun hisoblanadi.
        """
        token = await self._token()

        response = await self._ad_view(token)

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        # Hech qanday avtorizatsiya qaytmaydi.
        self.assertNotIn("authorization", body)

    async def test_the_attempt_endpoint_is_gone(self):
        token = await self._token()

        response = await self._post(
            "/api/v3/android/ad/attempt", token, ad_id=1, access_ref="ref-12345678"
        )

        self.assertEqual(404, response.status_code)

    async def test_an_old_client_still_sending_the_attempt_fields_is_not_refused(self):
        # Eski Android build hali `access_ref` va `attempt_token` yuborishi
        # mumkin — u 422 olmasligi kerak.
        token = await self._token()

        response = await self._post(
            "/api/v3/android/ad/view",
            token,
            ad_id=1,
            watched_seconds=9,
            placement="screen_center",
            access_ref="ref-12345678",
            attempt_token="t" * 32,
        )

        self.assertEqual(200, response.status_code)


    # --- ekran markazi ---------------------------------------------------
    #
    # Ikkinchi joy. Mini App'da u ilova ochilganda markazda chiqadi va
    # kuniga ko'pi bilan 2 marta. Chegara SERVERDA — shuning uchun telefonda
    # ikkitasini ko'rgan odam desktopda uchinchisini ololmaydi.

    async def test_the_screen_centre_slot_is_served(self):
        types, body = await self._types("?channel=play&slot=screen_center")

        self.assertEqual("screen_center", body["slot"])
        self.assertTrue(types)
        # Har bir reklama qancha soniyadan keyin yopilishi mumkinligini
        # SERVER aytadi — klient o'zi o'ylab topmaydi.
        for ad in body["ads"]:
            with self.subTest(ad=ad["id"]):
                self.assertEqual("screen_center", ad["placement"])
                self.assertGreater(int(ad["skip_after_seconds"]), 0)

    async def test_the_screen_centre_slot_stops_at_the_daily_cap(self):
        token = await self._token()

        async def ask():
            return await self.client.get(
                "/api/v3/android/ad?slot=screen_center&channel=play",
                headers={"Authorization": f"Bearer {token}"},
            )

        self.assertEqual(200, (await ask()).status_code)
        first_ad = (await ask()).json()["ads"][0]["id"]

        # Ikkita ko'rsatish yoziladi — bu kunlik chegara.
        for _ in range(2):
            recorded = await self._ad_view(
                token, ad_id=first_ad, placement="screen_center"
            )
            self.assertEqual(200, recorded.status_code, recorded.text)

        exhausted = await ask()
        self.assertEqual(404, exhausted.status_code)
        self.assertEqual("course_ad_not_found", exhausted.json()["error"])

    async def test_a_paid_learner_gets_no_screen_centre_ad(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=30)
            await session.commit()

        response = await self._ask("?slot=screen_center&channel=play")

        self.assertEqual(404, response.status_code)

    async def test_a_view_for_an_unknown_ad_is_an_error(self):
        token = await self._token()
        response = await self._post(
            "/api/v3/android/ad/view",
            token,
            ad_id=9999,
            watched_seconds=7,
            feature="recognition",
        )
        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual("ad_not_found", response.json()["error"])


class AndroidExamRouteTests(unittest.IsolatedAsyncioTestCase):
    """Android must sit the SAME HSK exam as the Mini App.

    The two clients used to disagree here: the Mini App opened
    `CourseHskExamService`, Android opened a ten-question level drill. These
    routes only exist to hand Android the same service, so what is worth
    pinning is that the call reaches it with the level, language and answers
    the client sent.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.calls = []

        outer = self

        class FakeExamService:
            def __init__(self, session):
                self.session = session

            async def start(self, telegram_id, *, level, lang, access_ref, ad_supported=False):
                outer.calls.append(
                    ("start", telegram_id, level, lang, access_ref, ad_supported)
                )
                return {
                    "ok": True,
                    "session": {
                        "id": "hsk-exam:1:hsk2:seed",
                        "level": level,
                        "duration_min": 30,
                        "pass_score": 60,
                        "questions": [],
                    },
                }

            async def complete(self, telegram_id, *, session_id, answers, level=None, lang=None):
                outer.calls.append(("complete", telegram_id, session_id, answers, level, lang))
                return {"ok": True, "result": {"percent": 75, "passed": True}}

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                exam_service_factory=FakeExamService,
            )
        )
        self.auth = patch.object(
            DesktopAuthService,
            "authenticate",
            AsyncMock(
                return_value=SimpleNamespace(user=SimpleNamespace(telegram_id=4242))
            ),
        )
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def _headers(self):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def test_start_hands_the_level_and_language_to_the_exam_service(self):
        response = await self.client.post(
            "/api/v3/android/exams/start",
            headers=self._headers(),
            json={
                "level": "hsk2",
                "language": "uz",
                "access_ref": "ref-1",
                "ad_supported": True,
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(
            ("start", 4242, "hsk2", "uz", "ref-1", True),
            self.calls[0],
        )

    async def test_complete_forwards_the_answers_in_the_service_shape(self):
        response = await self.client.post(
            "/api/v3/android/exams/complete",
            headers=self._headers(),
            json={
                "session_id": "hsk-exam:1:hsk2:seed",
                "level": "hsk2",
                "language": "uz",
                "answers": [{"question_id": "q1", "selected_index": 2}],
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            (
                "complete",
                4242,
                "hsk-exam:1:hsk2:seed",
                [{"question_id": "q1", "selected_index": 2}],
                "hsk2",
                "uz",
            ),
            self.calls[0],
        )

    async def test_complete_without_a_level_lets_the_session_decide(self):
        # An empty level means "whatever the exam was started with"; passing
        # the empty string through would read as a level that changed mid-exam.
        await self.client.post(
            "/api/v3/android/exams/complete",
            headers=self._headers(),
            json={"session_id": "hsk-exam:1:hsk2:seed", "answers": []},
        )
        self.assertIsNone(self.calls[0][4])
        self.assertIsNone(self.calls[0][5])

    async def test_a_spent_allowance_is_refused_with_403(self):
        outer = self

        class LimitedExamService:
            def __init__(self, session):
                pass

            async def start(self, telegram_id, **kwargs):
                return {
                    "ok": False,
                    "error": "free_feature_limit_reached",
                    "ad": {"available": True, "limited": False},
                }

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=outer.sessions,
                settings_obj=_settings(),
                exam_service_factory=LimitedExamService,
            )
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://android.test"
        ) as client:
            response = await client.post(
                "/api/v3/android/exams/start",
                headers=self._headers(),
                json={"level": "hsk1", "language": "uz"},
            )
        self.assertEqual(403, response.status_code)
        self.assertEqual("free_feature_limit_reached", response.json()["error"])


class AndroidChallengeRouteTests(unittest.IsolatedAsyncioTestCase):
    """Android can take part in the league, not only watch it.

    The Mini App lets a learner challenge someone from the leaderboard to the
    same short quiz. These pin the adapter's job: the opponent, the action and
    the answers reach the one challenge service, unchanged.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 4242, "Challenger"))
            await session.commit()
        self.calls = []

        outer = self

        class FakeGamificationService:
            def __init__(self, session):
                self.session = session

            async def leaderboard(self, user, *, limit, timezone_offset_minutes=None):
                return {
                    "leaderboard": [
                        {"rank": 1, "name": "Rival", "telegram_id": 777, "xp": 30},
                    ]
                }

        class FakeChallengeService:
            def __init__(self, session):
                self.session = session

            async def list_for_user(self, telegram_id):
                outer.calls.append(("list", telegram_id))
                return {"ok": True, "pending_count": 1, "active_count": 0, "items": []}

            async def create(self, telegram_id, *, opponent_telegram_id, level, lang, bot=None):
                outer.calls.append(("create", telegram_id, opponent_telegram_id, level, lang))
                return {"ok": True, "challenge": {"id": 5}}

            async def respond(self, telegram_id, challenge_id, action, *, bot=None):
                outer.calls.append(("respond", telegram_id, challenge_id, action))
                return {"ok": True}

            async def start(self, telegram_id, challenge_id):
                outer.calls.append(("start", telegram_id, challenge_id))
                return {"ok": True, "session": {"questions": []}}

            async def submit(
                self, telegram_id, challenge_id, answers, *, duration_seconds=0, bot=None
            ):
                outer.calls.append(("submit", telegram_id, challenge_id, answers, duration_seconds))
                return {"ok": True, "result": {"score": 4}}

        class FakeReferralService:
            def __init__(self, session):
                self.session = session

            async def list_miniapp_referrals(self, user, **_kwargs):
                return [
                    {
                        "name": "Invited rival",
                        "telegram_id": 778,
                        "status": "active",
                    }
                ]

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                challenge_service_factory=FakeChallengeService,
                gamification_service_factory=FakeGamificationService,
                referral_service_factory=FakeReferralService,
            )
        )
        self.auth = patch.object(
            DesktopAuthService,
            "authenticate",
            AsyncMock(
                return_value=SimpleNamespace(user=SimpleNamespace(telegram_id=4242))
            ),
        )
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def _headers(self):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def test_a_challenge_reaches_the_learner_behind_the_reference(self):
        ref = challenge_ref(777, _settings().DESKTOP_AUTH_SIGNING_SECRET)

        response = await self.client.post(
            "/api/v3/android/challenges",
            headers=self._headers(),
            json={"opponent_ref": ref, "level": "hsk2", "language": "uz"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(("create", 4242, 777, "hsk2", "uz"), self.calls[0])

    async def test_a_reference_from_outside_the_leaderboard_reaches_nobody(self):
        response = await self.client.post(
            "/api/v3/android/challenges",
            headers=self._headers(),
            json={"opponent_ref": "f" * 32},
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual([], [call for call in self.calls if call[0] == "create"])

    async def test_an_invited_friend_can_be_challenged_outside_the_leaderboard(self):
        ref = challenge_ref(778, _settings().DESKTOP_AUTH_SIGNING_SECRET)

        response = await self.client.post(
            "/api/v3/android/challenges",
            headers=self._headers(),
            json={"opponent_ref": ref, "level": "hsk3", "language": "uz"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(("create", 4242, 778, "hsk3", "uz"), self.calls[0])

    async def test_only_accept_or_decline_are_accepted(self):
        response = await self.client.post(
            "/api/v3/android/challenges/1/respond",
            headers=self._headers(),
            json={"action": "maybe"},
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual([], self.calls)

    async def test_answers_reach_the_service_in_its_own_shape(self):
        response = await self.client.post(
            "/api/v3/android/challenges/9/submit",
            headers=self._headers(),
            json={
                "answers": [{"question_id": "q1", "selected_index": 2}],
                "duration_seconds": 42,
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            (
                "submit",
                4242,
                9,
                [{"question_id": "q1", "selected_index": 2}],
                42,
            ),
            self.calls[0],
        )


class AndroidAdaptiveDrillTests(unittest.IsolatedAsyncioTestCase):
    """Both clients must practise the SAME words.

    The Mini App asks the mastery service which characters are due and reports
    the outcome back so the interval moves. Android built its recognition and
    pronunciation sections from a different generator, so the same learner
    practised two different sets and only one of them fed the review schedule.
    These pin the forwarding: the skill and the limit reach the adviser, and a
    reported miss reaches both the mistake book and the schedule.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 4242, "Drill"))
            await session.commit()
        self.calls = []

        # Shadow solishtiruvi ataylab O'Z sessiyasida yozadi (so'rov rollback
        # bo'lsa ham yozuv yo'qolmasin). Testda uni shu bazaga bog'laymiz,
        # aks holda u haqiqiy Postgres'ga ulanishga urinardi.
        self.shadow_sessions_patch = patch(
            "app.services.entitlements.shadow.async_session_maker", self.sessions
        )
        self.shadow_sessions_patch.start()
        self.addCleanup(self.shadow_sessions_patch.stop)

        outer = self

        class FakeMasteryService:
            def __init__(self, session):
                self.session = session

            async def drill_words(self, user, *, skill, limit):
                outer.calls.append(("words", int(user.telegram_id), skill, limit))
                return {
                    "skill": skill,
                    "day": "2026-09-07",
                    "words": [{"zh": "好", "kind": "review", "box": 2}],
                }

            async def record_drill(self, user, *, skill, results):
                outer.calls.append(("schedule", skill, results))
                return len(results)

        class FakeDrillSignalService:
            def __init__(self, session):
                self.session = session

            async def record(self, user, *, feature, level, language, entries):
                outer.calls.append(("mistakes", feature, level, language, entries))
                return len(entries)

        class RecordingBot:
            """Stands in for the Telegram bot the app is handed off to."""

            def __init__(self):
                self.messages = []

            async def send_message(self, *, chat_id, text, **_ignored):
                self.messages.append((chat_id, text))

        self.bot = RecordingBot()

        # Seeded creatives have no file on disk; these tests are about the
        # gate, not about media storage.
        async def _always_available(self, ad):
            return True, False

        self.media = patch.object(
            CourseAdService,
            "ensure_media_available",
            _always_available,
        )
        self.media.start()
        self.addCleanup(self.media.stop)

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                bot=self.bot,
                mastery_service_factory=FakeMasteryService,
                drill_service_factory=FakeDrillSignalService,
            )
        )
        self.auth = patch.object(
            DesktopAuthService,
            "authenticate",
            AsyncMock(
                return_value=SimpleNamespace(user=SimpleNamespace(telegram_id=4242))
            ),
        )
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def _headers(self):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def _seed_practice_ad(self):
        """An ad the practice slot can actually offer this learner."""

        async with self.sessions() as session:
            session.add(
                CourseAdCreative(
                    title="Practice creative",
                    media_path="practice.mp4",
                    media_type="video",
                    language="all",
                    ad_type="odiy",
                    duration_seconds=7,
                    is_active=True,
                )
            )
            await session.commit()

    async def test_the_first_free_run_is_allowed_and_the_second_is_not(self):
        await self._seed_practice_ad()
        first = await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-1"},
        )
        second = await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-2"},
        )

        self.assertEqual(200, first.status_code)
        self.assertTrue(first.json()["allowed"])
        # The Mini App gives a free learner this section once, not once a day.
        self.assertEqual(403, second.status_code)
        body = second.json()
        self.assertEqual("free_feature_limit_reached", body["error"])
        # Reklama endi hech narsani ochmaydi — javob buni ochiq aytadi.
        # Shakl saqlanadi, chunki do'kondagi eski build shu kalitni o'qiydi.
        self.assertFalse(body["ad"]["available"])
        # Qachon qayta ochilishi Mini App'dagidek aytiladi.
        self.assertIn("reset_at", body)

    async def test_a_spent_allowance_reaches_the_learner_in_telegram(self):
        """The limit is also news, not just a closed door.

        The Mini App tells the learner in the bot chat when a free section is
        spent, so the message is what they find later — Android reaching the
        same limit silently would leave the two clients telling different
        stories about the same account.
        """

        await self._seed_practice_ad()
        await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-1"},
        )
        self.assertEqual([], self.bot.messages)

        spent = await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-2"},
        )

        self.assertEqual(403, spent.status_code)
        self.assertEqual(1, len(self.bot.messages))
        chat_id, text = self.bot.messages[0]
        self.assertEqual(4242, chat_id)
        self.assertTrue(text.strip())

        # Once told, not told again: the notice is deduped for the learner.
        await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-3"},
        )
        self.assertEqual(1, len(self.bot.messages))

    async def test_an_empty_ad_catalogue_no_longer_opens_the_section(self):
        """Reklama yo'qligi endi bepul kirish EMAS.

        Ilgari bu yerda "ko'rsatadigan reklama yo'q ekan, bo'limni ochamiz"
        degan yo'l bor edi. Mashq reklamalari olib tashlangach o'sha yo'l
        Android'da bepul foydalanuvchiga cheksiz mashq berardi, Mini App'da
        esa o'sha odam paywall ko'rardi — ya'ni bitta hisob, ikki xil qoida.
        """

        await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-1"},
        )

        second = await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-2"},
        )

        self.assertEqual(403, second.status_code)
        body = second.json()
        self.assertFalse(body["ok"])
        self.assertEqual("free_feature_limit_reached", body["error"])
        self.assertNotIn("source", body)

    async def test_a_watched_ad_can_no_longer_open_the_section(self):
        """`access_ref` bilan "reklama ko'rdim" deyish endi ishlamaydi.

        Eski build hali bu maydonni yuboradi. U jimgina e'tiborsiz qoldirilishi
        kerak: 422 emas (build yiqilmasin), lekin ochib ham yubormasin.
        """

        await self._seed_practice_ad()
        await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "recognition", "ref": "drill-1"},
        )

        with_ref = await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={
                "feature": "recognition",
                "ref": "drill-2",
                "access_ref": "whatever-the-old-build-sends",
            },
        )

        self.assertEqual(403, with_ref.status_code)
        self.assertEqual(
            "free_feature_limit_reached", with_ref.json()["error"]
        )

    async def test_an_unknown_section_cannot_be_gated(self):
        response = await self.client.post(
            "/api/v3/android/practice/gate",
            headers=self._headers(),
            json={"feature": "writing"},
        )

        self.assertEqual(422, response.status_code)

    async def test_the_words_come_from_the_mastery_adviser(self):
        response = await self.client.post(
            "/api/v3/android/practice/words",
            headers=self._headers(),
            json={"feature": "recognition", "limit": 8},
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual([{"zh": "好", "kind": "review", "box": 2}], body["words"])
        self.assertEqual(("words", 4242, "recognition", 8), self.calls[0])

    async def test_a_report_feeds_both_the_mistake_book_and_the_schedule(self):
        response = await self.client.post(
            "/api/v3/android/practice/report",
            headers=self._headers(),
            json={
                "feature": "recognition",
                "level": "hsk2",
                "language": "uz",
                "mistakes": [{"hanzi": "好", "selected": "你"}],
                "results": [
                    {"hanzi": "好", "correct": False},
                    {"hanzi": "你", "correct": True},
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"ok": True, "recorded": 1, "scheduled": 2}, response.json())
        self.assertEqual(
            ("mistakes", "recognition", "hsk2", "uz", [{"hanzi": "好", "selected": "你"}]),
            self.calls[0],
        )
        self.assertEqual("schedule", self.calls[1][0])

    async def test_an_unknown_skill_is_refused(self):
        response = await self.client.post(
            "/api/v3/android/practice/words",
            headers=self._headers(),
            json={"feature": "writing", "limit": 8},
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual([], self.calls)


class AndroidVoiceTypedTurnTests(unittest.IsolatedAsyncioTestCase):
    """The Mini App's call screen answers by keyboard as well as by voice.

    `VoicePracticeService.process_message` has always accepted typed text; the
    Android adapter insisted on audio, so the client could not offer the
    keyboard at all. These pin the adapter's own job: forward the typed turn,
    and refuse a turn that is both spoken and typed, which would leave the
    grading ambiguous.
    """

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.calls = []

        outer = self

        class FakeVoiceService:
            def __init__(self, session):
                self.session = session

            async def process_message(
                self, telegram_id, *, session_id, audio_bytes, filename, text=""
            ):
                outer.calls.append((telegram_id, session_id, audio_bytes, filename, text))
                return {
                    "transcription": text,
                    "chinese_reply": "你好",
                    "turn_count": 1,
                    "max_dialogs": 7,
                }

        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                voice_service_factory=FakeVoiceService,
            )
        )
        self.auth = patch.object(
            DesktopAuthService,
            "authenticate",
            AsyncMock(
                return_value=SimpleNamespace(user=SimpleNamespace(telegram_id=4242))
            ),
        )
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def _headers(self):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def test_a_typed_turn_reaches_the_service_without_audio(self):
        response = await self.client.post(
            "/api/v3/android/voice/message",
            headers=self._headers(),
            json={"session_id": "voice-session-1", "text": "你好，我是学生"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            (4242, "voice-session-1", b"", "", "你好，我是学生"),
            self.calls[0],
        )

    async def test_a_turn_that_is_neither_spoken_nor_typed_is_refused(self):
        response = await self.client.post(
            "/api/v3/android/voice/message",
            headers=self._headers(),
            json={"session_id": "voice-session-1"},
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual([], self.calls)

    async def test_a_turn_that_is_both_spoken_and_typed_is_refused(self):
        response = await self.client.post(
            "/api/v3/android/voice/message",
            headers=self._headers(),
            json={
                "session_id": "voice-session-1",
                "text": "你好",
                "audio_data_url": "data:audio/mp4;base64," + "A" * 64,
            },
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual([], self.calls)


class AndroidFeatureAuthTests(unittest.IsolatedAsyncioTestCase):
    """Every feature route is bearer-only; none of them accept an anonymous call."""

    ROUTES = (
        ("POST", "/api/v3/android/trial/start"),
        ("GET", "/api/v3/android/trial/status"),
        ("GET", "/api/v3/android/profile"),
        ("GET", "/api/v3/android/subscription/overview"),
        ("POST", "/api/v3/android/subscription/open"),
        ("POST", "/api/v3/android/practice/start"),
        ("POST", "/api/v3/android/practice/complete"),
        ("POST", "/api/v3/android/practice/gate"),
        ("POST", "/api/v3/android/practice/words"),
        ("POST", "/api/v3/android/practice/report"),
        ("POST", "/api/v3/android/exams/start"),
        ("POST", "/api/v3/android/exams/complete"),
        ("GET", "/api/v3/android/mistakes"),
        ("POST", "/api/v3/android/mistakes/review/start"),
        ("POST", "/api/v3/android/mistakes/review/answer"),
        ("POST", "/api/v3/android/mistakes/review/complete"),
        ("GET", "/api/v3/android/rating/leaderboard"),
        ("GET", "/api/v3/android/challenges"),
        ("POST", "/api/v3/android/challenges"),
        ("POST", "/api/v3/android/challenges/{challenge_id}/respond"),
        ("POST", "/api/v3/android/challenges/{challenge_id}/start"),
        ("POST", "/api/v3/android/challenges/{challenge_id}/submit"),
        ("GET", "/api/v3/android/referral/overview"),
        ("GET", "/api/v3/android/voice/status"),
        ("POST", "/api/v3/android/voice/session/start"),
        ("POST", "/api/v3/android/voice/message"),
        ("POST", "/api/v3/android/voice/pronounce"),
        ("POST", "/api/v3/android/voice/session/end"),
        ("GET", "/api/v3/android/ad"),
        ("POST", "/api/v3/android/ad/view"),
        ("POST", "/api/v3/android/hints/dismiss"),
    )

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        app = FastAPI()
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
                bot=SimpleNamespace(send_message=AsyncMock()),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def test_the_adapter_exposes_exactly_the_known_routes(self):
        app = FastAPI()
        router = create_android_features_router(
            session_factory=self.sessions,
            settings_obj=_settings(),
        )
        app.include_router(router)
        exposed = {
            (method, route.path)
            for route in router.routes
            for method in route.methods
            if method != "HEAD"
        }
        self.assertEqual(set(self.ROUTES), exposed)

    #: Routes that take no request body, so the bearer check is the first gate.
    BODYLESS_ROUTES = (
        ("POST", "/api/v3/android/trial/start"),
        ("GET", "/api/v3/android/trial/status"),
        ("GET", "/api/v3/android/profile"),
        ("GET", "/api/v3/android/subscription/overview"),
        ("POST", "/api/v3/android/subscription/open"),
        ("GET", "/api/v3/android/mistakes"),
        ("GET", "/api/v3/android/rating/leaderboard"),
        ("GET", "/api/v3/android/referral/overview"),
        ("GET", "/api/v3/android/voice/status"),
        ("GET", "/api/v3/android/ad"),
    )

    async def test_no_route_does_any_work_without_a_bearer_token(self):
        # Routes carrying a body validate it before the bearer check, so an
        # anonymous call is refused as 422 rather than 401. Either way it is
        # refused and nothing runs — that is the invariant worth pinning.
        for method, path in self.ROUTES:
            with self.subTest(route=f"{method} {path}"):
                # A path parameter needs a value to be requestable at all.
                requested = path.replace("{challenge_id}", "1")
                response = await self.client.request(method, requested, json={})
                self.assertIn(response.status_code, (401, 422))
                self.assertFalse(response.json().get("ok", False))

    async def test_bodyless_routes_reject_anonymous_callers_as_unauthorised(self):
        for method, path in self.BODYLESS_ROUTES:
            with self.subTest(route=f"{method} {path}"):
                response = await self.client.request(method, path)
                self.assertEqual(401, response.status_code)
                self.assertFalse(response.json()["ok"])


if __name__ == "__main__":
    unittest.main()
