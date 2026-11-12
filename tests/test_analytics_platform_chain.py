"""Chain tests (task 3.4): a real platform route reaches the Admin analytics API.

One representative metric, Course `completed_user_lessons`, is written through
each client's own authenticated route on PostgreSQL, then read through the
cookie-authenticated Admin analytics API under every filter:

- Telegram Mini App: signed `/api/v3/lesson/start` + `/api/v3/lesson/complete`;
- iPhone PWA: cookie + CSRF `/api/v3/pwa/lesson/start` + `/api/v3/pwa/lesson/complete`;
- Android: bearer `/api/v3/android/course/complete`.

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
from urllib.parse import urlencode
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
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
        self.client = AsyncClient(transport=ASGITransport(app=learner), base_url=pwa.ORIGIN)

    async def asyncTearDown(self):
        await self.client.aclose()
        self.stack.close()
        async with self.engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS " + self.schema + " CASCADE"))
        await self.engine.dispose()

    def telegram_headers(self):
        values = {"auth_date": str(int(time.time())), "user": json.dumps({"id": TELEGRAM_ID})}
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

    async def complete_lessons(self, start, complete, headers, count):
        for lesson in range(1, count + 1):
            body = {"lesson_id": lesson, "level": "hsk1"}
            started = await self.client.post(start, headers=headers, json=body)
            self.assertEqual(started.status_code, 200, started.text)
            done = await self.client.post(complete, headers=headers,
                                          json={**body, "completion_proof": started.json()["completion_proof"]})
            self.assertEqual(done.status_code, 200, done.text)

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


if __name__ == "__main__":
    unittest.main()
