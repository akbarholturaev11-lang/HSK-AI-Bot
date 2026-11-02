"""Real native source facts, migration, retry/races and analysis-only expiry."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, func, insert, select, update

from app.db.base import Base
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.smart_reminder_analysis import (
    EVENT, MONTHLY, RAW_RETENTION, UNAVAILABLE_OUTCOMES, SmartReminderAnalysisService, oldest_month,
)
from tests import test_smart_reminder_android as android

ATTEMPT, GRANT, JOB, PG_URL = android.ATTEMPT, android.GRANT, android.JOB, android.PG_URL

spec = importlib.util.spec_from_file_location("analysis_0137", Path(__file__).resolve().parents[1] /
    "alembic/versions/0137_smart_analysis.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class AnalysisChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = android.PostgreSQLAndroidProtocolTests if self.postgres else android.SQLiteAndroidProtocolTests
        self.case = cls(methodName="test_due_is_non_persisting_and_claim_commits_once_before_response")
        await self.case.asyncSetUp()
        self.engine, self.sessions = self.case.engine, self.case.sessions
        self.moment = self.case.tick
        self.analysis = SmartReminderAnalysisService(self.sessions, clock=lambda: self.moment)
        async with self.sessions.begin() as session:
            await session.execute(update(JOB).values(created_at=self.moment, updated_at=self.moment))
        async with self.engine.begin() as c:
            await c.run_sync(MONTHLY.drop)
            await c.run_sync(EVENT.drop)
            await c.run_sync(self.migrate, "upgrade")

    async def asyncTearDown(self):
        if hasattr(self, "case"):
            await self.case.asyncTearDown()

    @staticmethod
    def migrate(connection, operation):
        with Operations.context(MigrationContext.configure(connection)):
            getattr(migration, operation)()

    async def rows(self, table):
        async with self.sessions() as session:
            return (await session.execute(select(table))).mappings().all()

    async def capture(self, uid=1, job=None):
        return await self.analysis.capture_job(uid, job or self.case.job_id)

    async def stages(self):
        return {r["stage"] for r in await self.rows(EVENT)}

    async def second_job(self):
        job = dict((await self.rows(JOB))[0])
        job.update(id=str(uuid4()), user_id=2)
        async with self.sessions.begin() as session:
            await session.execute(insert(JOB).values(**job))
        return job["id"]

    async def test_reserved_fact_replay_counts_once_and_source_is_unchanged(self):
        before = await self.rows(JOB)
        self.assertEqual(await self.capture(), 1)
        self.assertEqual(await self.capture(), 0)
        self.assertEqual(await self.rows(JOB), before)
        self.assertEqual(await self.stages(), {"reserved"})
        self.assertEqual((await self.rows(MONTHLY))[0]["fact_count"], 1)
        raw = (await self.rows(EVENT))[0]
        self.assertEqual(raw["expires_at"] - raw["occurred_at"], RAW_RETENTION)

    async def test_actual_native_posted_receipt_is_never_shown_or_learning(self):
        grant = await self.case.claim()
        await self.case.receipt(grant)
        self.assertEqual(await self.capture(), 3)
        self.assertEqual(await self.capture(), 0)
        self.assertEqual(await self.stages(), {"reserved", "in_flight", "client_posted_unverified"})
        self.assertTrue(set(UNAVAILABLE_OUTCOMES).isdisjoint(await self.stages()))
        self.assertEqual(len(await self.rows(GRANT)), 1)

    async def test_in_flight_without_receipt_has_no_final_outcome(self):
        await self.case.claim()
        self.assertEqual(await self.capture(), 2)
        self.assertEqual(await self.stages(), {"reserved", "in_flight"})

    async def test_unknown_receipt_stays_unknown(self):
        grant = await self.case.claim()
        await self.case.receipt(grant, "client_outcome_unknown")
        self.assertEqual(await self.capture(), 3)
        self.assertIn("outcome_unknown", await self.stages())
        self.assertNotIn("client_posted_unverified", await self.stages())

    async def test_precall_decline_preserves_original_day_and_grant(self):
        grant = await self.case.claim()
        await self.case.receipt(grant, "client_declined_before_post")
        before = await self.rows(GRANT)
        self.assertEqual(await self.capture(), 4)
        self.assertIn("confirmed_not_displayed", await self.stages())
        self.assertEqual(await self.rows(GRANT), before)
        self.assertFalse((await self.case.claim())["dispatch_allowed"])

    async def test_unpaired_post_or_shown_state_is_not_display_proof(self):
        grant = await self.case.claim()
        for state in ("client_posted_unverified", "verified_shown"):
            async with self.sessions.begin() as session:
                await session.execute(update(ATTEMPT).values(state=state, resolved_at=self.moment))
            await self.capture()
        self.assertEqual(await self.stages(), {"reserved", "in_flight"})
        self.assertIsNone((await self.rows(GRANT))[0]["receipt_id"])

    async def test_provider_acceptance_is_only_accepted(self):
        async with self.sessions.begin() as session:
            await session.execute(update(JOB).values(selected_channel="telegram", selected_device_id=None,
                policy_version="smart-telegram-v1:synthetic"))
            await session.execute(insert(ATTEMPT).values(id=str(uuid4()), job_id=self.case.job_id,
                attempt_key="t" * 64, channel="telegram", grant_epoch=1, state="provider_accepted",
                prepared_at=self.moment, started_at=self.moment, resolved_at=self.moment,
                expires_at=self.case.expiry))
        self.assertEqual(await self.capture(), 3)
        self.assertIn("provider_accepted", await self.stages())
        self.assertTrue(set(UNAVAILABLE_OUTCOMES).isdisjoint(await self.stages()))

    async def test_shadow_and_unknown_policy_are_not_delivery_metrics(self):
        for version in ("smart-queue-shadow-v1", "unreviewed-v2"):
            async with self.sessions.begin() as session:
                await session.execute(update(JOB).values(policy_version=version))
            self.assertEqual(await self.capture(), 0)
        self.assertEqual(await self.rows(MONTHLY), [])

    async def test_foreign_missing_and_deleted_sources_cannot_create_facts(self):
        self.assertEqual(await self.capture(uid=2), 0)
        self.assertEqual(await self.capture(job=str(uuid4())), 0)
        self.assertEqual(await self.capture(uid=999), 0)
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(await self.rows(MONTHLY), [])

    async def test_submitted_deletion_prevents_recreation(self):
        await self.case._deletion()
        self.assertEqual(await self.capture(), 0)
        self.assertEqual(await self.rows(EVENT), [])

    async def test_future_sources_refused_and_exact_current_time_is_accepted(self):
        async with self.sessions.begin() as session:
            await session.execute(update(JOB).values(created_at=self.moment + timedelta(microseconds=1)))
        self.assertEqual(await self.capture(), 0)
        async with self.sessions.begin() as session:
            await session.execute(update(JOB).values(created_at=self.moment))
        self.assertEqual(await self.capture(), 1)

    async def test_retention_exact_boundary_and_expired_replay_preserve_source_evidence(self):
        grant = await self.case.claim()
        await self.case.receipt(grant)
        await self.capture()
        before = [await self.rows(table) for table in (JOB, ATTEMPT, GRANT)]
        self.moment += RAW_RETENTION
        dry = await self.analysis.retention()
        self.assertEqual((dry["expired_raw"], dry["removed_raw"]), (3, 0))
        result = await self.analysis.retention(execute=True)
        self.assertEqual(result["removed_raw"], 3)
        self.assertEqual(await self.capture(), 0)
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 3)
        self.assertEqual([await self.rows(table) for table in (JOB, ATTEMPT, GRANT)], before)

    async def test_bounded_cleanup_keeps_anonymous_totals_and_other_rows(self):
        other = await self.second_job()
        await self.capture()
        await self.capture(uid=2, job=other)
        self.moment += RAW_RETENTION
        self.assertEqual((await self.analysis.retention(execute=True, limit=1))["removed_raw"], 1)
        self.assertEqual(len(await self.rows(EVENT)), 1)
        self.assertEqual((await self.analysis.retention(execute=True, limit=1))["removed_raw"], 1)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 2)
        self.assertEqual(len(await self.rows(JOB)), 2)

    async def test_monthly_expiry_is_twelve_calendar_buckets(self):
        await self.capture()
        self.moment = self.moment.replace(year=self.moment.year + 1)
        result = await self.analysis.retention(execute=True)
        self.assertEqual(result["removed_monthly"], 1)
        self.assertEqual(await self.rows(MONTHLY), [])
        self.assertEqual(len(await self.rows(JOB)), 1)

    async def test_ambiguous_cleanup_flags_and_unbounded_batches_are_refused(self):
        for values in ({"execute": "false"}, {"execute": 1}, {"limit": True}, {"limit": 0}, {"limit": 129}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                await self.analysis.retention(**values)

    async def test_real_account_purge_removes_only_owned_analysis_and_retains_anonymous_totals(self):
        other = await self.second_job()
        await self.capture()
        await self.capture(uid=2, job=other)
        async with self.sessions.begin() as session:
            await UserRepository(session)._delete_account(await session.get(User, 1))
        self.assertEqual([r["user_id"] for r in await self.rows(EVENT)], [2])
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 2)
        self.assertEqual(await self.capture(), 0)

    async def test_fk_user_purge_is_additional_guard(self):
        await self.capture()
        async with self.sessions.begin() as session:
            await session.execute(delete(User).where(User.id == 1))
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)

    async def test_analysis_failure_rolls_back_analysis_without_erasing_committed_delivery(self):
        grant = await self.case.claim()
        await self.case.receipt(grant)
        before = [await self.rows(table) for table in (JOB, ATTEMPT, GRANT)]
        original = self.analysis._insert
        def fail_monthly(session, table):
            if table is MONTHLY:
                raise RuntimeError("synthetic-analysis-failure")
            return original(session, table)
        with patch.object(self.analysis, "_insert", side_effect=fail_monthly):
            with self.assertRaisesRegex(RuntimeError, "synthetic-analysis-failure"):
                await self.capture()
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(await self.rows(MONTHLY), [])
        self.assertEqual([await self.rows(table) for table in (JOB, ATTEMPT, GRANT)], before)

    async def test_actual_ddl_matches_models_and_populated_downgrade_refuses(self):
        async with self.engine.begin() as connection:
            self.assertEqual(await connection.run_sync(lambda c: compare_metadata(
                MigrationContext.configure(c), Base.metadata)), [])
            await connection.run_sync(self.migrate, "downgrade")
            await connection.run_sync(self.migrate, "upgrade")
        await self.capture()
        with self.assertRaisesRegex(RuntimeError, "Refusing populated"):
            async with self.engine.begin() as connection:
                await connection.run_sync(self.migrate, "downgrade")

    async def test_postgres_independent_capture_race_counts_once(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent transactions")
        self.assertEqual(sum(await asyncio.gather(self.capture(), self.capture())), 1)
        self.assertEqual(len(await self.rows(EVENT)), 1)
        self.assertEqual((await self.rows(MONTHLY))[0]["fact_count"], 1)


class SQLiteAnalysisTests(AnalysisChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLAnalysisTests(AnalysisChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class AnalysisContractTests(unittest.TestCase):
    def test_month_window_handles_leap_days_and_year_rollover(self):
        self.assertEqual(str(oldest_month(datetime(2024, 2, 29, tzinfo=timezone.utc))), "2023-03-01")
        self.assertEqual(str(oldest_month(datetime(2027, 1, 1, tzinfo=timezone.utc))), "2026-02-01")

    def test_aggregate_has_no_account_or_source_identifiers(self):
        self.assertEqual(set(MONTHLY.c.keys()), {"month", "stage", "channel", "fact_count"})
        self.assertTrue(set(EVENT.c.keys()).isdisjoint({"token", "device_id", "session_id", "body", "email", "lesson_order"}))
