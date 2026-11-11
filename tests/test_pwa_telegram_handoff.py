"""Telegram Mini App -> learner PWA one-time handoff: security contract.

Contract: docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md and
openspec/changes/telegram-miniapp-pwa-android-handoff/specs/pwa-telegram-handoff.
Real ASGI routes and SQL; only Telegram's signature is produced locally with
the test bot token.
"""
import asyncio
import hashlib
import hmac
import json
import os
import re
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.pwa_auth import create_pwa_auth_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.services.desktop_app_promo_settings_service import save_desktop_app_promo_settings
from app.services.desktop_auth_service import (
    MINIAPP_HANDOFF_FLOW, DesktopAuthError, DesktopAuthService,
)
from app.services.pwa_auth_service import (
    PWA_HANDOFF_RATE_LIMIT_COUNT, PWA_HANDOFF_TTL_SECONDS, PWA_SESSION_COOKIE,
    PwaAuthError, PwaAuthService,
)
from tests.native_postgres_deadlines import postgres_timeout

ORIGIN = "https://hskai.example.test"
BOT_TOKEN = "123456789:AAExampleBotTokenForInitDataSigning1234"


def settings(**kwargs):
    values = dict(
        PWA_AUTH_ENABLED=True,
        PUBLIC_SITE_URL=ORIGIN,
        OAUTH_REDIRECT_BASE_URL=ORIGIN,
        DESKTOP_AUTH_SIGNING_SECRET="pwa-handoff-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        BOT_USERNAME="pomp_test_bot",
        BOT_TOKEN=BOT_TOKEN,
        GOOGLE_OAUTH_ENABLED=False,
        APPLE_OAUTH_ENABLED=False,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def learner(uid, telegram_id, **kwargs):
    values = dict(
        id=uid, telegram_id=telegram_id, full_name="Learner", language="uz",
        level="hsk1", learning_mode="course", voice_mode="none", status="free",
        payment_status="none", question_limit=5, questions_used=0,
        bonus_questions=0, bonus_questions_used=0, discount_referral_count=0,
        discount_eligible=False, discount_used=False, daily_practice_streak=0,
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    values.update(kwargs)
    return User(**values)


def init_data(telegram_id, *, bot_token=BOT_TOKEN, age_seconds=0):
    params = {
        "auth_date": str(int(time.time()) - age_seconds),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps({"id": telegram_id, "first_name": "T"}, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


class HandoffFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = settings()
        self.engine = await self.make_engine()
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([learner(1, 1001), learner(2, 2002)])
            await db.commit()
        await self.routing(True)
        self.app = FastAPI()
        self.app.include_router(create_pwa_auth_router(
            session_factory=self.sessions, settings_obj=self.settings,
        ))
        self.browser = self.new_browser()
        self.miniapp = self.new_browser()

    async def make_engine(self):
        return create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)

    async def asyncTearDown(self):
        await self.browser.aclose()
        await self.miniapp.aclose()
        await self.engine.dispose()

    def new_browser(self):
        client = AsyncClient(transport=ASGITransport(app=self.app), base_url=ORIGIN)
        self.addAsyncCleanup(client.aclose)
        return client

    async def routing(self, enabled):
        async with self.sessions() as db:
            await save_desktop_app_promo_settings(db, {"platforms": {
                "macos": True, "windows": True, "android": True, "ios": enabled}})
            await db.commit()

    async def start(self, telegram_id=1001, *, headers=None, body=None):
        return await self.miniapp.post(
            "/api/v3/pwa-auth/handoff/start",
            headers=headers if headers is not None else {
                "X-Telegram-Init-Data": init_data(telegram_id)},
            json=body if body is not None else {"language": "uz", "source": "home_prompt"},
        )

    async def secret(self, telegram_id=1001):
        response = await self.start(telegram_id)
        self.assertEqual(response.status_code, 200, response.text)
        fragment = urlsplit(response.json()["url"]).fragment
        return dict(item.split("=", 1) for item in fragment.split("&"))["t"]

    async def redeem(self, token, *, browser=None, switch=None, origin=ORIGIN):
        body = {"token": token}
        if switch is not None:
            body["switch"] = switch
        return await (browser or self.browser).post(
            "/api/v3/pwa-auth/handoff/redeem",
            headers={"Origin": origin} if origin else {}, json=body,
        )

    async def session_user(self, browser=None):
        response = await (browser or self.browser).get("/api/v3/pwa-auth/session")
        return response.json().get("user_id") if response.status_code == 200 else None

    async def count(self, model, *where):
        async with self.sessions() as db:
            return await db.scalar(select(func.count()).select_from(model).where(*where))

    async def live_sessions(self):
        return await self.count(DesktopSession, DesktopSession.revoked_at.is_(None))


class HandoffIssueTests(HandoffFixture):
    async def test_only_fresh_signed_telegram_data_can_start(self):
        for headers in (
            {},
            {"X-Telegram-Init-Data": "user=%7B%22id%22%3A1001%7D&auth_date=1&hash=00"},
            {"X-Telegram-Init-Data": init_data(1001, bot_token="987654321:" + "B" * 35)},
            {"X-Telegram-Init-Data": init_data(1001, age_seconds=3 * 3600)},
        ):
            response = await self.start(headers=headers)
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.json()["error"], "invalid_telegram_init_data")
        self.assertEqual(await self.count(DesktopLinkRequest), 0)

    async def test_client_cannot_choose_the_account(self):
        for body in ({"user_id": 2}, {"telegram_id": 2002}, {"language": "uz", "token": "x" * 40}):
            response = await self.start(1001, body=body)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self.count(DesktopLinkRequest), 0)

    async def test_issued_link_carries_only_a_fragment_secret(self):
        response = await self.start()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        payload = response.json()
        self.assertEqual(set(payload), {"ok", "url", "expires_in"})
        self.assertEqual(payload["expires_in"], PWA_HANDOFF_TTL_SECONDS)
        self.assertLessEqual(PWA_HANDOFF_TTL_SECONDS, 120)
        url = urlsplit(payload["url"])
        self.assertEqual((url.scheme + "://" + url.netloc, url.path, url.query),
                         (ORIGIN, "/iphone-pwa/handoff", ""))
        fragment = dict(item.split("=", 1) for item in url.fragment.split("&"))
        self.assertEqual(set(fragment), {"t", "lang"})
        self.assertEqual(fragment["lang"], "uz")
        self.assertGreaterEqual(len(fragment["t"]), 43)
        for forbidden in ("1001", "user", "cookie", "session"):
            self.assertNotIn(forbidden, payload["url"].replace("hskai.example.test", ""))
        async with self.sessions() as db:
            row = (await db.execute(select(DesktopLinkRequest))).scalar_one()
        self.assertEqual(
            (row.platform, row.flow, row.intent, row.status, row.approved_user_id,
             row.approved_telegram_id, row.language),
            ("pwa", MINIAPP_HANDOFF_FLOW, "signin", "approved", 1, 1001, "uz"))
        self.assertIsNone(row.consumed_at)
        lifetime = (row.expires_at.replace(tzinfo=timezone.utc)
                    - row.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        self.assertLessEqual(lifetime, PWA_HANDOFF_TTL_SECONDS + 2)
        # Only a keyed hash is at rest.
        for stored in (row.polling_secret_hash, row.display_code_hash,
                       row.installation_key_hash, row.id):
            self.assertNotIn(fragment["t"], stored)
        self.assertNotEqual(
            row.polling_secret_hash,
            hashlib.sha256(fragment["t"].encode()).hexdigest())
        # Starting creates no device, session or cookie.
        self.assertEqual(await self.count(DesktopSession), 0)
        self.assertEqual(await self.count(DesktopDevice), 0)
        self.assertNotIn("set-cookie", response.headers)

    async def test_gates_block_new_handoffs(self):
        await self.routing(False)
        off = await self.start()
        self.assertEqual((off.status_code, off.json()["error"]), (403, "pwa_handoff_unavailable"))
        await self.routing(True)
        self.settings.PWA_AUTH_ENABLED = False
        disabled = await self.start()
        self.assertEqual(disabled.status_code, 503)
        self.settings.PWA_AUTH_ENABLED = True
        unknown = await self.start(9999)
        self.assertEqual((unknown.status_code, unknown.json()["error"]),
                         (403, "pwa_handoff_user_unavailable"))
        async with self.sessions() as db:
            (await db.get(User, 1)).status = "blocked"
            await db.commit()
        blocked = await self.start()
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(await self.count(DesktopLinkRequest), 0)

    async def test_newest_link_wins_and_issuing_is_rate_limited(self):
        first = await self.secret()
        second = await self.secret()
        self.assertNotEqual(first, second)
        self.assertEqual((await self.redeem(first)).status_code, 401)
        self.assertIsNone(await self.session_user())
        self.assertEqual((await self.redeem(second)).status_code, 200)
        for _ in range(PWA_HANDOFF_RATE_LIMIT_COUNT - 2):
            self.assertEqual((await self.start()).status_code, 200)
        limited = await self.start()
        self.assertEqual((limited.status_code, limited.json()["error"]),
                         (429, "pwa_handoff_rate_limited"))
        # Another learner is not affected by this learner's limit.
        self.assertEqual((await self.start(2002)).status_code, 200)

    async def test_handoffs_do_not_consume_the_public_sign_in_limiter(self):
        self.settings.DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_COUNT = 2
        for _ in range(3):
            self.assertEqual((await self.start()).status_code, 200)
        started = await self.browser.post(
            "/api/v3/pwa-auth/telegram/start", headers={"Origin": ORIGIN}, json={})
        self.assertEqual(started.status_code, 200, started.text)


class HandoffRedeemTests(HandoffFixture):
    async def test_valid_link_signs_in_once(self):
        token = await self.secret()
        response = await self.redeem(token)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"ok": True, "status": "complete"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        cookie = response.headers["set-cookie"]
        self.assertIn(PWA_SESSION_COOKIE + "=", cookie)
        for attribute in ("HttpOnly", "Secure", "Path=/", "SameSite=lax"):
            self.assertIn(attribute, cookie)
        self.assertNotIn(token, response.text)
        self.assertEqual(await self.session_user(), 1)
        async with self.sessions() as db:
            row = (await db.execute(select(DesktopLinkRequest))).scalar_one()
            self.assertEqual(row.status, "consumed")
            self.assertIsNotNone(row.consumed_at)
        # Replay from the same and from another browser.
        other = self.new_browser()
        for browser in (self.browser, other):
            replay = await self.redeem(token, browser=browser)
            self.assertEqual((replay.status_code, replay.json()["error"]),
                             (401, "pwa_handoff_invalid"))
            self.assertNotIn("set-cookie", replay.headers)
        self.assertIsNone(await self.session_user(other))
        self.assertEqual(await self.count(DesktopSession), 1)
        self.assertEqual(await self.count(DesktopDevice), 1)

    async def test_wrong_transport_is_refused_before_lookup(self):
        token = await self.secret()
        for origin in (None, "https://evil.example.test", "null"):
            response = await self.redeem(token, origin=origin)
            self.assertEqual((response.status_code, response.json()["error"]),
                             (403, "pwa_origin_invalid"))
        form = await self.browser.post(
            "/api/v3/pwa-auth/handoff/redeem", headers={"Origin": ORIGIN},
            data={"token": token})
        self.assertEqual(form.status_code, 415)
        for body in ({"token": token, "user_id": 2}, {"token": "short"}, {"token": 5},
                     {"token": token, "switch": "yes"}, {}):
            response = await self.browser.post(
                "/api/v3/pwa-auth/handoff/redeem", headers={"Origin": ORIGIN}, json=body)
            self.assertEqual(response.status_code, 422, body)
        query = await self.browser.get("/api/v3/pwa-auth/handoff/redeem", params={"token": token})
        self.assertEqual(query.status_code, 405)
        self.assertIsNone(await self.session_user())
        # None of the refusals burned the link.
        self.assertEqual((await self.redeem(token)).status_code, 200)

    async def test_unknown_and_expired_links_issue_nothing(self):
        unknown = await self.redeem("A" * 43)
        self.assertEqual((unknown.status_code, unknown.json()["error"]), (401, "pwa_handoff_invalid"))
        token = await self.secret()
        async with self.sessions() as db:
            row = (await db.execute(select(DesktopLinkRequest))).scalar_one()
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        expired = await self.redeem(token)
        self.assertEqual((expired.status_code, expired.json()["error"]), (410, "pwa_handoff_expired"))
        self.assertNotIn("set-cookie", expired.headers)
        self.assertEqual(await self.count(DesktopSession), 0)

    async def test_owner_state_is_rechecked_at_redeem(self):
        blocked_token = await self.secret(1001)
        async with self.sessions() as db:
            (await db.get(User, 1)).status = "blocked"
            await db.commit()
        blocked = await self.redeem(blocked_token)
        self.assertEqual((blocked.status_code, blocked.json()["error"]),
                         (403, "pwa_handoff_owner_invalid"))
        moved_token = await self.secret(2002)
        async with self.sessions() as db:
            (await db.get(User, 2)).telegram_id = 2999
            await db.commit()
        moved = await self.redeem(moved_token)
        self.assertEqual(moved.status_code, 403)
        self.assertEqual(await self.count(DesktopSession), 0)
        self.assertIsNone(await self.session_user())

    async def test_switch_off_stops_redemption_but_not_existing_sessions(self):
        self.assertEqual((await self.redeem(await self.secret())).status_code, 200)
        pending = await self.secret()
        await self.routing(False)
        other = self.new_browser()
        refused = await self.redeem(pending, browser=other)
        self.assertEqual((refused.status_code, refused.json()["error"]),
                         (403, "pwa_handoff_unavailable"))
        self.assertIsNone(await self.session_user(other))
        self.assertEqual(await self.session_user(), 1)

    async def test_same_learner_keeps_the_session_and_burns_the_link(self):
        self.assertEqual((await self.redeem(await self.secret())).status_code, 200)
        before = self.browser.cookies.get(PWA_SESSION_COOKIE)
        token = await self.secret()
        again = await self.redeem(token)
        self.assertEqual(again.status_code, 200, again.text)
        self.assertNotIn("set-cookie", again.headers)
        self.assertEqual(self.browser.cookies.get(PWA_SESSION_COOKIE), before)
        self.assertEqual(await self.count(DesktopSession), 1)
        self.assertEqual((await self.redeem(token, browser=self.new_browser())).status_code, 401)

    async def test_other_account_is_never_replaced_silently(self):
        self.assertEqual((await self.redeem(await self.secret(2002))).status_code, 200)
        self.assertEqual(await self.session_user(), 2)
        second_device = self.new_browser()
        self.assertEqual(
            (await self.redeem(await self.secret(2002), browser=second_device)).status_code, 200)
        before = self.browser.cookies.get(PWA_SESSION_COOKIE)
        token = await self.secret(1001)
        for switch in (None, False):
            mismatch = await self.redeem(token, switch=switch)
            self.assertEqual((mismatch.status_code, mismatch.json()["error"]),
                             (409, "pwa_handoff_account_mismatch"))
            self.assertNotIn("set-cookie", mismatch.headers)
        self.assertEqual(self.browser.cookies.get(PWA_SESSION_COOKIE), before)
        self.assertEqual(await self.session_user(), 2)
        self.assertEqual(await self.live_sessions(), 2)
        # The person explicitly chooses to switch: the same link still works.
        switched = await self.redeem(token, switch=True)
        self.assertEqual(switched.status_code, 200, switched.text)
        self.assertEqual(await self.session_user(), 1)
        # Only THIS browser's previous session was revoked.
        self.assertEqual(await self.session_user(second_device), 2)
        self.assertEqual(await self.live_sessions(), 2)

    async def test_stale_cookie_counts_as_signed_out(self):
        self.assertEqual((await self.redeem(await self.secret(2002))).status_code, 200)
        async with self.sessions() as db:
            session = (await db.execute(select(DesktopSession))).scalar_one()
            session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        response = await self.redeem(await self.secret(1001))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await self.session_user(), 1)

    async def test_entitlement_and_progress_fields_are_untouched(self):
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.status, user.payment_status, user.level = "active", "approved", "hsk3"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=20)
            await db.commit()
        fields = ("status", "payment_status", "level", "end_date", "language",
                  "telegram_id", "question_limit", "questions_used")
        async with self.sessions() as db:
            user = await db.get(User, 1)
            before = {key: getattr(user, key) for key in fields}
        self.assertEqual((before["status"], before["level"]), ("active", "hsk3"))
        self.assertEqual((await self.redeem(await self.secret())).status_code, 200)
        async with self.sessions() as db:
            user = await db.get(User, 1)
            self.assertEqual({key: getattr(user, key) for key in fields}, before)

    async def test_funnel_events_are_written_once_per_link(self):
        token = await self.secret()
        await self.redeem(token)
        await self.redeem(token)
        async with self.sessions() as db:
            rows = (await db.execute(select(
                CourseMiniAppEvent.event_name, CourseMiniAppEvent.user_id,
                CourseMiniAppEvent.source, CourseMiniAppEvent.payload_json,
            ).order_by(CourseMiniAppEvent.id))).all()
        self.assertEqual([(row[0], row[1], row[2]) for row in rows], [
            ("pwa_handoff_issued", 1, "miniapp_home_prompt"),
            ("pwa_handoff_completed", 1, "pwa_handoff"),
        ])
        for row in rows:
            self.assertNotIn(token, row[3] or "")


