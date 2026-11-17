"""Diagnostic intake routes, backend middleware and reporter, Lava sites (task 1.3)."""
import asyncio
import hashlib
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401  (register every table)
import tests.test_pwa_browser_auth as pwa
from app.api.monitoring_intake import PAUSED, create_monitoring_intake_router
from app.db.base import Base
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.services import blocked_user_guard
from app.services.blocked_user_guard import BlockedUserApiMiddleware
from app.services.desktop_auth_service import DesktopAuthService
from app.services.lava.notify import ADMIN_ALERT_TEXT, LavaNotifier
from app.services.monitoring import backend, catalog
from app.services.monitoring.backend import BackendReporter, DiagnosticMiddleware, platform_for_route
from app.services.monitoring.intake import diagnostic_slot, fingerprint
from app.services.pwa_auth_service import PWA_PLATFORM, PWA_SESSION_COOKIE, PwaAuthService
from tests.monitoring_chain import client_event

LEARNER_TG, OWNER_TG = 1001, 9001


def settings(mode="all"):
    return pwa.settings(MONITORING_MODE=mode, admin_id_list=[OWNER_TG])


def body(*items):
    return {"schema": catalog.SCHEMA, "events": list(items) or [client_event("lessons", "api_5xx", "lesson_open")]}


async def memory_sessions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


class IntakeRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine, self.sessions = await memory_sessions()
        async with self.sessions() as db, db.begin():
            db.add_all([pwa.user(1, LEARNER_TG), pwa.user(2, OWNER_TG)])
        self.settings = settings()
        self.client = self.make_client(self.settings)

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def make_client(self, settings_obj, session_factory=None):
        app = FastAPI()
        app.include_router(create_monitoring_intake_router(session_factory=session_factory or self.sessions,
                                                           settings_obj=settings_obj))
        return AsyncClient(transport=ASGITransport(app=app), base_url=pwa.ORIGIN)

    async def bearer(self, platform="android", telegram_id=LEARNER_TG):
        async with self.sessions() as db:
            auth = DesktopAuthService(db, self.settings)
            link = await auth.start_link(platform=platform, app_version="1.8.0", installation_key=uuid4().hex * 2)
            await auth.approve_link(display_code=link["display_code"], telegram_id=telegram_id)
            linked = await auth.poll_link(link_request_id=link["link_request_id"],
                                          polling_secret=link["polling_secret"])
            return linked["access_token"]

    async def pwa_cookie(self, user_id=1, telegram_id=LEARNER_TG):
        cookie = secrets.token_urlsafe(32)
        async with self.sessions() as db, db.begin():
            service = PwaAuthService(db, self.settings)
            device = DesktopDevice(id=str(uuid4()), user_id=user_id, telegram_id=telegram_id,
                                   installation_key_hash=hashlib.sha256(cookie.encode()).hexdigest(),
                                   platform=PWA_PLATFORM, app_version="1.0.0")
            db.add(device)
            await db.flush()
            db.add(DesktopSession(id=str(uuid4()), device_id=device.id,
                                  refresh_token_hash=service.desktop._hash("pwa-cookie", cookie),
                                  expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                                  last_seen_at=datetime.now(timezone.utc)))
            return cookie, service.csrf(cookie)

    async def android_post(self, token, payload=None):
        return await self.client.post("/api/v3/android/diagnostics", json=payload or body(),
                                      headers={"Authorization": f"Bearer {token}"} if token else {})

    async def pwa_post(self, cookie, csrf, payload=None, path="/api/v3/pwa/diagnostics", **headers):
        sent = {"Origin": pwa.ORIGIN, "Cookie": f"{PWA_SESSION_COOKIE}={cookie}", "X-HSK-PWA-CSRF": csrf}
        sent.update(headers)
        payload = payload or body(client_event("lessons", "api_5xx", "lesson_open", "iphone_pwa"))
        return await self.client.post(path, json=payload, headers=sent)

    async def receipts(self):
        async with self.sessions() as db:
            return (await db.execute(select(DiagnosticReceipt.user_id))).scalars().all()

    async def test_android_requires_a_bearer_from_an_android_device(self):
        self.assertEqual((await self.android_post("")).status_code, 401)
        self.assertEqual((await self.android_post(await self.bearer("macos"))).status_code, 403)
        self.assertEqual(await self.receipts(), [])

    async def test_android_owner_comes_only_from_the_session(self):
        response = await self.android_post(await self.bearer())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["accepted"], 1)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(await self.receipts(), [1])

    async def test_client_owner_fingerprint_or_severity_is_rejected(self):
        token = await self.bearer()
        cookie, csrf = await self.pwa_cookie()
        forged = {"user_id": 2, "telegram_id": OWNER_TG, "fingerprint": "f" * 64, "severity": "critical"}
        for key, value in forged.items():
            android = client_event("lessons", "api_5xx", "lesson_open", **{key: value})
            web = client_event("lessons", "api_5xx", "lesson_open", "iphone_pwa", **{key: value})
            with self.subTest(key=key):
                self.assertEqual((await self.android_post(token, body(android))).status_code, 422)
                self.assertEqual((await self.pwa_post(cookie, csrf, body(web))).status_code, 422)
        self.assertEqual(await self.receipts(), [])

    async def test_blocked_and_revoked_accounts_are_refused(self):
        token = await self.bearer()
        cookie, csrf = await self.pwa_cookie()
        async with self.sessions() as db, db.begin():
            (await db.get(app.db.models.User, 1)).status = "blocked"
        self.assertEqual((await self.android_post(token)).status_code, 403)
        self.assertEqual((await self.pwa_post(cookie, csrf)).status_code, 401)
        async with self.sessions() as db, db.begin():
            (await db.get(app.db.models.User, 1)).status = "free"
            for device in (await db.execute(select(DesktopDevice))).scalars():
                device.revoked_at = datetime.now(timezone.utc)
        self.assertEqual((await self.android_post(token)).status_code, 401)
        self.assertEqual((await self.pwa_post(cookie, csrf)).status_code, 401)
        self.assertEqual(await self.receipts(), [])

    async def test_pwa_needs_cookie_csrf_same_origin_and_no_telegram_or_query(self):
        cookie, csrf = await self.pwa_cookie()
        self.assertEqual((await self.pwa_post("", csrf)).status_code, 401)
        self.assertEqual((await self.pwa_post(cookie, "forged")).status_code, 403)
        self.assertEqual((await self.pwa_post(cookie, csrf, Origin="https://evil.test")).status_code, 403)
        self.assertEqual((await self.pwa_post(cookie, csrf, path="/api/v3/pwa/diagnostics?u=2")).status_code, 422)
        self.assertEqual((await self.pwa_post(cookie, csrf, **{"X-Telegram-Init-Data": "x"})).status_code, 422)
        self.assertEqual(await self.receipts(), [])
        response = await self.pwa_post(cookie, csrf)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await self.receipts(), [1])
        async with self.sessions() as db:
            platform = await db.scalar(select(DiagnosticIncident.platform))
        self.assertEqual(platform, "iphone_pwa")

    async def test_previous_cookie_csrf_cannot_attribute_the_batch_to_a_new_account(self):
        _, previous_csrf = await self.pwa_cookie()
        cookie, csrf = await self.pwa_cookie(user_id=2, telegram_id=OWNER_TG)
        payload = body(client_event("lessons", "load_failed", "lesson_open", "iphone_pwa"))
        self.assertEqual((await self.pwa_post(cookie, previous_csrf, payload)).status_code, 403)
        self.assertEqual(await self.receipts(), [])
        self.assertEqual((await self.pwa_post(cookie, csrf, payload)).json()["accepted"], 1)
        self.assertEqual(await self.receipts(), [2])

    async def test_oversized_or_non_json_body_is_rejected_before_parsing(self):
        token = await self.bearer()
        huge = await self.client.post("/api/v3/android/diagnostics", content=b"{" + b" " * catalog.MAX_BODY_BYTES,
                                      headers={"Authorization": f"Bearer {token}",
                                               "Content-Type": "application/json"})
        self.assertEqual(huge.status_code, 413)
        text_body = await self.client.post("/api/v3/android/diagnostics", content=b"{}",
                                           headers={"Authorization": f"Bearer {token}",
                                                    "Content-Type": "text/plain"})
        self.assertEqual(text_body.status_code, 422)
        nested = await self.client.post("/api/v3/android/diagnostics",
                                        content=b"[" * 2000 + b"]" * 2000,
                                        headers={"Authorization": f"Bearer {token}",
                                                 "Content-Type": "application/json"})
        self.assertEqual((nested.status_code, nested.json()["error"]), (422, "invalid_body"))

    async def test_off_answers_paused_without_touching_the_database(self):
        def no_database():
            raise AssertionError("off mode must not open a session")
        client = self.make_client(settings("off"), session_factory=no_database)
        try:
            for path in ("/api/v3/android/diagnostics", "/api/v3/pwa/diagnostics"):
                response = await client.post(path, json=body())
                self.assertEqual((response.status_code, response.json()), (200, PAUSED))
        finally:
            await client.aclose()

    async def test_saturation_does_not_open_a_diagnostic_session(self):
        token = await self.bearer()

        def no_database():
            self.fail("diagnostics cannot open more sessions under saturation")

        async with self.make_client(self.settings, session_factory=no_database) as client:
            with diagnostic_slot(self.settings), diagnostic_slot(self.settings):
                response = await client.post("/api/v3/android/diagnostics", json=body(),
                                             headers={"Authorization": f"Bearer {token}"})
        self.assertEqual((response.status_code, response.json()["error"]), (503, "diagnostics_unavailable"))
        self.assertEqual(await self.receipts(), [])

    async def test_owners_stage_admits_only_admin_accounts(self):
        await self.client.aclose()
        self.client = self.make_client(settings("owners"))
        learner = await self.android_post(await self.bearer())
        self.assertEqual((learner.json()["accepted"], learner.json()["dropped"]), (0, 1))
        owner = await self.android_post(await self.bearer(telegram_id=OWNER_TG))
        self.assertEqual(owner.json()["accepted"], 1)
        self.assertEqual(await self.receipts(), [2])


