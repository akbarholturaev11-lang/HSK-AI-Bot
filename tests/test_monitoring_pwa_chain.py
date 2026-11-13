"""Verified PWA cookie + CSRF → diagnostic intake → PostgreSQL."""
import unittest
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import tests.test_pwa_browser_auth as pwa
from app.api.monitoring_intake import create_monitoring_intake_router
from app.api.pwa_auth import create_pwa_auth_router
from app.db.models.desktop import DesktopLinkRequest
from app.db.models.diagnostic import DiagnosticReceipt
from app.services.pwa_auth_service import PWA_SESSION_COOKIE, PwaAuthService
from tests.monitoring_chain import PG_URL, assert_monitoring_chain, pg_sessions


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"),
                     "set MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL")
class PwaMonitoringChainTests(unittest.IsolatedAsyncioTestCase):
    SIGNALS = (
        ("lessons", "js_uncaught", "course_v3"),
        ("auth_session", "restore_failed", "session_restore"),
        ("onboarding_activation", "save_unconfirmed", "li_onboarding"),
        ("practice", "save_unconfirmed", "practice"),
        ("checkout_payments", "save_unconfirmed", "payment"),
        ("pwa_pro_checkout", "save_unconfirmed", "payment"),
        ("distribution_handoff", "restore_failed", "pwa_handoff"),
        ("voice_practice", "live_session_failed", "live_response_invalid"),
    )

    async def test_pwa_priority_failures_reach_inbox_as_verified_browser_owner(self):
        settings = pwa.settings(MONITORING_MODE="all", admin_id_list=[])
        async with pg_sessions(PG_URL, users=()) as sessions:
            async with sessions() as db, db.begin():
                learner = pwa.user(1, 1001)
                db.add(learner)
                await db.flush()
                cookie = await PwaAuthService(db, settings)._mint_session(
                    learner, DesktopLinkRequest(installation_key_hash=uuid4().hex * 2))

            app = FastAPI()
            app.include_router(create_pwa_auth_router(session_factory=sessions, settings_obj=settings))
            app.include_router(create_monitoring_intake_router(session_factory=sessions, settings_obj=settings))
            async with AsyncClient(transport=ASGITransport(app=app), base_url=pwa.ORIGIN,
                                   cookies={PWA_SESSION_COOKIE: cookie}) as client:
                actor = await client.get("/api/v3/pwa-auth/session")
                self.assertEqual(actor.status_code, 200, actor.text)
                self.assertEqual(actor.json()["user_id"], 1)
                for feature, failure, site in self.SIGNALS:
                    with self.subTest(feature=feature):
                        incident = await assert_monitoring_chain(
                            self, platform="iphone_pwa", feature=feature, failure=failure, site=site,
                            sessions=sessions, client=client, intake_route="/api/v3/pwa/diagnostics",
                            inbox_route="/api/admin/v1/inbox/list",
                            headers={"Origin": pwa.ORIGIN, "X-HSK-PWA-CSRF": actor.json()["csrf"]})

            async with sessions() as db:
                receipt = (await db.scalars(select(DiagnosticReceipt).where(
                    DiagnosticReceipt.incident_id == incident.id))).one()
                self.assertEqual(receipt.user_id, 1)
                self.assertIsNone(receipt.channel)
