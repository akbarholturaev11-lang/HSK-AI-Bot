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
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.services.lava.notify import ADMIN_ALERT_TEXT, LavaNotifier
from app.services.monitoring import backend
from app.services.monitoring.backend import BackendReporter, DiagnosticMiddleware
from tests.monitoring_chain import PG_URL, assert_monitoring_chain, pg_sessions
from tests.test_monitoring_telegram_chain import signed


def reporter_for(sessions):
    return BackendReporter(session_factory=sessions, settings_obj=SimpleNamespace(MONITORING_MODE="all"),
                           coalesce_seconds=60)


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"),
                     "set MONITORING_TEST_DATABASE_URL or ANALYTICS_TEST_DATABASE_URL")
class ServerMonitoringChainTests(unittest.IsolatedAsyncioTestCase):
    async def test_lava_integration_failure_reaches_postgres(self):
        async with pg_sessions(PG_URL) as sessions:
            reporter = reporter_for(sessions)

            telegram = SimpleNamespace(send_message=AsyncMock())
            notifier = LavaNotifier(bot=telegram, admin_ids=[2002])

            async def lava_failure():
                await notifier.admin_alert("activation_failed", invoice_id=41)
                telegram.send_message.assert_awaited_once_with(
                    chat_id=2002, text=ADMIN_ALERT_TEXT["activation_failed"] + "\n#lava_invoice_41")

            with patch.object(backend, "reporter", reporter):
                incident = await assert_monitoring_chain(
                    self, platform="server", feature="checkout_payments", failure="provider_failed",
                    site="lava_ledger", sessions=sessions, reporter=reporter, trigger=lava_failure,
                    inbox_route="/api/admin/v1/inbox/list")
            self.assertEqual(incident.severity, "critical")

    async def test_pwa_lava_provider_failure_reaches_inbox(self):
        from sqlalchemy import select
        from app.db.models.diagnostic import DiagnosticIncident
        from app.db.models.lava import LavaInvoice
        from app.services.lava.checkout import LavaCheckoutError, LavaCheckoutService
        from app.services.lava.config import LavaConfigService, config_from_dict
        from tests.lava_fakes import FakeLava, OFFER_ID, make_runtime

        async with pg_sessions(PG_URL) as sessions:
            reporter = reporter_for(sessions)
            fake = FakeLava()
            fake.unavailable = True
            runtime = make_runtime(sessions, fake)
            checkout = LavaCheckoutService(runtime)
            async with sessions() as db, db.begin():
                await LavaConfigService(db).save(config_from_dict({
                    "checkout_mode": "both", "currency": "USD",
                    "plans": {"1_month": {"enabled": True, "offer_id": OFFER_ID,
                                          "price": {"amount": "10.00", "currency": "USD"},
                                          "regional_prices": {"RUB": "900.00"}}},
                }))

            async def start(currency):
                return await checkout.start(
                    sessions, user_id=1, plan_type="1_month", email="buyer@example.com",
                    source="pwa", language="ru", context_mode="subscription",
                    currency=currency)

            async def provider_failure():
                with self.assertRaises(LavaCheckoutError) as ctx:
                    await start("RUB")
                self.assertEqual((ctx.exception.code, ctx.exception.status),
                                 ("provider_unavailable", 503))
                self.assertTrue(any(method == "POST" and path == "/api/v3/invoice"
                                    for method, path in fake.calls))
                async with sessions() as db:
                    invoice = (await db.scalars(select(LavaInvoice))).one()
                    self.assertEqual((invoice.currency, invoice.status), ("RUB", "failed"))

            with patch.object(backend, "reporter", reporter):
                with self.assertRaises(LavaCheckoutError) as invalid:
                    await start("CNY")
                self.assertEqual(invalid.exception.code, "plan_unavailable")
                self.assertFalse(fake.calls)
                await reporter.drain()
                async with sessions() as db:
                    self.assertIsNone(await db.scalar(select(DiagnosticIncident.id)))
                    self.assertIsNone(await db.scalar(select(LavaInvoice.id)))

                incident = await assert_monitoring_chain(
                    self, platform="server", feature="pwa_pro_checkout", failure="provider_failed",
                    site="v3_pwa_subscription_lava_start", sessions=sessions, reporter=reporter,
                    trigger=provider_failure, inbox_route="/api/admin/v1/inbox/list")
                self.assertEqual(incident.severity, "critical")

    async def test_learner_route_5xx_reaches_postgres_through_the_middleware(self):
        async with pg_sessions(PG_URL) as sessions:
            reporter = reporter_for(sessions)
            app = FastAPI()

            from app import main
            from app.db.models.course_progress import CourseProgress
            from sqlalchemy import func, select

            app.post("/api/v3/lesson/complete")(main.v3_course_lesson_complete)
            app.add_middleware(DiagnosticMiddleware, reporter_obj=reporter)

            async def route_5xx():
                # Enter the real signed handler and its real PostgreSQL lookup.
                # Inject the failure at the lesson service boundary, after auth.
                failure = AsyncMock(side_effect=RuntimeError("synthetic lesson service failure"))
                async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False),
                                       base_url="http://test") as client:
                    with (patch.object(main, "async_session_maker", sessions),
                          patch.object(main, "_v3_complete_lesson_for_canonical_actor", failure)):
                        headers = {"X-Telegram-Init-Data": signed(main.settings.BOT_TOKEN)}
                        response = await client.post("/api/v3/lesson/complete", headers=headers, json={"lesson_id": 1})
                        self.assertEqual(response.status_code, 500)
                        failure.assert_awaited_once()
                async with sessions() as db:
                    self.assertEqual(await db.scalar(select(func.count()).select_from(CourseProgress)), 0)

            await assert_monitoring_chain(
                self, platform="server", feature="lessons", failure="server_exception",
                site="v3_lesson_complete", sessions=sessions, reporter=reporter, trigger=route_5xx,
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