class FakeReporter:
    def __init__(self):
        self.calls = []

    def report(self, feature, failure, site, platform="server"):
        self.calls.append((platform, feature, failure, site))


def learner_app(reporter_obj, *, blocked_middleware=False):
    app = FastAPI()

    @app.get("/api/v3/android/dictionary")
    async def five_hundred():
        return JSONResponse({"ok": False, "error": "boom"}, status_code=500)

    @app.post("/api/v3/pwa/profile")
    async def explodes():
        raise RuntimeError("unhandled")

    @app.get("/api/v3/pwa/practice/words")
    async def unavailable():
        return JSONResponse({"ok": False, "error": "pwa_auth_unavailable"}, status_code=503)

    @app.get("/api/miniapp/course/{lesson_order}")
    async def not_found(lesson_order: int):
        return JSONResponse({"ok": False}, status_code=404)

    @app.get("/api/not-mapped")
    async def unmapped():
        return JSONResponse({}, status_code=500)

    if blocked_middleware:
        app.add_middleware(BlockedUserApiMiddleware, session_maker=None, bot_token="t", admin_ids=())
    app.add_middleware(DiagnosticMiddleware, reporter_obj=reporter_obj)
    return app


class DiagnosticMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, app, method, path, **kwargs):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    async def test_a_5xx_is_recorded_once_and_the_response_is_unchanged(self):
        fake = FakeReporter()
        response = await self.request(learner_app(fake), "GET", "/api/v3/android/dictionary")
        self.assertEqual((response.status_code, response.json()), (500, {"ok": False, "error": "boom"}))
        self.assertEqual(fake.calls, [("android", "lessons", "server_5xx", "v3_android_dictionary")])

    async def test_an_unhandled_exception_is_recorded_once(self):
        fake = FakeReporter()
        response = await self.request(learner_app(fake), "POST", "/api/v3/pwa/profile", json={"secret": "x"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(fake.calls, [("iphone_pwa", "app_shell", "server_exception", "v3_pwa_profile")])

    async def test_4xx_503_and_unmapped_routes_are_not_recorded(self):
        fake = FakeReporter()
        app = learner_app(fake)
        self.assertEqual((await self.request(app, "GET", "/api/miniapp/course/3")).status_code, 404)
        self.assertEqual((await self.request(app, "GET", "/api/v3/pwa/practice/words")).status_code, 503)
        self.assertEqual((await self.request(app, "GET", "/api/not-mapped")).status_code, 500)
        self.assertEqual((await self.request(app, "GET", "/api/v3/android/missing")).status_code, 404)
        self.assertEqual(fake.calls, [])

    async def test_blocked_user_403_is_not_recorded(self):
        fake = FakeReporter()
        with patch.object(blocked_user_guard, "extract_verified_webapp_user_id", return_value=3003), \
                patch.object(blocked_user_guard, "is_blocked_telegram_id", AsyncMock(return_value=True)), \
                patch.object(blocked_user_guard, "get_admin_contact_url", AsyncMock(return_value="")):
            response = await self.request(learner_app(fake, blocked_middleware=True), "GET",
                                          "/api/v3/android/dictionary", headers={"X-Telegram-Init-Data": "signed"})
        self.assertEqual((response.status_code, response.json()["error"]), (403, "user_blocked"))
        self.assertEqual(fake.calls, [])

    async def test_no_body_is_read_and_messages_pass_through_untouched(self):
        sent_messages = [{"type": "http.response.start", "status": 500, "headers": []},
                         {"type": "http.response.body", "body": b"original"}]

        async def inner(scope, receive, send):
            for message in sent_messages:
                await send(message)

        received, delivered, fake = [], [], FakeReporter()

        async def receive():
            received.append(1)
            return {"type": "http.request", "body": b"secret", "more_body": False}

        async def send(message):
            delivered.append(message)

        scope = {"type": "http", "path": "/api/v3/android/dictionary", "method": "POST", "headers": []}
        await DiagnosticMiddleware(inner, reporter_obj=fake)(scope, receive, send)
        self.assertEqual(received, [])
        self.assertEqual(delivered, sent_messages)
        self.assertIs(delivered[1], sent_messages[1])
        self.assertEqual(len(fake.calls), 1)

    async def test_diagnostic_transports_do_not_report_their_own_5xx(self):
        fake = FakeReporter()
        app = FastAPI()

        async def unavailable():
            return JSONResponse({"ok": False}, status_code=500)

        paths = ("/api/v3/android/diagnostics", "/api/v3/pwa/diagnostics", "/api/miniapp/event")
        for path in paths:
            app.add_api_route(path, unavailable, methods=["POST"])
        app.add_middleware(DiagnosticMiddleware, reporter_obj=fake)
        for path in paths:
            headers = {"X-HSK-Diagnostic": "diag.v1"} if path == paths[-1] else {}
            self.assertEqual((await self.request(app, "POST", path, headers=headers)).status_code, 500)
        self.assertEqual(fake.calls, [])
        self.assertEqual((await self.request(app, "POST", paths[-1])).status_code, 500)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][0], "telegram")

    def test_platform_follows_the_route_prefix(self):
        self.assertEqual(platform_for_route("/api/v3/android/course/map"), "android")
        self.assertEqual(platform_for_route("/api/v3/pwa-auth/session"), "iphone_pwa")
        self.assertEqual(platform_for_route("/api/subscription-miniapp/plans"), "telegram")
        self.assertEqual(platform_for_route("/api/v3/lesson/complete"), "server")


class BackendReporterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine, self.sessions = await memory_sessions()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def reporter(self, mode="all", **kwargs):
        kwargs.setdefault("coalesce_seconds", 60)
        return BackendReporter(session_factory=self.sessions, settings_obj=settings(mode), **kwargs)

    async def incidents(self):
        async with self.sessions() as db:
            rows = (await db.execute(select(DiagnosticIncident))).scalars().all()
            return {(r.platform, r.feature_code, r.failure_code, r.site_code): r.occurrence_count for r in rows}

    async def test_repeats_coalesce_into_one_write(self):
        reporter = self.reporter()
        for _ in range(3):
            reporter.report("lessons", "server_5xx", "v3_android_dictionary", "android")
        await reporter.drain()
        self.assertEqual(await self.incidents(), {("android", "lessons", "server_5xx", "v3_android_dictionary"): 3})
        async with self.sessions() as db:
            owners = (await db.execute(select(DiagnosticReceipt.user_id))).scalars().all()
        self.assertEqual(owners, [None])

    async def test_saturation_drops_are_counted_and_reported_as_a_self_incident(self):
        reporter = self.reporter(concurrency=1, coalesce_seconds=0)
        await reporter._semaphore.acquire()
        reporter.report("chat_ai", "provider_failed", "ai_provider")
        reporter.report("voice_practice", "provider_failed", "voice_provider")
        await asyncio.sleep(0.05)
        self.assertEqual(reporter.dropped, 2)
        reporter._semaphore.release()
        await reporter.flush_self_dropped()
        self.assertEqual((await self.incidents(), reporter.dropped),
                         ({("server", "monitoring", "self_dropped", "backend_writer"): 2}, 0))

    async def test_off_unknown_codes_and_write_failures_never_raise(self):
        off = self.reporter("off")
        off.report("lessons", "server_5xx", "v3_android_dictionary")
        self.assertEqual(off._pending, {})
        reporter = self.reporter()
        reporter.report("made_up", "server_5xx", "v3_android_dictionary")
        reporter.report("lessons", "api_5xx", "v3_android_dictionary")  # a client-only failure code
        self.assertEqual(reporter._pending, {})

        def broken():
            raise RuntimeError("database down")
        failing = BackendReporter(session_factory=broken, settings_obj=settings(), coalesce_seconds=60)
        failing.report("lessons", "server_5xx", "v3_android_dictionary")
        await failing.drain()
        self.assertEqual((failing.dropped, await self.incidents()), (1, {}))

    async def test_lava_failure_keeps_its_telegram_alert_and_records_one_incident(self):
        reporter = self.reporter()
        bot = SimpleNamespace(send_message=AsyncMock())
        notifier = LavaNotifier(bot=bot, admin_ids=[OWNER_TG, 9002])
        with patch.object(backend, "reporter", reporter):
            await notifier.admin_alert("activation_failed", invoice_id=7, throttle_seconds=300)
            await notifier.admin_alert("activation_failed", invoice_id=7, throttle_seconds=300)
            await notifier.admin_alert("refund_revoked", invoice_id=8)
            await notifier.admin_alert("webhook_auth_failed")
            await reporter.drain()
        text = ADMIN_ALERT_TEXT["activation_failed"] + "\n#lava_invoice_7"
        refund = ADMIN_ALERT_TEXT["refund_revoked"] + "\n#lava_invoice_8"
        self.assertEqual([call.kwargs for call in bot.send_message.await_args_list],
                         [{"chat_id": OWNER_TG, "text": text}, {"chat_id": 9002, "text": text},
                          {"chat_id": OWNER_TG, "text": refund}, {"chat_id": 9002, "text": refund},
                          {"chat_id": OWNER_TG, "text": ADMIN_ALERT_TEXT["webhook_auth_failed"]},
                          {"chat_id": 9002, "text": ADMIN_ALERT_TEXT["webhook_auth_failed"]}])
        self.assertEqual(await self.incidents(),
                         {("server", "checkout_payments", "provider_failed", "lava_ledger"): 2})
        async with self.sessions() as db:
            count = await db.scalar(select(func.count()).select_from(DiagnosticIncident))
            stored = await db.scalar(select(DiagnosticIncident.fingerprint))
        self.assertEqual((count, stored),
                         (1, fingerprint("server", "checkout_payments", "provider_failed", "lava_ledger")))

    async def test_openai_stt_failure_reports_only_the_safe_signal(self):
        from app.services.ai_provider import AIProviderChain

        reporter = self.reporter()
        chain = AIProviderChain.__new__(AIProviderChain)
        chain._openai = object()
        expected = RuntimeError("synthetic provider failure")
        with patch.object(backend, "reporter", reporter), \
                patch("app.services.ai_provider.settings", SimpleNamespace(GEMINI_API_KEY="")), \
                patch.object(chain, "_openai_transcribe", new=AsyncMock(side_effect=expected)):
            with self.assertRaises(RuntimeError) as raised:
                await chain.transcribe(audio_bytes=b"synthetic", filename="synthetic", mime_type="audio/ogg", prompt="")
            self.assertIs(raised.exception, expected)
            await reporter.drain()
        self.assertEqual(await self.incidents(), {("server", "voice_practice", "provider_failed", "voice_provider"): 1})

    async def test_ai_provider_reports_only_when_the_last_fallback_fails(self):
        from app.services.ai_provider import AIProviderChain
        reporter = self.reporter()

        def client(**create):
            return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(**create))))

        chain = AIProviderChain.__new__(AIProviderChain)
        chain._gemini_compat = None
        down, up = client(side_effect=RuntimeError("provider down")), client(return_value="answer")
        with patch.object(backend, "reporter", reporter), \
                patch.object(AIProviderChain, "_build_chat_request", return_value={}):
            with patch.object(AIProviderChain, "_chat_providers", return_value=[("gemini", down), ("openai", up)]):
                self.assertEqual(await chain.chat_completion(openai_model="m", messages=[]), ("answer", "m"))
            self.assertEqual(reporter._pending, {})
            with patch.object(AIProviderChain, "_chat_providers", return_value=[("gemini", down), ("openai", down)]):
                with self.assertRaises(RuntimeError):
                    await chain.chat_completion(openai_model="m", messages=[])
            await reporter.drain()
        self.assertEqual(await self.incidents(), {("server", "chat_ai", "provider_failed", "ai_provider"): 1})

if __name__ == "__main__":
    unittest.main()
