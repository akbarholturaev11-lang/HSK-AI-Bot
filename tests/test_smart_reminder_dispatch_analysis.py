"""Committed runtime refusal reasons preserve protocol and outcome truth."""
import asyncio
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import AsyncMock

from sqlalchemy import select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.smart_reminder import SmartReminderCapability
from app.db.models.user import User
from app.services.smart_reminder_analysis import EVENT, MONTHLY
from tests import test_smart_reminder_analysis as source
from tests import test_smart_reminder_analysis_observer as fixture


class NativeGuardChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not source.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = fixture.PostgreSQLAndroidObservationTests if self.postgres else fixture.SQLiteAndroidObservationTests
        self.f = cls(methodName="test_actual_http_claim_receipt_and_retry_capture_once")
        await self.f.asyncSetUp()
        self.case, self.observer = self.f.case, self.f.observer
        self.observer.service.clock = lambda: self.case.tick

    async def asyncTearDown(self):
        if hasattr(self, "f"):
            await self.f.asyncTearDown()

    async def rows(self, table):
        return await self.f.fixture.rows(table)

    async def goal(self):
        # The native claim runs at the real clock (`tick = now`), but study()
        # defaults to 02:00 UTC of that day: between 00:00 and 02:00 UTC the
        # goal would lie in the future and the job is cancelled as
        # shadow_context_changed instead. Midnight is never after the claim.
        await self.case.study(order=5, xp=20, hour=0)

    async def test_actual_goal_refusal_records_original_reason_and_never_issues_grant(self):
        await self.goal()
        self.assertEqual((await self.case.claim())["reason"], "goal_completed")
        rows = await self.rows(EVENT)
        self.assertEqual({r["stage"] for r in rows}, {"reserved", "cancelled"})
        self.assertEqual(next(r["reason_code"] for r in rows if r["stage"] == "cancelled"), "goal_completed")
        self.assertEqual(await self.rows(source.GRANT), [])
        self.assertEqual(await self.rows(source.ATTEMPT), [])
        self.assertEqual((await self.case.claim())["reason"], "android_job_not_claimable")
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 2)

    async def test_refusal_response_body_and_committed_source_precede_capture(self):
        await self.goal()
        sent, seen = [], []
        original = self.observer.service.capture_job
        async def capture(uid, job):
            self.assertTrue(any(m["type"] == "http.response.body" and not m.get("more_body", False) for m in sent))
            async with self.case.sessions.begin() as session:
                if self.postgres:
                    await session.execute(select(User.id).where(User.id == uid).with_for_update(nowait=True))
                row = (await session.execute(select(source.JOB).where(source.JOB.c.id == job))).mappings().one()
                self.assertEqual((row["state"], row["reason_code"]), ("cancelled", "goal_completed"))
            seen.append(job)
            return await original(uid, job)
        self.observer.service.capture_job = capture
        headers, payload = await self.case.bearer(1), json.dumps(self.case.body()).encode()
        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}
        async def send(message):
            sent.append(dict(message))
        path = "/api/v3/android/smart-reminder/jobs/" + self.case.job_id + "/claim"
        scope = {"type": "http", "asgi": {"version": "3.0"}, "method": "POST", "scheme": "https",
            "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": [(b"content-type", b"application/json"), (b"authorization", headers["Authorization"].encode())],
            "server": ("claims.test", 443), "client": ("127.0.0.1", 1234), "http_version": "1.1"}
        await self.f.app(scope, receive, send)
        self.assertEqual(seen, [self.case.job_id])
        self.assertEqual(json.loads(next(m["body"] for m in sent if m["type"] == "http.response.body"))["reason"], "goal_completed")

    async def test_actual_expiry_and_d1_guards_are_source_derived(self):
        async with self.case.sessions.begin() as session:
            session.add(CourseMiniAppEvent(user_id=1, event_name="d1_recovery_assigned", source="d1_recovery_v1",
                payload_json='{"arm":"control"}', created_at=self.case.tick))
        self.assertEqual((await self.case.claim())["reason"], "d1_holdout_active")
        self.assertIn("d1_holdout_active", {r["reason_code"] for r in await self.rows(EVENT)})
        # Independent expired source frame, retaining the same logical day/job.
        async with self.case.sessions.begin() as session:
            await session.execute(update(source.JOB).values(state="pending"))
        self.case.tick = self.case.expiry + timedelta(microseconds=1)
        self.assertEqual((await self.case.claim())["reason"], "android_job_expired")
        self.assertIn("android_job_expired", {r["reason_code"] for r in await self.rows(EVENT)})
        self.assertEqual(await self.rows(source.GRANT), [])

    async def test_transient_gates_and_default_off_schedule_no_analysis(self):
        capture = AsyncMock(side_effect=AssertionError("nonterminal observation"))
        self.observer.service.capture_job = capture
        self.case.enabled = False
        self.assertEqual((await self.case.claim())["reason"], "android_dispatch_disabled")
        self.case.enabled = True
        self.case.options["calibration"] = None
        self.assertEqual((await self.case.claim())["reason"], "cadence_calibration_unconfigured")
        self.case.options.clear()
        self.case.coverage = False
        self.assertEqual((await self.case.claim())["reason"], "learning_coverage_unavailable")
        self.case.coverage = True
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderCapability).values(study_notifications_allowed=False))
        self.assertEqual((await self.case.claim())["reason"], "android_capability_unavailable")
        capture.assert_not_awaited()
        self.assertEqual(await self.rows(EVENT), [])

    async def test_analytics_failure_preserves_http_refusal_and_reconciliation_recovers_it(self):
        await self.goal()
        original = self.observer.service.capture_job
        self.observer.service.capture_job = AsyncMock(side_effect=RuntimeError("synthetic-private-proof"))
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            result = await self.case.claim()
        self.assertEqual(result["reason"], "goal_completed")
        self.assertEqual(logs.output, ["WARNING:app.services.smart_reminder_analysis:Smart analysis capture unavailable"])
        self.assertEqual(await self.rows(EVENT), [])
        self.observer.service.capture_job = original
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 2)
        self.assertIn("goal_completed", {r["reason_code"] for r in await self.rows(EVENT)})
        self.assertEqual(await self.rows(source.GRANT), [])

    async def test_unknown_and_wrong_channel_text_stays_generic_and_old_facts_immutable(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(source.JOB).values(state="cancelled", reason_code="synthetic-private-proof"))
        self.assertEqual(await self.observer.service.capture_job(1, self.case.job_id), 2)
        before = await self.rows(EVENT)
        self.assertIn("stored_cancelled", {r["reason_code"] for r in before})
        self.assertNotIn("synthetic-private-proof", repr(before))
        async with self.case.sessions.begin() as session:
            await session.execute(update(source.JOB).values(reason_code="goal_completed"))
        self.assertEqual(await self.observer.service.capture_job(1, self.case.job_id), 0)
        self.assertEqual(await self.rows(EVENT), before)
        async with self.case.sessions.begin() as session:
            await session.execute(update(source.JOB).values(state="expired", reason_code="telegram_expired"))
        self.assertEqual(await self.observer.service.capture_job(1, self.case.job_id), 1)
        self.assertIn("stored_expired", {r["reason_code"] for r in await self.rows(EVENT)})

    async def test_cancellation_reason_alone_is_never_display_or_decline_proof(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(source.JOB).values(state="cancelled", reason_code="client_declined_before_post"))
        await self.observer.service.capture_job(1, self.case.job_id)
        self.assertEqual({r["stage"] for r in await self.rows(EVENT)}, {"reserved", "cancelled"})
        self.assertEqual(await self.rows(source.GRANT), [])

    async def test_postgres_two_goal_claims_keep_one_original_guard_fact(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent claim/capture transactions")
        await self.goal()
        results = await asyncio.gather(self.case.claim(), self.case.claim())
        self.assertEqual({r["reason"] for r in results}, {"goal_completed", "android_job_not_claimable"})
        self.assertEqual(len(await self.rows(EVENT)), 2)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 2)
        self.assertEqual(await self.rows(source.GRANT), [])


class TelegramGuardChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not source.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = fixture.PostgreSQLTelegramObservationTests if self.postgres else fixture.SQLiteTelegramObservationTests
        self.f = cls(methodName="test_provider_io_has_no_analysis_and_committed_acceptance_is_captured")
        await self.f.asyncSetUp()
        self.case = self.f.case
        self.observer = self.case.service.analysis_observer

    async def asyncTearDown(self):
        if hasattr(self, "f"):
            await self.f.asyncTearDown()

    async def test_actual_goal_refusal_commits_before_capture_and_never_calls_provider(self):
        self.case.moment = self.case.tick
        await self.case.study(order=5, xp=20)
        original, seen = self.observer.service.capture_job, []
        async def capture(uid, job):
            async with self.case.sessions.begin() as session:
                if self.postgres:
                    await session.execute(select(User.id).where(User.id == uid).with_for_update(nowait=True))
                row = (await session.execute(select(source.JOB).where(source.JOB.c.id == job))).mappings().one()
                self.assertEqual((row["state"], row["reason_code"]), ("cancelled", "goal_completed"))
            seen.append(job)
            return await original(uid, job)
        self.observer.service.capture_job = capture
        result = await self.case.dispatch(self.f.lease)
        self.assertEqual(result.reason, "goal_completed")
        self.assertEqual(seen, [self.f.lease.job_id])
        rows = await self.f.rows(EVENT)
        self.assertEqual({r["stage"] for r in rows}, {"reserved", "cancelled"})
        self.assertIn("goal_completed", {r["reason_code"] for r in rows})
        self.case.bot.send_message.assert_not_awaited()
        attempt = (await self.f.rows(source.ATTEMPT))[0]
        self.assertEqual(attempt["state"], "cancelled")
        self.assertIsNone(attempt["started_at"])

    async def test_actual_d1_refusal_is_recorded_and_failure_preserves_it(self):
        async with self.case.sessions.begin() as session:
            session.add(CourseMiniAppEvent(user_id=1, event_name="d1_recovery_assigned", source="d1_recovery_v1",
                payload_json='{"arm":"control"}', created_at=self.case.tick))
        self.observer.service.capture_job = AsyncMock(side_effect=RuntimeError("synthetic-private-proof"))
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            result = await self.case.dispatch(self.f.lease)
        self.assertEqual(result.reason, "d1_holdout_active")
        self.case.bot.send_message.assert_not_awaited()
        self.assertEqual((await self.f.rows(source.JOB))[0]["reason_code"], "d1_holdout_active")
        self.assertEqual(await self.f.rows(EVENT), [])

    async def test_disabled_analysis_and_nonmutating_lease_loss_do_not_capture(self):
        self.observer.service.capture_job = AsyncMock(side_effect=AssertionError("nonterminal capture"))
        result = await self.case.dispatch(replace(self.f.lease, token="stale"))
        self.assertEqual(result.reason, "telegram_lease_lost")
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = False
        self.case.moment = self.case.tick
        await self.case.study(order=5, xp=20)
        self.assertEqual((await self.case.dispatch(self.f.lease)).reason, "goal_completed")
        self.observer.service.capture_job.assert_not_awaited()
        self.assertEqual(await self.f.rows(EVENT), [])
        self.case.bot.send_message.assert_not_awaited()


class SQLiteNativeGuardTests(NativeGuardChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLNativeGuardTests(NativeGuardChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class SQLiteTelegramGuardTests(TelegramGuardChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLTelegramGuardTests(TelegramGuardChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
