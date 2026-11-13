"""Signed Mini App diagnostics and backward-compatible legacy error capture."""
import hashlib
import hmac
import json
import time
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

import app.main as main
from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.db.models.message import Message
from app.services.app_error_context_service import AppErrorContextService
from tests.monitoring_chain import PG_URL, assert_monitoring_chain, client_event, pg_sessions
from tests.test_pwa_browser_auth import settings as learner_settings


def signed(token, telegram_id=1001, *, age=0):
    fields = {"auth_date": str(int(time.time()) - age), "user": json.dumps({"id": telegram_id})}
    key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    message = "\n".join(f"{name}={value}" for name, value in sorted(fields.items()))
    fields["hash"] = hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


@asynccontextmanager
async def telegram_client(sessions, settings):
    app = FastAPI()
    app.post("/api/miniapp/event")(main.miniapp_event)
    with (patch.object(main, "async_session_maker", sessions),
          patch.object(main, "settings", settings), patch("app.config.settings", settings)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hsk.test") as client:
            yield client


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"), "requires disposable monitoring PostgreSQL")
class TelegramMonitoringChainTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = learner_settings(MONITORING_MODE="all", MONITORING_MINIAPP_ADAPTER_ENABLED=True,
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUSH_ENABLED=True, admin_id_list=[2002])
        self.headers = {"X-Telegram-Init-Data": signed(self.settings.BOT_TOKEN), "X-HSK-Diagnostic": "diag.v1"}

    async def test_signed_web_report_reaches_inbox_without_a_message_or_kpi_event(self):
        async with pg_sessions(PG_URL) as sessions, telegram_client(sessions, self.settings) as client:
            for feature, failure, site in (("lessons", "js_uncaught", "course_v3"),
                                           ("voice_practice", "load_failed", "mic_unavailable")):
                await assert_monitoring_chain(
                    self, platform="telegram", feature=feature, failure=failure, site=site,
                    sessions=sessions, client=client, intake_route="/api/miniapp/event",
                    inbox_route="/api/admin/v1/inbox/list", headers=self.headers)
            event = client_event("lessons", "js_uncaught", "course_v3", platform="telegram")
            payload = {"event": "app_error", "schema": "diag.v1", "events": [event], "user_id": 2}
            response = await client.post("/api/miniapp/event", json=payload, headers=self.headers)
            self.assertEqual(response.json()["accepted"], 1)
            without_marker = {"X-Telegram-Init-Data": self.headers["X-Telegram-Init-Data"]}
            response = await client.post("/api/miniapp/event", json=payload, headers=without_marker)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["error"], "diagnostic_transport_required")
            forged = {**payload, "events": [{**event, "user_id": 2}]}
            self.assertEqual((await client.post("/api/miniapp/event", json=forged, headers=self.headers)).json()["error"],
                             "forbidden_field")
            stale = {**self.headers, "X-Telegram-Init-Data": signed(self.settings.BOT_TOKEN, age=86401)}
            self.assertEqual((await client.post("/api/miniapp/event", json=payload, headers=stale)).status_code, 401)
            large = {**payload, "padding": "x" * (16 * 1024)}
            self.assertEqual((await client.post("/api/miniapp/event", json=large, headers=self.headers)).status_code, 413)
            async with sessions() as db:
                self.assertEqual(await db.scalar(select(DiagnosticReceipt.user_id).where(
                    DiagnosticReceipt.event_id == event["event_id"])), 1)
                self.assertEqual(await db.scalar(select(func.count()).select_from(Message)), 0)
                self.assertEqual(await db.scalar(select(func.count()).select_from(CourseMiniAppEvent)), 0)
                self.assertEqual(await db.scalar(select(func.count()).select_from(ConversionFunnelEvent)), 0)

    async def test_legacy_errors_keep_their_own_technical_alert_and_ai_context(self):
        async with pg_sessions(PG_URL) as sessions, telegram_client(sessions, self.settings) as client:
            now = datetime.now(timezone.utc)
            async with sessions() as db, db.begin():
                db.add(AdminPwaPushSubscription(id=str(uuid4()), user_id=2, endpoint_hash="a" * 64,
                    encrypted_payload="synthetic-not-dispatched", platform="iphone", created_at=now, updated_at=now))
            private = "fixture-private-context"
            payload = {"event": "app_error", "source": "course_v3_onboarding",
                       "error_name": "OnboardingSaveResponseError", "error_message": "onboarding_save_timeout",
                       "extra": {"recovered": True}, "stack": private}
            headers = {"X-Telegram-Init-Data": self.headers["X-Telegram-Init-Data"]}
            for _ in range(30):
                self.assertTrue((await client.post("/api/miniapp/event", json=payload, headers=headers)).json()["ok"])
            self.settings.MONITORING_MINIAPP_ADAPTER_ENABLED = False
            self.assertTrue((await client.post("/api/miniapp/event", json=payload, headers=headers)).json()["ok"])
            self.settings.MONITORING_MINIAPP_ADAPTER_ENABLED = True
            self.settings.MONITORING_MODE = "off"
            self.assertTrue((await client.post("/api/miniapp/event", json=payload, headers=headers)).json()["ok"])
            async with sessions() as db:
                incident = (await db.scalars(select(DiagnosticIncident))).one()
                self.assertEqual((incident.feature_code, incident.site_code, incident.occurrence_count, incident.severity),
                                 ("onboarding_activation", "onboarding_timeout", 30, "normal"))
                self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox).where(
                    AdminPwaPushOutbox.source == "technical")), 32)
                self.assertEqual(await db.scalar(select(func.count()).select_from(Message)), 32)
                self.assertEqual(await db.scalar(select(func.count()).select_from(CourseMiniAppEvent)), 0)
                self.assertEqual(await db.scalar(select(func.count()).select_from(ConversionFunnelEvent)), 0)
                self.assertIn(private, await AppErrorContextService(db).build_ai_context(1))
                self.assertNotIn(private, repr(vars(incident)))
