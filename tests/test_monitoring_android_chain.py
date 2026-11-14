"""Android monitoring chain (task 2.1) on PostgreSQL.

A linked Android device posts a `diag.v1` event to the bearer intake
`/api/v3/android/diagnostics`; the shared helper
`tests/monitoring_chain.py::assert_monitoring_chain` checks the PostgreSQL
incident and authenticated Admin Inbox before writing the proof row.

Run with MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL pointing
at a disposable `*_test` PostgreSQL database.
"""
import unittest
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import tests.test_pwa_browser_auth as pwa
from app.api.monitoring_intake import create_monitoring_intake_router
from app.services.desktop_auth_service import DesktopAuthService
from tests.monitoring_chain import PG_URL, assert_monitoring_chain, pg_sessions

TELEGRAM_ID = 1001


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"),
                     "set MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL")
class AndroidMonitoringChainTests(unittest.IsolatedAsyncioTestCase):
    API_SIGNALS = (
        ("lessons", "api_5xx", "lesson_complete"),
        ("auth_session", "api_5xx", "login"),
        ("onboarding_activation", "api_5xx", "onboarding"),
        ("practice", "api_5xx", "practice"),
        ("checkout_payments", "api_5xx", "payment"),
        ("subscription_entries", "api_5xx", "subscription"),
    )

    async def bearer(self, sessions, settings):
        async with sessions() as db:
            auth = DesktopAuthService(db, settings)
            link = await auth.start_link(platform="android", app_version="1.8.0", installation_key=uuid4().hex * 2)
            await auth.approve_link(display_code=link["display_code"], telegram_id=TELEGRAM_ID)
            linked = await auth.poll_link(link_request_id=link["link_request_id"],
                                          polling_secret=link["polling_secret"])
            return linked["access_token"]

    async def test_android_api_failures_reach_inbox(self):
        settings = pwa.settings(MONITORING_MODE="all", admin_id_list=[])
        async with pg_sessions(PG_URL, users=()) as sessions:
            async with sessions() as db, db.begin():
                db.add(pwa.user(1, TELEGRAM_ID))
            app = FastAPI()
            app.include_router(create_monitoring_intake_router(session_factory=sessions, settings_obj=settings))
            async with AsyncClient(transport=ASGITransport(app=app), base_url=pwa.ORIGIN) as client:
                token = await self.bearer(sessions, settings)
                for feature, failure, site in self.API_SIGNALS:
                    with self.subTest(feature=feature):
                        incident = await assert_monitoring_chain(
                            self, platform="android", feature=feature, failure=failure, site=site,
                            sessions=sessions, client=client, headers={"Authorization": f"Bearer {token}"},
                            intake_route="/api/v3/android/diagnostics", inbox_route="/api/admin/v1/inbox/list")
                        self.assertEqual(incident.last_version, "1.8.0")

                await assert_monitoring_chain(
                    self, platform="android", feature="voice_practice", failure="live_session_failed",
                    site="live_connection_lost", sessions=sessions, client=client,
                    headers={"Authorization": f"Bearer {token}"}, intake_route="/api/v3/android/diagnostics",
                    inbox_route="/api/admin/v1/inbox/list")


if __name__ == "__main__":
    unittest.main()
