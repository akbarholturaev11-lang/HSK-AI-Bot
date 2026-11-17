"""Recover missed committed facts without touching source delivery authority."""
import asyncio
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import event, insert, select, update

from app.db.models.user import User
from app.services.smart_reminder_analysis import (
    AnalysisOwnerBusy, AnalysisSourcePage, EVENT, MONTHLY, RAW_RETENTION,
    SmartReminderAnalysisObserver, SmartReminderAnalysisService,
)
from tests import test_smart_reminder_analysis as fixture


class ReconciliationWorkerTests(unittest.IsolatedAsyncioTestCase):
    def observer(self, **options):
        return SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True), Mock(), **options)

    async def test_tick_budget_yields_between_healthy_captures_without_cancelling_one(self):
        # Each capture needs 1.2s, below its 2s operation limit. The old
        # shrinking timeout gives the second capture only .8s and cancels it.
        for baseline in (False, True):
            with self.subTest(baseline=baseline):
                observer = self.observer(timeout=2)
                clock = SimpleNamespace(now=0)
                calls = []
                async def capture(*args, **kwargs):
                    calls.append(args)
                    clock.now += 1.2
                    return 1
                async def wait_for(awaitable, *, timeout):
                    before = clock.now
                    result = await awaitable
                    if clock.now - before > timeout:
                        raise asyncio.TimeoutError
                    return result
                if baseline:
                    observer.baseline.aggregation_page = AsyncMock(return_value=((1, 2, 3), False))
                    observer.baseline.observe_member = capture
                    tick = observer.baseline_tick
                else:
                    observer.service.reconciliation_page = AsyncMock(return_value=
                        AnalysisSourcePage(((1, "a"), (2, "b"), (3, "c")), False))
                    observer.service.capture_job = capture
                    tick = observer.reconcile_tick
                proxy = SimpleNamespace(get_running_loop=lambda: SimpleNamespace(time=lambda: clock.now),
                                        wait_for=wait_for, TimeoutError=asyncio.TimeoutError)
                with patch("app.services.smart_reminder_analysis.asyncio", proxy), \
                        self.assertNoLogs("app.services.smart_reminder_analysis", level="WARNING"):
                    result = await tick()
                self.assertEqual(len(calls), 2)
                self.assertEqual(result["examined"], 2)
                self.assertEqual(result["unavailable"], 0)
                self.assertFalse(result["pass_finished"])
                self.assertEqual(result["updated_observations" if baseline else "inserted_facts"], 2)

    async def test_failed_owner_advances_cursor_and_retries_on_next_pass(self):
        observer = self.observer(timeout=.01)
        async def page(**kwargs):
            return AnalysisSourcePage(((2, "b"),), False) if kwargs["after_job_id"] == "a" else AnalysisSourcePage(((1, "a"), (2, "b")), False)
        observer.service.reconciliation_page = AsyncMock(side_effect=page)
        cleaned = asyncio.Event()
        async def capture(uid, job, **options):
            if job == "a":
                try:
                    await asyncio.Event().wait()
                finally:
                    cleaned.set()
            return 1
        observer.service.capture_job = AsyncMock(side_effect=capture)
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            first = await observer.reconcile_tick()
        self.assertEqual(first, dict(examined=1, inserted_facts=0, unavailable=1, deferred=0, pass_finished=False))
        self.assertTrue(cleaned.is_set())
        self.assertEqual(logs.output, ["WARNING:app.services.smart_reminder_analysis:Smart analysis reconciliation capture unavailable; reason=timeout"])
        self.assertEqual(await observer.reconcile_tick(), dict(examined=1, inserted_facts=1, unavailable=0, deferred=0, pass_finished=True))
        observer.service.capture_job = AsyncMock(return_value=0)
        await observer.reconcile_tick()
        self.assertEqual(observer.service.capture_job.await_args_list[0].args, (1, "a"))

    async def test_busy_deferral_does_not_hide_a_real_capture_error(self):
        observer = self.observer()
        observer.service.reconciliation_page = AsyncMock(return_value=
            AnalysisSourcePage(((1, "a"), (2, "b")), False))
        observer.service.capture_job = AsyncMock(side_effect=
            (AnalysisOwnerBusy(), RuntimeError("synthetic-private-proof")))
        with self.assertLogs("app.services.smart_reminder_analysis", level="INFO") as logs:
            result = await observer.reconcile_tick()
        self.assertEqual(result, dict(examined=2, inserted_facts=0, unavailable=1,
                                      deferred=1, pass_finished=True))
        self.assertEqual([line for line in logs.output if line.startswith("WARNING:")],
            ["WARNING:app.services.smart_reminder_analysis:Smart analysis reconciliation capture unavailable"])
        self.assertIn("examined=2 inserted_facts=0 deferred=1 unavailable=1", logs.output[-1])
        self.assertNotIn("synthetic-private-proof", str(logs.output))

    async def test_worker_query_failure_is_sanitized_and_retention_is_independent(self):
        observer = self.observer(interval=.001)
        observer.service.retention = AsyncMock(side_effect=AssertionError("unrelated retention"))
        observer.baseline.aggregation_page = AsyncMock(return_value=((), False))
        async def tick():
            if observer.reconcile_tick.await_count == 1:
                raise RuntimeError("synthetic-private-proof")
            observer.settings.SMART_REMINDER_ANALYSIS_ENABLED = False
        observer.reconcile_tick = AsyncMock(side_effect=tick)
        with self.assertLogs("app.services.smart_reminder_analysis", level="WARNING") as logs:
            await asyncio.wait_for(observer.run_reconciliation(), 1)
        self.assertEqual(logs.output, ["WARNING:app.services.smart_reminder_analysis:Smart analysis reconciliation unavailable"])
        self.assertEqual(observer.reconcile_tick.await_count, 2)
        observer.baseline.aggregation_page.assert_awaited_once()
        observer.service.retention.assert_not_awaited()

    async def test_parent_cancellation_propagates_and_does_not_advance_unfinished_work(self):
        for phase in ("page", "capture"):
            observer = self.observer()
            started, cleaned = asyncio.Event(), asyncio.Event()
            async def hang(*args, **kwargs):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cleaned.set()
            observer.service.reconciliation_page = AsyncMock(return_value=AnalysisSourcePage(((1, "a"),), False))
            observer.service.capture_job = AsyncMock(return_value=1)
            if phase == "page":
                observer.service.reconciliation_page = hang
            else:
                observer.service.capture_job = hang
            task = asyncio.create_task(observer.run_reconciliation())
            await asyncio.wait_for(started.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(cleaned.is_set())
            self.assertIsNone(observer._reconcile_after)

    async def test_page_failure_keeps_position_and_invalid_bounds_do_no_sql(self):
        observer = self.observer()
        observer._reconcile_after = "previous"
        observer.service.reconciliation_page = AsyncMock(side_effect=RuntimeError("unavailable"))
        with self.assertRaises(RuntimeError):
            await observer.reconcile_tick()
        self.assertEqual(observer._reconcile_after, "previous")
        factory = Mock(side_effect=AssertionError("invalid SQL"))
        service = SmartReminderAnalysisService(factory)
        for values in ({"limit": 0}, {"limit": 129}, {"limit": True}, {"after_job_id": ""},
                       {"after_job_id": 1}, {"after_job_id": "x" * 37}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                await service.reconciliation_page(**values)
        factory.assert_not_called()


class ReconciliationSourceChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not fixture.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = fixture.PostgreSQLAnalysisTests if self.postgres else fixture.SQLiteAnalysisTests
        self.case = cls(methodName="test_reserved_fact_replay_counts_once_and_source_is_unchanged")
        await self.case.asyncSetUp()
        self.native, self.sessions = self.case.case, self.case.sessions
        self.observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True),
            self.sessions, clock=lambda: self.case.moment, timeout=2)

    async def asyncTearDown(self):
        if hasattr(self, "case"):
            await self.case.asyncTearDown()

    async def snapshot(self):
        return [await self.case.rows(t) for t in (fixture.JOB, fixture.ATTEMPT, fixture.GRANT)]

    async def second_job(self):
        job = dict((await self.case.rows(fixture.JOB))[0])
        job.update(id="zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz", user_id=2)
        async with self.sessions.begin() as session:
            await session.execute(insert(fixture.JOB).values(**job))
        return job["id"]

    async def test_missed_native_receipt_callback_recovers_once_without_source_mutation(self):
        grant = await self.native.claim()
        await self.native.receipt(grant)
        self.assertEqual(await self.case.rows(EVENT), [])
        before = await self.snapshot()
        result = await self.observer.reconcile_tick()
        self.assertEqual(result, dict(examined=1, inserted_facts=3, unavailable=0, deferred=0, pass_finished=True))
        self.assertEqual(await self.case.stages(), {"reserved", "in_flight", "client_posted_unverified"})
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual(sum(r["fact_count"] for r in await self.case.rows(MONTHLY)), 3)
        self.assertEqual(await self.snapshot(), before)

    async def test_partial_capture_and_restart_only_add_missing_source_stages(self):
        self.assertEqual(await self.case.capture(), 1)
        grant = await self.native.claim()
        await self.native.receipt(grant, "client_outcome_unknown")
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 2)
        restarted = SmartReminderAnalysisObserver(self.observer.settings, self.sessions, clock=lambda: self.case.moment)
        self.assertEqual((await restarted.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual(await self.case.stages(), {"reserved", "in_flight", "outcome_unknown"})

    async def test_keyset_pages_wrap_and_late_outcome_on_earlier_job_is_revisited(self):
        other = await self.second_job()
        self.observer.batch = 1
        first = await self.observer.reconcile_tick()
        self.assertEqual((first["examined"], first["inserted_facts"], first["pass_finished"]), (1, 1, False))
        grant = await self.native.claim()
        await self.native.receipt(grant)
        self.assertEqual(await self.observer.reconcile_tick(), dict(examined=1, inserted_facts=1, unavailable=0, deferred=0, pass_finished=True))
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 2)
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual({r["job_id"] for r in await self.case.rows(EVENT)}, {self.native.job_id, other})
        self.assertEqual(sum(r["fact_count"] for r in await self.case.rows(MONTHLY)), 4)

    async def test_recent_receipt_on_old_parent_does_not_resurrect_expired_facts(self):
        grant = await self.native.claim()
        await self.native.receipt(grant)
        old = self.case.moment - RAW_RETENTION - timedelta(days=1)
        # Owned retrospective fixture: preserve the original actual receipt,
        # backdate only its parent/start facts to exercise each source window.
        async with self.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(created_at=old, updated_at=old))
            await session.execute(update(fixture.ATTEMPT).values(prepared_at=old, started_at=old, resolved_at=old))
        before = await self.snapshot()
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 1)
        self.assertEqual(await self.case.stages(), {"client_posted_unverified"})
        self.assertEqual(await self.snapshot(), before)

    async def test_recent_telegram_attempt_on_old_parent_is_recoverable(self):
        old = self.case.moment - RAW_RETENTION - timedelta(days=1)
        async with self.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(created_at=old, updated_at=old,
                selected_channel="telegram", selected_device_id=None, policy_version="smart-telegram-v1:synthetic"))
            await session.execute(insert(fixture.ATTEMPT).values(id="original-telegram", job_id=self.native.job_id,
                attempt_key="t" * 64, channel="telegram", grant_epoch=1, state="provider_accepted",
                prepared_at=self.case.moment, started_at=self.case.moment, resolved_at=self.case.moment,
                expires_at=self.native.expiry))
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 2)
        self.assertEqual(await self.case.stages(), {"in_flight", "provider_accepted"})

    async def test_source_time_boundary_future_and_unknown_families_are_excluded(self):
        for stamp in (self.case.moment - RAW_RETENTION, self.case.moment + timedelta(microseconds=1)):
            async with self.sessions.begin() as session:
                await session.execute(update(fixture.JOB).values(created_at=stamp))
            self.assertEqual((await self.observer.service.reconciliation_page()).sources, ())
        async with self.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(created_at=self.case.moment))
        for version in ("smart-queue-shadow-v1", "unreviewed-v2", "smart-telegram-v1:wrong-channel"):
            async with self.sessions.begin() as session:
                await session.execute(update(fixture.JOB).values(policy_version=version))
            self.assertEqual((await self.observer.service.reconciliation_page()).sources, ())
        self.assertEqual(await self.case.rows(EVENT), [])

    async def test_pending_deletion_after_page_read_prevents_capture(self):
        page = await self.observer.service.reconciliation_page()
        await self.native._deletion()
        self.observer.service.reconciliation_page = AsyncMock(return_value=page)
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual(await self.case.rows(EVENT), [])

    async def test_missing_owner_is_not_reported_as_busy(self):
        self.assertEqual(await self.observer.service.capture_job(9999, self.native.job_id, skip_locked=True), 0)
        self.assertEqual(await self.observer.baseline.observe_member(9999, skip_locked=True), 0)

    async def test_expired_replay_after_retention_never_recounts(self):
        await self.observer.reconcile_tick()
        self.case.moment += RAW_RETENTION
        await self.case.analysis.retention(execute=True)
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual(await self.case.rows(EVENT), [])
        self.assertEqual(sum(r["fact_count"] for r in await self.case.rows(MONTHLY)), 1)
        self.assertEqual(len(await self.case.rows(fixture.JOB)), 1)

    async def test_page_read_is_nonpersisting_and_transaction_closes_before_capture(self):
        statements = []
        def trace(c, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(self.case.engine.sync_engine, "before_cursor_execute", trace)
        try:
            page = await self.observer.service.reconciliation_page(limit=1)
        finally:
            event.remove(self.case.engine.sync_engine, "before_cursor_execute", trace)
        self.assertEqual(page, AnalysisSourcePage(((1, self.native.job_id),), False))
        self.assertFalse(any(s.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"} for s in statements))
        self.assertNotIn("android_push_tokens", " ".join(statements))
        if self.postgres:
            self.assertEqual(self.case.engine.sync_engine.pool.checkedout(), 0)
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 1)

    async def test_postgres_busy_owner_is_deferred_without_starving_next_or_leaking_lock(self):
        if not self.postgres:
            self.skipTest("PostgreSQL real User lock and cancellation")
        other = await self.second_job()
        self.observer.timeout = 2
        async with self.sessions.begin() as blocker:
            # Actual legacy delivery bookkeeping writes User and flushes without
            # owning commit; hold that transaction as the known local blocker.
            from app.services.bot_block_status_service import BotBlockStatusService
            await BotBlockStatusService(blocker).handle_send_success(await blocker.get(User, 1))
            with self.assertNoLogs("app.services.smart_reminder_analysis", level="WARNING"):
                first = await self.observer.reconcile_tick()
            self.assertEqual((first["examined"], first["unavailable"], first["deferred"],
                              first["pass_finished"]), (2, 0, 1, True))
            self.assertEqual({r["job_id"] for r in await self.case.rows(EVENT)}, {other})
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 1)
        self.assertEqual({r["job_id"] for r in await self.case.rows(EVENT)}, {other, self.native.job_id})
        self.assertEqual(await self.case.rows(fixture.GRANT), [])
        self.assertEqual(await self.case.rows(fixture.ATTEMPT), [])

    async def test_postgres_two_reconcilers_and_source_hook_count_each_fact_once(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent reconciliation transactions")
        grant = await self.native.claim()
        await self.native.receipt(grant)
        before = await self.snapshot()
        other = SmartReminderAnalysisObserver(self.observer.settings, self.sessions, clock=lambda: self.case.moment)
        direct, first, second = await asyncio.gather(self.case.capture(),
            self.observer.reconcile_tick(), other.reconcile_tick())
        self.assertEqual(direct + first["inserted_facts"] + second["inserted_facts"], 3)
        self.assertEqual(len(await self.case.rows(EVENT)), 3)
        self.assertEqual(sum(r["fact_count"] for r in await self.case.rows(MONTHLY)), 3)
        self.assertEqual(await self.snapshot(), before)


class SQLiteReconciliationTests(ReconciliationSourceChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLReconciliationTests(ReconciliationSourceChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
