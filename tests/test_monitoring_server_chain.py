"""Server monitoring chain (task 1.3) on PostgreSQL.

Backend reporter → PostgreSQL incident → proof row, through the shared helper
`tests/monitoring_chain.py::assert_monitoring_chain`:
- an integration failure (`report_server_failure` at the Lava ledger site);
- a learner route 5xx through the real `DiagnosticMiddleware`.

Task 3.1 extends the helper with the Admin Inbox read. Run with
MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL pointing at a
disposable `*_test` PostgreSQL database.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.services.monitoring import backend
from app.services.monitoring.backend import BackendReporter, DiagnosticMiddleware, report_server_failure
from tests.monitoring_chain import PG_URL, assert_monitoring_chain, pg_sessions


def reporter_for(sessions):
    return BackendReporter(session_factory=sessions, settings_obj=SimpleNamespace(MONITORING_MODE="all"),
                           coalesce_seconds=60)


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"),
                     "set MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL")
class ServerMonitoringChainTests(unittest.IsolatedAsyncioTestCase):
    async def test_lava_integration_failure_reaches_postgres(self):
        async with pg_sessions(PG_URL) as sessions:
            reporter = reporter_for(sessions)

            async def lava_failure():
                report_server_failure("checkout_payments", "provider_failed", "lava_ledger")

            with patch.object(backend, "reporter", reporter):
                incident = await assert_monitoring_chain(
                    self, platform="server", feature="checkout_payments", failure="provider_failed",
                    site="lava_ledger", sessions=sessions, reporter=reporter, trigger=lava_failure)
            self.assertEqual(incident.severity, "critical")

    async def test_learner_route_5xx_reaches_postgres_through_the_middleware(self):
        async with pg_sessions(PG_URL) as sessions:
            reporter = reporter_for(sessions)
            app = FastAPI()

            @app.post("/api/v3/lesson/complete")
            async def complete():
                return JSONResponse({"ok": False}, status_code=502)

            app.add_middleware(DiagnosticMiddleware, reporter_obj=reporter)

            async def route_5xx():
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    self.assertEqual((await client.post("/api/v3/lesson/complete", json={})).status_code, 502)

            await assert_monitoring_chain(
                self, platform="server", feature="lessons", failure="server_5xx",
                site="v3_lesson_complete", sessions=sessions, reporter=reporter, trigger=route_5xx)


if __name__ == "__main__":
    unittest.main()
