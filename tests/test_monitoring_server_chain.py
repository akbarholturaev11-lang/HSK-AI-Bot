"""Server monitoring chain (task 1.3) on PostgreSQL.

Backend reporter → PostgreSQL incident → Admin Inbox, through the shared helper
`tests/monitoring_chain.py::assert_monitoring_chain`:
- an integration failure (`report_server_failure` at the Lava ledger site);
- a learner route 5xx through the real `DiagnosticMiddleware`.

Run with MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL pointing at a
disposable `*_test` PostgreSQL database.
"""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.api.monitoring_guard_fixture import router as scratch_router
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
                    site="lava_ledger", sessions=sessions, reporter=reporter, trigger=lava_failure,
                    inbox_route="/api/admin/v1/inbox/list")
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
                site="v3_lesson_complete", sessions=sessions, reporter=reporter, trigger=route_5xx,
                inbox_route="/api/admin/v1/inbox/list")

    async def test_scratch_covered_route_reaches_inbox(self):
        async with pg_sessions(PG_URL) as sessions:
            reporter = reporter_for(sessions)
            app = FastAPI()
            app.include_router(scratch_router)
            app.add_middleware(DiagnosticMiddleware, reporter_obj=reporter)

            async def route_5xx():
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    self.assertEqual((await client.get("/api/v3/monitoring-guard-fixture")).status_code, 502)

            await assert_monitoring_chain(
                self, platform="server", feature="lessons", failure="server_5xx",
                site="v3_monitoring_guard_fixture", sessions=sessions, reporter=reporter, trigger=route_5xx,
                inbox_route="/api/admin/v1/inbox/list")

    async def test_saturated_backend_writer_reports_its_drop_to_inbox(self):
        async with pg_sessions(PG_URL) as sessions:
            reporter = BackendReporter(session_factory=sessions, settings_obj=SimpleNamespace(MONITORING_MODE="all"),
                                       concurrency=1, coalesce_seconds=0)

            async def saturate_writer():
                # Simulate an in-flight diagnostic write occupying the sole slot.
                async with reporter._semaphore:
                    reporter.report("lessons", "server_exception", "v3_lesson_start")
                    await asyncio.gather(*tuple(reporter._tasks))
                await reporter.flush_self_dropped()

            await assert_monitoring_chain(
                self, platform="server", feature="monitoring", failure="self_dropped", site="backend_writer",
                sessions=sessions, reporter=reporter, trigger=saturate_writer,
                inbox_route="/api/admin/v1/inbox/list")


if __name__ == "__main__":
    unittest.main()
