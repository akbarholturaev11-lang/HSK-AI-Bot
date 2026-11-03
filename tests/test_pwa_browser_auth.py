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
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.payment import Payment
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
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
        self.receipt_bot = SimpleNamespace()
        app.include_router(create_pwa_auth_router(
            session_factory=self.sessions, settings_obj=self.settings,
            bot=self.receipt_bot,
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

    async def test_pwa_payment_action_ignores_stale_rejection_after_retry_or_approval(self):
        """Modal eligibility reflects only the owner's latest submitted receipt.

        Review history stays available, but a pending retry or approval must
        not resurrect an old rejection as a mandatory centered warning.
        """
        url = "/api/v3/pwa/account-notices"
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(user(2, None))
            db.add(Payment(
                id=901, user_id=1, user_telegram_id=1001,
                plan_type="1_month", amount=89, currency="somoni",
                payment_status="rejected",
                submitted_at=now - timedelta(days=4),
                reviewed_at=now - timedelta(days=3),
                admin_comment="Internal-only reviewer note",
            ))
            db.add(Payment(
                id=902, user_id=1, user_telegram_id=1001,
                plan_type="1_month", amount=89, currency="somoni",
                payment_status="pending",
                submitted_at=now - timedelta(days=2),
            ))
            db.add(Payment(
                id=909, user_id=2, user_telegram_id=None,
                plan_type="1_month", amount=89, currency="somoni",
                payment_status="rejected",
                submitted_at=now + timedelta(days=1),
                reviewed_at=now,
                admin_comment="Other user's private data",
            ))
            await db.commit()

        state = await self.begin()
        await self.callback(state)
        pending = await self.client.get(url)
        self.assertEqual(pending.status_code, 200, pending.text)
        self.assertIsNone(pending.json()["payment_action"])
        self.assertEqual(
            [(x["payment_id"], x["status"]) for x in pending.json()["payment_reviews"]],
            [(901, "rejected")],
        )
        self.assertNotIn("Internal-only reviewer note", pending.text)
        self.assertNotIn("Other user's private data", pending.text)
        self.assertNotIn('"payment_id":909', pending.text)

        async with self.sessions() as db:
            retry = await db.get(Payment, 902)
            retry.payment_status = "approved"
            retry.reviewed_at = now - timedelta(days=1)
            await db.commit()
        approved = await self.client.get(url)
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertIsNone(approved.json()["payment_action"])
        self.assertEqual(
            [(x["payment_id"], x["status"]) for x in approved.json()["payment_reviews"]],
            [(902, "approved"), (901, "rejected")],
        )

        async with self.sessions() as db:
            db.add(Payment(
                id=903, user_id=1, user_telegram_id=1001,
                plan_type="10_days", amount=29, currency="somoni",
                payment_status="rejected",
                submitted_at=now,
                reviewed_at=now + timedelta(minutes=1),
                admin_comment="Do not expose rejection details",
            ))
            await db.commit()
        rejected = await self.client.get(url)
        self.assertEqual(rejected.status_code, 200, rejected.text)
        focus = rejected.json()["payment_action"]
        self.assertEqual(
            {k: v for k, v in focus.items() if k != "reviewed_at"},
            {"payment_id": 903, "status": "rejected", "plan_type": "10_days"},
        )
        restored_date = datetime.fromisoformat(focus["reviewed_at"])
        if restored_date.tzinfo is None:
            # SQLite persists UTC timestamps without timezone information.
            restored_date = restored_date.replace(tzinfo=timezone.utc)
        self.assertEqual(
            restored_date.astimezone(timezone.utc),
            now + timedelta(minutes=1),
        )
        self.assertNotIn("Do not expose rejection details", rejected.text)

        # New pending receipt takes precedence; older rejection remains in
        # historical payment_reviews but cannot trigger an active modal.
        async with self.sessions() as db:
            db.add(Payment(
                id=904, user_id=1, user_telegram_id=1001,
                plan_type="10_days", amount=29, currency="somoni",
                payment_status="pending", submitted_at=now + timedelta(days=1),
            ))
            await db.commit()
        latest = await self.client.get(url)
        self.assertEqual(latest.status_code, 200, latest.text)
        self.assertIsNone(latest.json()["payment_action"])

    async def test_account_switch_keeps_dual_inbox_and_receipt_owner_isolated(self):
        """Verified Google account switching must not leak either notification
        feed or a rejected receipt to a browser-only learner with no TG ID.
        """
        notices_url = "/api/v3/pwa/account-notices"
        course_url = "/api/v3/pwa/notifications"
        payment_url = "/api/v3/pwa/subscription/payment-status"
        async with self.sessions() as db:
            db.add(AccountNoticeDelivery(
                user_id=1, telegram_id=1001,
                key="subscription_update", language="uz",
                title="First owner service notice", body="Private receipt message",
                action="subscription", status="android_pending",
                android_targets=1, reason="account_notice",
            ))
            db.add(CourseUserNotification(
                user_id=1, telegram_id=1001, key="lesson_time",
                source="telegram_reminder", language="uz",
                title="First owner course notice", body="Private lesson",
                action="course",
            ))
            db.add(Payment(
                id=801, user_id=1, user_telegram_id=1001,
                plan_type="1_month", amount=89, currency="somoni",
                payment_status="rejected",
                admin_comment="Private admin-only rejection note",
                reviewed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

        state = await self.begin()
        first = await self.callback(state)
        self.assertEqual(first.status_code, 303, first.text)
        old_cookie = first.cookies[PWA_SESSION_COOKIE]
        first_notices = (await self.client.get(notices_url)).json()
        self.assertEqual(
            [row["title"] for row in first_notices["notices"]],
            ["First owner service notice"],
        )
        self.assertEqual(
            [(row["payment_id"], row["status"]) for row in first_notices["payment_reviews"]],
            [(801, "rejected")],
        )
        self.assertNotIn("admin_comment", first_notices["payment_reviews"][0])
        self.assertEqual(
            [row["title"] for row in (await self.client.get(course_url)).json()["notifications"]],
            ["First owner course notice"],
        )
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        self.assertEqual((await self.client.post(
            payment_url,
            headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
            json={"payment_id": 801},
        )).json()["status"], "rejected")

        # A new verified provider subject creates a separate canonical user.
        # It must not inherit the Telegram owner or read old receipts.
        state = await self.begin()
        second_identity = VerifiedIdentity(
            provider="google", subject="independent-pwa-learner",
            email="second-pwa@example.test", email_verified=True,
            display_name="Independent learner",
            audience="222-desktop.apps.googleusercontent.com",
        )
        from app.services import google_auth
        with patch.object(google_auth, "exchange_code", return_value="second-id-token"), patch.object(
            google_auth, "verify_desktop_id_token", return_value=second_identity,
        ):
            second = await self.client.get(
                "/api/v3/native-auth/oauth/callback/google",
                params={"state": state, "code": "second-provider-code"},
            )
        self.assertEqual(second.status_code, 303, second.text)
        own_session = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(own_session.status_code, 200, own_session.text)
        second_user_id = own_session.json()["user_id"]
        self.assertNotEqual(second_user_id, 1)
        self.assertFalse(own_session.json()["telegram_linked"])
        async with self.sessions() as db:
            second_user = await db.get(User, second_user_id)
            self.assertIsNone(second_user.telegram_id)
            db.add(AccountNoticeDelivery(
                user_id=second_user_id, telegram_id=None,
                key="subscription_update", language="uz",
                title="Native-only service notice", body="Private native-only",
                action="subscription", status="telegram_failed",
                android_targets=0, reason="account_notice",
            ))
            db.add(CourseUserNotification(
                user_id=second_user_id, telegram_id=None,
                key="lesson_time", source="course_notification",
                language="uz", title="Native-only course notice",
                body="Private native-only lesson", action="course",
            ))
            db.add(Payment(
                id=802, user_id=second_user_id, user_telegram_id=None,
                plan_type="1_month", amount=89, currency="somoni",
                payment_status="pending",
            ))
            db.add(Payment(
                id=803, user_id=second_user_id, user_telegram_id=None,
                plan_type="1_month", amount=89, currency="somoni",
                payment_status="approved",
                reviewed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

        second_account_notices = await self.client.get(notices_url)
        second_course_notices = await self.client.get(course_url)
        self.assertEqual(second_account_notices.status_code, 200, second_account_notices.text)
        self.assertEqual(second_course_notices.status_code, 200, second_course_notices.text)
        self.assertEqual(
            [row["title"] for row in second_account_notices.json()["notices"]],
            ["Native-only service notice"],
        )
        self.assertEqual(
            [(row["payment_id"], row["status"]) for row in second_account_notices.json()["payment_reviews"]],
            [(803, "approved")],
        )
        self.assertEqual(
            [row["title"] for row in second_course_notices.json()["notifications"]],
            ["Native-only course notice"],
        )
        second_csrf = own_session.json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": second_csrf}
        self.assertEqual((await self.client.post(
            payment_url, headers=headers, json={"payment_id": 801},
        )).status_code, 404)
        own_payment = await self.client.post(
            payment_url, headers=headers, json={"payment_id": 802},
        )
        self.assertEqual(own_payment.status_code, 200, own_payment.text)
        self.assertEqual(own_payment.json()["status"], "pending")
        self.assertEqual(own_payment.headers.get("cache-control"), "no-store")

        prior = AsyncClient(
            transport=self.client._transport, base_url=ORIGIN,
            cookies={PWA_SESSION_COOKIE: old_cookie},
        )
        try:
            self.assertEqual((await prior.get(notices_url)).status_code, 401)
            self.assertEqual((await prior.get(course_url)).status_code, 401)
        finally:
            await prior.aclose()
        # Browsing a PWA inbox is not an Android shown/delivery receipt.
        async with self.sessions() as db:
            old_delivery = (await db.execute(
                select(AccountNoticeDelivery).where(AccountNoticeDelivery.user_id == 1)
            )).scalar_one()
            self.assertEqual(old_delivery.status, "android_pending")
            self.assertIsNone(old_delivery.android_shown_at)

    async def test_canonical_feedback_owner_dedupes_telegram_and_provider_accounts(self):
        """One users.id per campaign, including two distinct NULL TG learners."""
        from app.db.models.bot_feedback import BotFeedback
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, ReleaseFeedbackResponse,
        )
        from app.db.models.discount_campaign import DiscountCampaign
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from app.repositories.release_feedback_repo import ReleaseFeedbackRepository
        from app.services.release_feedback_service import ReleaseFeedbackService

        async with self.sessions() as db:
            db.add_all([user(2, None), user(3, None)])
            campaign = ReleaseFeedbackCampaign(
                id=77, title="Verified course update", status="sent",
                send_at=datetime.now(timezone.utc),
            )
            db.add(campaign)
            await db.flush()
            owners = [await db.get(User, account) for account in (1, 2, 3)]
            repo = ReleaseFeedbackRepository(db)
            replies = [
                await repo.create_response(
                    campaign_id=77, user=owner, rating=4,
                ) for owner in owners
            ]
            self.assertEqual([row.user_id for row in replies], [1, 2, 3])
            self.assertEqual(
                [row.user_telegram_id for row in replies],
                [1001, None, None],
            )
            for owner, reply in zip(owners, replies):
                existing = await repo.get_response(campaign_id=77, user=owner)
                self.assertEqual(existing.id, reply.id)
            via_telegram = await repo.get_response(
                campaign_id=77, user_telegram_id=1001,
            )
            self.assertEqual(via_telegram.user_id, 1)
            self.assertIsNone(await repo.get_response(
                campaign_id=77, user_telegram_id=None,
            ))
            with self.assertRaisesRegex(ValueError, "feedback_transport_owner_mismatch"):
                await repo.create_response(
                    campaign_id=77, user=owners[1],
                    user_telegram_id=1001, rating=4,
                )

            await repo.create_delivery(
                campaign_id=77, user=owners[1], status="clicked",
            )
            await repo.create_delivery(
                campaign_id=77, user=owners[2], status="clicked",
            )
            linked = await repo.create_delivery(
                campaign_id=77, user_telegram_id=1001, status="sent",
            )
            self.assertEqual(linked.user_id, 1)
            self.assertEqual(await repo.list_delivery_user_ids(77), {1001})
            self.assertEqual(await repo.list_delivery_account_ids(77), {1, 2, 3})
            self.assertEqual(
                (await repo.get_delivery(
                    campaign_id=77, user=owners[2],
                )).user_id, 3,
            )
            first, until = await ReleaseFeedbackService(db).grant_trial_access(
                campaign=campaign, user=owners[1],
            )
            self.assertTrue(first)
            again, same_until = await ReleaseFeedbackService(db).grant_trial_access(
                campaign=campaign, user=owners[1],
            )
            self.assertFalse(again)
            self.assertEqual(same_until, until)
            self.assertIsNone(owners[1].telegram_id)

            discount_id = await ReleaseFeedbackService(db).create_discount_for_response(
                campaign=campaign, response=replies[2], user=owners[2],
            )
            discount = await db.get(DiscountCampaign, discount_id)
            self.assertEqual(discount.target_user_id, 3)
            self.assertIsNone(discount.target_telegram_id)

            pending_google = await BotFeedbackRepository(db).create_pending(owners[1])
            pending_apple = await BotFeedbackRepository(db).create_pending(owners[2])
            self.assertEqual(
                (pending_google.user_id, pending_apple.user_id), (2, 3),
            )
            self.assertIsNone(pending_google.telegram_id)
            self.assertIsNone(pending_apple.telegram_id)

            # A scheduled Telegram-only offer must never look up a NULL
            # transport ID and accidentally target a different native owner.
            from app.services.bot_feedback_service import BotFeedbackService
            pending_google.status = "completed"
            pending_google.disliked_code = "price"
            pending_google.price_offer_due_at = (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            class NoTelegramSend:
                async def send_message(self, **_kwargs):
                    raise AssertionError("Provider-only feedback must not send a Telegram DM")
            sent = await BotFeedbackService(db).send_due_price_discount_offers(
                NoTelegramSend(),
            )
            self.assertEqual(sent, 0)
            self.assertIsNotNone(pending_google.price_offer_sent_at)

            # Account linking can expose an unmapped legacy Telegram record
            # beside a preexisting canonical PWA response. Prefer the real
            # user_id and never throw MultipleResultsFound or reward twice.
            owners[1].telegram_id = 2002
            await db.flush()
            from app.bot.handlers.feedback import _load_feedback_context
            _, permitted_feedback, linked_owner = await _load_feedback_context(
                db, 2002, pending_google.id,
            )
            self.assertEqual(permitted_feedback.id, pending_google.id)
            self.assertEqual(linked_owner.id, 2)
            # The delayed price-offer button must still resolve the same
            # canonical feedback after a native-only learner links Telegram.
            offered = await BotFeedbackRepository(db).get_available_price_offer(
                feedback_id=pending_google.id, telegram_id=2002,
            )
            self.assertEqual(offered.user_id, 2)
            self.assertIsNone(await BotFeedbackRepository(db).get_available_price_offer(
                feedback_id=pending_google.id, telegram_id=1001,
            ))
            latest_offer = await BotFeedbackRepository(db).get_latest_available_price_offer(
                telegram_id=2002,
            )
            self.assertEqual(latest_offer.id, pending_google.id)
            await BotFeedbackRepository(db).mark_latest_price_offer_used(2002)
            self.assertIsNotNone(pending_google.price_offer_used_at)
            _, forbidden_feedback, forbidden_owner = await _load_feedback_context(
                db, 1001, pending_google.id,
            )
            self.assertIsNone(forbidden_feedback)
            self.assertIsNone(forbidden_owner)
            db.add(ReleaseFeedbackResponse(
                campaign_id=77, user_id=None, user_telegram_id=2002,
                rating=1,
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=77, user_id=None, user_telegram_id=2002,
                status="sent",
            ))
            await db.flush()
            resolved = await repo.get_response(campaign_id=77, user=owners[1])
            self.assertEqual(resolved.id, replies[1].id)
            resolved_delivery = await repo.get_delivery(
                campaign_id=77, user=owners[1],
            )
            self.assertEqual(resolved_delivery.user_id, 2)

            with self.assertRaises(IntegrityError):
                async with db.begin_nested():
                    await repo.create_response(
                        campaign_id=77, user=owners[1], rating=3,
                    )
            await db.commit()
            saved = (await db.execute(sa.select(ReleaseFeedbackResponse))).scalars().all()
            deliveries = (await db.execute(sa.select(ReleaseFeedbackDelivery))).scalars().all()
            pending = (await db.execute(sa.select(BotFeedback))).scalars().all()
            self.assertEqual(len(saved), 4)
            self.assertEqual(len(deliveries), 4)
            self.assertEqual(len(pending), 2)

    def test_0146_feedback_migration_backfills_real_owners_and_rejects_data_loss(self):
        """Legacy Telegram IDs are backfilled; provider rows never fake TG IDs."""
        import importlib.util
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        filename = Path("alembic/versions/0146_pwa_feedback_owner.py")
        spec = importlib.util.spec_from_file_location("test_0146_pwa_feedback", filename)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)

        engine = sa.create_engine("sqlite:///:memory:")
        meta = sa.MetaData()
        sa.Table(
            "users", meta, sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("telegram_id", sa.BigInteger, unique=True, nullable=True),
        )
        sa.Table(
            "bot_feedbacks", meta, sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, nullable=False),
            sa.Column("telegram_id", sa.BigInteger, nullable=False),
        )
        sa.Table(
            "release_feedback_campaigns", meta,
            sa.Column("id", sa.Integer, primary_key=True),
        )
        for table in ("release_feedback_deliveries", "release_feedback_responses"):
            sa.Table(
                table, meta, sa.Column("id", sa.Integer, primary_key=True),
                sa.Column("campaign_id", sa.Integer, nullable=False),
                sa.Column("user_telegram_id", sa.BigInteger, nullable=False),
                sa.UniqueConstraint("campaign_id", "user_telegram_id",
                    name=f"uq_{table}_campaign_user"),
            )
        meta.create_all(engine)
        try:
            with engine.begin() as conn:
                conn.execute(sa.text("INSERT INTO users VALUES (1,1001),(2,NULL),(3,NULL)"))
                conn.execute(sa.text("INSERT INTO bot_feedbacks VALUES (1,1,1001)"))
                conn.execute(sa.text("INSERT INTO release_feedback_campaigns VALUES (77)"))
                for table in ("release_feedback_deliveries", "release_feedback_responses"):
                    conn.execute(sa.text(
                        f"INSERT INTO {table} (id,campaign_id,user_telegram_id) "
                        "VALUES (1,77,1001),(2,77,9999)"
                    ))
                with Operations.context(MigrationContext.configure(conn)):
                    revision.upgrade()
                    revision.upgrade()  # Empty/latest QA and real legacy both supported
                self.assertTrue(sa.inspect(conn).get_columns("bot_feedbacks"))
                for table in ("release_feedback_deliveries", "release_feedback_responses"):
                    self.assertEqual(
                        conn.execute(sa.text(
                            f"SELECT user_id FROM {table} ORDER BY id"
                        )).scalars().all(), [1, None],
                    )
                    conn.execute(sa.text(
                        f"INSERT INTO {table} (id,campaign_id,user_id,user_telegram_id) "
                        "VALUES (3,77,2,NULL),(4,77,3,NULL)"
                    ))
                    with self.assertRaises(IntegrityError):
                        with conn.begin_nested():
                            conn.execute(sa.text(
                                f"INSERT INTO {table} "
                                "(id,campaign_id,user_id,user_telegram_id) "
                                "VALUES (5,77,2,NULL)"
                            ))
                with self.assertRaisesRegex(RuntimeError, "Refusing downgrade"):
                    with Operations.context(MigrationContext.configure(conn)):
                        revision.downgrade()
                self.assertEqual(conn.execute(sa.text(
                    "SELECT COUNT(*) FROM release_feedback_responses "
                    "WHERE user_telegram_id IS NULL"
                )).scalar_one(), 2)
        finally:
            engine.dispose()

    def test_0146_feedback_migration_accepts_empty_latest_orm_qa_baseline(self):
        """The QA bootstrap uses latest empty ORM tables, not old 0145 DDL."""
        import importlib.util
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        path = Path("alembic/versions/0146_pwa_feedback_owner.py")
        spec = importlib.util.spec_from_file_location("test_0146_current", path)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)

        engine = sa.create_engine("sqlite:///:memory:")
        try:
            with engine.begin() as conn:
                # Register metadata in the existing module-level Base.
                Base.metadata.create_all(conn)
                with Operations.context(MigrationContext.configure(conn)):
                    revision.upgrade()
                    revision.upgrade()
                for table in ("release_feedback_deliveries", "release_feedback_responses"):
                    columns = {c["name"]: c for c in sa.inspect(conn).get_columns(table)}
                    self.assertTrue(columns["user_telegram_id"]["nullable"])
                    self.assertIn("user_id", columns)
                    constraints = {item["name"] for item in sa.inspect(conn).get_unique_constraints(table)}
                    self.assertIn(f"uq_{table}_campaign_account", constraints)
                    indexes = {item["name"] for item in sa.inspect(conn).get_indexes(table)}
                    self.assertIn(f"ix_{table}_user_id", indexes)
        finally:
            engine.dispose()

    async def test_pwa_feedback_choices_reuse_existing_localized_bot_options(self):
        """PWA option labels and follow-up codes are exactly the live bot catalog."""
        from app.api.pwa_auth import _pwa_feedback_choices
        from app.bot.keyboards.feedback import (
            LIKED_OPTIONS, DISLIKED_OPTIONS, LIKE_SUB_OPTIONS,
            PAID_OPTIONS, PAID_SUB_POSITIVE, PAID_SUB_NEGATIVE,
            feedback_like_label, feedback_dislike_label, feedback_sub_label,
            feedback_paid_label,
        )
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        for lang in ("uz", "ru", "tj"):
            unpaid = _pwa_feedback_choices(lang, paid=False)
            paid = _pwa_feedback_choices(lang, paid=True)
            self.assertEqual(unpaid["liked"], [
                {"code":code, "label":feedback_like_label(code, lang)}
                for code in LIKED_OPTIONS
            ])
            self.assertEqual(unpaid["disliked"], [
                {"code":code, "label":feedback_dislike_label(code, lang)}
                for code in DISLIKED_OPTIONS
            ])
            for parent, codes in LIKE_SUB_OPTIONS.items():
                self.assertEqual(unpaid["liked_sub"][parent], [
                    {"code":code, "label":feedback_sub_label(code, lang)}
                    for code in codes
                ])
            self.assertEqual(unpaid["disliked_detail_required"],
                             ["other", "pace", "unclear"])
            self.assertEqual(paid["paid"], [
                {"code":code, "label":feedback_paid_label(code, lang)}
                for code in PAID_OPTIONS
            ])
            self.assertEqual(
                [choice["code"] for choice in paid["paid_sub_positive"]],
                list(PAID_SUB_POSITIVE),
            )
            self.assertEqual(
                [choice["code"] for choice in paid["paid_sub_negative"]],
                list(PAID_SUB_NEGATIVE),
            )
            self.assertEqual(_pwa_feedback_choices("not-a-language", paid=False),
                             _pwa_feedback_choices("ru", paid=False))

        async with self.sessions() as db:
            person = await db.get(User, 1)
            person.language = "tj"
            person.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            row = await BotFeedbackRepository(db).create_pending(person)
            feedback_id = row.id
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        response = await self.client.get("/api/v3/pwa/feedback/available")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["ordinary"]["feedback_id"], feedback_id)
        self.assertEqual(
            response.json()["ordinary"]["choices"],
            _pwa_feedback_choices("tj", paid=False),
        )
        # A prepared eligible account sees exactly the same server choices.
        async with self.sessions() as db:
            person = await db.get(User, 1)
            person.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            await db.commit()
        session = (await self.client.get("/api/v3/pwa-auth/session")).json()
        prepared = await self.client.post(
            "/api/v3/pwa/feedback/ordinary/prepare",
            json={}, headers={
                "Origin": ORIGIN, "X-HSK-PWA-CSRF": session["csrf"],
            },
        )
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(
            prepared.json()["ordinary"]["choices"],
            _pwa_feedback_choices("tj", paid=False),
        )

    async def test_pwa_feedback_get_and_prepare_share_original_eligibility(self):
        """A stale or too-new owner cannot see an ordinary prompt via GET."""
        from app.repositories.bot_feedback_repo import BotFeedbackRepository

        async with self.sessions() as db:
            owner = await db.get(User, 1)
            row = await BotFeedbackRepository(db).create_pending(owner)
            feedback_id = row.id
            await db.commit()

        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        get_url = "/api/v3/pwa/feedback/available"
        post_url = "/api/v3/pwa/feedback/ordinary/prepare"
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        self.assertIsNone((await self.client.get(get_url)).json()["ordinary"])
        self.assertIsNone((await self.client.post(
            post_url, headers=headers, json={},
        )).json()["ordinary"])

        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            owner.last_active_at = datetime.now(timezone.utc) - timedelta(days=8)
            await db.commit()
        self.assertIsNone((await self.client.get(get_url)).json()["ordinary"])
        self.assertIsNone((await self.client.post(
            post_url, headers=headers, json={},
        )).json()["ordinary"])

        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.last_active_at = datetime.now(timezone.utc)
            await db.commit()
        fetched = await self.client.get(get_url)
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["ordinary"]["feedback_id"], feedback_id)
        prepared = await self.client.post(post_url, headers=headers, json={})
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(prepared.json()["ordinary"]["feedback_id"], feedback_id)

    async def test_pwa_feedback_administrator_reply_uses_current_linked_account(self):
        """Admin reply never tries a provider-only NULL or historical TG ID."""
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from app.bot.handlers.feedback import _admin_feedback_reply_recipient, _load_feedback_context
        from app.bot.handlers.release_feedback import _locked_telegram_feedback_user

        async with self.sessions() as db:
            db.add(user(2, None))
            db.add(user(3, None))
            await db.flush()
            owner = await db.get(User, 2)
            feedback = await BotFeedbackRepository(db).create_pending(owner)
            self.assertIsNone(await _admin_feedback_reply_recipient(db, feedback))
            owner.telegram_id = 2002
            await db.flush()
            linked = await _admin_feedback_reply_recipient(db, feedback)
            self.assertEqual(linked.id, 2)
            self.assertEqual(linked.telegram_id, 2002)
            self.assertIsNone(feedback.telegram_id)
            _, matched_feedback, matched_owner = await _load_feedback_context(
                db, 2002, feedback.id,
            )
            self.assertEqual(matched_feedback.id, feedback.id)
            self.assertEqual(matched_owner.id, 2)
            _, rejected, rejected_user = await _load_feedback_context(
                db, 1001, feedback.id,
            )
            self.assertIsNone(rejected)
            self.assertIsNone(rejected_user)
            self.assertEqual(
                (await _locked_telegram_feedback_user(db, 2002)).id, 2
            )
            self.assertIsNone(await _locked_telegram_feedback_user(db, 0))
            owner.telegram_id = None
            await db.flush()
            self.assertIsNone(await _admin_feedback_reply_recipient(db, feedback))
            await db.rollback()

    async def test_pwa_feedback_prepare_preserves_bot_cooldown_and_canonical_owner(self):
        """Browser cannot manufacture recipients or repeatedly create due rows."""
        from app.db.models.bot_feedback import BotFeedback
        from app.repositories.bot_feedback_repo import BotFeedbackRepository

        url = "/api/v3/pwa/feedback/ordinary/prepare"
        feed_url = "/api/v3/pwa/feedback/available"
        self.assertEqual((await self.client.get(feed_url)).status_code, 401)
        self.assertEqual((await self.client.post(
            url, headers={"Origin": ORIGIN}, json={},
        )).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        session = (await self.client.get("/api/v3/pwa-auth/session")).json()
        csrf = session["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        self.assertEqual((await self.client.post(
            url, headers={"Origin": ORIGIN}, json={},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={"user_id": 2},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, headers={**headers, "X-Telegram-Init-Data": "fake"}, json={},
        )).status_code, 422)
        young = await self.client.post(url, headers=headers, json={})
        self.assertEqual(young.status_code, 200, young.text)
        self.assertIsNone(young.json()["ordinary"])
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            owner.created_at = datetime.now(timezone.utc) - timedelta(days=3)
            await db.commit()
        ready = await self.client.post(url, headers=headers, json={})
        self.assertEqual(ready.status_code, 200, ready.text)
        feedback_id = ready.json()["ordinary"]["feedback_id"]
        self.assertIsInstance(feedback_id, int)
        again = await self.client.post(url, headers=headers, json={})
        self.assertEqual(again.json()["ordinary"]["feedback_id"], feedback_id)
        projected = (await self.client.get(feed_url)).json()
        self.assertEqual(projected["ordinary"]["feedback_id"], feedback_id)
        self.assertEqual(projected["release"], [])
        async with self.sessions() as db:
            pending = (await db.execute(
                select(BotFeedback).where(BotFeedback.user_id == 1)
            )).scalars().all()
            self.assertEqual(len(pending), 1)
            self.assertIsNone(pending[0].prompted_at)
            # One account cannot bypass the existing two-attempt limit by
            # fetching the same prompt in Safari or from the home screen.
            pending[0].prompt_attempts = 2
            await db.commit()
        self.assertIsNone((await self.client.post(
            url, headers=headers, json={},
        )).json()["ordinary"])
        self.assertIsNone((await self.client.get(feed_url)).json()["ordinary"])
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(feed_url)).status_code, 503)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={},
        )).status_code, 503)

    async def test_pwa_admin_feedback_notified_only_after_commit_and_once(self):
        """Accepted PWA answers use existing Admin channel; replay does not."""
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery,
        )
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from unittest.mock import patch, AsyncMock

        async with self.sessions() as db:
            db.add(ReleaseFeedbackCampaign(
                id=86, title="PWA admin parity", status="sent",
                send_at=datetime.now(timezone.utc) - timedelta(days=1),
            ))
            await db.flush()
            db.add(ReleaseFeedbackDelivery(
                campaign_id=86, user_id=1, user_telegram_id=1001,
                status="sent",
            ))
            feedback = await BotFeedbackRepository(db).create_pending(await db.get(User, 1))
            feedback_id = feedback.id
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        with patch("app.services.admin_notify_service.AdminNotifyService") as admin:
            instance = admin.return_value
            instance.notify_bot_feedback = AsyncMock()
            instance.notify_release_feedback_response = AsyncMock()
            ordinary = await self.client.post(
                "/api/v3/pwa/feedback/ordinary/submit",
                headers=headers,
                json={
                    "feedback_id": feedback_id, "liked_code": "photo",
                    "liked_sub_code": "translate", "disliked_code": "price",
                },
            )
            self.assertEqual(ordinary.status_code, 200, ordinary.text)
            instance.notify_bot_feedback.assert_awaited_once()
            self.assertEqual(
                instance.notify_bot_feedback.await_args.kwargs["user"].id, 1
            )
            self.assertEqual((await self.client.post(
                "/api/v3/pwa/feedback/ordinary/submit", headers=headers,
                json={"feedback_id": feedback_id, "liked_code": "photo",
                      "liked_sub_code": "translate", "disliked_code": "price"},
            )).status_code, 409)
            instance.notify_bot_feedback.assert_awaited_once()

            answer = await self.client.post(
                "/api/v3/pwa/feedback/release/respond", headers=headers,
                json={"campaign_id": 86, "rating": 5},
            )
            self.assertEqual(answer.status_code, 200, answer.text)
            instance.notify_release_feedback_response.assert_awaited_once()
            self.assertEqual(
                instance.notify_release_feedback_response.await_args.kwargs["user"].id, 1
            )
            self.assertEqual((await self.client.post(
                "/api/v3/pwa/feedback/release/respond", headers=headers,
                json={"campaign_id": 86, "rating": 5},
            )).status_code, 409)
            instance.notify_release_feedback_response.assert_awaited_once()

    async def test_pwa_admin_feedback_transport_failure_does_not_rollback_answer(self):
        from app.repositories.bot_feedback_repo import BotFeedbackRepository
        from app.db.models.bot_feedback import BotFeedback
        from unittest.mock import patch, AsyncMock

        async with self.sessions() as db:
            item = await BotFeedbackRepository(db).create_pending(await db.get(User, 1))
            feedback_id = item.id
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        with patch("app.services.admin_notify_service.AdminNotifyService") as admin:
            admin.return_value.notify_bot_feedback = AsyncMock(
                side_effect=RuntimeError("simulated admin outage")
            )
            accepted = await self.client.post(
                "/api/v3/pwa/feedback/ordinary/submit",
                headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                json={"feedback_id": feedback_id, "liked_code": "answers",
                      "liked_sub_code": "speed", "disliked_code": "price"},
            )
            self.assertEqual(accepted.status_code, 200, accepted.text)
        async with self.sessions() as db:
            stored = await db.get(BotFeedback, feedback_id)
            self.assertEqual(stored.status, "completed")
            self.assertIsNotNone(stored.reward_granted_at)

    async def test_pwa_ordinary_feedback_submit_reuses_one_bot_reward_and_locked_owner(self):
        from app.db.models.bot_feedback import BotFeedback
        from app.repositories.bot_feedback_repo import BotFeedbackRepository

        url = "/api/v3/pwa/feedback/ordinary/submit"
        async with self.sessions() as db:
            actor = await db.get(User, 1)
            feedback = await BotFeedbackRepository(db).create_pending(actor)
            feedback_id = feedback.id
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        session = (await self.client.get("/api/v3/pwa-auth/session")).json()
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": session["csrf"]}
        valid = {
            "feedback_id": feedback_id,
            "liked_code": "course", "liked_sub_code": "lessons",
            "disliked_code": "unclear", "disliked_detail_text": "Need clearer examples",
        }
        self.assertEqual((await self.client.post(
            url, headers={"Origin": ORIGIN}, json=valid,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={**valid, "user_id": 2},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={**valid, "disliked_detail_text": None},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={**valid, "feedback_id": feedback_id + 1},
        )).status_code, 404)
        accepted = await self.client.post(url, headers=headers, json=valid)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertTrue(accepted.json()["completed"])
        replay = await self.client.post(url, headers=headers, json=valid)
        self.assertEqual(replay.status_code, 409, replay.text)
        async with self.sessions() as db:
            stored = await db.get(BotFeedback, feedback_id)
            owner = await db.get(User, 1)
            self.assertEqual(stored.status, "completed")
            self.assertEqual(stored.liked_code, "course")
            self.assertEqual(stored.disliked_code, "unclear")
            self.assertEqual(stored.disliked_text, "Need clearer examples")
            self.assertIsNotNone(stored.reward_granted_at)
            self.assertEqual(owner.status, "active")
            self.assertIsNotNone(owner.end_date)

    async def test_telegram_release_reward_refuses_undelivered_or_failed_campaign(self):
        """Telegram callback data alone must not grant another user's trial."""
        from app.bot.handlers.release_feedback import release_feedback_user_callback
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery,
        )
        from unittest.mock import patch, AsyncMock

        async with self.sessions() as db:
            db.add(ReleaseFeedbackCampaign(
                id=97, title="Private rating campaign", status="sent",
                send_at=datetime.now(timezone.utc) - timedelta(hours=2),
            ))
            await db.commit()

        callback = SimpleNamespace(
            data="relfb:97:try",
            from_user=SimpleNamespace(id=1001),
            answer=AsyncMock(),
            message=SimpleNamespace(message_id=15),
        )
        state = SimpleNamespace(set_state=AsyncMock(), update_data=AsyncMock())
        with patch("app.services.release_feedback_service.ReleaseFeedbackService.grant_trial_access",
                   new_callable=AsyncMock) as grant:
            async with self.sessions() as db:
                await release_feedback_user_callback(callback, state, db)
            grant.assert_not_awaited()
            self.assertTrue(callback.answer.await_args.kwargs["show_alert"])

            async with self.sessions() as db:
                db.add(ReleaseFeedbackDelivery(
                    campaign_id=97, user_id=1, user_telegram_id=1001,
                    status="failed",
                ))
                await db.commit()
            callback.answer.reset_mock()
            async with self.sessions() as db:
                await release_feedback_user_callback(callback, state, db)
            grant.assert_not_awaited()
            self.assertTrue(callback.answer.await_args.kwargs["show_alert"])

        # The actual sent delivery remains eligible for rating: the guard
        # may not disable legitimate Telegram feedback during rollout.
        async with self.sessions() as db:
            delivery = (await db.execute(
                select(ReleaseFeedbackDelivery).where(
                    ReleaseFeedbackDelivery.campaign_id == 97,
                )
            )).scalar_one()
            delivery.status = "sent"
            await db.commit()
        callback.data = "relfb:97:rate:1"
        callback.answer.reset_mock()
        with patch("app.bot.handlers.release_feedback._edit_user_feedback_message",
                   new_callable=AsyncMock):
            async with self.sessions() as db:
                await release_feedback_user_callback(callback, state, db)
            state.set_state.assert_awaited_once()
            state.update_data.assert_awaited_once()
            self.assertFalse(callback.answer.await_args.kwargs.get("show_alert", False))

    async def test_pwa_release_comment_after_rating_does_not_repeat_reward(self):
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, ReleaseFeedbackResponse,
        )
        from app.db.models.discount_campaign import DiscountCampaign
        from unittest.mock import patch, AsyncMock

        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            db.add(user(2, None))
            db.add(ReleaseFeedbackCampaign(
                id=88, title="Optional rating comment", status="sent",
                send_at=now - timedelta(days=1),
            ))
            db.add(ReleaseFeedbackCampaign(
                id=89, title="Other account rating", status="sent",
                send_at=now - timedelta(days=1),
            ))
            await db.flush()
            db.add(ReleaseFeedbackDelivery(
                campaign_id=88, user_id=1, user_telegram_id=1001,
                status="clicked",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=89, user_id=2, user_telegram_id=None,
                status="sent",
            ))
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        session = (await self.client.get("/api/v3/pwa-auth/session")).json()
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": session["csrf"]}
        url = "/api/v3/pwa/feedback/release/comment"
        valid = {"campaign_id": 88, "comment_text": "Clearer lessons are useful"}
        self.assertEqual((await self.client.post(
            url, json=valid, headers={"Origin": ORIGIN},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            url, json={**valid, "user_id": 2}, headers=headers,
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, json={**valid, "comment_text": " "}, headers=headers,
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, json={**valid, "campaign_id": 89}, headers=headers,
        )).status_code, 404)
        self.assertEqual((await self.client.post(
            url, json=valid, headers=headers,
        )).status_code, 409)
        rated = await self.client.post(
            "/api/v3/pwa/feedback/release/respond",
            headers=headers, json={"campaign_id": 88, "rating": 5},
        )
        self.assertEqual(rated.status_code, 200, rated.text)
        original_discount_id = rated.json()["discount_campaign_id"]
        original_trial_until = rated.json()["trial_until"]
        with patch("app.services.admin_notify_service.AdminNotifyService") as notify:
            notify.return_value.notify_release_feedback_response = AsyncMock()
            added = await self.client.post(url, json=valid, headers=headers)
            self.assertEqual(added.status_code, 200, added.text)
            self.assertTrue(added.json()["updated"])
            notify.return_value.notify_release_feedback_response.assert_awaited_once()
            self.assertEqual(
                notify.return_value.notify_release_feedback_response.await_args.kwargs["event"],
                "comment",
            )
            retry = await self.client.post(url, json=valid, headers=headers)
            self.assertEqual(retry.status_code, 200, retry.text)
            self.assertFalse(retry.json()["updated"])
            notify.return_value.notify_release_feedback_response.assert_awaited_once()
        async with self.sessions() as db:
            response = (await db.execute(
                select(ReleaseFeedbackResponse).where(
                    ReleaseFeedbackResponse.campaign_id == 88,
                )
            )).scalar_one()
            self.assertEqual(response.comment_text, valid["comment_text"])
            self.assertEqual(response.rating, 5)
            self.assertEqual(response.discount_campaign_id, original_discount_id)
            self.assertEqual(response.user_id, 1)
            discounts = (await db.execute(
                select(DiscountCampaign).where(DiscountCampaign.target_user_id == 1)
            )).scalars().all()
            self.assertEqual(len(discounts), 1)
            delivery = (await db.execute(
                select(ReleaseFeedbackDelivery).where(
                    ReleaseFeedbackDelivery.campaign_id == 88,
                )
            )).scalar_one()
            self.assertEqual(
                delivery.trial_granted_until.replace(tzinfo=timezone.utc).isoformat(),
                original_trial_until,
            )

    async def test_pwa_release_sending_campaign_matches_delivered_telegram_recipient(self):
        """One recipient can answer after delivery while the larger batch runs.

        A merely queued/failed recipient does not gain a discount or trial.
        """
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, ReleaseFeedbackResponse,
        )
        from app.db.models.discount_campaign import DiscountCampaign

        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            for cid in (95, 96):
                db.add(ReleaseFeedbackCampaign(
                    id=cid, title=f"Sending batch {cid}", status="sending",
                    send_at=now - timedelta(hours=1),
                ))
            await db.flush()
            db.add(ReleaseFeedbackDelivery(
                campaign_id=95, user_id=1, user_telegram_id=1001, status="sent",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=96, user_id=1, user_telegram_id=1001, status="failed",
            ))
            await db.commit()

        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        listed = (await self.client.get("/api/v3/pwa/feedback/available")).json()
        self.assertEqual(
            [item["campaign_id"] for item in listed["release"]], [95],
        )
        self.assertEqual((await self.client.post(
            "/api/v3/pwa/feedback/release/respond", headers=headers,
            json={"campaign_id": 96, "rating": 5},
        )).status_code, 404)
        accepted = await self.client.post(
            "/api/v3/pwa/feedback/release/respond", headers=headers,
            json={"campaign_id": 95, "rating": 5},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertIsInstance(accepted.json()["discount_campaign_id"], int)
        self.assertTrue(accepted.json()["trial_until"])
        comment = await self.client.post(
            "/api/v3/pwa/feedback/release/comment", headers=headers,
            json={"campaign_id": 95, "comment_text": "Useful new lesson"},
        )
        self.assertEqual(comment.status_code, 200, comment.text)
        self.assertTrue(comment.json()["updated"])
        self.assertEqual((await self.client.post(
            "/api/v3/pwa/feedback/release/respond", headers=headers,
            json={"campaign_id": 95, "rating": 5},
        )).status_code, 409)
        async with self.sessions() as db:
            replies = (await db.execute(
                select(ReleaseFeedbackResponse)
            )).scalars().all()
            self.assertEqual(len(replies), 1)
            self.assertEqual(replies[0].campaign_id, 95)
            self.assertEqual(replies[0].comment_text, "Useful new lesson")
            coupons = (await db.execute(
                select(DiscountCampaign)
            )).scalars().all()
            self.assertEqual(len(coupons), 1)
            self.assertEqual(coupons[0].target_user_id, 1)

    async def test_pwa_release_rating_requires_delivered_canonical_owner_and_one_reward(self):
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, ReleaseFeedbackResponse,
        )
        from app.db.models.discount_campaign import DiscountCampaign

        url = "/api/v3/pwa/feedback/release/respond"
        order = {"campaign_id": 81, "rating": 5}
        self.assertEqual((await self.client.post(
            url, headers={"Origin": ORIGIN}, json=order,
        )).status_code, 401)
        async with self.sessions() as db:
            db.add(user(2, None))
            db.add(ReleaseFeedbackCampaign(
                id=81, title="Verified release", status="sent",
                send_at=datetime.now(timezone.utc) - timedelta(days=1),
            ))
            db.add(ReleaseFeedbackCampaign(
                id=82, title="Never delivered", status="sent",
                send_at=datetime.now(timezone.utc) - timedelta(days=1),
            ))
            await db.flush()
            db.add(ReleaseFeedbackDelivery(
                campaign_id=81, user_id=1, user_telegram_id=1001,
                status="sent",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=82, user_id=2, user_telegram_id=None,
                status="sent",
            ))
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        self.assertEqual((await self.client.post(
            url, headers={"Origin": ORIGIN}, json=order,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={**order, "user_id": 2},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={"campaign_id": 82, "rating": 5},
        )).status_code, 404)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={"campaign_id": 81, "rating": 1},
        )).status_code, 422)
        good = await self.client.post(url, headers=headers, json=order)
        self.assertEqual(good.status_code, 200, good.text)
        self.assertTrue(good.json()["trial_until"])
        discount_id = good.json()["discount_campaign_id"]
        self.assertIsInstance(discount_id, int)
        self.assertEqual(good.headers.get("cache-control"), "no-store")
        repeated = await self.client.post(url, headers=headers, json=order)
        self.assertEqual(repeated.status_code, 409, repeated.text)
        async with self.sessions() as db:
            replies = (await db.execute(
                select(ReleaseFeedbackResponse)
            )).scalars().all()
            self.assertEqual(len(replies), 1)
            self.assertEqual(replies[0].user_id, 1)
            self.assertEqual(replies[0].discount_campaign_id, discount_id)
            discounts = (await db.execute(
                select(DiscountCampaign)
            )).scalars().all()
            self.assertEqual(len(discounts), 1)
            self.assertEqual(discounts[0].target_user_id, 1)
            learner = await db.get(User, 1)
            self.assertEqual(learner.status, "active")

    async def test_pwa_release_feedback_availability_requires_existing_sent_delivery(self):
        """No unrelated campaign, unsent draft or already answered release leaks."""
        from app.db.models.release_feedback import (
            ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, ReleaseFeedbackResponse,
        )
        from app.repositories.release_feedback_repo import ReleaseFeedbackRepository

        async with self.sessions() as db:
            db.add(user(2, None))
            now = datetime.now(timezone.utc)
            for cid, status in ((71, "sent"), (72, "scheduled"), (73, "sent"),
                                (74, "sent"), (75, "sending"), (76, "sending")):
                db.add(ReleaseFeedbackCampaign(
                    id=cid, title=f"Campaign {cid}", status=status,
                    send_at=now - timedelta(days=1),
                ))
            await db.flush()
            db.add(ReleaseFeedbackDelivery(
                campaign_id=71, user_id=1, user_telegram_id=1001,
                status="sent",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=72, user_id=1, user_telegram_id=1001,
                status="sent",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=73, user_id=2, user_telegram_id=None,
                status="sent",
            ))
            # A "try" click must not make a still-unanswered release vanish.
            db.add(ReleaseFeedbackDelivery(
                campaign_id=74, user_id=1, user_telegram_id=1001,
                status="clicked",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=75, user_id=1, user_telegram_id=1001,
                status="sent",
            ))
            db.add(ReleaseFeedbackDelivery(
                campaign_id=76, user_id=1, user_telegram_id=1001,
                status="failed",
            ))
            await db.commit()
        state = await self.begin()
        await self.callback(state)
        url = "/api/v3/pwa/feedback/available"
        ready = await self.client.get(url)
        self.assertEqual(ready.status_code, 200, ready.text)
        self.assertEqual(
            [item["campaign_id"] for item in ready.json()["release"]], [75, 74, 71],
        )
        self.assertNotIn("media_file_id", ready.text)
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            await ReleaseFeedbackRepository(db).create_response(
                campaign_id=71, user=owner, rating=5,
            )
            await db.commit()
        self.assertEqual(
            [item["campaign_id"] for item in (await self.client.get(url)).json()["release"]],
            [75, 74],
        )

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
        sample = bytes.fromhex("000000146674797069736f6d") + bytes(1300)
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

    async def test_pwa_hsk_exams_use_existing_server_grading_and_user_xp(self):
        page_url = "/iphone-pwa/practice/test"
        start_url = "/api/v3/pwa/exams/start"
        complete_url = "/api/v3/pwa/exams/complete"
        self.assertEqual(
            (await self.client.get(page_url, follow_redirects=False)).status_code, 303,
        )
        self.assertEqual((await self.client.post(
            start_url, headers={"Origin": ORIGIN},
            json={"level": "hsk1", "lang": "uz", "access_ref": "exam-1"},
        )).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(page_url)
        self.assertEqual(page.status_code, 200, page.text[:180])
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        self.assertNotIn("maximum-scale=1", page.text)
        session = await self.client.get("/api/v3/pwa-auth/session")
        csrf = session.json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        payload = {"level": "hsk1", "lang": "uz", "access_ref": "exam-1"}
        self.assertEqual((await self.client.post(
            start_url, headers={"Origin": ORIGIN}, json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            start_url, headers={**headers, "Origin": "https://bad.example"}, json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            start_url, headers=headers,
            json={**payload, "telegram_id": 1001},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            start_url, headers={**headers, "X-Telegram-Init-Data": "bogus"},
            json=payload,
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            start_url, headers=headers, json={**payload, "ad_supported": True},
        )).status_code, 422)

        with patch(
            "app.services.course_hsk_exam_service.CourseHskExamService.start",
            new_callable=AsyncMock,
        ) as start, patch(
            "app.services.course_hsk_exam_service.CourseHskExamService.complete",
            new_callable=AsyncMock,
        ) as complete:
            start.return_value = {
                "ok": True, "session": {"id": "exam-owner-one", "questions": [{}]},
            }
            complete.return_value = {
                "ok": True, "score": 11, "reward": {"awarded_xp": 25},
            }
            opened = await self.client.post(start_url, headers=headers, json=payload)
            self.assertEqual(opened.status_code, 200, opened.text)
            self.assertEqual(start.await_args.args[0].id, 1)
            self.assertIs(start.await_args.kwargs["ad_supported"], False)
            completed = await self.client.post(
                complete_url, headers=headers,
                json={"session_id": "exam-owner-one",
                      "answers": [{"question_id": "q1", "selected_index": 2}]},
            )
            self.assertEqual(completed.status_code, 200, completed.text)
            self.assertEqual(completed.json()["reward"]["awarded_xp"], 25)
            self.assertEqual(complete.await_args.args[0].id, 1)
            self.assertEqual(complete.await_args.kwargs["session_id"], "exam-owner-one")
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(page_url)).status_code, 503)

    def test_existing_exam_screens_use_pwa_server_results_without_forged_xp(self):
        inline = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        standalone = (Path("app/static") / "course_v3_test.html").read_text(encoding="utf-8")
        self.assertIn('"/api/v3/exams/start":"/api/v3/pwa/exams/start"', inline)
        self.assertIn('"/api/v3/exams/complete":"/api/v3/pwa/exams/complete"', inline)
        self.assertIn('_apiPost("/api/v3/exams/start"', inline)
        self.assertIn('_apiPost("/api/v3/exams/complete"', inline)
        self.assertIn("d.reward&&d.reward.awarded_xp", inline)
        self.assertIn('PWA_TEST_HOST=location.pathname==="/iphone-pwa/practice/test"', standalone)
        self.assertIn('"/api/v3/pwa/exams/start"', standalone)
        self.assertIn('"/api/v3/pwa/exams/complete"', standalone)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', standalone)
        self.assertIn('if(PWA_TEST_HOST){showEmpty();return}', standalone)
        self.assertIn('if(PWA_COURSE_HOST){showEmpty();return}', inline)

    async def test_pwa_onboarding_uses_canonical_profile_service_and_real_actor(self):
        page_url = "/iphone-pwa/onboarding"
        api_url = "/api/v3/pwa/onboarding"
        self.assertEqual((await self.client.get(
            page_url, follow_redirects=False,
        )).status_code, 303)
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(page_url)
        self.assertEqual(page.status_code, 200, page.text[:160])
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        payload = {
            "level": "hsk1", "goal": "hsk_exam", "daily_minutes": 10,
            "start_mode": "lesson_1", "language": "uz",
            "timezone_offset_minutes": 480,
            "activation_variant": "direct_start_v1",
        }
        self.assertEqual((await self.client.post(
            api_url, headers={"Origin": ORIGIN}, json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            api_url, headers={**headers, "Origin": "https://attacker.example"},
            json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            api_url, headers=headers,
            json={**payload, "telegram_id": 1},
        )).status_code, 422)
        with patch(
            "app.services.course_miniapp_onboarding_service.CourseMiniAppOnboardingService.complete",
            new_callable=AsyncMock,
        ) as complete:
            complete.return_value = {
                "ok": True, "level": "hsk1", "tab": "course",
                "lesson": 1, "foundation_required": False,
            }
            result = await self.client.post(api_url, headers=headers, json=payload)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(complete.await_args.args[0].id, 1)
            self.assertEqual(complete.await_args.kwargs["level"], "hsk1")
            self.assertEqual(complete.await_args.kwargs["language"], "uz")
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(page_url)).status_code, 503)

    def test_pwa_original_onboarding_never_fakes_save_or_uses_shared_draft(self):
        source = (Path("app/static") / "course_v3_onboarding.html").read_text(encoding="utf-8")
        self.assertIn('PWA_ONBOARDING_HOST=location.pathname==="/iphone-pwa/onboarding"', source)
        self.assertIn('"/api/v3/pwa/onboarding"', source)
        self.assertIn('"/api/v3/pwa/onboarding/status?"', source)
        self.assertIn('"/api/v3/pwa/course-tracks"', source)
        self.assertIn('if(!INIT_DATA&&!PWA_ONBOARDING_HOST)', source)
        self.assertIn('if(PWA_ONBOARDING_HOST)return;', source)
        self.assertIn('"X-HSK-PWA-CSRF":actor.csrf', source)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', source)

    def test_pwa_lesson_completion_reuses_one_signed_proof_and_one_xp_award(self):
        source = (Path("app") / "main.py").read_text(encoding="utf-8")
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertEqual(source.count(
            'async def _v3_complete_lesson_for_canonical_actor(',
        ), 1)
        self.assertEqual(source.count(
            'valid_proof = verify_lesson_completion_proof(',
        ), 1)
        self.assertEqual(source.count(
            'activity_ref=f"v3-part:{resolved_level}:{lesson_order}:complete"',
        ), 1)
        self.assertIn('async def v3_course_lesson_complete(request: Request)', source)
        self.assertIn('async def pwa_v3_course_lesson_complete(request: Request)', source)
        self.assertIn('require_same_origin(request, settings)', source)
        self.assertIn('PwaAuthService(session, settings).mutation_actor(', source)
        self.assertIn('get_by_user_id(actor.id, lock=True)', source)
        self.assertIn('return await _v3_complete_lesson_for_canonical_actor(', source)
        self.assertIn('response = await _v3_complete_lesson_for_canonical_actor(', source)
        self.assertIn('"/api/v3/lesson/complete":"/api/v3/pwa/lesson/complete"', course)
        self.assertIn('_apiPost("/api/v3/lesson/complete"', course)
        self.assertIn('completion_proof:LESSON_COMPLETION_PROOF', course)
        self.assertIn('mistakes:(Flow.mistakes||[]).slice(0,50)', course)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', course)

    async def test_pwa_voice_session_text_audio_and_end_keep_canonical_owner(self):
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        start_url = "/api/v3/pwa/voice/session/start"
        msg_url = "/api/v3/pwa/voice/message"
        end_url = "/api/v3/pwa/voice/session/end"
        start_data = {"role": "teacher", "voice": "female"}
        self.assertEqual((await self.client.post(
            start_url, headers={"Origin": ORIGIN}, json=start_data,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            start_url, headers={**headers, "Origin": "https://attacker.invalid"}, json=start_data,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            start_url, headers=headers, json={**start_data, "user_id": 999},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            start_url, headers={**headers, "X-Telegram-Init-Data": "fake"},
            json=start_data,
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            msg_url, headers=headers,
            files={
                "session_id": (None, "voice-1"),
                "telegram_id": (None, "999"),
                "text": (None, "你好"),
            },
        )).status_code, 422)
        with patch(
            "app.services.voice_practice_service.VoicePracticeService.start_session",
            new_callable=AsyncMock,
        ) as start, patch(
            "app.services.voice_practice_service.VoicePracticeService.process_message",
            new_callable=AsyncMock,
        ) as message, patch(
            "app.services.voice_practice_service.VoicePracticeService.end_session",
            new_callable=AsyncMock,
        ) as end, patch(
            "app.services.course_miniapp_analytics_service.CourseMiniAppAnalyticsService.record_server_event",
            new_callable=AsyncMock,
        ) as record:
            start.return_value = {"ok": True, "session_id": "voice-1", "remaining_limit": 2}
            message.return_value = {"ok": True, "chinese_reply": "你好"}
            end.return_value = {"ok": True, "reward": {"xp_awarded": 12}}
            opened = await self.client.post(start_url, headers=headers, json=start_data)
            self.assertEqual(opened.status_code, 200, opened.text)
            self.assertEqual(opened.json()["live_available"], False)
            self.assertEqual(start.await_args.args[0].id, 1)
            self.assertEqual(start.await_args.kwargs["language"], "uz")
            self.assertEqual(start.await_args.kwargs["level"], "hsk1")
            typed = await self.client.post(
                msg_url, headers=headers,
                files={
                    "session_id": (None, "voice-1"),
                    "text": (None, "你好"),
                },
            )
            self.assertEqual(typed.status_code, 200, typed.text)
            self.assertEqual(message.await_args.args[0].id, 1)
            self.assertEqual(message.await_args.kwargs["text"], "你好")
            audio = bytes.fromhex("000000146674797069736f6d") + bytes(1300)
            spoken = await self.client.post(
                msg_url, headers=headers,
                data={"session_id": "voice-1"},
                files={"audio": ("voice.mp4", audio, "audio/mp4")},
            )
            self.assertEqual(spoken.status_code, 200, spoken.text)
            self.assertEqual(message.await_args.args[0].id, 1)
            self.assertEqual(message.await_args.kwargs["audio_bytes"], audio)
            self.assertEqual(message.await_args.kwargs["filename"], "voice.mp4")
            finished = await self.client.post(
                end_url, headers=headers, json={"session_id": "voice-1"},
            )
            self.assertEqual(finished.status_code, 200, finished.text)
            self.assertEqual(finished.json()["reward"]["xp_awarded"], 12)
            self.assertEqual(end.await_args.args[0].id, 1)
            self.assertEqual(record.await_args.kwargs["user_id"], 1)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.post(
            start_url, headers=headers, json=start_data,
        )).status_code, 503)

    async def test_pwa_standalone_voice_keeps_original_page_without_telegram_session(self):
        path = "/iphone-pwa/practice/voice"
        self.assertEqual(
            (await self.client.get(path, follow_redirects=False)).status_code, 303,
        )
        self.assertEqual(
            (await self.client.get("/api/v3/pwa/voice/me")).status_code, 401,
        )
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(path)
        self.assertEqual(page.status_code, 200, page.text[:150])
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        self.assertNotIn("maximum-scale=1", page.text)
        self.assertIn('font-size:16px;line-height:1.35', page.text)
        with patch(
            "app.services.voice_practice_service.VoicePracticeService.user_status",
            new_callable=AsyncMock,
        ) as status:
            status.return_value = {
                "level": "hsk1", "language": "uz", "is_paid": False,
                "remaining_voice_limit": 2,
            }
            result = await self.client.get("/api/v3/pwa/voice/me")
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(status.await_args.args[0].id, 1)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(path)).status_code, 503)

    def test_voice_standalone_ui_uses_pwa_actor_and_real_same_service(self):
        html = (Path("app/static") / "course_v3_voice.html").read_text(encoding="utf-8")
        self.assertIn('PWA_VOICE_HOST=location.pathname==="/iphone-pwa/practice/voice"', html)
        self.assertIn('"/api/v3/pwa/voice/me"', html)
        self.assertIn('"/api/v3/pwa/voice/session/start"', html)
        self.assertIn('"/api/v3/pwa/voice/message"', html)
        self.assertIn('"/api/v3/pwa/voice/session/end"', html)
        self.assertIn('voiceMessage(fd).then(jr)', html)
        self.assertIn('voicePost("/api/voice-practice/session/start"', html)
        self.assertIn('voicePost("/api/voice-practice/session/end"', html)
        self.assertIn('delete payload.initData;delete payload.user_id;delete payload.telegram_id;', html)
        self.assertIn('fields.append("session_id",sid)', html)
        self.assertIn('"X-HSK-PWA-CSRF":s.csrf', html)
        self.assertIn('if(!PWA_VOICE_HOST&&window.CourseAds&&CourseAds.showLimitPromo)', html)

    def test_voice_inline_ui_uses_only_authenticated_browser_transport(self):
        html = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('"/api/voice-practice/session/start":"/api/v3/pwa/voice/session/start"', html)
        self.assertIn('"/api/voice-practice/session/end":"/api/v3/pwa/voice/session/end"', html)
        self.assertIn('function courseVoiceMessage(fd)', html)
        self.assertIn('"/api/v3/pwa/voice/message"', html)
        self.assertIn('fields.append("session_id",sessionId)', html)
        self.assertIn('headers:{"X-HSK-PWA-CSRF":actor.csrf}', html)
        self.assertIn('_apiPost("/api/voice-practice/session/start"', html)
        self.assertIn('courseVoiceMessage(fd).then(jr)', html)
        self.assertIn('_apiPost("/api/voice-practice/session/end"', html)
        self.assertIn('if(!PWA_COURSE_HOST&&window.CourseAds&&CourseAds.showLimitPromo)', html)

    async def test_pwa_checkout_reuses_original_receipts_and_account_ownership(self):
        url = "/iphone-pwa/checkout"
        self.assertEqual((await self.client.get(
            url, follow_redirects=False,
        )).status_code, 303)
        self.assertEqual((await self.client.post(
            "/api/v3/pwa/subscription/quote", headers={"Origin": ORIGIN},
            json={"plan_type": "1_month", "payment_method": "visa"},
        )).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        page = await self.client.get(url)
        self.assertEqual(page.status_code, 200, page.text[:200])
        self.assertIn("HSK AI Pro", page.text)
        self.assertEqual(page.headers.get("cache-control"), "no-store")
        self.assertEqual(page.headers.get("x-frame-options"), "DENY")
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        quote_url = "/api/v3/pwa/subscription/quote"
        order = {"plan_type": "1_month", "payment_method": "visa"}
        self.assertEqual((await self.client.post(
            quote_url, headers={"Origin": ORIGIN}, json=order,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            quote_url, headers={**headers, "Origin": "https://attacker.example"},
            json=order,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            quote_url, headers=headers, json={**order, "user_id": 2},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            quote_url, headers={**headers, "X-Telegram-Init-Data": "fake"}, json=order,
        )).status_code, 422)
        with patch(
            "app.services.subscription_miniapp_service.SubscriptionMiniAppService.overview",
            new_callable=AsyncMock,
        ) as overview, patch(
            "app.services.subscription_miniapp_service.SubscriptionMiniAppService.quote",
            new_callable=AsyncMock,
        ) as quote, patch(
            "app.services.subscription_miniapp_service.SubscriptionMiniAppService.submit",
            new_callable=AsyncMock,
        ) as submit, patch(
            "app.services.subscription_entry_analytics_service.SubscriptionEntryAnalyticsService.record_entry",
            new_callable=AsyncMock,
        ) as entry, patch(
            "app.services.conversion_funnel_service.ConversionFunnelService.record",
            new_callable=AsyncMock,
        ) as funnel, patch(
            "app.repositories.payment_repo.PaymentRepository.get_by_id",
            new_callable=AsyncMock,
        ) as payment:
            overview.return_value = {"ok": True, "mode": "subscription", "pending_payment": None}
            quote.return_value = {"ok": True, "quote": {"pay_amount": 89, "pay_currency": "TJS"}}
            submit.return_value = {
                "ok": True, "status": "pending", "payment_id": 77,
                "provisional_access": False,
            }
            entry.return_value = True
            funnel.return_value = True
            payment.return_value = SimpleNamespace(
                id=77, payment_status="pending", plan_type="1_month",
            )
            ctx = {
                "mode": "subscription", "source": "v3_paywall",
                "plan": "1_month", "attempt_id": "sub-1000-abc",
            }
            opened = await self.client.post(
                "/api/v3/pwa/subscription/overview", headers=headers, json=ctx,
            )
            self.assertEqual(opened.status_code, 200, opened.text)
            self.assertEqual(overview.await_args.args[0].id, 1)
            self.assertIs(overview.await_args.kwargs["bot"], self.receipt_bot)
            self.assertEqual(entry.await_args.kwargs["user"].id, 1)
            self.assertEqual(funnel.await_args.kwargs["user"].id, 1)
            quoted = await self.client.post(quote_url, headers=headers, json={**ctx, **order})
            self.assertEqual(quoted.status_code, 200, quoted.text)
            self.assertEqual(quote.await_args.kwargs["telegram_id"].id, 1)
            self.assertEqual(quoted.json()["quote"]["pay_amount"], 89)
            submitted = await self.client.post(
                "/api/v3/pwa/subscription/submit", headers=headers,
                json={**ctx, **order, "screenshot_data_url": "data:image/png;base64,aGVsbG8="},
            )
            self.assertEqual(submitted.status_code, 200, submitted.text)
            self.assertEqual(submit.await_args.kwargs["telegram_id"].id, 1)
            self.assertIs(submit.await_args.kwargs["bot"], self.receipt_bot)
            self.assertEqual(submit.await_args.kwargs["source"], "iphone_pwa")
            self.assertEqual(submitted.json()["payment_id"], 77)
            checked = await self.client.post(
                "/api/v3/pwa/subscription/payment-status", headers=headers,
                json={"payment_id": 77},
            )
            self.assertEqual(checked.status_code, 200, checked.text)
            self.assertEqual(payment.await_args.kwargs["actor"].id, 1)
            self.assertEqual(checked.json()["status"], "pending")
            self.assertEqual((await self.client.post(
                "/api/v3/pwa/subscription/payment-status", headers=headers,
                json={"payment_id": 77, "user_id": 2},
            )).status_code, 422)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.get(url)).status_code, 503)

    async def test_pwa_checkout_stage_event_requires_same_owner_opened_attempt(self):
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        url = "/api/v3/pwa/subscription/event"
        payload = {
            "attempt_id": "sub-111-a1b2c3", "stage": "payment_receipt_selected",
            "source": "iphone_pwa", "mode": "subscription",
            "plan_type": "1_month", "payment_method": "visa",
        }
        self.assertEqual((await self.client.post(
            url, headers={"Origin": ORIGIN}, json=payload,
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={**payload, "user_id": 1},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            url, headers=headers, json={**payload, "attempt_id": "bad';--"},
        )).status_code, 422)
        async with self.sessions() as db:
            db.add(user(2, 1002))
            db.add(ConversionFunnelEvent(
                user_id=2, telegram_id=1002,
                event_name="checkout_opened", source="iphone_pwa",
                payload_json=json.dumps({"attempt_id": "sub-111-a1b2c3", "mode": "subscription"}),
            ))
            await db.commit()
        self.assertEqual((await self.client.post(
            url, headers=headers, json=payload,
        )).status_code, 409)
        async with self.sessions() as db:
            db.add(ConversionFunnelEvent(
                user_id=1, telegram_id=1001,
                event_name="checkout_opened", source="iphone_pwa",
                payload_json=json.dumps({"attempt_id": "sub-111-a1b2c3", "mode": "subscription"}),
            ))
            await db.commit()
        with patch(
            "app.services.conversion_funnel_service.ConversionFunnelService.record",
            new_callable=AsyncMock,
        ) as record:
            record.return_value = True
            response = await self.client.post(url, headers=headers, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["ok"])
            self.assertEqual(record.await_args.kwargs["user"].id, 1)
            self.assertEqual(record.await_args.kwargs["payload"]["stage"], "payment_receipt_selected")

    def test_home_screen_resume_revalidates_server_actor_in_existing_pages(self):
        pages = {
            "course-v3.html": ("PWA_COURSE_HOST", "PWA_COURSE_ACTOR_PROMISE", "pwaCourseActor"),
            "subscription.html": ("PWA_CHECKOUT_HOST", "PWA_CHECKOUT_PROMISE", "checkoutPwaActor"),
            "course_v3_voice.html": ("PWA_VOICE_HOST", "PWA_VOICE_PROMISE", "voicePwaActor"),
            "course_v3_recognition.html": ("PWA_RECOGNITION_HOST", "PWA_RECOGNITION_PROMISE", "recognitionPwaSession"),
            "course_v3_memorize.html": ("PWA_MEMORIZE_HOST", "PWA_MEMORIZE_PROMISE", "memorizePwaSession"),
            "course_v3_pronunciation.html": ("PWA_PRONUNCIATION_HOST", "PWA_PRONUNCIATION_PROMISE", "pronunciationPwaSession"),
            "course_v3_mistakes.html": ("PWA_MISTAKES_HOST", "PWA_MISTAKES_PROMISE", "mistakesPwaSession"),
            "course_v3_test.html": ("PWA_TEST_HOST", "PWA_TEST_PROMISE", "testPwaActor"),
            "course_v3_onboarding.html": ("PWA_ONBOARDING_HOST", "PWA_ONBOARDING_PROMISE", "onboardingPwaActor"),
        }
        for name, (host, cache, verifier) in pages.items():
            with self.subTest(page=name):
                html = (Path("app/static") / name).read_text(encoding="utf-8")
                self.assertIn('function verifyPwaReturn(){', html)
                self.assertIn(f'  if(!{host})return;', html)
                self.assertIn(f'  {cache}=null;', html)
                self.assertIn(f'  {verifier}().catch(function(){{location.replace("/iphone-pwa")}});', html)
                self.assertIn('window.addEventListener("pageshow",function(ev){if(ev.persisted)verifyPwaReturn()})', html)
                self.assertIn('document.visibilityState==="visible"', html)
                self.assertNotIn("user-scalable=no", html)

    def test_ios_pwa_text_focus_does_not_disable_pinch_or_legacy_ui(self):
        targets = {
            "course-v3.html": "PWA_COURSE_HOST",
            "subscription.html": "PWA_CHECKOUT_HOST",
            "course_v3_voice.html": "PWA_VOICE_HOST",
            "course_v3_onboarding.html": "PWA_ONBOARDING_HOST",
        }
        for name, flag in targets.items():
            with self.subTest(page=name):
                html = (Path("app/static") / name).read_text(encoding="utf-8")
                self.assertIn(f'if({flag})document.documentElement.classList.add("hsk-pwa-browser");', html)
                self.assertIn('html.hsk-pwa-browser textarea,html.hsk-pwa-browser select{font-size:16px!important}', html)
                self.assertIn('name="viewport"', html)
                self.assertNotIn("user-scalable=no", html)
                self.assertNotIn("maximum-scale=1", html)
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn("touch-action:manipulation", course)
        standalone_voice = (Path("app/static") / "course_v3_voice.html").read_text(encoding="utf-8")
        self.assertIn(".kb textarea{", standalone_voice)

    def test_browser_practice_pro_ctas_use_shared_checkout_with_safe_return(self):
        """Server-owned Pro paths are reachable without a fake Telegram actor."""
        checkout = Path("app/static/subscription.html").read_text(encoding="utf-8")
        course = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        cases = [
            ("course_v3_recognition.html", "PWA_RECOGNITION_HOST", "goPremium", "v3_recognition_limit"),
            ("course_v3_memorize.html", "PWA_MEMORIZE_HOST", "goPremium", "v3_memorize_limit"),
            ("course_v3_pronunciation.html", "PWA_PRONUNCIATION_HOST", "goPremium", "v3_pronunciation_limit"),
            ("course_v3_mistakes.html", "PWA_MISTAKES_HOST", "goPay", "v3_mistake_review"),
            ("course_v3_test.html", "PWA_TEST_HOST", "goPremium", "v3_test_limit"),
            ("course_v3_voice.html", "PWA_VOICE_HOST", "goPremium", "v3_voice_limit"),
        ]
        self.assertIn('const RETURN_TO_COURSE=PARAMS.get("return_to")==="course"', checkout)
        self.assertIn('return map[requestedPage]+"?"+query.toString()', checkout)
        for filename, host, handler, source in cases:
            with self.subTest(page=filename):
                html = (Path("app/static") / filename).read_text(encoding="utf-8")
                self.assertIn(
                    f'function {handler}(){{location.href=({host}?"/iphone-pwa/checkout":"/subscription.html")+"?lang="+LANG',
                    html,
                )
                self.assertIn(f'&source={source}&', html)
                self.assertIn(f'&return_page={filename}&', html)
                self.assertIn(f'"{filename}":"/iphone-pwa/practice/', checkout)
                self.assertNotIn(f'if({host}){{goBack();return}}', html)
                self.assertNotIn(f'({host}?', html.split("function showLimitNow(){")[1].split("\n}")[0] if "function showLimitNow(){" in html else "")
        mistakes = Path("app/static/course_v3_mistakes.html").read_text(encoding="utf-8")
        standalone_voice = Path("app/static/course_v3_voice.html").read_text(encoding="utf-8")
        self.assertIn('$("lim-btn").hidden=false;', mistakes)
        self.assertIn('$("pwb").hidden=false;', standalone_voice)
        for expression in (
            'function premium(){App.goPay("v3_mistake_review")}',
            'function premium(){App.goPay("v3_test_limit")}',
            'function goPremium(){App.goPay("v3_voice_limit")}',
            '$("pwb").hidden=false;',
        ):
            self.assertIn(expression, course)
        self.assertNotIn('hidden=PWA_COURSE_HOST', course)
        self.assertNotIn('if(window.CourseAds&&CourseAds.showLimitPromo){', course)
        self.assertGreaterEqual(course.count('if(!PWA_COURSE_HOST&&window.CourseAds&&CourseAds.showLimitPromo){'), 5)
        self.assertIn('PWA_COURSE_HOST?"/iphone-pwa/checkout":"/subscription.html"', course)

    def test_existing_checkout_ui_never_enters_fake_pwa_preview(self):
        html = (Path("app/static") / "subscription.html").read_text(encoding="utf-8")
        course = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('PWA_CHECKOUT_HOST=location.pathname==="/iphone-pwa/checkout"', html)
        self.assertIn('preview:!INIT_DATA&&!PWA_CHECKOUT_HOST', html)
        self.assertIn('if(!INIT_DATA&&!PWA_CHECKOUT_HOST){', html)
        self.assertIn('if(PWA_CHECKOUT_HOST)return "";', html)
        self.assertIn('"/api/v3/pwa/subscription/submit"', html)
        self.assertIn('"/api/v3/pwa/subscription/payment-status"', html)
        self.assertIn('"X-HSK-PWA-CSRF":actor.csrf', html)
        self.assertIn('const response=await checkoutTransport(API.event', html)
        self.assertIn('"/iphone-pwa/practice/voice"', html)
        self.assertIn('PWA_COURSE_HOST?"/iphone-pwa/checkout":"/subscription.html"', course)

    async def test_pwa_language_updates_canonical_learner_only_with_csrf(self):
        path = "/api/v3/pwa/language"
        self.assertEqual((await self.client.post(
            path, headers={"Origin": ORIGIN}, json={"language": "tj"},
        )).status_code, 401)
        state = await self.begin()
        await self.callback(state)
        csrf = (await self.client.get("/api/v3/pwa-auth/session")).json()["csrf"]
        headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf}
        self.assertEqual((await self.client.post(
            path, headers={"Origin": ORIGIN}, json={"language": "tj"},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            path, headers={**headers, "Origin": "https://not-us.example"},
            json={"language": "tj"},
        )).status_code, 403)
        self.assertEqual((await self.client.post(
            path, headers=headers, json={"language": "tg"},
        )).status_code, 422)
        self.assertEqual((await self.client.post(
            path, headers=headers, json={"language": "tj", "user_id": 999},
        )).status_code, 422)
        response = await self.client.post(
            path, headers=headers, json={"language": "tj"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"ok": True, "language": "tj"})
        async with self.sessions() as db:
            owner = await db.get(User, 1)
            self.assertEqual(owner.language, "tj")
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.client.post(
            path, headers=headers, json={"language": "uz"},
        )).status_code, 503)

    def test_original_language_picker_uses_same_pwa_session_and_preserves_telegram(self):
        page = (Path("app/static") / "course-v3.html").read_text(encoding="utf-8")
        self.assertIn('"/api/v3/language":"/api/v3/pwa/language"', page)
        self.assertIn('if(!INIT_DATA&&!PWA_COURSE_HOST)return;', page)
        self.assertIn('_apiPost("/api/v3/language",{language:l})', page)
        self.assertIn('"X-HSK-PWA-CSRF":actor.csrf', page)

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
        self.assertIn('"/course_v3_recognition.html":"/iphone-pwa/practice/recognition"', course)
        self.assertIn("src=safePaths[path]+target.search;", course)
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

    async def test_pwa_only_rollback_fences_existing_sessions_without_account_deletion(self):
        """Feature OFF must close both browser HTML and API routes, not Telegram.

        Turning it back ON in an isolated test preserves the canonical user's
        existing verified session and progress ownership; no database cleanup
        or native/Telegram token invalidation is a legitimate PWA rollback.
        """
        state = await self.begin()
        await self.callback(state)
        session_url = "/api/v3/pwa-auth/session"
        actor = (await self.client.get(session_url)).json()
        self.assertEqual(actor["user_id"], 1)
        paths = (
            "/iphone-pwa",
            "/iphone-pwa/manifest.webmanifest",
            "/iphone-pwa/course",
            "/iphone-pwa/practice/recognition",
            "/iphone-pwa/practice/memorize",
            "/iphone-pwa/practice/pronunciation",
            "/iphone-pwa/practice/mistakes",
            "/iphone-pwa/practice/test",
            "/iphone-pwa/practice/voice",
            "/iphone-pwa/onboarding",
            "/api/v3/pwa/account-notices",
        )
        for url in paths:
            with self.subTest(enabled=url):
                result = await self.client.get(url, follow_redirects=False)
                self.assertEqual(result.status_code, 200, (url, result.text[:160]))

        self.settings.PWA_AUTH_ENABLED = False
        for url in (session_url, *paths, "/api/v3/pwa/notifications"):
            with self.subTest(disabled=url):
                result = await self.client.get(url, follow_redirects=False)
                self.assertEqual(result.status_code, 503, (url, result.text[:160]))
                self.assertEqual(result.headers.get("cache-control"), "no-store")

        csrf_headers = {"Origin": ORIGIN, "X-HSK-PWA-CSRF": actor["csrf"]}
        forbidden = await self.client.post(
            "/api/v3/pwa/practice/daily-gate",
            headers=csrf_headers,
            json={"feature": "recognition", "ref": "rollback-must-not-consume"},
        )
        self.assertEqual(forbidden.status_code, 503, forbidden.text)
        no_logout = await self.client.post(
            "/api/v3/pwa-auth/logout", headers=csrf_headers,
        )
        self.assertEqual(no_logout.status_code, 503, no_logout.text)
        # Legacy Telegram API is still protected by signed initData, not by
        # the browser feature flag or a valid PWA cookie.
        legacy = await self.client.post(
            "/api/v3/practice/daily-gate",
            json={"feature": "recognition", "ref": "rollback-legacy"},
        )
        self.assertEqual(legacy.status_code, 401, legacy.text)

        self.settings.PWA_AUTH_ENABLED = True
        restored = await self.client.get(session_url)
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["user_id"], 1)
        self.assertEqual(restored.json()["csrf"], actor["csrf"])
        async with self.sessions() as db:
            original = await db.get(User, 1)
            self.assertEqual((original.telegram_id, original.status), (1001, "free"))
            self.assertIsNotNone(await db.scalar(
                select(UserIdentity.id).where(UserIdentity.user_id == 1)
            ))

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

    def test_login_bfcache_rechecks_server_cookie_and_recovers_disabled_provider(self):
        """A restored Safari login page cannot keep a stale auth or disabled UI."""
        import subprocess

        script = r"""
const fs = require("fs");
const vm = require("vm");
const handlers = {};
const elements = {};
function el(id) {
  if (!elements[id]) elements[id] = {
    textContent: "", value: "", hidden: false, disabled: false,
    addEventListener() {}, setAttribute() {}, removeAttribute() {},
  };
  return elements[id];
}
const buttons = ["telegram", "google", "apple"].map(provider => ({
  dataset: {provider}, hidden: false, disabled: false,
  addEventListener() {},
}));
el("actions").querySelectorAll = () => buttons;
let signedIn = false;
let sessionReads = 0;
let providerReads = 0;
const redirects = [];
async function fakeFetch(path) {
  if (path === "/api/v3/pwa-auth/session") {
    sessionReads++;
    return signedIn
      ? {ok: true, json: async () => ({ok: true, user_id: 1, language: "uz", csrf: "test-csrf"})}
      : {ok: false, json: async () => ({ok: false, error: "pwa_session_required"})};
  }
  if (path === "/api/v3/pwa-auth/providers") {
    providerReads++;
    return {ok: true, json: async () => ({ok: true, providers: ["google", "apple"]})};
  }
  throw new Error("Unexpected request: " + path);
}
const document = {
  getElementById: el,
  documentElement: {lang: "uz"},
  visibilityState: "visible",
  addEventListener() {},
};
const window = {
  addEventListener(name, callback) {handlers[name] = callback;},
  setInterval: () => 1,
  clearInterval() {},
  HSKCharacters: null,
};
const location = {
  search: "", href: "https://example.test/iphone-pwa",
  replace(url) {redirects.push(url);}, assign() {},
};
const saved = new Map();
const sessionStorage = {
  getItem: key => saved.get(key) || null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: key => saved.delete(key),
};
vm.runInNewContext(fs.readFileSync("app/static/iphone-pwa-login.js", "utf8"), {
  window, document, location, fetch: fakeFetch, sessionStorage,
  URL, URLSearchParams, console,
});
const settle = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  await settle();
  // Simulate Safari retaining disabled controls after an external redirect.
  buttons[0].disabled = true;
  handlers.pageshow({persisted: false});
  await settle();
  const initialReads = sessionReads;
  handlers.pageshow({persisted: true});
  await settle();
  const telegramRecovered = !buttons[0].disabled;
  signedIn = true;
  handlers.pageshow({persisted: true});
  await settle();
  process.stdout.write(JSON.stringify({
    initialReads, sessionReads, providerReads, telegramRecovered,
    redirects, actionsHidden: elements.actions.hidden,
  }));
})().catch(error => {console.error(error); process.exit(1);});
"""
        result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
        self.assertEqual(result["initialReads"], 1)
        self.assertEqual(result["sessionReads"], 3)
        self.assertGreaterEqual(result["providerReads"], 2)
        self.assertTrue(result["telegramRecovered"])
        self.assertEqual(result["redirects"], ["/iphone-pwa/course"])
        self.assertTrue(result["actionsHidden"])

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
