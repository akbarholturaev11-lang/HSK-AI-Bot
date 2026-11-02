"""Actual post-commit reserve/refusal observations, with no synthetic jobs."""
import asyncio
from dataclasses import replace
from datetime import timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, insert, select, update

from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.motivation_reminder_service import D1_RECOVERY_ASSIGNED_EVENT, D1_RECOVERY_EXPERIMENT
from app.services.smart_reminder_analysis import (
    EVENT, MONTHLY, RESERVATION, RAW_RETENTION, SmartReminderAnalysisObserver, SmartReminderAnalysisService,
)
from app.services.smart_reminder_preferences import SmartReminderError
from app.services.smart_reminder_shadow_queue import ReservationObservation
from app.services.smart_reminder_shadow_worker import SmartReminderShadowWorker
from tests import test_smart_reminder_analysis as analysis_fixture
from tests import test_smart_reminder_shadow_queue as queue_fixture


class ReservationBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_untrusted_observations_are_refused_before_sql(self):
        factory = Mock(side_effect=AssertionError("untrusted SQL"))
        service = SmartReminderAnalysisService(factory)
        from datetime import datetime, timezone
        valid = ReservationObservation(1, "a"*64, "shadow_refused", "master_off", datetime.now(timezone.utc))
        for source in (None, {}, replace(valid, user_id=True), replace(valid, event_key="?"*64),
                       replace(valid, stage="reserved"), replace(valid, reason_code="synthetic-private-proof"),
                       replace(valid, stage="shadow_reserved")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                await service.capture_reservation(source)
        factory.assert_not_called()

    async def test_disabled_strict_flags_create_no_capture_sql(self):
        factory = Mock(side_effect=AssertionError("disabled SQL"))
        for value in (False, None, 1, "true"):
            observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=value), factory)
            self.assertIsNone(await observer.capture_reservation(None))
        factory.assert_not_called()


class ReservationSourceChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not analysis_fixture.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = queue_fixture.PostgreSQLQueueTests if self.postgres else queue_fixture.SQLiteQueueTests
        self.q = cls(methodName="test_reservation_commits_frozen_shadow_only_and_retry_never_extends_it")
        await self.q.asyncSetUp()
        self.observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True),
            self.q.sessions, clock=lambda: self.q.tick)
        self.q.queue.analysis_observer = self.observer

    async def asyncTearDown(self):
        if hasattr(self, "q"):
            await self.q.asyncTearDown()

    async def rows(self, table):
        async with self.q.sessions() as session:
            return (await session.execute(select(table))).mappings().all()

    async def test_actual_off_refusal_needs_no_job_and_repeat_is_one_reason_fact(self):
        await self.q.update_pref(master_enabled=False)
        for _ in range(3):
            self.assertEqual((await self.q.reserve()).reason, "master_off")
            self.q.tick += timedelta(seconds=1)
        rows = await self.rows(RESERVATION)
        self.assertEqual([(r["stage"], r["reason_code"]) for r in rows], [("shadow_refused", "master_off")])
        self.assertEqual(rows[0]["expires_at"]-rows[0]["occurred_at"], RAW_RETENTION)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)
        self.assertEqual(await self.q.counts(), (0, 0))
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(set(RESERVATION.c.keys()), {"user_id", "event_key", "stage", "reason_code", "occurred_at", "expires_at"})

    async def test_actual_d1_before_policy_is_a_refusal_without_reservation(self):
        async with self.q.sessions.begin() as session:
            session.add(CourseMiniAppEvent(user_id=1, event_name=D1_RECOVERY_ASSIGNED_EVENT,
                source=D1_RECOVERY_EXPERIMENT, payload_json=json.dumps({"arm": "control"}), created_at=self.q.tick))
        self.assertEqual((await self.q.reserve()).reason, "d1_holdout_active")
        self.assertEqual((await self.rows(RESERVATION))[0]["reason_code"], "d1_holdout_active")
        self.assertEqual(await self.q.counts(), (0, 0))

    async def test_actual_goal_before_reservation_is_recorded(self):
        async with self.q.sessions.begin() as session:
            await self.q.accepted_lesson(session)
        self.assertEqual((await self.q.reserve()).reason, "goal_completed")
        self.assertEqual((await self.rows(RESERVATION))[0]["reason_code"], "goal_completed")
        self.assertEqual(await self.q.counts(), (0, 0))

    async def test_source_commit_and_user_lock_release_precede_capture(self):
        original, seen = self.observer.service.capture_reservation, []
        async def inspect(source):
            async with self.q.sessions.begin() as session:
                if self.postgres:
                    await session.execute(select(User.id).where(User.id == 1).with_for_update(nowait=True))
                jobs = (await session.execute(select(queue_fixture.JOB))).mappings().all()
                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0]["state"], "shadow")
                self.assertEqual((await session.execute(select(RESERVATION))).all(), [])
            seen.append(source)
            return await original(source)
        self.observer.service.capture_reservation = inspect
        result = await self.q.reserve()
        self.assertEqual(result.reason, "shadow_reserved")
        self.assertEqual(len(seen), 1)
        self.assertEqual((await self.rows(RESERVATION))[0]["stage"], "shadow_reserved")
        self.assertFalse(result.dispatch_allowed)

    async def test_existing_day_refusal_uses_its_actual_reason_not_old_cadence(self):
        await self.q.reserve()
        self.assertEqual((await self.q.reserve()).reason, "account_day_already_owned")
        self.assertEqual({r["reason_code"] for r in await self.rows(RESERVATION)}, {"shadow_reserved", "account_day_already_owned"})
        self.assertEqual(await self.q.counts(), (1, 0))
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 2)

    async def test_default_off_and_real_worker_queue_leave_source_result_unchanged(self):
        worker = SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=False), self.q.sessions,
            clock=lambda: self.q.tick)
        worker.queue.analysis_observer.service.capture_reservation = AsyncMock(side_effect=AssertionError("disabled capture"))
        self.q.queue = worker.queue
        self.assertEqual((await self.q.reserve()).reason, "shadow_reserved")
        worker.queue.analysis_observer.service.capture_reservation.assert_not_awaited()
        self.assertEqual(await self.rows(RESERVATION), [])
        self.assertEqual(await self.q.counts(), (1, 0))

    async def test_failure_timeout_and_parent_cancel_do_not_erase_committed_source(self):
        self.observer.service.capture_reservation = AsyncMock(side_effect=RuntimeError("synthetic-private-proof"))
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            self.assertEqual((await self.q.reserve()).reason, "shadow_reserved")
        self.assertEqual(logs.output, ["WARNING:app.services.smart_reminder_analysis:Smart reservation analysis unavailable"])
        cleaned = asyncio.Event()
        async def hang(source):
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        self.observer.timeout = .01
        self.observer.service.capture_reservation = hang
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            self.assertEqual((await self.q.reserve()).reason, "account_day_already_owned")
        self.assertTrue(cleaned.is_set())
        self.observer.service.capture_reservation = AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):
            await self.q.reserve()
        self.assertEqual(await self.q.counts(), (1, 0))
        self.assertEqual(await self.rows(RESERVATION), [])

    async def test_source_rollback_auth_and_deletion_errors_do_not_observe(self):
        capture = AsyncMock(side_effect=AssertionError("uncommitted observation"))
        self.observer.service.capture_reservation = capture
        with patch("app.services.smart_reminder_shadow_queue.insert", side_effect=RuntimeError("synthetic source rollback")):
            with self.assertRaises(RuntimeError):
                await self.q.reserve()
        with self.assertRaises(SmartReminderError):
            await self.q.reserve(actor=replace(self.q.actor, user_id=999))
        await self.q._deletion()
        with self.assertRaises(SmartReminderError):
            await self.q.reserve()
        capture.assert_not_awaited()
        self.assertEqual(await self.q.counts(), (0, 0))

    async def test_analysis_monthly_failure_rolls_back_detail_without_erasing_reservation(self):
        original = self.observer.service._insert
        def fail_monthly(session, table):
            if table is MONTHLY:
                raise RuntimeError("synthetic-private-proof")
            return original(session, table)
        with patch.object(self.observer.service, "_insert", side_effect=fail_monthly), \
             self.assertLogs("app.services.smart_reminder_analysis", level="WARNING"):
            self.assertEqual((await self.q.reserve()).reason, "shadow_reserved")
        self.assertEqual(await self.rows(RESERVATION), [])
        self.assertEqual(await self.rows(MONTHLY), [])
        self.assertEqual(await self.q.counts(), (1, 0))

    async def test_one_iana_local_day_is_not_split_at_utc_midnight(self):
        await self.q.update_pref(master_enabled=False, timezone_name="Pacific/Honolulu")
        self.q.tick = self.q.tick.replace(hour=23, minute=59)
        await self.q.reserve()
        self.q.tick += timedelta(minutes=2)
        await self.q.reserve()
        self.assertEqual(len(await self.rows(RESERVATION)), 1)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)

    async def test_scope_revision_day_unknown_zone_and_purged_replay_are_explicit(self):
        await self.q.update_pref(master_enabled=False, timezone_name=None)
        await self.q.reserve()
        first = (await self.rows(RESERVATION))[0]
        self.q.tick += timedelta(seconds=1)
        await self.q.reserve()
        self.assertEqual((await self.rows(RESERVATION))[0], first)
        await self.q.update_pref(revision=3)
        await self.q.reserve()
        self.q.tick += timedelta(days=1)
        await self.q.reserve()
        self.assertEqual(len(await self.rows(RESERVATION)), 3)
        source = ReservationObservation(1, first["event_key"], first["stage"], first["reason_code"],
            first["occurred_at"].replace(tzinfo=self.q.tick.tzinfo))
        self.q.tick += RAW_RETENTION
        dry = await self.observer.service.retention()
        self.assertEqual((dry["expired_reservations"], dry["removed_reservations"]), (3, 0))
        self.assertEqual((await self.observer.service.retention(execute=True, limit=1))["removed_reservations"], 1)
        await self.observer.service.retention(execute=True)
        self.assertEqual(await self.rows(RESERVATION), [])
        self.assertEqual(await self.observer.service.capture_reservation(source), 0)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 3)

    async def test_future_late_and_deleted_source_observations_are_withheld(self):
        sources = []
        self.observer.service.capture_reservation = AsyncMock(side_effect=lambda source: sources.append(source) or 0)
        await self.q.update_pref(master_enabled=False)
        await self.q.reserve()
        service = SmartReminderAnalysisService(self.q.sessions, clock=lambda: self.q.tick)
        self.assertEqual(await service.capture_reservation(replace(sources[0], observed_at=self.q.tick+timedelta(seconds=1))), 0)
        self.assertEqual(await service.capture_reservation(replace(sources[0], observed_at=self.q.tick-RAW_RETENTION)), 0)
        await self.q._deletion()
        self.assertEqual(await service.capture_reservation(sources[0]), 0)
        self.assertEqual(await self.rows(RESERVATION), [])

    async def test_real_account_purge_removes_owned_detail_and_retains_anonymous_total(self):
        await self.q.update_pref(master_enabled=False)
        await self.q.reserve()
        async with self.q.sessions.begin() as session:
            await UserRepository(session)._delete_account(await session.get(User, 1))
        self.assertEqual(await self.rows(RESERVATION), [])
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)

    async def test_populated_observation_or_anonymous_only_refuses_downgrade(self):
        await self.q.update_pref(master_enabled=False)
        await self.q.reserve()
        def downgrade(connection):
            with Operations.context(MigrationContext.configure(connection)):
                analysis_fixture.reservation_migration.downgrade()
        for raw in (True, False):
            if not raw:
                self.q.tick += RAW_RETENTION
                await self.observer.service.retention(execute=True)
            with self.assertRaisesRegex(RuntimeError, "Refusing populated reservation"):
                async with self.q.engine.begin() as connection:
                    await connection.run_sync(downgrade)

    async def test_postgres_parallel_same_reason_is_one_fact(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent reservation transactions")
        await self.q.update_pref(master_enabled=False)
        results = await asyncio.gather(self.q.reserve(), self.q.reserve())
        self.assertEqual([r.reason for r in results], ["master_off", "master_off"])
        self.assertEqual(len(await self.rows(RESERVATION)), 1)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)


class SQLiteReservationAnalysisTests(ReservationSourceChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLReservationAnalysisTests(ReservationSourceChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
