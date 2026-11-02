"""Security contract for PWA-only OAuth session, no native/Telegram bypass."""

import unittest
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.native_oauth import create_native_oauth_router
from app.api.pwa_auth import create_pwa_auth_router
from app.db.base import Base
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
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
