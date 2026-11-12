"""Chain tests (task 3.4): a real platform route reaches the Admin analytics API.

One representative metric, Course `completed_user_lessons`, is written through
each client's own authenticated route on PostgreSQL, then read through the
cookie-authenticated Admin analytics API under every filter:

- Telegram Mini App: signed `/api/v3/lesson/start` + `/api/v3/lesson/complete`;
- iPhone PWA: cookie + CSRF `/api/v3/pwa/lesson/start` + `/api/v3/pwa/lesson/complete`;
- Android: bearer `/api/v3/android/course/complete`.

Next-stage R1 adds Course `features.lessons` for Android: the bearer lesson
route writes the server-only `android_lesson_started`.

Next-stage R2 adds PWA activation: `/api/v3/pwa/onboarding` tags the cohort
anchor, and `/api/v3/pwa-auth/handoff/redeem` writes the handoff anchor.
Next-stage R4 adds D1/D7 return per platform from each account's first use.

Each client completes a different number of lessons, so a value that leaked
into another filter would change that filter's count.
Run with ANALYTICS_TEST_DATABASE_URL pointing at a disposable PostgreSQL DB.
"""
import hashlib
import hmac
import json
import os
import time
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.main as main
import tests.test_pwa_browser_auth as pwa
from app.admin_api.pwa_analytics_transport import create_admin_pwa_analytics_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.api.android_course import create_android_course_router
from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.api.native_oauth import create_native_oauth_router
from app.api.pwa_auth import create_pwa_auth_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.course_miniapp_event import CourseMiniAppEvent as Event
from app.db.models.course_progress import CourseProgress
from app.services.desktop_app_promo_settings_service import save_desktop_app_promo_settings
from app.services.desktop_auth_service import DesktopAuthService
from app.services.identity_link_service import IdentityLinkService

URL = os.environ.get("ANALYTICS_TEST_DATABASE_URL", "")
ADMIN_ORIGIN = "https://hskai.app"
ADMIN_COOKIE = "C" * 64
TELEGRAM_ID, ANDROID_TELEGRAM_ID, ADMIN_TELEGRAM_ID = 1001, 1003, 9001
# Different counts per client: a leak into another filter changes its value.
LESSONS = {"telegram": 1, "iphone_pwa": 2, "android": 3}


def pro(user):
    # PRO learners have no daily lesson cap, so one test can complete several.
    user.status, user.payment_status = "active", "approved"
    user.end_date = datetime.now(timezone.utc) + timedelta(days=30)
    return user