class HandoffIsolationTests(HandoffFixture):
    """A handoff row is useless to every other sign-in path, and vice versa."""

    async def handoff_row(self):
        token = await self.secret()
        async with self.sessions() as db:
            return token, (await db.execute(select(DesktopLinkRequest))).scalar_one()

    async def test_native_poll_bot_approval_and_telegram_claim_refuse_it(self):
        token, row = await self.handoff_row()
        async with self.sessions() as db:
            desktop = DesktopAuthService(db, self.settings)
            with self.assertRaises(DesktopAuthError):
                await desktop.poll_link(link_request_id=row.id, polling_secret=token)
        # The row id is not secret, so every by-id bot path must refuse it for
        # the owner and for a stranger alike.
        for telegram_id in (1001, 2002):
            for call, extra in (
                ("link_request_preview", {}),
                ("link_request_confirmation", {"telegram_id": telegram_id}),
                ("approve_link_request", {"telegram_id": telegram_id}),
                ("cancel_link_request", {"telegram_id": telegram_id}),
            ):
                async with self.sessions() as db:
                    desktop = DesktopAuthService(db, self.settings)
                    with self.assertRaises(DesktopAuthError, msg=call):
                        await getattr(desktop, call)(
                            link_request_id=row.id, platform="pwa", **extra)
        async with self.sessions() as db:
            with self.assertRaises(PwaAuthError):
                await PwaAuthService(db, self.settings).claim_telegram(
                    request_id=row.id, proof=token)
        claim = await self.browser.post(
            "/api/v3/pwa-auth/telegram/claim", headers={"Origin": ORIGIN},
            json={"link_request_id": row.id})
        self.assertEqual(claim.status_code, 401)
        async with self.sessions() as db:
            with self.assertRaises(DesktopAuthError):
                await DesktopAuthService(db, self.settings).start_link(
                    platform="pwa", app_version="1.0.0", installation_key="k" * 40,
                    flow=MINIAPP_HANDOFF_FLOW)
        # Still owned by learner 1 and still redeemable exactly once.
        async with self.sessions() as db:
            fresh = await db.get(DesktopLinkRequest, row.id)
            self.assertEqual((fresh.status, fresh.approved_user_id), ("approved", 1))
        self.assertEqual((await self.redeem(token)).status_code, 200)
        self.assertEqual(await self.session_user(), 1)

    async def test_other_flows_secrets_cannot_be_redeemed_as_a_handoff(self):
        async with self.sessions() as db:
            started = await DesktopAuthService(db, self.settings).start_link(
                platform="android", app_version="1.0.0", installation_key="i" * 40)
            await DesktopAuthService(db, self.settings).approve_link_request(
                link_request_id=started["link_request_id"], telegram_id=1001)
        for secret in (started["polling_secret"], started["link_request_id"] + "0000"):
            response = await self.redeem(secret)
            self.assertEqual((response.status_code, response.json()["error"]),
                             (401, "pwa_handoff_invalid"))
        self.assertEqual(await self.count(DesktopSession), 0)

    async def test_landing_shell_is_static_private_and_script_restricted(self):
        page = await self.browser.get("/iphone-pwa/handoff")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(page.headers["referrer-policy"], "no-referrer")
        self.assertEqual(page.headers["x-frame-options"], "DENY")
        self.assertEqual(page.headers["x-content-type-options"], "nosniff")
        policy = page.headers["content-security-policy"]
        for directive in ("default-src 'none'", "script-src 'self'", "connect-src 'self'",
                          "manifest-src 'self'",
                          "frame-ancestors 'none'", "form-action 'none'", "base-uri 'none'"):
            self.assertIn(directive, policy)
        self.assertNotIn("unsafe-inline'; connect", policy.split("script-src")[1].split(";")[0])
        self.assertNotIn("set-cookie", page.headers)
        html = page.text
        self.assertIn('name="robots" content="noindex,nofollow"', html)
        self.assertIn('name="referrer" content="no-referrer"', html)
        for external in ("http://", "//cdn", "googletagmanager", "telegram.org"):
            self.assertNotIn(external, html)
        self.assertNotIn("<script>", html)  # No inline script under this policy.
        # Shared assets are immutable for a year: every reference carries a
        # token derived from that file's current bytes.
        self.assertNotIn("?v=AUTO", html)
        versioned = re.findall(r'"(/(?:course_v3_data|assets/characters)/[^"?]+)\?v=([0-9a-f]{12})"', html)
        self.assertEqual(len(versioned), 6)
        for path, token in versioned:
            digest = hashlib.sha256(Path("app/static" + path).read_bytes()).hexdigest()
            self.assertEqual(token, digest[:12], path)
        script = await self.browser.get("/iphone-pwa-handoff.js")
        self.assertEqual(script.status_code, 200)
        self.assertEqual(script.headers["cache-control"], "no-store")
        source = script.text
        # The secret leaves the address bar before the first network request.
        self.assertLess(source.index("history.replaceState"), source.index("fetch("))
        for forbidden in ("localStorage.setItem(\"t", "document.cookie", "console.log", "location.search"):
            self.assertNotIn(forbidden, source)
        self.settings.PWA_AUTH_ENABLED = False
        self.assertEqual((await self.browser.get("/iphone-pwa/handoff")).status_code, 503)
        self.assertEqual((await self.browser.get("/iphone-pwa-handoff.js")).status_code, 503)


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"),
                     "requires isolated PostgreSQL test database")
