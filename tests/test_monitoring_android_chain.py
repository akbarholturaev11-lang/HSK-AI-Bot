"""Android monitoring chain (task 2.1) on PostgreSQL.

A linked Android device posts a `diag.v1` event to the bearer intake
`/api/v3/android/diagnostics`; the shared helper
`tests/monitoring_chain.py::assert_monitoring_chain` checks the PostgreSQL
incident and writes the proof row. Task 3.1 adds the Admin Inbox read.

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
    async def bearer(self, sessions, settings):
        async with sessions() as db:
            auth = DesktopAuthService(db, settings)
            link = await auth.start_link(platform="android", app_version="1.8.0", installation_key=uuid4().hex * 2)
            await auth.approve_link(display_code=link["display_code"], telegram_id=TELEGRAM_ID)
            linked = await auth.poll_link(link_request_id=link["link_request_id"],
                                          polling_secret=link["polling_secret"])
            return linked["access_token"]

    async def test_android_lesson_failure_reaches_postgres(self):
        settings = pwa.settings(MONITORING_MODE="all", admin_id_list=[])
        async with pg_sessions(PG_URL, users=()) as sessions:
            async with sessions() as db, db.begin():
                db.add(pwa.user(1, TELEGRAM_ID))
            app = FastAPI()
            app.include_router(create_monitoring_intake_router(session_factory=sessions, settings_obj=settings))
            async with AsyncClient(transport=ASGITransport(app=app), base_url=pwa.ORIGIN) as client:
                token = await self.bearer(sessions, settings)
                # The Android intake is "/api/v3/android/diagnostics"; the helper posts there.
                incident = await assert_monitoring_chain(
                    self, platform="android", feature="lessons", failure="api_5xx", site="lesson_open",
                    sessions=sessions, client=client, headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(incident.severity, "high")
            self.assertEqual(incident.last_version, "1.8.0")


if __name__ == "__main__":
    unittest.main()