@unittest.skipUnless(URL.startswith("postgresql+asyncpg://"), "set ANALYTICS_TEST_DATABASE_URL for the chain tests")
class CoursePlatformChainTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "analytics_chain_" + uuid4().hex
        self.engine = create_async_engine(URL, connect_args={"server_settings": {"search_path": self.schema}})
        async with self.engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA " + self.schema))
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = pwa.settings()
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add_all([pro(pwa.user(1, TELEGRAM_ID)), pro(pwa.user(2, None)),
                        pro(pwa.user(3, ANDROID_TELEGRAM_ID)), pwa.user(101, ADMIN_TELEGRAM_ID)])
            await db.flush()
            db.add_all([CourseProgress(user_id=uid, level="hsk1", completed_lessons_count=0, current_step="intro",
                                       waiting_for="none", homework_status="none") for uid in (1, 2, 3)])
            db.add(AdminPwaSession(id=str(uuid4()), user_id=101, auth_method="webauthn",
                                   token_hash=hashlib.sha256(ADMIN_COOKIE.encode()).hexdigest(),
                                   created_at=now, expires_at=now + timedelta(hours=1)))
            await db.commit()
            # The PWA learner signs in with Google; that identity owns account 2.
            await IdentityLinkService(db, self.settings).link_to_user(pwa.identity(), user_id=2)
            await db.commit()

        self.stack = ExitStack()
        # Telegram and PWA completions live in app.main and use its settings
        # and session maker; point both at this disposable schema.
        for key, value in vars(self.settings).items():
            self.stack.enter_context(patch.object(main.settings, key, value))
        for target in ("app.main.async_session_maker",
                       "app.services.conversion_funnel_service.async_session_maker",
                       "app.services.entitlements.shadow.async_session_maker"):
            self.stack.enter_context(patch(target, self.sessions))

        learner = FastAPI()
        learner.include_router(create_native_oauth_router(session_factory=self.sessions, settings_obj=self.settings))
        learner.include_router(create_pwa_auth_router(session_factory=self.sessions, settings_obj=self.settings,
                                                      bot=SimpleNamespace()))
        learner.include_router(create_miniapp_entitlements_router(session_factory=self.sessions,
                                                                  settings_obj=self.settings))
        learner.include_router(create_android_course_router(session_factory=self.sessions, settings_obj=self.settings))
        learner.add_api_route("/api/v3/lesson/complete", main.v3_course_lesson_complete, methods=["POST"])
        learner.add_api_route("/api/v3/pwa/lesson/complete", main.pwa_v3_course_lesson_complete, methods=["POST"])
        learner.add_api_route("/api/miniapp/event", main.miniapp_event, methods=["POST"])
        learner.add_api_route("/api/miniapp/onboarding", main.miniapp_onboarding, methods=["POST"])
        self.learner = learner
        self.client = AsyncClient(transport=ASGITransport(app=learner), base_url=pwa.ORIGIN)

    async def asyncTearDown(self):
        await self.client.aclose()
        self.stack.close()
        async with self.engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS " + self.schema + " CASCADE"))
        await self.engine.dispose()

    def telegram_headers(self, telegram_id=TELEGRAM_ID):
        values = {"auth_date": str(int(time.time())), "user": json.dumps({"id": telegram_id})}
        secret = hmac.new(b"WebAppData", self.settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
        values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        return {"X-Telegram-Init-Data": urlencode(values)}

    async def pwa_headers(self):
        started = await self.client.post("/api/v3/pwa-auth/start", headers={"Origin": pwa.ORIGIN},
                                          json={"provider": "google", "language": "uz"})
        self.assertEqual(started.status_code, 200, started.text)
        state = started.json()["authorize_url"].split("state=", 1)[1].split("&", 1)[0]
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="google-id-token"), \
                patch.object(google_auth, "verify_desktop_id_token", return_value=pwa.identity()):
            await self.client.get("/api/v3/native-auth/oauth/callback/google",
                                  params={"state": state, "code": "auth-code"})
        session = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(session.status_code, 200, session.text)
        return {"Origin": pwa.ORIGIN, "X-HSK-PWA-CSRF": session.json()["csrf"]}

    async def android_headers(self):
        async with self.sessions() as db:
            auth = DesktopAuthService(db, self.settings)
            link = await auth.start_link(platform="android", app_version="1.0.0", installation_key="i" * 48)
            await auth.approve_link(display_code=link["display_code"], telegram_id=ANDROID_TELEGRAM_ID)
            linked = await auth.poll_link(link_request_id=link["link_request_id"],
                                          polling_secret=link["polling_secret"])
            await db.commit()
        return {"Authorization": "Bearer " + linked["access_token"]}

    async def complete_lessons(self, start, complete, headers, count, first=1):
        for lesson in range(first, first + count):
            body = {"lesson_id": lesson, "level": "hsk1"}
            started = await self.client.post(start, headers=headers, json=body)
            self.assertEqual(started.status_code, 200, started.text)
            done = await self.client.post(complete, headers=headers,
                                          json={**body, "completion_proof": started.json()["completion_proof"]})
            self.assertEqual(done.status_code, 200, done.text)

    async def handoff_browser(self, telegram_id):
        """A Telegram account hands off to a fresh PWA browser; returns that
        browser and its CSRF headers."""
        started = await self.client.post("/api/v3/pwa-auth/handoff/start", headers=self.telegram_headers(telegram_id),
                                         json={"language": "uz", "source": "profile"})
        self.assertEqual(started.status_code, 200, started.text)
        token = dict(item.split("=", 1) for item in urlsplit(started.json()["url"]).fragment.split("&"))["t"]
        browser = AsyncClient(transport=ASGITransport(app=self.learner), base_url=pwa.ORIGIN)
        self.addAsyncCleanup(browser.aclose)
        redeemed = await browser.post("/api/v3/pwa-auth/handoff/redeem", headers={"Origin": pwa.ORIGIN},
                                      json={"token": token})
        self.assertEqual(redeemed.status_code, 200, redeemed.text)
        session = await browser.get("/api/v3/pwa-auth/session")
        self.assertEqual(session.status_code, 200, session.text)
        return browser, {"Origin": pwa.ORIGIN, "X-HSK-PWA-CSRF": session.json()["csrf"]}

    async def admin_read(self, platform):
        admin_settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ADMIN_ORIGIN,
                                         admin_id_list=[ADMIN_TELEGRAM_ID])
        app = FastAPI()
        app.include_router(create_admin_pwa_analytics_router(settings_obj=admin_settings,
                                                             session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url=ADMIN_ORIGIN) as admin:
            response = await admin.post("/api/admin/v1/analytics",
                                        json={"section": "course", "platform": platform, "period": "weekly"},
                                        headers={"Origin": ADMIN_ORIGIN,
                                                 "Cookie": ADMIN_PWA_COOKIE_NAME + "=" + ADMIN_COOKIE})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_each_client_route_reaches_its_own_admin_filter_and_overall(self):
        await self.complete_lessons("/api/v3/lesson/start", "/api/v3/lesson/complete",
                                    self.telegram_headers(), LESSONS["telegram"])
        await self.complete_lessons("/api/v3/pwa/lesson/start", "/api/v3/pwa/lesson/complete",
                                    await self.pwa_headers(), LESSONS["iphone_pwa"])
        android = await self.android_headers()
        for lesson in range(1, LESSONS["android"] + 1):
            done = await self.client.post("/api/v3/android/course/complete", headers=android,
                                          json={"lesson_order": lesson, "event_id": f"android:{lesson:032x}"})
            self.assertEqual(done.status_code, 200, done.text)

        async with self.sessions() as db:
            rows = (await db.execute(select(Event.user_id, Event.source, Event.payload_json).where(
                Event.event_name == "lesson_completed").order_by(Event.id))).all()
        # The routes, not the callers, decided each attribution.
        self.assertEqual([(uid, source) for uid, source, _ in rows],
                         [(1, "course_v3"), *[(2, "course_v3")] * 2, *[(3, "android_course")] * 3])
        self.assertEqual({json.loads(payload).get("client") for uid, _, payload in rows if uid != 3},
                         {"telegram", "iphone_pwa"})

        views = {platform: await self.admin_read(platform)
                 for platform in ("overall", "android", "telegram", "iphone_pwa")}
        values = {platform: view["metrics"]["completed_user_lessons"] for platform, view in views.items()}
        self.assertEqual(values, {"overall": 6, **LESSONS})
        for platform, view in views.items():
            self.assertEqual(view["metric_states"]["completed_user_lessons"],
                             {"state": "available", "reason": None}, platform)
        # Telegram and PWA count from their first server-tagged completion.
        for platform in ("telegram", "iphone_pwa"):
            self.assertIsNotNone(views[platform]["metrics"]["attributed_since"]["completed_user_lessons"])
        self.assertNotIn("completed_user_lessons", views["android"]["metrics"]["attributed_since"])

    async def test_android_lesson_open_counts_once_under_android_and_overall(self):
        android = await self.android_headers()
        for _ in range(2):  # a refetch on the same UTC day
            opened = await self.client.get("/api/v3/android/course/lesson/1", headers=android)
            self.assertEqual(opened.status_code, 200, opened.text)
        locked = await self.client.get("/api/v3/android/course/lesson/2", headers=android)
        self.assertEqual(locked.status_code, 403, locked.text)
        # The same account also starts a lesson in the Telegram Mini App, and a
        # caller tries to write the Android name through the Telegram route.
        telegram = self.telegram_headers(ANDROID_TELEGRAM_ID)
        for event in ("lesson_started", "android_lesson_started"):
            await self.client.post("/api/miniapp/event", headers=telegram,
                                   json={"event": event, "level": "hsk1", "lesson_id": 1, "client": "android"})

        async with self.sessions() as db:
            rows = (await db.execute(select(Event.event_name, Event.user_id, Event.source, Event.lesson_order,
                                            Event.payload_json).where(
                Event.event_name.in_(("android_lesson_started", "lesson_started"))).order_by(Event.id))).all()
        # One server-built Android start; reminders read `lesson_started`, which
        # only the Telegram route wrote, with its own route key.
        self.assertEqual([(name, uid, source, order) for name, uid, source, order, _ in rows],
                         [("android_lesson_started", 3, "android_course", 1), ("lesson_started", 3, "course_miniapp", 1)])
        self.assertEqual([json.loads(payload)["client"] for *_, payload in rows], ["android", "telegram"])

        android_view, overall_view = await self.admin_read("android"), await self.admin_read("overall")
        lessons = {view: next(row for row in data["metrics"]["features"] if row["key"] == "lessons")
                   for view, data in (("android", android_view), ("overall", overall_view))}
        self.assertEqual({view: (row["paid"], row["free"]) for view, row in lessons.items()},
                         {"android": (1, 0), "overall": (1, 0)})
        self.assertIsNotNone(android_view["metrics"]["attributed_since"]["features_lessons"])
        self.assertEqual(android_view["metric_states"]["features"], {"state": "available", "reason": None})

    async def test_pwa_onboarding_and_handoff_reach_the_pwa_activation(self):
        onboarding = {"level": "hsk1", "goal": "hsk_exam", "daily_minutes": 10, "start_mode": "placement",
                      "language": "uz", "timezone_offset_minutes": 0, "activation_variant": "direct_start_v1"}
        lesson = {"event": "lesson_started", "level": "hsk1", "lesson_id": 1}
        # New PWA learner (account 2): onboards, starts and completes a lesson.
        browser = await self.pwa_headers()
        finished = await self.client.post("/api/v3/pwa/onboarding", headers=browser, json=onboarding)
        self.assertEqual(finished.status_code, 200, finished.text)
        started = await self.client.post("/api/v3/pwa/event", headers=browser, json=lesson)
        self.assertEqual(started.status_code, 200, started.text)
        await self.complete_lessons("/api/v3/pwa/lesson/start", "/api/v3/pwa/lesson/complete", browser, 1)
        # A Telegram learner (account 1) onboards and starts in the Mini App; the
        # caller's `client` cannot move either row to the PWA.
        telegram = self.telegram_headers()
        finished = await self.client.post("/api/miniapp/onboarding", headers=telegram,
                                          json={**onboarding, "client": "iphone_pwa"})
        self.assertEqual(finished.status_code, 200, finished.text)
        await self.client.post("/api/miniapp/event", headers=telegram, json={**lesson, "client": "iphone_pwa"})
        # Accounts 1 and 3 hand off from Telegram; only account 1 then learns on the PWA.
        async with self.sessions() as db:
            await save_desktop_app_promo_settings(db, {"platforms": {
                "macos": True, "windows": True, "android": True, "ios": True}})
            await db.commit()
        handed, handed_headers = await self.handoff_browser(TELEGRAM_ID)
        started = await handed.post("/api/v3/pwa/event", headers=handed_headers, json=lesson)
        self.assertEqual(started.status_code, 200, started.text)
        await self.handoff_browser(ANDROID_TELEGRAM_ID)

        async with self.sessions() as db:
            rows = (await db.execute(select(Event.event_name, Event.user_id, Event.payload_json).where(
                Event.event_name.in_(("onboarding_completed", "lesson_started", "pwa_handoff_completed")))
                .order_by(Event.id))).all()
            # Age every row past the 24-hour handoff window; their order is kept.
            await db.execute(update(Event).values(created_at=Event.created_at - timedelta(hours=25)))
            await db.commit()
        clients = [(name, uid, json.loads(payload).get("client")) for name, uid, payload in rows]
        self.assertEqual(clients, [
            ("onboarding_completed", 2, "iphone_pwa"), ("lesson_started", 2, "iphone_pwa"),
            ("onboarding_completed", 1, "telegram"), ("lesson_started", 1, "telegram"),
            ("pwa_handoff_completed", 1, None), ("lesson_started", 1, "iphone_pwa"),
            ("pwa_handoff_completed", 3, None)])

        pwa_view, overall_view = await self.admin_read("iphone_pwa"), await self.admin_read("overall")
        metrics = pwa_view["metrics"]
        self.assertEqual(metrics["activation"], {"eligible": 1, "started": 1, "percent": 100.0})
        self.assertEqual(metrics["direct_activation"], {"eligible": 1, "started": 1, "percent": 100.0})
        self.assertEqual(metrics["handoff_activation"], {"eligible": 2, "activated": 1, "percent": 50.0})
        for key in ("activation", "direct_activation", "handoff_activation"):
            self.assertEqual(pwa_view["metric_states"][key], {"state": "available", "reason": None}, key)
            self.assertIsNotNone(metrics["attributed_since"]["activation" if key == "direct_activation" else key])
        # Overall reads the same rows as before: both onboarded accounts.
        self.assertEqual(overall_view["metrics"]["activation"], {"eligible": 2, "started": 2, "percent": 100.0})
        self.assertEqual(overall_view["metrics"]["direct_activation"], {"eligible": 2, "started": 2, "percent": 100.0})
        self.assertNotIn("handoff_activation", overall_view["metrics"])
        telegram_view = await self.admin_read("telegram")
        self.assertEqual(telegram_view["metric_states"]["activation"]["state"], "unavailable")
        self.assertNotIn("handoff_activation", telegram_view["metrics"])

    async def age_rows(self, hours):
        async with self.sessions() as db:
            await db.execute(update(Event).values(created_at=Event.created_at - timedelta(hours=hours)))
            await db.commit()

    async def test_first_use_returns_reach_each_platform_filter(self):
        telegram, pwa_browser, android = self.telegram_headers(), await self.pwa_headers(), await self.android_headers()
        async def learn(lesson):
            await self.complete_lessons("/api/v3/lesson/start", "/api/v3/lesson/complete", telegram, 1, lesson)
            await self.complete_lessons("/api/v3/pwa/lesson/start", "/api/v3/pwa/lesson/complete",
                                        pwa_browser, 1, lesson)
            # A completed lesson is recorded once per account, so the Android
            # account's own lessons follow its Telegram lesson 1.
            done = await self.client.post("/api/v3/android/course/complete", headers=android,
                                          json={"lesson_order": lesson + 1, "event_id": f"android:{lesson:032x}"})
            self.assertEqual(done.status_code, 200, done.text)
        # First use on each client; the Android account also learns once in Telegram.
        await self.complete_lessons("/api/v3/lesson/start", "/api/v3/lesson/complete",
                                    self.telegram_headers(ANDROID_TELEGRAM_ID), 1)
        await learn(1)
        await self.age_rows(30)
        # 30 hours later each account returns on its own client only (D1 window).
        await learn(2)
        await self.age_rows(48)  # the D1 cohort is now mature

        views = {platform: await self.admin_read(platform) for platform in ("android", "telegram", "iphone_pwa")}
        returns = {platform: (view["metrics"]["return_retention"]["d1"]["eligible"],
                              view["metrics"]["return_retention"]["d1"]["returned"])
                   for platform, view in views.items()}
        # The Android account's return was on Android, so it is not a Telegram return.
        self.assertEqual(returns, {"android": (1, 1), "telegram": (2, 1), "iphone_pwa": (1, 1)})
        for platform, view in views.items():
            self.assertEqual(view["metric_states"]["return_retention"], {"state": "available", "reason": None})
            self.assertIsNotNone(view["metrics"]["attributed_since"]["return_retention"], platform)


if __name__ == "__main__":
    unittest.main()