class HandoffPostgresConcurrencyTests(HandoffFixture):
    """Row locks and the per-learner issue lock on a real PostgreSQL.

    SQLite serializes writers, so only this class can show that two requests
    racing on one link, or one learner racing on issuance, stay single-use.
    Every test owns a random schema; no shared table is read or written.
    """

    async def make_engine(self):
        url = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
        self.schema = "pwa_handoff_" + uuid4().hex
        self.admin = create_async_engine(url)
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        return create_async_engine(url, pool_size=20, connect_args={"server_settings": {
            "search_path": self.schema, "statement_timeout": "15000",
            "lock_timeout": "10000",
        }})

    async def asyncTearDown(self):
        await super().asyncTearDown()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def race(self, *calls):
        ready = asyncio.Event()

        async def run(call):
            await ready.wait()
            return await call()

        tasks = [asyncio.create_task(run(call)) for call in calls]
        ready.set()
        return await asyncio.wait_for(asyncio.gather(*tasks), postgres_timeout(20))

    async def live_links(self):
        return await self.count(
            DesktopLinkRequest, DesktopLinkRequest.status == "approved",
            DesktopLinkRequest.consumed_at.is_(None))

    @staticmethod
    def token_of(response):
        fragment = urlsplit(response.json()["url"]).fragment
        return dict(item.split("=", 1) for item in fragment.split("&"))["t"]

    async def test_parallel_redeems_of_one_link_mint_exactly_one_session(self):
        token = await self.secret()
        browsers = [self.new_browser() for _ in range(8)]
        replies = await self.race(*[
            (lambda browser=browser: self.redeem(token, browser=browser))
            for browser in browsers])
        self.assertEqual(sorted(reply.status_code for reply in replies), [200] + [401] * 7)
        self.assertEqual(
            {reply.json()["error"] for reply in replies if reply.status_code != 200},
            {"pwa_handoff_invalid"})
        self.assertEqual(await self.count(DesktopSession), 1)
        self.assertEqual(await self.count(DesktopDevice), 1)
        signed_in = [await self.session_user(browser) for browser in browsers]
        self.assertEqual([user for user in signed_in if user], [1])
        self.assertEqual(await self.count(
            CourseMiniAppEvent,
            CourseMiniAppEvent.event_name == "pwa_handoff_completed"), 1)

    async def test_parallel_issues_keep_one_live_link_within_the_rate_limit(self):
        extra = 3
        replies = await self.race(*[
            self.start for _ in range(PWA_HANDOFF_RATE_LIMIT_COUNT + extra)])
        self.assertEqual(
            sorted(reply.status_code for reply in replies),
            [200] * PWA_HANDOFF_RATE_LIMIT_COUNT + [429] * extra)
        self.assertEqual(await self.count(DesktopLinkRequest), PWA_HANDOFF_RATE_LIMIT_COUNT)
        self.assertEqual(await self.live_links(), 1)
        tokens = [self.token_of(reply) for reply in replies if reply.status_code == 200]
        self.assertEqual(len(set(tokens)), PWA_HANDOFF_RATE_LIMIT_COUNT)
        outcomes = []
        for token in tokens:
            outcomes.append((await self.redeem(token, browser=self.new_browser())).status_code)
        # Only the newest link survived; every superseded one is dead.
        self.assertEqual(sorted(outcomes), [200] + [401] * (PWA_HANDOFF_RATE_LIMIT_COUNT - 1))
        self.assertEqual(await self.count(DesktopSession), 1)
        # Another learner is not throttled by this one's burst.
        self.assertEqual((await self.start(2002)).status_code, 200)

    async def test_issuing_while_redeeming_cannot_deadlock_or_double_spend(self):
        token = await self.secret()
        browsers = [self.new_browser() for _ in range(3)]
        replies = await self.race(
            *[(lambda browser=browser: self.redeem(token, browser=browser))
              for browser in browsers],
            *[self.start for _ in range(3)])
        redeems, issues = replies[:3], replies[3:]
        self.assertEqual([reply.status_code for reply in issues], [200, 200, 200])
        self.assertTrue(all(reply.status_code in (200, 401) for reply in redeems), redeems)
        spent = sum(reply.status_code == 200 for reply in redeems)
        self.assertLessEqual(spent, 1)
        self.assertEqual(await self.count(DesktopSession), spent)
        self.assertEqual(await self.live_links(), 1)

    async def test_two_learners_racing_keep_their_own_accounts(self):
        first, second = await self.secret(1001), await self.secret(2002)
        one, two = self.new_browser(), self.new_browser()
        replies = await self.race(
            lambda: self.redeem(first, browser=one),
            lambda: self.redeem(second, browser=two))
        self.assertEqual([reply.status_code for reply in replies], [200, 200])
        self.assertEqual((await self.session_user(one), await self.session_user(two)), (1, 2))


if __name__ == "__main__":
    unittest.main()
