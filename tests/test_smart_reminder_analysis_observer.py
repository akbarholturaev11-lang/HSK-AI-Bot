"""Optional source observation must never change a committed delivery outcome."""
import ast
import asyncio
import contextlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.api.smart_reminder import create_smart_reminder_router
from app.db.models.user import User
from app.services.smart_reminder_analysis import (
    EVENT, MONTHLY, RAW_RETENTION, SmartReminderAnalysisObserver,
)
from tests import test_smart_reminder_analysis as analysis_fixture
from tests import test_smart_reminder_telegram as telegram_fixture


class ObserverTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_and_nonboolean_flags_do_no_sql_or_work(self):
        factory = Mock(side_effect=AssertionError("disabled SQL"))
        for value in (False, None, 1, "true"):
            observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=value), factory)
            self.assertIsNone(await observer.capture_job(1, "job"))
            self.assertIsNone(await observer.tick())
            self.assertIsNone(await observer.reconcile_tick())
            await observer.run_retention()
            await observer.run_reconciliation()
        factory.assert_not_called()

    async def test_capture_failure_has_no_error_payload_or_fabricated_zero(self):
        observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True), Mock())
        observer.service.capture_job = AsyncMock(side_effect=RuntimeError("synthetic-private-proof"))
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            self.assertIsNone(await observer.capture_job(1, "job"))
        self.assertEqual(logs.output, ["WARNING:app.services.smart_reminder_analysis:Smart analysis capture unavailable"])

    async def test_capture_timeout_cleans_up_and_parent_cancellation_propagates(self):
        observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True), Mock(), timeout=.01)
        cleaned = asyncio.Event()
        async def hang(*args):
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        observer.service.capture_job = hang
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            self.assertIsNone(await observer.capture_job(1, "job"))
        self.assertTrue(cleaned.is_set())
        observer.service.capture_job = AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):
            await observer.capture_job(1, "job")

    async def test_retention_failure_is_isolated_and_live_disable_ends_worker(self):
        settings = SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True)
        observer = SmartReminderAnalysisObserver(settings, Mock(), interval=.001)
        calls = []
        async def retention(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("synthetic-private-proof")
            settings.SMART_REMINDER_ANALYSIS_ENABLED = False
            return {"removed_raw": 0}
        observer.service.retention = retention
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            await asyncio.wait_for(observer.run_retention(), 1)
        self.assertEqual(calls, [{"execute": True, "limit": 128}] * 2)
        self.assertNotIn("synthetic-private-proof", " ".join(logs.output))

    async def test_retention_cancellation_releases_running_operation(self):
        observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True), Mock())
        started, cleaned = asyncio.Event(), asyncio.Event()
        async def hang(**kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        observer.service.retention = hang
        task = asyncio.create_task(observer.run_retention())
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(cleaned.is_set())

    async def test_invalid_technical_bounds_are_refused(self):
        for values in ({"timeout": 0}, {"timeout": float("nan")}, {"interval": float("inf")},
                       {"timeout": True}, {"batch": True}, {"batch": 129}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                SmartReminderAnalysisObserver(SimpleNamespace(), Mock(), **values)


class AndroidObservationChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = analysis_fixture.PostgreSQLAnalysisTests if self.postgres else analysis_fixture.SQLiteAnalysisTests
        self.fixture = cls(methodName="test_reserved_fact_replay_counts_once_and_source_is_unchanged")
        await self.fixture.asyncSetUp()
        self.case = self.fixture.case
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = True
        self.observer = SmartReminderAnalysisObserver(self.case.settings, self.case.sessions,
            clock=lambda: self.fixture.moment, timeout=1)
        self.app = FastAPI()
        self.app.include_router(create_smart_reminder_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings, android_delivery_factory=self.case.service,
            analysis_observer=self.observer))
        await self.case.client.aclose()
        self.case.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="https://claims.test")

    async def asyncTearDown(self):
        if hasattr(self, "fixture") and hasattr(self.fixture, "case"):
            await self.fixture.asyncTearDown()

    async def test_actual_http_claim_receipt_and_retry_capture_once(self):
        grant = await self.case.claim()
        self.assertEqual(await self.fixture.stages(), {"reserved", "in_flight"})
        _, receipt = await self.case.receipt(grant)
        await self.case.receipt(grant, body=receipt)
        self.assertEqual(await self.fixture.stages(), {"reserved", "in_flight", "client_posted_unverified"})
        self.assertEqual(sum(row["fact_count"] for row in await self.fixture.rows(MONTHLY)), 3)
        self.assertEqual(len(await self.fixture.rows(analysis_fixture.GRANT)), 1)

    async def test_response_body_and_committed_source_precede_capture(self):
        sent, observed = [], []
        original = self.observer.service.capture_job
        async def inspect_source(uid, job):
            self.assertTrue(any(m["type"] == "http.response.body" and not m.get("more_body", False) for m in sent))
            # Independent PG transaction proves the original User lock released.
            async with self.case.sessions.begin() as session:
                if self.postgres:
                    await session.execute(text("SET LOCAL lock_timeout = '500ms'"))
                await session.execute(select(User.id).where(User.id == uid).with_for_update())
                self.assertEqual(len(await self.fixture.rows(analysis_fixture.GRANT)), 1)
            observed.append((uid, job))
            return await original(uid, job)
        self.observer.service.capture_job = inspect_source
        payload = json.dumps(self.case.body()).encode()
        headers = await self.case.bearer(1)
        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}
        async def send(message):
            sent.append(dict(message))
        path = "/api/v3/android/smart-reminder/jobs/" + self.case.job_id + "/claim"
        scope = {"type": "http", "asgi": {"version": "3.0"}, "method": "POST", "scheme": "https",
            "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": [(b"content-type", b"application/json"), (b"authorization", headers["Authorization"].encode())],
            "server": ("claims.test", 443), "client": ("127.0.0.1", 1234), "http_version": "1.1"}
        await self.app(scope, receive, send)
        body = json.loads(next(m["body"] for m in sent if m["type"] == "http.response.body"))
        self.assertTrue(body["dispatch_allowed"])
        self.assertEqual(observed, [(1, self.case.job_id)])
        self.assertEqual(await self.fixture.stages(), {"reserved", "in_flight"})

    async def test_analysis_failure_does_not_change_grant_or_receipt_http_success(self):
        self.observer.service.capture_job = AsyncMock(side_effect=RuntimeError("synthetic-private-proof"))
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            grant = await self.case.claim()
            ack, _ = await self.case.receipt(grant)
        self.assertTrue(grant["dispatch_allowed"])
        self.assertTrue(ack["ok"])
        self.assertEqual((await self.fixture.rows(analysis_fixture.ATTEMPT))[0]["state"], "client_posted_unverified")
        self.assertEqual(await self.fixture.rows(EVENT), [])
        self.assertNotIn("synthetic-private-proof", " ".join(logs.output))

    async def test_capture_timeout_leaves_committed_grant_and_response_intact(self):
        self.observer.timeout = .01
        stopped = asyncio.Event()
        async def hang(*args):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        self.observer.service.capture_job = hang
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            grant = await self.case.claim()
        self.assertTrue(grant["dispatch_allowed"])
        self.assertTrue(stopped.is_set())
        self.assertEqual(len(await self.fixture.rows(analysis_fixture.GRANT)), 1)

    async def test_disabled_hook_does_no_analysis_work_on_valid_claim_and_receipt(self):
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = False
        self.observer.service.capture_job = AsyncMock(side_effect=AssertionError("disabled analytics SQL"))
        grant = await self.case.claim()
        await self.case.receipt(grant)
        self.observer.service.capture_job.assert_not_awaited()
        self.assertEqual(await self.fixture.rows(EVENT), [])

    async def test_get_auth_forgery_and_payload_error_never_schedule_capture(self):
        self.observer.service.capture_job = AsyncMock(side_effect=AssertionError("not an outcome"))
        base = "/api/v3/android/smart-reminder"
        for suffix in ("/mode", "/due", "/capability", "/preferences"):
            response = await self.case.client.get(base + suffix, headers=await self.case.bearer(1))
            self.assertEqual(response.status_code, 200)
        path = base + "/jobs/" + self.case.job_id + "/claim"
        self.assertEqual((await self.case.client.post(path, json=self.case.body())).status_code, 401)
        self.assertEqual((await self.case.client.post(path, headers=await self.case.bearer(2), json=self.case.body())).status_code, 404)
        self.assertEqual((await self.case.client.post(path, headers=await self.case.bearer(1),
            json=self.case.body() | {"verified_shown": True})).status_code, 422)
        self.observer.service.capture_job.assert_not_awaited()

    async def test_retention_tick_removes_only_expired_analysis(self):
        grant = await self.case.claim()
        await self.case.receipt(grant)
        before = [await self.fixture.rows(t) for t in (analysis_fixture.JOB, analysis_fixture.ATTEMPT, analysis_fixture.GRANT)]
        self.fixture.moment += RAW_RETENTION
        self.assertEqual((await self.observer.tick())["removed_raw"], 3)
        self.assertEqual([await self.fixture.rows(t) for t in (analysis_fixture.JOB, analysis_fixture.ATTEMPT, analysis_fixture.GRANT)], before)

    async def test_postgres_racing_claim_callbacks_keep_single_issuance_and_counts(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent native transactions")
        results = await asyncio.gather(self.case.claim(), self.case.claim())
        self.assertEqual(sum(r["dispatch_allowed"] for r in results), 1)
        self.assertEqual(len(await self.fixture.rows(analysis_fixture.GRANT)), 1)
        self.assertEqual(sum(r["fact_count"] for r in await self.fixture.rows(MONTHLY)), 2)

    async def test_postgres_capture_lock_timeout_leaks_no_lock_or_delivery_change(self):
        if not self.postgres:
            self.skipTest("PostgreSQL real post-commit lock wait")
        original = self.observer.service.capture_job
        self.observer.timeout = .05
        async def lock_then_capture(uid, job):
            async with self.case.sessions.begin() as holder:
                await holder.execute(select(User.id).where(User.id == uid).with_for_update())
                return await original(uid, job)
        self.observer.service.capture_job = lock_then_capture
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            grant = await self.case.claim()
        self.assertTrue(grant["dispatch_allowed"])
        self.assertEqual(await self.fixture.rows(EVENT), [])
        async with self.case.sessions.begin() as session:
            await session.execute(text("SET LOCAL lock_timeout = '500ms'"))
            await session.execute(select(User.id).where(User.id == 1).with_for_update())
        self.observer.service.capture_job = original
        self.observer.timeout = 1
        self.assertTrue((await self.case.receipt(grant))[0]["ok"])
        self.assertEqual(len(await self.fixture.rows(analysis_fixture.GRANT)), 1)


class SQLiteAndroidObservationTests(AndroidObservationChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLAndroidObservationTests(AndroidObservationChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class TelegramObservationChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not analysis_fixture.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = telegram_fixture.PostgreSQLTelegramTests if self.postgres else telegram_fixture.SQLiteTelegramTests
        self.case = cls(methodName="test_hold_is_sticky_for_both_server_study_paths_but_changes_no_consent")
        await self.case.asyncSetUp()
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = True
        await self.case.active()
        prepared = await self.case.prepare()
        self.assertEqual(prepared.reason, "telegram_planned")
        self.case.tick = self.case.tick.replace(hour=14)
        self.lease = await self.case.claim(prepared.job_id)
        self.assertEqual(self.lease.reason, "telegram_claimed")

    async def asyncTearDown(self):
        if hasattr(self, "case") and hasattr(self.case, "engine"):
            await self.case.asyncTearDown()

    async def rows(self, table):
        async with self.case.sessions() as session:
            return (await session.execute(select(table))).mappings().all()

    async def test_provider_io_has_no_analysis_and_committed_acceptance_is_captured(self):
        original = self.case.service.analysis_observer.service.capture_job
        seen = []
        async def capture(uid, job):
            async with self.case.sessions.begin() as session:
                if self.postgres:
                    await session.execute(text("SET LOCAL lock_timeout = '500ms'"))
                await session.execute(select(User.id).where(User.id == uid).with_for_update())
                row = (await self.rows(analysis_fixture.ATTEMPT))[0]
                self.assertEqual(row["state"], "provider_accepted")
            seen.append(job)
            return await original(uid, job)
        self.case.service.analysis_observer.service.capture_job = capture
        async def send(envelope):
            self.assertEqual(await self.rows(EVENT), [])
            return await self.case.send(envelope)
        result = await self.case.dispatch(self.lease, send)
        self.assertEqual(result.reason, "telegram_provider_accepted")
        self.assertEqual(seen, [self.lease.job_id])
        self.assertEqual({r["stage"] for r in await self.rows(EVENT)}, {"reserved", "in_flight", "provider_accepted"})
        self.case.bot.send_message.assert_awaited_once()

    async def test_provider_timeout_remains_unknown_in_source_and_analysis(self):
        async def timeout(envelope):
            raise asyncio.TimeoutError("synthetic provider")
        result = await self.case.dispatch(self.lease, timeout)
        self.assertEqual(result.reason, "telegram_unknown")
        self.assertEqual({r["stage"] for r in await self.rows(EVENT)}, {"reserved", "in_flight", "outcome_unknown"})
        self.assertEqual((await self.rows(analysis_fixture.ATTEMPT))[0]["state"], "unknown")

    async def test_analytics_failure_preserves_accepted_source_and_no_replay(self):
        observer = self.case.service.analysis_observer
        observer.service.capture_job = AsyncMock(side_effect=RuntimeError("synthetic-private-proof"))
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            result = await self.case.dispatch(self.lease)
        self.assertEqual(result.reason, "telegram_provider_accepted")
        self.assertEqual((await self.rows(analysis_fixture.ATTEMPT))[0]["state"], "provider_accepted")
        self.assertEqual(await self.rows(EVENT), [])
        await self.case.dispatch(self.lease)
        self.case.bot.send_message.assert_awaited_once()

    async def test_disabled_telegram_hook_does_no_analysis_sql(self):
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = False
        observer = self.case.service.analysis_observer
        observer.service.capture_job = AsyncMock(side_effect=AssertionError("disabled SQL"))
        self.assertEqual((await self.case.dispatch(self.lease)).reason, "telegram_provider_accepted")
        observer.service.capture_job.assert_not_awaited()
        self.assertEqual(await self.rows(EVENT), [])


class SQLiteTelegramObservationTests(TelegramObservationChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLTelegramObservationTests(TelegramObservationChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class LifespanObservationTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, enabled):
        source = Path(__file__).resolve().parents[1] / "app/main.py"
        node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.AsyncFunctionDef) and n.name == "lifespan")
        started, cancelled = asyncio.Event(), asyncio.Event()
        reconcile_started, reconcile_cancelled = asyncio.Event(), asyncio.Event()
        async def block(*args):
            await asyncio.Event().wait()
        async def retention():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        async def reconciliation():
            reconcile_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                reconcile_cancelled.set()
        observer = Mock(return_value=SimpleNamespace(run_retention=retention, run_reconciliation=reconciliation))
        namespace = {"asynccontextmanager": contextlib.asynccontextmanager, "FastAPI": object,
            "asyncio": asyncio, "contextlib": contextlib, "init_db": AsyncMock(), "_seed_lessons": block,
            "dp": SimpleNamespace(start_polling=block), "bot": SimpleNamespace(session=SimpleNamespace(close=AsyncMock())),
            "_background_scheduler": block, "_desktop_auth_retention_scheduler": block,
            "settings": SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=False, SMART_REMINDER_ANALYSIS_ENABLED=enabled,
                ADMIN_PWA_ENABLED=False, ADMIN_PWA_PUSH_ENABLED=False), "async_session_maker": Mock(),
            "SmartReminderAnalysisObserver": observer, "sender_config": lambda settings: None,
            "_study_ai_tasks": set(), "admin_pwa_due_campaigns": SimpleNamespace(close=AsyncMock()),
            "engine": SimpleNamespace(dispose=AsyncMock())}
        for name in ("statistics", "analytics", "feedback"):
            namespace["admin_pwa_" + name + "_reader"] = SimpleNamespace(aclose=AsyncMock())
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
        async with namespace["lifespan"](object()):
            if enabled is True:
                await asyncio.wait_for(started.wait(), 1)
                await asyncio.wait_for(reconcile_started.wait(), 1)
            else:
                await asyncio.sleep(0)
                observer.assert_not_called()
        if enabled is True:
            observer.assert_called_once()
            self.assertTrue(cancelled.is_set())
            self.assertTrue(reconcile_cancelled.is_set())
        namespace["engine"].dispose.assert_awaited_once()

    async def test_actual_lifespan_starts_independent_task_and_awaits_cancellation(self):
        await self.exercise(True)

    async def test_actual_lifespan_default_off_creates_no_analysis_task(self):
        from app.config import Settings
        self.assertFalse(Settings.model_fields["SMART_REMINDER_ANALYSIS_ENABLED"].default)
        await self.exercise(False)

    async def test_actual_lifespan_rejects_nonboolean_enable_values(self):
        for value in (None, 1, "false"):
            with self.subTest(value=value):
                await self.exercise(value)
