"""First-party aggregate exports: current auth, daily reuse and no PII cells."""
from contextlib import asynccontextmanager
import copy
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

from app.admin_api.pwa_read import StatisticsRequest, create_admin_pwa_read_router, statistics
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader
from app.admin_api.pwa_statistics_export import MAX_EXPORT_BYTES
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.payment import Payment
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


class StatisticsExportTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    def client(self, *, reader=None, sessions=None, cookie=fixtures.COOKIE):
        self.reader = reader or AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions)
        app = FastAPI()
        app.include_router(create_admin_pwa_read_router(settings_obj=self.settings,
            session_factory=sessions or self.sessions, statistics_reader=self.reader))
        return AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
            headers={"origin": "https://hskai.app"}, cookies={ADMIN_PWA_COOKIE_NAME: cookie} if cookie else {})

    async def export(self, client, format="json", **fields):
        return await client.post("/api/admin/v1/statistics/export", json={"format": format, **fields})

    async def test_real_json_csv_share_the_dashboard_snapshot_without_aggregate_sql_or_writes(self):
        queries = []
        def observe(conn, cursor, statement, parameters, context, many):
            queries.append(statement.strip())
        event.listen(self.engine.sync_engine, "before_cursor_execute", observe)
        try:
            async with self.client() as client:
                dashboard = (await client.post("/api/admin/v1/statistics", json={})).json()
                cold_count = len(queries)
                first = await self.export(client)
                self.assertEqual(first.status_code, 200, first.text)
                data = first.json()
                self.assertEqual(data["generated_at"], dashboard["generated_at"])
                self.assertEqual(data["expires_at"], dashboard["snapshot"]["expires_at"])
                values = {row["metric"]: row["value"] for row in data["metrics"]}
                self.assertEqual(values["users_total"], 3)
                self.assertEqual(values["payments_by_status.pending"], 1)
                self.assertIn("denominator", data["metric_definitions"]["registration_conversion"])
                second = await self.export(client, "csv")
                self.assertEqual(second.status_code, 200, second.text)
                rows = list(csv.DictReader(io.StringIO(second.text)))
                self.assertEqual(len(rows), len(data["metrics"]))
                self.assertEqual(rows[0]["generated_at"], dashboard["generated_at"])
                self.assertEqual(rows[0]["expires_at"], data["expires_at"])
                self.assertTrue(all(row["source"] == data["source"] and row["definition"] and row["date_basis"] for row in rows))
                self.assertEqual([q for q in queries[cold_count:] if "count(" in q.lower()], [])
                self.assertTrue(all(q.lower().startswith("select ") for q in queries))
                self.assertEqual(len([q for q in queries if "FROM ai_usage_events" in q]), 1)
                for response in (first, second):
                    self.assertEqual(response.headers["cache-control"], "no-store")
                    self.assertEqual(response.headers["x-content-type-options"], "nosniff")
                    self.assertTrue(response.headers["content-disposition"].startswith('attachment; filename="hskai-statistics-overall-weekly-'))
                    self.assertNotIn("set-cookie", response.headers)
                    self.assertLess(len(response.content), MAX_EXPORT_BYTES)
                    for private in ("user_id", "telegram_id", "screenshot_file_id", "synthetic-receipt", fixtures.COOKIE):
                        self.assertNotIn(private, response.text)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", observe)

    async def test_all_allowlisted_platform_periods_preserve_real_scope_and_missing_values(self):
        async with self.client() as client:
            for platform in ("overall", "android", "macos", "windows", "telegram", "iphone_pwa"):
                for period in ("weekly", "monthly", "all_time"):
                    with self.subTest(platform=platform, period=period):
                        response = await self.export(client, platform=platform, period=period)
                        self.assertEqual(response.status_code, 200, response.text)
                        data = response.json()
                        self.assertEqual((data["platform"], data["period"]), (platform, period))
                        self.assertEqual(data["since"] is None, period == "all_time")
                        if platform in ("telegram", "iphone_pwa"):
                            self.assertFalse(data["available"])
                            self.assertEqual(data["metrics"], [])
                            rows = list(csv.DictReader(io.StringIO((await self.export(client, "csv", platform=platform, period=period)).text)))
                            self.assertEqual(len(rows), 1)
                            self.assertEqual(rows[0]["value"], "")
                            self.assertTrue(rows[0]["reason"])
                        elif platform in ("macos", "windows"):
                            self.assertFalse(data["scope"]["period_filter_applied"])
                            self.assertEqual(len(data["metrics"]), 3)
                        elif platform == "android":
                            self.assertEqual(data["scope"]["active"], "rolling_1_7_30_days")
                            self.assertEqual(len(data["metrics"]), 28)
                        else:
                            percent = next(row for row in data["metrics"] if row["metric"] == "registration_conversion.percent")
                            self.assertEqual(percent["value"], 0.0)

    async def test_currency_lineage_is_separate_and_spreadsheet_formulas_are_rejected(self):
        async with self.sessions() as db:
            db.add_all([Payment(user_id=1, amount=10, currency="USD", plan_type="1_month", payment_status="approved"),
                        Payment(user_id=2, amount=25, currency="TJS", plan_type="1_month", payment_status="approved")])
            await db.commit()
        async with self.client() as client:
            response = await self.export(client)
            money = [row for row in response.json()["metrics"] if row["metric"].startswith("approved_amounts_by_currency.")]
            self.assertEqual({row["unit"]: row["value"] for row in money}, {"TJS": 25, "USD": 10})
        for currency in ("=1+1", "+USD", "@USD", "\tUSD", "usd", "USD\n"):
            with self.subTest(currency=currency):
                async def poisoned(db, query):
                    data = await statistics(db, query)
                    data["metrics"]["approved_amounts_by_currency"] = [{"currency": currency, "amount": 1}]
                    return data
                reader = AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions, loader=poisoned)
                async with self.client(reader=reader) as client:
                    response = await self.export(client, "csv")
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertNotIn(currency, response.text)

    async def test_unknown_nested_private_fields_are_omitted_and_bad_values_fail_closed(self):
        async def poisoned(db, query):
            data = copy.deepcopy(await statistics(db, query))
            for container in (data["metrics"], data["scope"], data["metric_definitions"]):
                container["private"] = {"email": "do-not-export@example.invalid", "token": "secret-export-canary"}
            return data
        reader = AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions, loader=poisoned)
        async with self.client(reader=reader) as client:
            for format in ("json", "csv"):
                response = await self.export(client, format)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn("secret-export-canary", response.text)
                self.assertNotIn("do-not-export", response.text)
            original = await reader(StatisticsRequest())
            from app.admin_api.pwa_read import StatisticsExportRequest
            from app.admin_api.pwa_statistics_export import render_statistics_export
            for value in (True, "=1+1", -1, float("nan"), float("inf"), 2**64, {"email": "private"}):
                data = copy.deepcopy(original)
                data["metrics"]["users_total"] = value
                with self.assertRaises(ValueError):
                    render_statistics_export(data, StatisticsExportRequest(format="csv"))
            with patch("app.admin_api.pwa_statistics_export.MAX_EXPORT_BYTES", 1), self.assertRaises(ValueError):
                render_statistics_export(original, StatisticsExportRequest(format="json"))
            empty = copy.deepcopy(original)
            empty["metrics"]["registration_conversion"] = {"registered_accounts": 0, "converted_accounts": 0, "percent": None}
            response = render_statistics_export(empty, StatisticsExportRequest(format="json"))
            self.assertIsNone(next(row["value"] for row in json.loads(response.body)["metrics"] if row["metric"] == "registration_conversion.percent"))
            for changes in (
                {"metrics": {**original["metrics"], "approved_amounts_by_currency": [{}] * 33}},
                {"generated_at": "2020-01-01T00:00:00+00:00"},
                {"platform": "android"}, {"since": "2020-01-01"},
            ):
                with self.assertRaises(ValueError):
                    render_statistics_export({**original, **changes}, StatisticsExportRequest(format="json"))

    async def test_strict_shape_csrf_origin_cookie_only_and_disabled_gate(self):
        async with self.client() as client:
            for body in ({}, {"format": "xml"}, {"format": "CSV"}, {"format": True},
                         {"format": "csv", "period": "custom"}, {"format": "json", "platform": "all"},
                         *({"format": "json", key: value} for key, value in
                           (("user_id", 1), ("force_refresh", True), ("since", "2020-01-01"), ("url", "https://example.invalid")))):
                self.assertEqual((await client.post("/api/admin/v1/statistics/export", json=body)).status_code, 400)
            for content in ('{"format":"json","format":"csv"}', '[]', '"csv"', '{', 'x'*2049):
                response = await client.post("/api/admin/v1/statistics/export", content=content, headers={"content-type": "application/json"})
                self.assertEqual(response.status_code, 400)
            self.assertEqual((await client.get("/api/admin/v1/statistics/export")).status_code, 405)
            for headers in ({"origin": "https://evil.invalid"}, {"origin": "null"}, {"sec-fetch-site": "cross-site"}):
                response = await client.post("/api/admin/v1/statistics/export", json={"format": "json"}, headers=headers)
                self.assertEqual(response.status_code, 403)
            self.settings.ADMIN_PWA_ENABLED = False
            self.assertEqual((await self.export(client)).status_code, 404)
        self.settings.ADMIN_PWA_ENABLED = True
        async with self.client(cookie="") as client:
            client.headers["authorization"] = "Bearer " + fixtures.COOKIE
            self.assertEqual((await self.export(client)).status_code, 401)

    async def test_current_admin_auth_is_checked_even_when_snapshot_is_warm(self):
        async with self.client() as client:
            self.assertEqual((await self.export(client)).status_code, 200)
            for field, value in (("auth_method", "google_telegram"), ("revoked_at", datetime.now(timezone.utc)),
                                 ("expires_at", datetime.now(timezone.utc)-timedelta(seconds=1))):
                async with self.sessions() as db:
                    row = await db.get(AdminPwaSession, self.session_id)
                    original = getattr(row, field)
                    setattr(row, field, value)
                    await db.commit()
                self.assertEqual((await self.export(client)).status_code, 401)
                async with self.sessions() as db:
                    setattr(await db.get(AdminPwaSession, self.session_id), field, original)
                    await db.commit()
            self.settings.admin_id_list = []
            self.assertEqual((await self.export(client)).status_code, 401)
            self.settings.admin_id_list = [9001]
            async with self.sessions() as db:
                (await db.get(User, 101)).status = "blocked"
                await db.commit()
            self.assertEqual((await self.export(client)).status_code, 401)

    async def test_no_open_auth_session_during_cache_wait_and_late_revocation_denies_file(self):
        opened = 0
        @asynccontextmanager
        async def sessions():
            nonlocal opened
            async with self.sessions() as db:
                opened += 1
                try:
                    yield db
                finally:
                    opened -= 1
        reader = AdminPwaStatisticsReader(settings_obj=self.settings, session_factory=self.sessions)
        async def revoke_during_read(query):
            self.assertEqual(opened, 0)
            data = await reader(query)
            async with self.sessions() as db:
                (await db.get(AdminPwaSession, self.session_id)).revoked_at = datetime.now(timezone.utc)
                await db.commit()
            return data
        async with self.client(reader=revoke_during_read, sessions=sessions) as client:
            response = await self.export(client)
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("metrics", response.text)
        self.assertEqual(opened, 0)

    async def test_cache_failure_is_private_and_does_not_return_a_partial_file(self):
        async with self.client(reader=AsyncMock(side_effect=RuntimeError("private cache detail"))) as client:
            response = await self.export(client)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("private cache detail", response.text)
            self.assertNotIn("content-disposition", response.headers)
