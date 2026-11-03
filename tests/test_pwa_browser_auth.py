"""Security contract for PWA-only OAuth session, no native/Telegram bypass."""

import unittest
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.native_oauth import create_native_oauth_router
from app.api.pwa_auth import create_pwa_auth_router
from app.api.course_tracks import create_course_tracks_router
from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.api.miniapp_practice import create_miniapp_practice_router
from app.db.base import Base
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from app.services.oidc_verifier import VerifiedIdentity
from app.services.pwa_auth_service import PWA_OAUTH_COOKIE, PWA_SESSION_COOKIE


ORIGIN = "https://api.example.test"


def settings(**kwargs):
    values = dict(
        PWA_AUTH_ENABLED=True,
        DESKTOP_AUTH_SIGNING_SECRET="pwa-security-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
        BOT_TOKEN="123456789:AAExampleBotTokenForInitDataSigning1234",
        GOOGLE_OAUTH_ENABLED=True,
        GOOGLE_ANDROID_WEB_CLIENT_ID="111-web.apps.googleusercontent.com",
        GOOGLE_DESKTOP_CLIENT_ID="222-desktop.apps.googleusercontent.com",
        GOOGLE_DESKTOP_CLIENT_SECRET="desktop-secret",
        APPLE_OAUTH_ENABLED=False,
        APPLE_SERVICE_ID="",
        APPLE_TEAM_ID="",
        APPLE_KEY_ID="",
        APPLE_PRIVATE_KEY="",
        OAUTH_REDIRECT_BASE_URL=ORIGIN,
        OAUTH_ID_TOKEN_MAX_AGE_SECONDS=300,
        OAUTH_HTTP_TIMEOUT_SECONDS=8.0,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def user(uid, telegram_id):
    return User(
        id=uid, telegram_id=telegram_id, full_name="Existing learner",
        language="uz", level="hsk1", learning_mode="course", voice_mode="none",
        status="free", payment_status="none", question_limit=5,
        questions_used=0, bonus_questions=0, bonus_questions_used=0,
        discount_referral_count=0, discount_eligible=False, discount_used=False,
        daily_practice_streak=0, created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )


def identity():
    return VerifiedIdentity(
        provider="google", subject="existing-sub", email="linked@example.test",
        email_verified=True, display_name="Existing learner",
        audience="222-desktop.apps.googleusercontent.com",
    )


class PwaBrowserAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = settings()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(user(1, 1001))
            await session.commit()
            await IdentityLinkService(session, self.settings).link_to_user(identity(), user_id=1)
            await session.commit()
        app = FastAPI()
        app.include_router(create_native_oauth_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        app.include_router(create_pwa_auth_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        app.include_router(create_course_tracks_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        app.include_router(create_miniapp_entitlements_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        app.include_router(create_miniapp_practice_router(
            session_factory=self.sessions, settings_obj=self.settings
        ))
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url=ORIGIN
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def begin(self):
        response = await self.client.post(
            "/api/v3/pwa-auth/start", headers={"Origin": ORIGIN},
            json={"provider": "google", "language": "uz"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(PWA_OAUTH_COOKIE, response.cookies)
        self.assertNotIn("polling_secret", response.json())
        state = parse_qs(urlparse(response.json()["authorize_url"]).query)["state"][0]
        return state

    async def callback(self, state, client=None):
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="google-id-token"), patch.object(
            google_auth, "verify_desktop_id_token", return_value=identity(),
        ):
            return await (client or self.client).get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "auth-code"},
            )

    async def test_pwa_limits_reuses_canonical_user_and_rejects_forged_requests(self):
        path = "/api/v3/pwa/limits/status"
        self.assertEqual((await self.client.post(
            path, headers={"Origin": ORIGIN}, json={"feature": "lesson"},
        )).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        self.assertEqual((await self.client.post(
            path, headers={"Origin": ORIGIN}, json={"feature": "voice"},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            path, headers={**headers, "Origin": "https://evil.test"},
            json={"feature": "voice"},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            path, headers=headers, json={"feature": "voice", "user_id": 999},
        )).status_code, 400)
        with patch(
            "app.api.miniapp_entitlements.CourseMiniAppAccessService.configured_decision",
            new_callable=AsyncMock,
        ) as decision:
            decision.return_value = {"allowed": False, "reason": "daily_limit"}
            response = await self.client.post(
                path, headers=headers, json={"feature": "mistake_review"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["reason"], "daily_limit")
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertEqual(decision.await_args.args[0].id, 1)
            self.assertEqual(decision.await_args.args[1], "training_test")
        self.assertEqual((await self.client.post(
            "/api/v3/limits/status", json={"feature": "lesson"},
        )).status_code, 401)

    async def test_pwa_foundation_is_server_authenticated_not_public_or_telegram(self):
        url = "/api/v3/pwa/lesson/foundation"
        self.assertEqual((await self.client.get(url)).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        with patch(
            "app.api.miniapp_entitlements._read_course_lesson",
            return_value={"foundation": {"cards": [{"id": "first"}]}},
        ) as source:
            response = await self.client.get(url)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["foundation"]["cards"][0]["id"], "first")
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            source.assert_called_once_with("hsk1", 1)
        self.assertEqual(
            (await self.client.get("/api/v3/lesson/foundation")).status_code,
            401,
        )

    async def test_pwa_lesson_start_retains_quota_proofs_and_csrf_guards(self):
        path = "/api/v3/pwa/lesson/start"
        payload = {"lesson_id": 1, "level": "hsk1"}
        unauthenticated = await self.client.post(
            path, headers={"Origin": ORIGIN}, json=payload,
        )
        self.assertEqual(unauthenticated.status_code, 401, unauthenticated.text)
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        for headers in [
            {"Origin": "https://evil.test", "X-HSK-PWA-CSRF": csrf},
            {"Origin": ORIGIN},
            {"Origin": ORIGIN, "X-HSK-PWA-CSRF": "forged"},
        ]:
            rejected = await self.client.post(path, headers=headers, json=payload)
            self.assertEqual(rejected.status_code, 403, rejected.text)
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        injected = await self.client.post(
            path, headers=headers, json={**payload, "user_id": 999},
        )
        self.assertEqual(injected.status_code, 400, injected.text)
        stale = await self.client.post(
            path, headers=headers, json={"lesson_id": 1, "level": "hsk2"},
        )
        self.assertEqual(stale.status_code, 409, stale.text)
        with patch(
            "app.api.miniapp_entitlements.LessonAccessService.status",
            new_callable=AsyncMock,
        ) as status, patch(
            "app.api.miniapp_entitlements.remember_authorized_lesson_start",
            new_callable=AsyncMock,
        ) as grant, patch(
            "app.api.miniapp_entitlements.issue_lesson_completion_proof",
            return_value="test-proof",
        ) as proof:
            status.return_value = {"ok": False, "allowed": False, "error": "limit_reached"}
            denied = await self.client.post(path, headers=headers, json=payload)
            self.assertEqual(denied.status_code, 403, denied.text)
            grant.assert_not_awaited()
            proof.assert_not_called()
            status.return_value = {"ok": True, "allowed": True}
            admitted = await self.client.post(path, headers=headers, json=payload)
            self.assertEqual(admitted.status_code, 200, admitted.text)
            self.assertEqual(admitted.json()["completion_proof"], "test-proof")
            self.assertEqual(admitted.headers.get("cache-control"), "no-store")
            self.assertEqual(status.await_args.args[0].id, 1)
            self.assertEqual(status.await_args.kwargs["consume"], True)
            grant.assert_awaited_once()
            self.assertEqual(grant.await_args.kwargs["user"].id, 1)
            self.assertEqual(proof.call_args.kwargs["user_id"], 1)
        legacy = await self.client.post(
            "/api/v3/lesson/start", json=payload,
        )
        self.assertEqual(legacy.status_code, 401, legacy.text)

    async def test_pwa_lesson_content_uses_exact_miniapp_policy_without_initdata(self):
        path = "/api/v3/pwa/lesson/content/hsk1/1"
        denied = await self.client.get(path)
        self.assertEqual(denied.status_code, 401, denied.text)
        self.assertEqual(denied.json()["error"], "pwa_session_required")
        state = await self.begin()
        await self.callback(state)
        self.assertEqual((await self.client.get(
            "/api/v3/lesson/content/hsk1/1"
        )).status_code, 401)
        wrong_level = await self.client.get("/api/v3/pwa/lesson/content/hsk2/1")
        self.assertEqual(wrong_level.status_code, 403, wrong_level.text)
        self.assertEqual(wrong_level.json()["error"], "course_level_not_allowed")
        with patch(
            "app.api.miniapp_entitlements.LessonAccessService.status",
            new_callable=AsyncMock,
        ) as access, patch(
            "app.api.miniapp_entitlements._read_course_lesson",
            return_value={"ok": True, "level": "hsk1", "lesson_order": 1},
        ) as read_course:
            access.return_value = {"allowed": True, "idempotent": True}
            permitted = await self.client.get(path)
            self.assertEqual(permitted.status_code, 200, permitted.text)
            self.assertEqual(permitted.json()["lesson_order"], 1)
            self.assertEqual(permitted.headers.get("cache-control"), "no-store")
            read_course.assert_called_once_with("hsk1", 1)
            self.assertEqual(access.await_args.args[0].id, 1)
            self.assertEqual(access.await_args.kwargs["consume"], False)
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.status = "blocked"
            await db.commit()
        self.assertEqual((await self.client.get(path)).status_code, 401)

    async def test_pwa_lesson_for_google_only_account_needs_no_fake_telegram_id(self):
        state = await self.begin()
        verified = VerifiedIdentity(
            provider="google", subject="pwa-only-lesson-subject",
            email="pwa-only@example.test", email_verified=True,
            display_name="Browser learner",
            audience="222-desktop.apps.googleusercontent.com",
        )
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="pwa-only-token"), patch.object(
            google_auth, "verify_desktop_id_token", return_value=verified,
        ):
            done = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "pwa-only-code"},
            )
        self.assertEqual(done.status_code, 303, done.text)
        actor = (await self.client.get("/api/v3/pwa-auth/session")).json()
        self.assertFalse(actor["telegram_linked"])
        async with self.sessions() as db:
            owner = await db.get(User, actor["user_id"])
            self.assertIsNone(owner.telegram_id)
            owner.level = "hsk1"
            await db.commit()
        with patch(
            "app.api.miniapp_entitlements.LessonAccessService.status",
            new_callable=AsyncMock,
        ) as access, patch(
            "app.api.miniapp_entitlements._read_course_lesson",
            return_value={"ok": True, "lesson_order": 1},
        ):
            access.return_value = {"allowed": True, "idempotent": True}
            response = await self.client.get(
                "/api/v3/pwa/lesson/content/hsk1/1"
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["ok"])
            self.assertEqual(access.await_args.args[0].id, actor["user_id"])
            self.assertIsNone(access.await_args.args[0].telegram_id)
        self.assertEqual(
            (await self.client.get("/api/v3/lesson/content/hsk1/1")).status_code,
            401,
        )

    def test_ios_writer_taps_do_not_trigger_browser_zoom_or_break_swipes(self):
        login = (Path("app/static") / "iphone-pwa-login.html").read_text(encoding="utf-8")
        dictionary = (Path("app/static") / "hsk-lugat.html").read_text(encoding="utf-8")
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        phrases = (Path("app/static") / "hsk-gaplar.html").read_text(encoding="utf-8")
        # A focused <select> below 16px causes Safari's accessibility
        # auto-focus zoom, even when it is visually small.
        self.assertIn("font:600 16px var(--hsk-font-ui)", login)
        # Writing canvas must keep one-finger vertical scrolling, own horizontal
        # pointer swipe between characters and accessible two-finger pinch-zoom.
        # Omit the double-tap-to-zoom gesture instead of disabling page zoom.
        self.assertIn("flex-shrink:0;touch-action:pan-y pinch-zoom}", dictionary)
        self.assertIn("rgba(181,146,98,.28);touch-action:pan-y pinch-zoom}", dictionary)
        self.assertIn("box.addEventListener('pointerup'", dictionary)
        self.assertIn("charBoxLg.addEventListener('pointerup'", dictionary)
        # The course's existing writing action still loads this exact shared
        # writer iframe. No extra PWA-only writer implementation is needed.
        self.assertIn('var url="/hsk-lugat.html?theme=light&fast=1&char="+encodeURIComponent(ch)', course)
        self.assertIn('fr.src=url;', course)
        self.assertIn("#search{width:100%;padding:13px 84px 13px 44px;font-size:16px", dictionary)
        self.assertIn("#vc-root .kb textarea{flex:1;min-height:46px;max-height:96px;resize:none;font-family:inherit;font-size:16px", course)
        self.assertIn("color: var(--ink); font-size: 16px;", phrases)
        for html in (login, dictionary, course, phrases):
            self.assertNotIn("user-scalable=no", html)
            self.assertNotIn("maximum-scale=1", html)

    async def test_shared_course_entry_needs_valid_pwa_session_and_flag(self):
        path = "/iphone-pwa/course"
        anonymous = await self.client.get(path, follow_redirects=False)
        self.assertEqual(anonymous.status_code, 303, anonymous.text)
        self.assertEqual(anonymous.headers["location"], "/iphone-pwa")
        self.assertEqual(anonymous.headers["cache-control"], "no-store")
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(path)
        self.assertEqual(page.status_code, 200, page.text[:200])
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(page.headers["x-frame-options"], "DENY")
        self.assertIn("var PWA_COURSE_HOST=", page.text)
        self.assertIn('location.pathname==="/iphone-pwa/course"', page.text)
        # It must serve the original course HTML, never a copied/parallel UI.
        self.assertIn('var INIT_DATA=(tg&&tg.initData)||"";', page.text)
        self.assertIn('id="s-course"', page.text)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(path)).status_code, 503)

    def test_pwa_course_cache_keys_are_per_verified_owner_not_preview(self):
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        source = (Path("app/main.py")).read_text(encoding="utf-8")
        self.assertIn('PWA_COURSE_USER_ID=ownerId;', course)
        self.assertIn('if(PWA_COURSE_HOST)return "pwa:"+String(PWA_COURSE_USER_ID||"unbound")', course)
        self.assertIn('r.headers.get("X-HSK-PWA-User-ID")!==String(PWA_COURSE_USER_ID)', course)
        self.assertIn('throw new Error("pwa_actor_changed")', course)
        self.assertIn('r.status===403&&d&&d.error==="pwa_csrf_invalid"', course)
        self.assertIn('response.headers["X-HSK-PWA-User-ID"] = str(user.id)', source)
        self.assertIn('function foundationCacheKey(id,version)', course)
        self.assertIn('function lessonResumeKey(level,lessonOrder)', course)
        self.assertIn('function lessonMasteryKey(level,lessonOrder)', course)
        # User-scoped browser caches must not be sent as access credentials.
        self.assertNotIn('localStorage.getItem("pwa_session"', course)
        self.assertNotIn('localStorage.setItem("pwa_token"', course)

    def test_pwa_course_allowlist_routes_and_verified_login_forward(self):
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        login = (Path("app/static") / "iphone-pwa-login.js").read_text(encoding="utf-8")
        self.assertIn('"/api/v3/course-tracks":"/api/v3/pwa/course-tracks"', course)
        self.assertIn('"/api/v3/lesson/foundation":"/api/v3/pwa/lesson/foundation"', course)
        self.assertIn('mapped=parsed.pathname.replace("/api/v3/lesson/content/","/api/v3/pwa/lesson/content/")', course)
        self.assertIn("parsed.origin!==location.origin", course)
        self.assertIn("var lessonRequest=PWA_COURSE_HOST?_apiGet(lessonDataUrl(lv,n))", course)
        self.assertIn('var foundationRequest=PWA_COURSE_HOST?_apiGet("/api/v3/lesson/foundation")', course)
        self.assertIn("return fetch(mapped+parsed.search,", course)
        self.assertIn('"/api/v3/course-tracks/switch":"/api/v3/pwa/course-tracks/switch"', course)
        self.assertIn('"/api/v3/course-tracks/promo-shown":"/api/v3/pwa/course-tracks/promo-shown"', course)
        self.assertIn('"/api/v3/limits/status":"/api/v3/pwa/limits/status"', course)
        self.assertIn('"/api/v3/lesson/start":"/api/v3/pwa/lesson/start"', course)
        self.assertIn('if(!mapped)return Promise.reject(new Error("pwa_route_unavailable"));', course)
        self.assertIn('delete payload.user_id;delete payload.telegram_id;', course)
        self.assertIn('if(url==="/api/v3/lesson/start")delete payload.lang;', course)
        self.assertIn('credentials:"same-origin",cache:"no-store",redirect:"error"', course)
        self.assertIn('if(!INIT_DATA&&!PWA_COURSE_HOST)return Promise.reject(new Error("auth"));', course)
        self.assertIn('if((!INIT_DATA&&!PWA_COURSE_HOST)||!l||l.status!=="current")', course)
        # Only a server-confirmed sign-in may enter the authenticated course.
        self.assertEqual(login.count('location.replace("/iphone-pwa/course");'), 2)
        self.assertIn('await json("/api/v3/pwa-auth/session")', login)
        self.assertIn('reply.status === "complete"', login)
        self.assertNotIn('localStorage.setItem("pwa', login)

    def test_browser_course_map_uses_csrf_post_without_changing_telegram_transport(self):
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('PWA_COURSE_HOST=location.pathname==="/iphone-pwa/course"', course)
        self.assertIn('if(PWA_COURSE_HOST)INIT_DATA="";', course)
        self.assertIn('if(PWA_COURSE_HOST||!INIT_DATA||q.getAll("source")', course)
        self.assertIn('fetch("/api/v3/pwa-auth/session"', course)
        self.assertIn('method:"POST",headers:{"X-HSK-PWA-CSRF":actor.csrf}', course)
        self.assertIn('url.replace("/api/v3/map?","/api/v3/pwa/map?")', course)
        self.assertIn('credentials:"same-origin",cache:"no-store"', course)
        self.assertIn('location.replace("/iphone-pwa")', course)
        self.assertIn('fetch(url,{headers:{"X-Telegram-Init-Data":INIT_DATA}', course)
        self.assertIn('if(!INIT_DATA&&!PWA_COURSE_HOST)', course)
        self.assertNotIn('PWA_COURSE_HOST=!!location.search', course)
        self.assertNotIn('user-scalable=no', course)
        self.assertNotIn('maximum-scale=1', course)

    async def test_pwa_manifest_is_feature_gated_and_source_brand_only(self):
        manifest_path = "/iphone-pwa/manifest.webmanifest"
        response = await self.client.get(manifest_path)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith(
            "application/manifest+json"
        ))
        self.assertEqual(response.headers["cache-control"], "no-store")
        manifest = response.json()
        self.assertEqual(manifest["start_url"], "/iphone-pwa")
        self.assertEqual(manifest["scope"], "/iphone-pwa")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["background_color"], "#FDF9F0")
        self.assertEqual(manifest["icons"][0]["src"], "/assets/hsk-ai-logo-256.png")
        html = (Path("app/static") / "iphone-pwa-login.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('rel="manifest" href="/iphone-pwa/manifest.webmanifest"', html)
        self.assertIn('rel="apple-touch-icon" href="/assets/hsk-ai-logo-256.png"', html)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(manifest_path)).status_code, 503)
        self.assertEqual((await self.client.get("/iphone-pwa")).status_code, 503)

    async def test_pwa_account_notices_are_owned_and_cannot_ack_delivery(self):
        url = "/api/v3/pwa/account-notices"
        self.assertEqual((await self.client.get(url)).status_code, 401)
        async with self.sessions() as db:
            db.add(user(2, 2002))
            db.add(AccountNoticeDelivery(
                user_id=1, telegram_id=1001,
                key="subscription_update", language="uz",
                title="Account alert", body="Existing status",
                action="subscription", status="android_pending",
                android_targets=1, reason="account_notice",
            ))
            db.add(AccountNoticeDelivery(
                user_id=2, telegram_id=2002,
                key="private_notice", language="ru",
                title="Different owner", body="Do not reveal",
                action="course", status="telegram_sent",
                android_targets=0, reason="account_notice",
            ))
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        response = await self.client.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        rows = response.json()["notices"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Account alert")
        self.assertNotIn("status", rows[0])
        self.assertNotIn("telegram_payload", rows[0])
        async with self.sessions() as db:
            delivered = (await db.execute(
                select(AccountNoticeDelivery).where(AccountNoticeDelivery.user_id == 1)
            )).scalar_one()
            self.assertEqual(delivered.status, "android_pending")
            self.assertIsNone(delivered.android_shown_at)
            self.assertIsNone(delivered.telegram_sent_at)

    async def test_pwa_inbox_uses_canonical_owner_and_does_not_invent_notices(self):
        url = "/api/v3/pwa/notifications"
        self.assertEqual((await self.client.get(url)).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        with patch(
            "app.services.course_notification_service.CourseNotificationService.list_for_user",
            new_callable=AsyncMock,
        ) as inbox:
            inbox.return_value = [
                {"id": 5, "key": "course_progress", "body": "Existing notice"}
            ]
            response = await self.client.get(url)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["notifications"][0]["id"], 5)
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertEqual(inbox.await_args.args[0].id, 1)
            inbox.return_value = []
            empty = await self.client.get(url)
            self.assertEqual(empty.json()["notifications"], [])
        # Read-only content must not manufacture Telegram/Android delivery state.
        self.assertEqual(
            (await self.client.get("/api/v3/native-auth/identities")).status_code, 401
        )

    async def test_pwa_recognition_reuses_original_html_and_requires_browser_cookie(self):
        path = "/iphone-pwa/practice/recognition"
        anonymous = await self.client.get(path, follow_redirects=False)
        self.assertEqual(anonymous.status_code, 303, anonymous.text)
        self.assertEqual(anonymous.headers["location"], "/iphone-pwa")
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(path)
        self.assertEqual(page.status_code, 200, page.text[:150])
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(page.headers["x-frame-options"], "DENY")
        self.assertIn('location.pathname==="/iphone-pwa/practice/recognition"', page.text)
        self.assertIn('function initData()', page.text)
        self.assertIn('recognitionPost("/api/v3/practice/daily-gate"', page.text)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(path)).status_code, 503)

    async def test_pwa_memorize_reuses_original_html_with_account_cookie(self):
        path = "/iphone-pwa/practice/memorize"
        anonymous = await self.client.get(path, follow_redirects=False)
        self.assertEqual(anonymous.status_code, 303)
        self.assertEqual(anonymous.headers["location"], "/iphone-pwa")
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(path)
        self.assertEqual(page.status_code, 200, page.text[:160])
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        self.assertIn('PWA_MEMORIZE_HOST=location.pathname==="/iphone-pwa/practice/memorize"', page.text)
        self.assertIn('LV_READY.then(function(){return runGate(ref)}).then', page.text)
        self.assertNotIn("maximum-scale=1", page.text)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(path)).status_code, 503)

    def test_pwa_memorize_shares_gate_and_owner_scoped_local_mastery(self):
        source = (Path("app/static") / "course_v3_memorize.html").read_text(encoding="utf-8")
        self.assertIn('"/api/v3/practice/daily-gate":"/api/v3/pwa/practice/daily-gate"', source)
        self.assertIn('"/api/v3/practice/report":"/api/v3/pwa/practice/report"', source)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', source)
        self.assertIn('"X-HSK-PWA-CSRF":s.csrf', source)
        self.assertIn('"/api/v3/pwa/practice/profile"', source)
        self.assertIn('return "pwa:"+String(PWA_MEMORIZE_SESSION.user_id)', source)
        self.assertIn('if(!PWA_MEMORIZE_HOST&&window.CourseAds)', source)
        self.assertNotIn("user-scalable=no", source)

    async def test_pwa_pronunciation_uses_existing_html_and_verified_voice_actor(self):
        page_url = "/iphone-pwa/practice/pronunciation"
        score_url = "/api/v3/pwa/voice/pronounce"
        anonymous = await self.client.get(page_url, follow_redirects=False)
        self.assertEqual(anonymous.status_code, 303)
        self.assertEqual(anonymous.headers["location"], "/iphone-pwa")
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(page_url)
        self.assertEqual(page.status_code, 200, page.text[:150])
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        self.assertIn('PWA_PRONUNCIATION_HOST=location.pathname==="/iphone-pwa/practice/pronunciation"', page.text)
        self.assertIn('LV_READY.then(function(){return runGate(ref)})', page.text)
        self.assertNotIn("maximum-scale=1", page.text)

        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        sample = b"\\x00\\x00\\x00\\x14ftypisom" + b"\\x00" * 1300
        def params():
            return {
                "data": {"target": "你", "target_pinyin": "nǐ"},
                "files": {"audio": ("speech.mp4", sample, "audio/mp4")},
            }

        missing_csrf = await self.client.post(
            score_url, headers={"Origin": ORIGIN}, **params(),
        )
        self.assertEqual(missing_csrf.status_code, 403)
        foreign = await self.client.post(
            score_url, headers={**headers, "Origin": "https://attacker.test"},
            **params(),
        )
        self.assertEqual(foreign.status_code, 403)
        extra = await self.client.post(
            score_url, headers=headers,
            data={"target": "你", "user_id": "999"},
            files={"audio": ("speech.mp4", sample, "audio/mp4")},
        )
        self.assertEqual(extra.status_code, 422)
        with patch(
            "app.services.voice_practice_service.VoicePracticeService.score_pronunciation",
            new_callable=AsyncMock,
        ) as scorer:
            scorer.return_value = {"ok": True, "score": 81, "passed": True, "heard": "你"}
            good = await self.client.post(score_url, headers=headers, **params())
            self.assertEqual(good.status_code, 200, good.text)
            self.assertEqual(good.json()["score"], 81)
            self.assertEqual(good.headers.get("cache-control"), "no-store")
            self.assertEqual(scorer.await_args.args[0].id, 1)
            self.assertEqual(scorer.await_args.kwargs["language"], "uz")
            self.assertEqual(scorer.await_args.kwargs["level"], "hsk1")
            self.assertEqual(scorer.await_args.kwargs["filename"], "voice.mp4")
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(page_url)).status_code, 503)

    def test_pronunciation_pwa_client_does_not_inject_telegram_identity(self):
        source = (Path("app/static") / "course_v3_pronunciation.html").read_text(encoding="utf-8")
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('"/api/v3/practice/daily-gate":"/api/v3/pwa/practice/daily-gate"', source)
        self.assertIn('"/api/v3/practice/words":"/api/v3/pwa/practice/words"', source)
        self.assertIn('"/api/v3/practice/report":"/api/v3/pwa/practice/report"', source)
        self.assertIn('"/api/v3/pwa/voice/pronounce"', source)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', source)
        self.assertIn('payload.append("audio",fd.get("audio"))', source)
        self.assertIn('"/course_v3_pronunciation.html":"/iphone-pwa/practice/pronunciation"', course)
        self.assertIn('if(!PWA_PRONUNCIATION_HOST&&window.CourseAds)', source)

    async def test_pwa_mistakes_review_reuses_canonical_engine_and_scored_xp(self):
        path = "/iphone-pwa/practice/mistakes"
        self.assertEqual((await self.client.get(path, follow_redirects=False)).status_code, 303)
        self.assertEqual((await self.client.get("/api/v3/pwa/mistakes")).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(path)
        self.assertEqual(page.status_code, 200, page.text[:160])
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        with patch(
            "app.services.course_mistake_service.CourseMistakeService.overview",
            new_callable=AsyncMock,
        ) as overview:
            overview.return_value = {
                "ok": True, "items": [], "targets": [],
                "summary": {"total": 0, "categories": {}},
            }
            inline = await self.client.get("/api/v3/pwa/mistakes?limit=30&offset=0")
            standalone = await self.client.get(
                "/api/v3/pwa/mistakes?view=targets&lang=uz&limit=30",
            )
            self.assertEqual(inline.status_code, 200, inline.text)
            self.assertEqual(standalone.status_code, 200, standalone.text)
            self.assertEqual(overview.await_args.args[0].id, 1)
            self.assertEqual(overview.await_args.kwargs["view"], "targets")

        start_url = "/api/v3/pwa/mistakes/review/start"
        payload = {"ad_supported": False, "access_ref": "pwa-review-1"}
        self.assertEqual((await self.client.post(
            start_url, headers={"Origin": ORIGIN}, json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            start_url, headers={**headers, "Origin": "https://attacker.test"}, json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            start_url, headers=headers, json={**payload, "telegram_id": 1001},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            start_url, headers={**headers, "X-Telegram-Init-Data": "forged"},
            json=payload,
        )).status_code, 422)

        with patch(
            "app.services.course_mistake_service.CourseMistakeService.start_review",
            new_callable=AsyncMock,
        ) as start, patch(
            "app.services.course_mistake_service.CourseMistakeService.answer_review_question",
            new_callable=AsyncMock,
        ) as answer, patch(
            "app.services.course_mistake_service.CourseMistakeService.complete_review",
            new_callable=AsyncMock,
        ) as complete:
            start.return_value = {"ok": True, "session": {"id": "review-1", "questions": [{}]}}
            answer.return_value = {"ok": True, "selected_index": 1, "correct": True}
            complete.return_value = {"ok": True, "score": 1, "reward": {"awarded_xp": 10}}
            opened = await self.client.post(start_url, headers=headers, json=payload)
            self.assertEqual(opened.status_code, 200, opened.text)
            self.assertEqual(start.await_args.args[0].id, 1)
            self.assertIs(start.await_args.kwargs["ad_supported"], False)
            marked = await self.client.post(
                "/api/v3/pwa/mistakes/review/answer", headers=headers,
                json={"session_id": "review-1", "question_id": "q1", "selected_index": 1},
            )
            self.assertEqual(marked.status_code, 200, marked.text)
            self.assertEqual(answer.await_args.args[0].id, 1)
            graded = await self.client.post(
                "/api/v3/pwa/mistakes/review/complete", headers=headers,
                json={"session_id": "review-1", "answers": []},
            )
            self.assertEqual(graded.status_code, 200, graded.text)
            self.assertEqual(graded.json()["reward"]["awarded_xp"], 10)
            self.assertEqual(complete.await_args.args[0].id, 1)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(path)).status_code, 503)

    def test_mistakes_pwa_stays_in_original_course_and_reads_real_server_xp(self):
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        child = (Path("app/static") / "course_v3_mistakes.html").read_text(encoding="utf-8")
        self.assertIn('"/api/miniapp/mistakes":"/api/v3/pwa/mistakes"', course)
        self.assertIn('"/api/miniapp/mistakes/review/start":"/api/v3/pwa/mistakes/review/start"', course)
        self.assertIn('_apiGet(url).then(function(r)', course)
        self.assertIn('_apiPost("/api/miniapp/mistakes/review/complete"', course)
        self.assertIn('var t=L(),xp=(d.reward&&d.reward.awarded_xp)||0;', course)
        self.assertIn('PWA_MISTAKES_HOST=location.pathname==="/iphone-pwa/practice/mistakes"', child)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', child)
        self.assertIn('"/api/v3/pwa/mistakes/review/answer"', child)
        self.assertNotIn("maximum-scale=1", child)

    async def test_pwa_recognition_profile_uses_real_owner_level_and_progress(self):
        path = "/api/v3/pwa/practice/profile"
        self.assertEqual((await self.client.get(path)).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        with patch(
            "app.api.miniapp_practice.CourseProgressRepository.get_by_user_id",
            new_callable=AsyncMock,
        ) as progress:
            progress.return_value = SimpleNamespace(
                level="hsk1", completed_lessons_count=7,
            )
            response = await self.client.get(path)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["level"], "hsk1")
            self.assertEqual(response.json()["completed_lessons"], 7)
            self.assertEqual(response.headers["cache-control"], "no-store")
            progress.assert_awaited_once_with(1)
            progress.return_value = SimpleNamespace(
                level="hsk2", completed_lessons_count=30,
            )
            wrong_band = await self.client.get(path)
            self.assertEqual(wrong_band.json()["completed_lessons"], 0)
        # The legacy Telegram-only API is not mounted in this isolated
        # router fixture, so it cannot be used to establish browser identity.
        self.assertNotIn("telegram_id", response.json())

    def test_recognition_browser_requests_keep_server_quota_and_telegram_isolation(self):
        source = (Path("app/static") / "course_v3_recognition.html").read_text(encoding="utf-8")
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('PWA_RECOGNITION_HOST=location.pathname==="/iphone-pwa/practice/recognition"', source)
        self.assertIn('"/api/v3/practice/daily-gate":"/api/v3/pwa/practice/daily-gate"', source)
        self.assertIn('"/api/v3/practice/words":"/api/v3/pwa/practice/words"', source)
        self.assertIn('"/api/v3/practice/report":"/api/v3/pwa/practice/report"', source)
        self.assertIn('"/api/v3/pwa/practice/profile"', source)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', source)
        self.assertIn('"X-HSK-PWA-CSRF":s.csrf', source)
        self.assertIn('if(!PWA_RECOGNITION_HOST&&window.CourseAds)', source)
        self.assertIn('src="/iphone-pwa/practice/recognition"+target.search;', course)
        self.assertIn('"/course_v3_recognition.html":"/iphone-pwa/practice/recognition"', course)
        self.assertIn('"/course_v3_memorize.html":"/iphone-pwa/practice/memorize"', course)
        self.assertIn("if(!safePaths[path])", course)
        self.assertIn('if(!PWA_RECOGNITION_HOST)return fetch(url,{', source)
        self.assertNotIn("user-scalable=no", source)

    async def test_pwa_practice_lifetime_gate_shares_telegram_policy_and_owner(self):
        path = "/api/v3/pwa/practice/daily-gate"
        payload = {"feature": "recognition", "ref": "browser-attempt-1"}
        unauthenticated = await self.client.post(
            path, headers={"Origin": ORIGIN}, json=payload,
        )
        self.assertEqual(unauthenticated.status_code, 401, unauthenticated.text)
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        allowed_headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        for headers in [
            {"Origin": ORIGIN},
            {"Origin": "https://attacker.test", "X-HSK-PWA-CSRF": csrf},
        ]:
            denied = await self.client.post(path, headers=headers, json=payload)
            self.assertEqual(denied.status_code, 403, denied.text)
        forged = await self.client.post(
            path, headers=allowed_headers,
            json={**payload, "initData": "forged"},
        )
        self.assertEqual(forged.status_code, 400, forged.text)
        self.assertEqual((await self.client.post(
            path, headers={**allowed_headers, "X-Telegram-Init-Data": "forged"},
            json=payload,
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            path, headers=allowed_headers,
            json={**payload, "user_id": 2002},
        )).status_code, 400)
        with patch(
            "app.api.miniapp_entitlements.CourseAccessPolicyService.get_policy",
            new_callable=AsyncMock,
        ) as policy, patch(
            "app.api.miniapp_entitlements.CourseMiniAppAccessService.consume_daily_use",
            new_callable=AsyncMock,
        ) as consume, patch(
            "app.api.miniapp_entitlements.shadow_compare_gate",
            new_callable=AsyncMock,
        ):
            policy.return_value = SimpleNamespace(free_active=False)
            consume.return_value = {
                "allowed": True, "is_paid": False, "remaining": 0,
            }
            ok = await self.client.post(path, headers=allowed_headers, json=payload)
            self.assertEqual(ok.status_code, 200, ok.text)
            self.assertTrue(ok.json()["allowed"])
            self.assertEqual(ok.headers["cache-control"], "no-store")
            self.assertEqual(consume.await_args.args[0].id, 1)
            self.assertEqual(consume.await_args.kwargs["feature_key"], "recognition")
            self.assertEqual(consume.await_args.kwargs["ref"], "browser-attempt-1")
            self.assertIs(consume.await_args.kwargs["lifetime"], True)
            consume.return_value = {
                "allowed": False, "is_paid": False,
                "error": "free_feature_limit_reached",
            }
            denied = await self.client.post(
                path, headers=allowed_headers,
                json={"feature": "recognition", "ref": "new-attempt-2"},
            )
            self.assertEqual(denied.status_code, 403, denied.text)
            self.assertEqual(denied.json()["ad"]["available"], False)
            self.assertEqual(consume.await_count, 2)
        # Legacy Telegram endpoint keeps signed initData as its only authority.
        legacy = await self.client.post(
            "/api/v3/practice/daily-gate", json=payload,
        )
        self.assertEqual(legacy.status_code, 401, legacy.text)

    async def test_pwa_drill_words_and_report_reuse_canonical_owner_and_guards(self):
        words_path = "/api/v3/pwa/practice/words"
        report_path = "/api/v3/pwa/practice/report"
        self.assertEqual((await self.client.post(
            words_path, headers={"Origin": ORIGIN},
            json={"feature": "recognition", "limit": 3},
        )).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        for forbidden in [
            {"feature": "recognition", "limit": 3, "initData": "pretend-telegram"},
            {"feature": "recognition", "limit": 3, "user_id": 999},
        ]:
            response = await self.client.post(words_path, headers=headers, json=forbidden)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.client.post(
            words_path, headers={"Origin": "https://evil.test", "X-HSK-PWA-CSRF": csrf},
            json={"feature": "recognition", "limit": 3},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            words_path, headers={"Origin": ORIGIN},
            json={"feature": "recognition", "limit": 3},
        )).status_code, 403)
        with patch(
            "app.api.miniapp_practice.CourseWordMasteryService.drill_words",
            new_callable=AsyncMock,
        ) as words:
            words.return_value = {"words": [{"hanzi": "你", "kind": "review"}]}
            response = await self.client.post(
                words_path, headers=headers,
                json={"feature": "recognition", "limit": 3},
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["words"][0]["hanzi"], "你")
            self.assertEqual(response.headers.get("cache-control"), "no-store")
            self.assertEqual(words.await_args.args[0].id, 1)
            self.assertEqual(words.await_args.kwargs["limit"], 3)
        self.assertEqual((await self.client.post(
            "/api/v3/practice/words",
            json={"feature": "recognition", "limit": 3},
        )).status_code, 401)
        report = {
            "feature": "recognition", "level": "hsk1", "language": "uz",
            "mistakes": [{"hanzi": "好", "selected": "坏"}],
            "results": [{"hanzi": "好", "correct": False}],
        }
        self.assertEqual((await self.client.post(
            report_path, headers={"Origin": ORIGIN}, json=report,
        )).status_code, 403)
        with patch(
            "app.api.miniapp_practice.CourseDrillSignalService.record",
            new_callable=AsyncMock,
        ) as mistakes, patch(
            "app.api.miniapp_practice.CourseWordMasteryService.record_drill",
            new_callable=AsyncMock,
        ) as mastery:
            mistakes.return_value = 1
            mastery.return_value = 1
            result = await self.client.post(report_path, headers=headers, json=report)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["recorded"], 1)
            self.assertEqual(result.json()["scheduled"], 1)
            self.assertEqual(mistakes.await_args.args[0].id, 1)
            self.assertEqual(mastery.await_args.args[0].id, 1)
        self.assertEqual((await self.client.post(
            "/api/v3/practice/report", json=report,
        )).status_code, 401)

    async def test_pwa_map_requires_browser_cookie_origin_csrf_and_locked_owner(self):
        # Real map service is shared with Telegram; isolate just the transport
        # to verify the correct canonical actor reaches the single map engine.
        # app.main initializes aiogram at import time. The test needs only a
        # syntactically valid fake token; do not change production validation.
        from app.config import settings as main_settings
        with patch.object(main_settings, "BOT_TOKEN", self.settings.BOT_TOKEN):
            import app.main as main
        from fastapi.responses import JSONResponse

        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        cookie = self.client.cookies.get(PWA_SESSION_COOKIE)
        app = FastAPI()
        app.add_api_route("/api/v3/pwa/map", main.pwa_course_map, methods=["POST"])
        with patch.object(main, "async_session_maker", self.sessions), patch.object(
            main, "settings", self.settings,
        ), patch.object(
            main, "_course_v3_map_for_user", new_callable=AsyncMock,
        ) as shared:
            shared.return_value = JSONResponse({"ok": True, "level": "hsk1"})
            client = AsyncClient(
                transport=ASGITransport(app=app), base_url=ORIGIN,
                cookies={PWA_SESSION_COOKIE: cookie},
            )
            try:
                url = "/api/v3/pwa/map"
                self.assertEqual((await client.get(url)).status_code, 405)
                missing_csrf = await client.post(url, headers={"Origin": ORIGIN})
                self.assertEqual(missing_csrf.status_code, 403, missing_csrf.text)
                wrong_origin = await client.post(
                    url, headers={
                        "Origin": "https://attacker.test",
                        "X-HSK-PWA-CSRF": csrf,
                    },
                )
                self.assertEqual(wrong_origin.status_code, 403, wrong_origin.text)
                forged_tg = await client.post(
                    url, headers={
                        "Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf,
                        "X-Telegram-Init-Data": "fake",
                    },
                )
                self.assertEqual(forged_tg.status_code, 422, forged_tg.text)
                shared.assert_not_awaited()
                good = await client.post(
                    url + "?tz=480&source=pwa_course_v3",
                    headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                )
                self.assertEqual(good.status_code, 200, good.text)
                self.assertEqual(good.headers["cache-control"], "no-store")
                self.assertEqual(good.headers["x-hsk-pwa-user-id"], "1")
                shared.assert_awaited_once()
                args, kwargs = shared.await_args
                self.assertEqual(args[2].id, 1)
                self.assertEqual(kwargs["telegram_id"], 1001)
                self.assertEqual(kwargs["default_source"], "pwa_course_v3")
                self.assertEqual(args[0].query_params["tz"], "480")
                # A fake owner in a JSON request body is never treated as actor.
                shared.reset_mock()
                again = await client.post(
                    url, headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                    json={"user_id": 999},
                )
                self.assertEqual(again.status_code, 200, again.text)
                self.assertEqual(shared.await_args.args[2].id, 1)
            finally:
                await client.aclose()
            anonymous = AsyncClient(
                transport=ASGITransport(app=app), base_url=ORIGIN,
            )
            try:
                denied = await anonymous.post(
                    "/api/v3/pwa/map",
                    headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                )
                self.assertEqual(denied.status_code, 401, denied.text)
            finally:
                await anonymous.aclose()

    async def test_pwa_map_accepts_verified_google_only_actor_without_telegram(self):
        from app.config import settings as main_settings
        with patch.object(main_settings, "BOT_TOKEN", self.settings.BOT_TOKEN):
            import app.main as main
        from fastapi.responses import JSONResponse
        from app.services import google_auth

        state = await self.begin()
        new_identity = VerifiedIdentity(
            provider="google", subject="map-browser-only-subject",
            email="map-browser@example.test", email_verified=True,
            display_name="Browser learner",
            audience="222-desktop.apps.googleusercontent.com",
        )
        with patch.object(google_auth, "exchange_code", return_value="browser-only-token"), patch.object(
            google_auth, "verify_desktop_id_token", return_value=new_identity,
        ):
            callback = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "browser-only-code"},
            )
        self.assertEqual(callback.status_code, 303, callback.text)
        me = (await self.client.get("/api/v3/pwa-auth/session")).json()
        self.assertFalse(me["telegram_linked"])
        app = FastAPI()
        app.add_api_route("/api/v3/pwa/map", main.pwa_course_map, methods=["POST"])
        with patch.object(main, "async_session_maker", self.sessions), patch.object(
            main, "settings", self.settings,
        ), patch.object(
            main, "_course_v3_map_for_user", new_callable=AsyncMock,
        ) as shared:
            shared.return_value = JSONResponse({"ok": True, "level": "hsk1"})
            client = AsyncClient(
                transport=ASGITransport(app=app), base_url=ORIGIN,
                cookies={PWA_SESSION_COOKIE: self.client.cookies.get(PWA_SESSION_COOKIE)},
            )
            try:
                result = await client.post(
                    "/api/v3/pwa/map", headers={
                        "Origin": ORIGIN, "X-HSK-PWA-CSRF": me["csrf"],
                    },
                )
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.headers["x-hsk-pwa-user-id"], str(me["user_id"]))
                shared.assert_awaited_once()
                self.assertEqual(shared.await_args.args[2].id, me["user_id"])
                self.assertIsNone(shared.await_args.kwargs["telegram_id"])
            finally:
                await client.aclose()

    def test_pwa_map_and_legacy_map_share_single_full_policy_engine(self):
        source = Path("app/main.py").read_text(encoding="utf-8")
        start = source.index("async def _course_v3_map_for_user(")
        stop = source.index('@app.get("/api/v3/invite")', start)
        block = source[start:stop]
        service = block[:block.index('@app.get("/api/v3/map")')]
        self.assertIn("LessonAccessService(session).apply_map(", service)
        self.assertIn("CourseTodayService(session).payload(", service)
        self.assertIn("CourseSalesExperimentService(session).resolve_offer(", service)
        self.assertIn("CourseTrackService(session).hsk30_access(user)", service)
        self.assertIn("progress_repo.get_by_user_id(user.id, for_update=True)", service)
        self.assertIn('data["progress"]', service)
        self.assertIn('data["notifications"]', service)
        self.assertIn("await session.commit()", service)
        self.assertIn('default_source: str = "course_v3"', block)
        self.assertEqual(block.count("await _course_v3_map_for_user("), 2)
        self.assertIn("get_by_telegram_id_for_update(telegram_id)", block)
        self.assertIn("get_by_user_id(actor.id, lock=True)", block)
        self.assertIn('raise PwaAuthError("pwa_session_required")', block)
        self.assertIn("require_same_origin(request, settings)", block)
        self.assertIn('request.headers.get("X-HSK-PWA-CSRF")', block)
        self.assertIn('default_source="pwa_course_v3"', block)
        self.assertIn(
            'request.query_params.get("source") if default_source == "course_v3" else None',
            service,
        )
        self.assertIn('dedupe_prefix = "course-v3" if default_source == "course_v3"', service)
        self.assertNotIn("PWA_SESSION_COOKIE", service)

    async def test_pwa_course_track_routes_require_pwa_session_and_no_native_bypass(self):
        # Legacy Telegram route rejects a PWA cookie even after browser login.
        unauthed = await self.client.get("/api/v3/pwa/course-tracks")
        self.assertEqual(unauthed.status_code, 401)
        unauthed_switch = await self.client.post(
            "/api/v3/pwa/course-tracks/switch",
            headers={"Origin": ORIGIN},
            json={"target_track": "hsk20", "level": "hsk1"},
        )
        self.assertEqual(unauthed_switch.status_code, 401)
        state = await self.begin()
        await self.callback(state)
        legacy = await self.client.get("/api/v3/course-tracks")
        self.assertEqual(legacy.status_code, 401)
        with patch("app.api.course_tracks._status_payload", new_callable=AsyncMock) as shared:
            shared.return_value = {"ok": True, "active_track": "hsk20"}
            response = await self.client.get("/api/v3/pwa/course-tracks")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["active_track"], "hsk20")
            self.assertEqual(shared.await_args.args[1].id, 1)
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    async def test_pwa_course_track_mutations_require_origin_csrf_and_canonical_actor(self):
        state = await self.begin()
        await self.callback(state)
        owner = (await self.client.get("/api/v3/pwa-auth/session")).json()
        csrf = owner["csrf"]
        path = "/api/v3/pwa/course-tracks/switch"
        body = {"target_track": "hsk20", "level": "hsk1"}
        self.assertEqual(
            (await self.client.post(path, headers={"Origin": "https://evil.test",
                                                   "X-HSK-PWA-CSRF": csrf}, json=body)).status_code,
            403,
        )
        self.assertEqual(
            (await self.client.post(path, headers={"Origin": ORIGIN}, json=body)).status_code,
            403,
        )
        self.assertEqual(
            (await self.client.post(path, headers={"Origin": ORIGIN,
                                                  "X-HSK-PWA-CSRF": "bad"}, json=body)).status_code,
            403,
        )
        self.assertEqual(
            (await self.client.post(
                path, headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                json={**body, "initData": "forged=telegram"},
            )).status_code,
            422,
        )
        with patch("app.api.course_tracks.CourseTrackService.switch", new_callable=AsyncMock) as switch, patch(
            "app.api.course_tracks.CourseTrackService.change_level", new_callable=AsyncMock,
        ) as change_level, patch(
            "app.api.course_tracks.Hsk30UnlockService.payment_eligibility", new_callable=AsyncMock,
        ) as eligibility:
            change_level.return_value = {"active_track": "hsk20", "active_level": "hsk1"}
            switch.return_value = {"active_track": "hsk20", "active_level": "hsk1"}
            eligibility.return_value = {"payment_enabled": False}
            passed = await self.client.post(
                path, headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}, json=body,
            )
            self.assertEqual(passed.status_code, 200, passed.text)
            self.assertTrue(passed.json()["ok"])
            performed = change_level if change_level.await_count else switch
            self.assertEqual(performed.await_count, 1)
            self.assertEqual(performed.await_args.args[0].id, owner["user_id"])
        self.assertEqual((await self.client.post(
            "/api/v3/pwa/course-tracks/promo-shown",
            headers={"Origin": ORIGIN}, json={},
        )).status_code, 403)

    async def test_origin_required_and_pwa_disabled_fails_closed(self):
        no_origin = await self.client.post(
            "/api/v3/pwa-auth/start", json={"provider": "google"},
        )
        self.assertEqual(no_origin.status_code, 403)
        bad_origin = await self.client.post(
            "/api/v3/pwa-auth/start",
            headers={"Origin": "https://attacker.test"},
            json={"provider": "google"},
        )
        self.assertEqual(bad_origin.status_code, 403)
        self.settings.PWA_AUTH_ENABLED = False
        disabled = await self.client.post(
            "/api/v3/pwa-auth/start",
            headers={"Origin": ORIGIN}, json={"provider": "google"},
        )
        self.assertEqual(disabled.status_code, 503)
        session = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(session.status_code, 503)
        self.assertEqual((await self.client.get("/iphone-pwa")).status_code, 503)
        self.assertEqual((await self.client.get("/iphone-pwa-login.js")).status_code, 503)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/providers")).status_code, 503)

    async def test_login_only_page_uses_source_tokens_and_existing_catalog(self):
        page = await self.client.get("/iphone-pwa")
        self.assertEqual(page.status_code, 200, page.text)
        self.assertIn("text/html", page.headers["Content-Type"])
        self.assertIn("script-src 'self'", page.headers["Content-Security-Policy"])
        self.assertIn("/course_v3_data/design-tokens.css", page.text)
        self.assertIn("/course_v3_data/hsk-common-i18n.js", page.text)
        self.assertNotIn("Telegram.WebApp", page.text)
        script = await self.client.get("/iphone-pwa-login.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("HSKAI_COMMON_I18N", script.text)
        self.assertNotIn("Telegram.WebApp.initData", script.text)
        providers = await self.client.get("/api/v3/pwa-auth/providers")
        self.assertEqual(providers.json(), {"ok": True, "providers": ["google"]})

    async def test_android_login_visual_source_and_three_locale_copy(self):
        """Login shell reuses Android entry components, not a second design."""
        response = await self.client.get("/iphone-pwa")
        self.assertEqual(response.status_code, 200)
        html = response.text
        for fragment in (
            "/assets/characters/hsk-character-pack.js",
            "/assets/characters/hsk-character-pack.css",
            'id="panda"',
            'class="hero-panda"',
            "min-height:68px",
            "border-radius:22px",
            'class="tagline"',
            "motif--left",
            "motif--right",
            "font-size:32px",
            ".subtitle{font-size:16px",
            ".provider__label{font-size:16px",
            "color-mix(in srgb,var(--hsk-card-surface) 98%",
            "overflow-y:auto",
        ):
            self.assertIn(fragment, html)
        self.assertLess(html.index('data-provider="telegram"'),
                        html.index('data-provider="google"'))
        self.assertLess(html.index('data-provider="google"'),
                        html.index('data-provider="apple"'))
        self.assertEqual(html.count("provider__chevron"), 4)  # CSS + 3 cards
        js = (Path("app/static") / "iphone-pwa-login.js").read_text(encoding="utf-8")
        self.assertIn('window.HSKCharacters.mount', js)
        self.assertIn('button.dataset.provider === "telegram"', js)
        self.assertIn('message("pwaAuth.telegramPending"', js)
        self.assertNotIn("Telegram.WebApp.initData", js)
        # All new copy lives in one local-first owner; Android's frozen
        # exact phrases are their source, not a second in-page dictionary.
        source = {
            "uz": "values",
            "ru": "values-ru",
            "tj": "values-tg",
        }
        keys = {
            "pwaAuth.welcome": "auth_welcome_greeting",
            "pwaAuth.choose": "auth_choose_method",
            "pwaAuth.tagline": "auth_tagline",
        }
        for lang, folder in source.items():
            with self.subTest(lang=lang):
                catalog = json.loads((Path("localization/ui") / lang / "common.json").read_text(encoding="utf-8"))
                native = ET.parse(Path("android/app/src/main/res") / folder / "strings.xml")
                native_map = {x.attrib["name"]: x.text or "" for x in native.getroot().findall("string")}
                for key, resource in keys.items():
                    self.assertIn(key, catalog["messages"])
                    self.assertEqual(
                        catalog["messages"][key],
                        native_map[resource].replace(r"\u2014", "—"),
                    )
                self.assertTrue(catalog["messages"]["pwaAuth.telegramPending"].strip())
        bundle = (Path("app/static/course_v3_data") / "hsk-common-i18n.js").read_text(encoding="utf-8")
        self.assertIn('"pwaAuth.welcome"', bundle)
        self.assertIn('"pwaAuth.telegramPending"', bundle)

    async def test_telegram_bot_approval_claims_only_the_originating_browser(self):
        from app.services.desktop_auth_service import DesktopAuthService
        started = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN},
            json={"language": "uz"},
        )
        self.assertEqual(started.status_code, 200, started.text)
        payload = started.json()
        self.assertNotIn("polling_secret", payload)
        self.assertNotIn("display_code", payload)
        self.assertIn("pwa_link_", payload["authorize_url"])
        link_id = payload["link_request_id"]
        body = {"link_request_id": link_id}
        before = await self.client.post(
            "/api/v3/pwa-auth/telegram/claim",
            headers={"Origin": ORIGIN}, json=body,
        )
        self.assertEqual(before.json(), {"ok": True, "status": "pending"})
        stranger = AsyncClient(transport=ASGITransport(app=self.client._transport.app), base_url=ORIGIN)
        try:
            spoof = await stranger.post(
                "/api/v3/pwa-auth/telegram/claim",
                headers={"Origin": ORIGIN}, json=body,
            )
            self.assertEqual(spoof.status_code, 401)
            bad_origin = await self.client.post(
                "/api/v3/pwa-auth/telegram/claim",
                headers={"Origin": "https://evil.example.test"}, json=body,
            )
            self.assertEqual(bad_origin.status_code, 403)
            async with self.sessions() as db:
                service = DesktopAuthService(db, self.settings)
                await service.link_request_confirmation(
                    link_request_id=link_id, telegram_id=1001, platform="pwa",
                )
                await service.approve_link_request(
                    link_request_id=link_id, telegram_id=1001, platform="pwa",
                )
            claim = await self.client.post(
                "/api/v3/pwa-auth/telegram/claim",
                headers={"Origin": ORIGIN}, json=body,
            )
            self.assertEqual(claim.status_code, 200, claim.text)
            self.assertEqual(claim.json()["status"], "complete")
            self.assertIn(PWA_SESSION_COOKIE, claim.cookies)
            self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).json()["user_id"], 1)
            replay = await self.client.post(
                "/api/v3/pwa-auth/telegram/claim",
                headers={"Origin": ORIGIN}, json=body,
            )
            self.assertEqual(replay.status_code, 401)
            self.assertNotIn(PWA_SESSION_COOKIE, replay.cookies)
        finally:
            await stranger.aclose()

    async def test_telegram_denial_reports_cancellation_without_fake_expiry(self):
        started = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN}, json={"language": "uz"},
        )
        self.assertEqual(started.status_code, 200, started.text)
        rid = started.json()["link_request_id"]
        async with self.sessions() as db:
            service = DesktopAuthService(db, self.settings)
            await service.link_request_confirmation(
                link_request_id=rid, telegram_id=1001, platform="pwa",
            )
            await service.cancel_link_request(
                link_request_id=rid, telegram_id=1001, platform="pwa",
            )
        denied = await self.client.post(
            "/api/v3/pwa-auth/telegram/claim",
            headers={"Origin": ORIGIN}, json={"link_request_id": rid},
        )
        self.assertEqual(denied.status_code, 401, denied.text)
        self.assertEqual(denied.json()["error"], "pwa_telegram_not_approved")
        script = (Path("app/static") / "iphone-pwa-login.js").read_text(encoding="utf-8")
        self.assertIn('error.message === "pwa_telegram_not_approved"', script)
        self.assertIn('"desktopAuth.cancelled"', script)

    async def test_telegram_pwa_and_android_bot_approvals_are_isolated(self):
        started = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN}, json={"language": "ru"},
        )
        rid = started.json()["link_request_id"]
        async with self.sessions() as db:
            service = DesktopAuthService(db, self.settings)
            from app.services.desktop_auth_service import DesktopAuthError
            with self.assertRaises(DesktopAuthError):
                await service.link_request_confirmation(
                    link_request_id=rid, telegram_id=1001, platform="android",
                )
            with self.assertRaises(DesktopAuthError):
                await service.approve_link_request(
                    link_request_id=rid, telegram_id=1001, platform="android",
                )
            row = await db.get(DesktopLinkRequest, rid)
            self.assertEqual(row.status, "pending")
            self.assertEqual(row.platform, "pwa")

    async def test_telegram_approval_cannot_switch_canonical_account(self):
        started = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN}, json={"language": "uz"},
        )
        rid = started.json()["link_request_id"]
        async with self.sessions() as db:
            row = await db.get(DesktopLinkRequest, rid)
            row.status = "approved"
            row.approved_user_id = 1
            row.approved_telegram_id = 2002  # Does not match canonical owner.
            await db.commit()
        attempt = await self.client.post(
            "/api/v3/pwa-auth/telegram/claim",
            headers={"Origin": ORIGIN}, json={"link_request_id": rid},
        )
        self.assertEqual(attempt.status_code, 403)
        self.assertNotIn(PWA_SESSION_COOKIE, attempt.cookies)

    async def test_pwa_callback_requires_same_browser_proof(self):
        state = await self.begin()
        other = AsyncClient(transport=self.client._transport, base_url=ORIGIN)
        try:
            missing_proof = await self.callback(state, client=other)
            self.assertNotIn(PWA_SESSION_COOKIE, missing_proof.cookies)
            self.assertIn("pwa_oauth_proof_invalid", missing_proof.text)
            denied_cancel = await other.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "error": "access_denied"},
            )
            self.assertIn("pwa_oauth_proof_invalid", denied_cancel.text)
            async with self.sessions() as db:
                still_pending = (await db.execute(
                    select(DesktopLinkRequest).where(DesktopLinkRequest.platform == "pwa")
                )).scalar_one()
                self.assertEqual(still_pending.status, "pending")
            good = await self.callback(state)
            self.assertEqual(good.status_code, 303)
            self.assertEqual(good.headers.get("location"), "/iphone-pwa")
            self.assertIn(PWA_SESSION_COOKIE, good.cookies)
            self.assertIn("HttpOnly", good.headers.get("set-cookie", ""))
            assert any("Secure" in item for item in good.headers.get_list("set-cookie"))
            assert any("SameSite=lax" in item for item in good.headers.get_list("set-cookie"))
            replay = await self.callback(state)
            self.assertNotIn(PWA_SESSION_COOKIE, replay.cookies)
            self.assertIn("pwa_oauth_proof_invalid", replay.text)
        finally:
            await other.aclose()

    async def test_google_cancel_returns_to_same_browser_without_session(self):
        state = await self.begin()
        cancelled = await self.client.get(
            "/api/v3/native-auth/oauth/callback/google",
            params={"state": state, "error": "access_denied"},
        )
        self.assertEqual(cancelled.status_code, 303, cancelled.text)
        self.assertEqual(cancelled.headers["location"], "/iphone-pwa?auth=cancelled")
        self.assertNotIn(PWA_SESSION_COOKIE, cancelled.cookies)
        # HTTPX may normalize the expired Set-Cookie away from Response.cookies;
        # the response must still instruct the browser to delete its proof.
        self.assertTrue(any(
            PWA_OAUTH_COOKIE in value and "Max-Age=0" in value
            for value in cancelled.headers.get_list("set-cookie")
        ))
        async with self.sessions() as db:
            row = (await db.execute(
                select(DesktopLinkRequest).where(DesktopLinkRequest.platform == "pwa")
            )).scalar_one()
            self.assertEqual(row.status, "failed")
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)
        script = (Path("app/static") / "iphone-pwa-login.js").read_text(encoding="utf-8")
        self.assertIn('get("auth") === "cancelled"', script)
        self.assertIn('message("desktopAuth.cancelled", true)', script)

    async def test_apple_cancel_returns_to_same_browser_without_session(self):
        self.settings.APPLE_OAUTH_ENABLED = True
        self.settings.APPLE_SERVICE_ID = "apple.service.test"
        self.settings.APPLE_TEAM_ID = "TESTTEAM"
        self.settings.APPLE_KEY_ID = "TESTKEY"
        self.settings.APPLE_PRIVATE_KEY = "unused-by-mocked-exchange"
        started = await self.client.post(
            "/api/v3/pwa-auth/start", headers={"Origin": ORIGIN},
            json={"provider": "apple", "language": "ru"},
        )
        self.assertEqual(started.status_code, 200, started.text)
        state = parse_qs(urlparse(started.json()["authorize_url"]).query)["state"][0]
        cancelled = await self.client.post(
            "/api/v3/native-auth/oauth/callback/apple",
            data={"state": state, "error": "access_denied"},
        )
        self.assertEqual(cancelled.status_code, 303, cancelled.text)
        self.assertEqual(cancelled.headers["location"], "/iphone-pwa?auth=cancelled")
        self.assertNotIn(PWA_SESSION_COOKIE, cancelled.cookies)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

    def test_telegram_poll_recovers_after_transient_error_and_is_single_flight(self):
        script = (Path("app/static") / "iphone-pwa-login.js").read_text(encoding="utf-8")
        self.assertIn("telegramClaimInFlight", script)
        self.assertIn("if (!terminal)", script)
        self.assertIn("the next poll can still claim it.", script)
        self.assertIn("telegramClaimInFlight = false", script)
        self.assertIn("function pendingTelegramId()", script)
        self.assertIn("catch (_) { return null; }", script)
        self.assertNotIn("const linkId = sessionStorage.getItem(", script)

    async def test_existing_telegram_owner_retained_and_logout_is_csrf_protected(self):
        state = await self.begin()
        response = await self.callback(state)
        self.assertIn(PWA_SESSION_COOKIE, response.cookies)
        status = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(status.status_code, 200, status.text)
        self.assertEqual(status.json()["user_id"], 1)
        self.assertTrue(status.json()["telegram_linked"])
        csrf = status.json()["csrf"]
        self.assertEqual(
            (await self.client.post("/api/v3/pwa-auth/logout",
                                    headers={"Origin": ORIGIN})).status_code, 403
        )
        self.assertEqual(
            (await self.client.post("/api/v3/pwa-auth/logout",
                                    headers={"Origin": "https://evil.test",
                                             "X-HSK-PWA-CSRF": csrf})).status_code, 403
        )
        self.assertEqual(
            (await self.client.post("/api/v3/pwa-auth/logout",
                                    headers={"Origin": ORIGIN,
                                             "X-HSK-PWA-CSRF": "wrong"})).status_code, 403
        )
        ok = await self.client.post(
            "/api/v3/pwa-auth/logout",
            headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

    async def test_provider_login_clears_unfinished_telegram_browser_proof(self):
        telegram_start = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN}, json={"language": "uz"},
        )
        self.assertEqual(telegram_start.status_code, 200, telegram_start.text)
        request_id = telegram_start.json()["link_request_id"]
        state = await self.begin()
        signed_in = await self.callback(state)
        self.assertEqual(signed_in.status_code, 303, signed_in.text)
        self.assertTrue(any(
            "hskai-pwa-telegram" in value and "Max-Age=0" in value
            for value in signed_in.headers.get_list("set-cookie")
        ))
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)
        stale = await self.client.post(
            "/api/v3/pwa-auth/telegram/claim", headers={"Origin": ORIGIN},
            json={"link_request_id": request_id},
        )
        self.assertEqual(stale.status_code, 401)
        self.assertEqual(stale.json()["error"], "pwa_telegram_proof_invalid")
        script = (Path("app/static") / "iphone-pwa-login.js").read_text(encoding="utf-8")
        self.assertIn("sessionStorage.removeItem(telegramStorageKey)", script)
        self.assertIn("stopTelegramPolling()", script)

    async def test_telegram_login_clears_unfinished_provider_browser_proof(self):
        state = await self.begin()
        started = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN}, json={"language": "ru"},
        )
        self.assertEqual(started.status_code, 200, started.text)
        request_id = started.json()["link_request_id"]
        async with self.sessions() as db:
            service = DesktopAuthService(db, self.settings)
            await service.link_request_confirmation(
                link_request_id=request_id, telegram_id=1001, platform="pwa",
            )
            await service.approve_link_request(
                link_request_id=request_id, telegram_id=1001, platform="pwa",
            )
        claim = await self.client.post(
            "/api/v3/pwa-auth/telegram/claim",
            headers={"Origin": ORIGIN}, json={"link_request_id": request_id},
        )
        self.assertEqual(claim.status_code, 200, claim.text)
        self.assertEqual(claim.json()["status"], "complete")
        self.assertTrue(any(
            PWA_OAUTH_COOKIE in value and "Max-Age=0" in value
            for value in claim.headers.get_list("set-cookie")
        ))
        stale = await self.callback(state)
        self.assertNotIn(PWA_SESSION_COOKIE, stale.cookies)
        self.assertIn("pwa_oauth_proof_invalid", stale.text)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)

    async def test_reauthentication_revokes_only_previous_browser_session(self):
        first_state = await self.begin()
        first_login = await self.callback(first_state)
        old_cookie = first_login.cookies[PWA_SESSION_COOKIE]

        # A separate Safari/Home Screen container has an independently valid
        # PWA session even when it belongs to the same canonical account.
        other = AsyncClient(transport=self.client._transport, base_url=ORIGIN)
        old = AsyncClient(
            transport=self.client._transport, base_url=ORIGIN,
            cookies={PWA_SESSION_COOKIE: old_cookie},
        )
        try:
            independent_start = await other.post(
                "/api/v3/pwa-auth/start", headers={"Origin": ORIGIN},
                json={"provider": "google", "language": "ru"},
            )
            self.assertEqual(independent_start.status_code, 200, independent_start.text)
            other_state = parse_qs(urlparse(
                independent_start.json()["authorize_url"]
            ).query)["state"][0]
            other_login = await self.callback(other_state, client=other)
            self.assertEqual(other_login.status_code, 303, other_login.text)
            self.assertEqual((await other.get("/api/v3/pwa-auth/session")).status_code, 200)
            self.assertEqual((await old.get("/api/v3/pwa-auth/session")).status_code, 200)

            next_state = await self.begin()
            replaced = await self.callback(next_state)
            self.assertEqual(replaced.status_code, 303, replaced.text)
            self.assertNotEqual(replaced.cookies[PWA_SESSION_COOKIE], old_cookie)
            self.assertEqual((await old.get("/api/v3/pwa-auth/session")).status_code, 401)
            self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)
            self.assertEqual((await other.get("/api/v3/pwa-auth/session")).status_code, 200)
            async with self.sessions() as db:
                rows = (await db.execute(
                    select(DesktopSession, DesktopDevice)
                    .join(DesktopDevice, DesktopSession.device_id == DesktopDevice.id)
                    .where(DesktopDevice.platform == "pwa")
                )).all()
                self.assertEqual(len(rows), 3)
                self.assertEqual(sum(s.revoked_at is not None for s, _ in rows), 1)
        finally:
            await old.aclose()
            await other.aclose()

    async def test_telegram_approval_replaces_current_browser_session(self):
        first_state = await self.begin()
        first_login = await self.callback(first_state)
        old_cookie = first_login.cookies[PWA_SESSION_COOKIE]
        start = await self.client.post(
            "/api/v3/pwa-auth/telegram/start",
            headers={"Origin": ORIGIN}, json={"language": "uz"},
        )
        self.assertEqual(start.status_code, 200, start.text)
        request_id = start.json()["link_request_id"]
        async with self.sessions() as db:
            service = DesktopAuthService(db, self.settings)
            await service.link_request_confirmation(
                link_request_id=request_id, telegram_id=1001, platform="pwa",
            )
            await service.approve_link_request(
                link_request_id=request_id, telegram_id=1001, platform="pwa",
            )
        claim = await self.client.post(
            "/api/v3/pwa-auth/telegram/claim",
            headers={"Origin": ORIGIN}, json={"link_request_id": request_id},
        )
        self.assertEqual(claim.status_code, 200, claim.text)
        self.assertEqual(claim.json()["status"], "complete")
        self.assertNotEqual(claim.cookies[PWA_SESSION_COOKIE], old_cookie)
        old = AsyncClient(
            transport=self.client._transport, base_url=ORIGIN,
            cookies={PWA_SESSION_COOKIE: old_cookie},
        )
        try:
            self.assertEqual((await old.get("/api/v3/pwa-auth/session")).status_code, 401)
            self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)
        finally:
            await old.aclose()

    async def test_browser_cannot_exchange_pwa_oauth_for_native_bearer(self):
        async with self.sessions() as session:
            service = DesktopAuthService(session, self.settings)
            started = await service.start_link(
                platform="pwa", app_version="1.0.0",
                installation_key="p" * 48, flow="google", intent="signin",
            )
            row = await session.get(DesktopLinkRequest, started["link_request_id"])
            row.status = "approved"
            row.approved_user_id = 1
            await session.commit()
            # Even a valid leaked polling secret MUST NOT mint native tokens.
            with self.assertRaises(DesktopAuthError) as exc:
                await service.poll_link(
                    link_request_id=row.id, polling_secret=started["polling_secret"],
                )
            self.assertEqual(exc.exception.code, "desktop_link_invalid")
            rows = (await session.execute(select(DesktopSession))).scalars().all()
            self.assertEqual(rows, [])

    async def test_expiry_and_blocked_account_cannot_restore_session(self):
        state = await self.begin()
        await self.callback(state)
        async with self.sessions() as session:
            device = (await session.execute(
                select(DesktopDevice).where(DesktopDevice.platform == "pwa")
            )).scalar_one()
            login = (await session.execute(
                select(DesktopSession).where(DesktopSession.device_id == device.id)
            )).scalar_one()
            login.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

        new_state = await self.begin()
        await self.callback(new_state)
        async with self.sessions() as session:
            owner = await session.get(User, 1)
            owner.status = "blocked"
            await session.commit()
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

    async def test_identity_unlink_revokes_existing_pwa_sessions(self):
        state = await self.begin()
        await self.callback(state)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)
        async with self.sessions() as db:
            identity_ids = (await db.execute(
                select(UserIdentity.id)
            )).scalars().all()
            self.assertEqual(len(identity_ids), 1)
            await IdentityLinkService(db, self.settings).unlink(identity_ids[0], user_id=1)
            await db.commit()
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)

    async def test_new_provider_identity_stays_browser_only_and_has_canonical_user(self):
        original_state = await self.begin()
        original_login = await self.callback(original_state)
        self.assertEqual(original_login.status_code, 303, original_login.text)
        original_cookie = original_login.cookies[PWA_SESSION_COOKIE]
        state = await self.begin()
        new_identity = VerifiedIdentity(
            provider="google", subject="brand-new-provider-subject",
            email="new@example.test", email_verified=True,
            display_name="New student", audience="222-desktop.apps.googleusercontent.com",
        )
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="fresh-token"), patch.object(
            google_auth, "verify_desktop_id_token", return_value=new_identity,
        ):
            done = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "new-provider-code"},
            )
        self.assertIn(PWA_SESSION_COOKIE, done.cookies)
        me = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(me.status_code, 200)
        self.assertNotEqual(me.json()["user_id"], 1)
        self.assertFalse(me.json()["telegram_linked"])
        async with self.sessions() as db:
            created = await db.get(User, me.json()["user_id"])
            self.assertIsNone(created.telegram_id)
        prior = AsyncClient(
            transport=self.client._transport, base_url=ORIGIN,
            cookies={PWA_SESSION_COOKIE: original_cookie},
        )
        try:
            # A different Google subject must not leave the old learner's
            # browser cookie usable or attribute their data to the new user.
            self.assertEqual((await prior.get("/api/v3/pwa-auth/session")).status_code, 401)
            self.assertNotEqual(me.json()["user_id"], 1)
        finally:
            await prior.aclose()

    async def test_apple_cross_site_post_rotates_session_without_lax_cookie(self):
        from app.services import apple_auth
        state = await self.begin()
        first_login = await self.callback(state)
        original_cookie = first_login.cookies[PWA_SESSION_COOKIE]
        async with self.sessions() as db:
            old_session = (await db.execute(
                select(DesktopSession).where(
                    DesktopSession.refresh_token_hash
                    == DesktopAuthService(db, self.settings)._hash(
                        "pwa-cookie", original_cookie
                    )
                )
            )).scalar_one()
            prior_session_id = old_session.id

        self.settings.APPLE_OAUTH_ENABLED = True
        self.settings.APPLE_SERVICE_ID = "apple.service.test"
        self.settings.APPLE_TEAM_ID = "TESTTEAM"
        self.settings.APPLE_KEY_ID = "TESTKEY"
        self.settings.APPLE_PRIVATE_KEY = "unused-by-mocked-exchange"
        started = await self.client.post(
            "/api/v3/pwa-auth/start", headers={"Origin": ORIGIN},
            json={"provider": "apple", "language": "ru"},
        )
        self.assertEqual(started.status_code, 200, started.text)
        apple_state = parse_qs(urlparse(started.json()["authorize_url"]).query)["state"][0]
        async with self.sessions() as db:
            pending = (await db.execute(
                select(DesktopLinkRequest).where(
                    DesktopLinkRequest.platform == "pwa",
                    DesktopLinkRequest.flow == "apple",
                )
            )).scalar_one()
            self.assertEqual(pending.bind_session_id, prior_session_id)

        # A cross-site Apple form POST sends the OAuth SameSite=None cookie,
        # but not the previous SameSite=Lax browser session cookie.
        callback_browser = AsyncClient(
            transport=ASGITransport(app=self.client._transport.app), base_url=ORIGIN,
            cookies={PWA_OAUTH_COOKIE: started.cookies[PWA_OAUTH_COOKIE]},
        )
        try:
            verified = VerifiedIdentity(
                provider="apple", subject="apple-switch-sub", email=None,
                email_verified=False, display_name=None, audience="apple.service.test",
            )
            with patch.object(apple_auth, "exchange_code", return_value="apple-id-token"), patch.object(
                apple_auth, "verify_id_token_for_service", return_value=verified,
            ), patch.object(apple_auth, "merge_first_authorization_name", return_value=verified):
                done = await callback_browser.post(
                    "/api/v3/native-auth/oauth/callback/apple",
                    data={"state": apple_state, "code": "apple-code"},
                )
            self.assertEqual(done.status_code, 303, done.text)
            self.assertIn(PWA_SESSION_COOKIE, done.cookies)
            new_actor = await callback_browser.get("/api/v3/pwa-auth/session")
            self.assertEqual(new_actor.status_code, 200, new_actor.text)
            self.assertNotEqual(new_actor.json()["user_id"], 1)
            self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 401)
            async with self.sessions() as db:
                old = await db.get(DesktopSession, prior_session_id)
                self.assertIsNotNone(old.revoked_at)
        finally:
            await callback_browser.aclose()

    async def test_apple_form_post_requires_browser_proof_and_separate_cookie(self):
        from app.services import apple_auth
        self.settings.APPLE_OAUTH_ENABLED = True
        self.settings.APPLE_SERVICE_ID = "apple.service.test"
        self.settings.APPLE_TEAM_ID = "TESTTEAM"
        self.settings.APPLE_KEY_ID = "TESTKEY"
        self.settings.APPLE_PRIVATE_KEY = "unused-by-mocked-exchange"

        response = await self.client.post(
            "/api/v3/pwa-auth/start", headers={"Origin": ORIGIN},
            json={"provider": "apple", "language": "uz"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(any("SameSite=none" in v for v in response.headers.get_list("set-cookie")))
        state = parse_qs(urlparse(response.json()["authorize_url"]).query)["state"][0]
        other = AsyncClient(transport=ASGITransport(app=self.client._transport.app), base_url=ORIGIN)
        try:
            denied = await other.post(
                "/api/v3/native-auth/oauth/callback/apple",
                data={"state": state, "code": "apple-code"},
            )
            self.assertIn("pwa_oauth_proof_invalid", denied.text)
            self.assertNotIn(PWA_SESSION_COOKIE, denied.cookies)

            verified = VerifiedIdentity(
                provider="apple", subject="apple-linked-sub", email=None,
                email_verified=False, display_name=None, audience="apple.service.test",
            )
            with patch.object(apple_auth, "exchange_code", return_value="apple-id-token"), patch.object(
                apple_auth, "verify_id_token_for_service", return_value=verified,
            ), patch.object(apple_auth, "merge_first_authorization_name", return_value=verified):
                done = await self.client.post(
                    "/api/v3/native-auth/oauth/callback/apple",
                    data={"state": state, "code": "apple-code"},
                )
            self.assertEqual(done.status_code, 303)
            self.assertEqual(done.headers.get("location"), "/iphone-pwa")
            self.assertIn(PWA_SESSION_COOKIE, done.cookies)
            status = await self.client.get("/api/v3/pwa-auth/session")
            self.assertEqual(status.status_code, 200)
        finally:
            await other.aclose()

    async def test_oversized_login_rejected_without_reserving_oauth(self):
        resp = await self.client.post(
            "/api/v3/pwa-auth/start",
            headers={"Origin": ORIGIN, "Content-Type": "application/json"},
            content=b"x" * 2048,
        )
        self.assertEqual(resp.status_code, 413)
        async with self.sessions() as db:
            self.assertEqual((await db.execute(
                select(DesktopLinkRequest).where(DesktopLinkRequest.platform == "pwa")
            )).scalars().all(), [])

    async def test_native_and_telegram_routes_never_accept_pwa_cookie_as_auth(self):
        state = await self.begin()
        await self.callback(state)
        # Legacy native identity listing is bearer/verified initData only.
        response = await self.client.get("/api/v3/native-auth/identities")
        self.assertEqual(response.status_code, 401)
        self.assertEqual((await self.client.get("/api/v3/pwa-auth/session")).status_code, 200)


if __name__ == "__main__":
    unittest.main()
