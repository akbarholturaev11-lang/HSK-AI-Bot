"""Durable anonymous outcomes, bounded collection and privacy under real SQL."""
import asyncio
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, patch

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, event, select, update

from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.smart_reminder_baseline import MEMBER, TOTAL, windows
from app.services.smart_reminder_preferences import _utc
from tests import test_smart_reminder_analysis as schema
from tests.test_smart_reminder_baseline import BaselineChecks


class OutcomeChecks:
    postgres=False
    asyncSetUp=BaselineChecks.asyncSetUp
    asyncTearDown=BaselineChecks.asyncTearDown
    rows=BaselineChecks.rows
    enroll=BaselineChecks.enroll
    clone_job=BaselineChecks.clone_job
    unit=BaselineChecks.unit
    scored=BaselineChecks.scored

    async def observe(self): return await self.baseline.observe_member(1)
    async def report(self): return await self.baseline.report(self.month)

    async def positive(self):
        await self.enroll()
        await self.unit(self.now+timedelta(hours=1))
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))

    async def test_repeat_noop_preserves_first_observation_and_counts(self):
        await self.positive()
        self.assertEqual(await self.observe(),1)
        before=(await self.rows(MEMBER),await self.rows(TOTAL))
        self.report_now+=timedelta(days=1)
        def no_write(conn,cursor,statement,*args):
            if statement.lstrip().upper().startswith(("UPDATE ","INSERT ","DELETE ")):
                raise AssertionError("no new evidence must not write")
        event.listen(self.q.engine.sync_engine,"before_cursor_execute",no_write)
        try: self.assertEqual(await self.observe(),0)
        finally: event.remove(self.q.engine.sync_engine,"before_cursor_execute",no_write)
        self.assertEqual(before,(await self.rows(MEMBER),await self.rows(TOTAL)))
        total=before[1][0]
        self.assertEqual(tuple(total[k] for k in ("enrolled_accounts","observed_accounts","observed_units",
            "observed_active_days","observed_d7_accounts")),(1,1,1,1,1))

    async def test_late_server_receipt_increases_original_unit_only_once(self):
        await self.enroll()
        await self.unit(self.now+timedelta(hours=1),source="client_telemetry")
        await self.observe()
        first=(await self.rows(MEMBER))[0]["observed_at"]
        self.assertEqual((await self.rows(TOTAL))[0]["observed_units"],0)
        async with self.q.sessions.begin() as s:
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name=="lesson_completed").values(
                source="course_v3",created_at=self.report_now-timedelta(hours=1)))
        self.assertEqual(await self.observe(),1)
        self.assertEqual(await self.observe(),0)
        total=(await self.rows(TOTAL))[0]
        self.assertEqual((total["observed_accounts"],total["observed_units"],total["observed_active_days"]),(1,1,1))
        self.assertEqual((await self.rows(MEMBER))[0]["observed_at"],first)

    async def test_source_loss_cannot_subtract_proven_lower_bounds(self):
        await self.positive();await self.observe()
        before=await self.rows(TOTAL)
        async with self.q.sessions.begin() as s:
            await s.execute(delete(CourseXpEvent));await s.execute(delete(CourseMiniAppEvent))
        self.assertEqual(await self.observe(),0)
        self.assertEqual(await self.rows(TOTAL),before)
        self.assertEqual((await self.report())["observed_d7_percent_lower_bound"],100)

    async def test_snapshot_failure_rolls_back_anonymous_delta_then_recovers(self):
        await self.positive()
        def fail(conn,cursor,statement,*args):
            if statement.lstrip().startswith("UPDATE smart_reminder_baseline_members"):
                raise RuntimeError("synthetic-private-observation")
        event.listen(self.q.engine.sync_engine,"before_cursor_execute",fail)
        try:
            with self.assertRaisesRegex(RuntimeError,"synthetic-private"): await self.observe()
        finally: event.remove(self.q.engine.sync_engine,"before_cursor_execute",fail)
        self.assertEqual((await self.rows(TOTAL))[0]["observed_accounts"],0)
        self.assertIsNone((await self.rows(MEMBER))[0]["observed_at"])
        self.assertEqual(await self.observe(),1)
        self.assertEqual((await self.rows(TOTAL))[0]["observed_units"],1)

    async def test_missing_original_denominator_cannot_create_an_observation(self):
        await self.positive()
        async with self.q.sessions.begin() as s: await s.execute(delete(TOTAL))
        with self.assertRaisesRegex(RuntimeError,"denominator unavailable"): await self.observe()
        self.assertIsNone((await self.rows(MEMBER))[0]["observed_at"])
        self.assertEqual(await self.rows(TOTAL),[])

    async def test_protected_or_immature_owner_never_reads_learning(self):
        await self.enroll()
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("private source")):
            self.report_now=self.now+timedelta(days=2)
            self.assertEqual(await self.observe(),0)
            result=await self.report()
            self.assertEqual((result["observed_accounts"],result["unobserved_accounts"],result["aggregation_pending_accounts"]),(0,1,1))
            self.report_now=self.now+timedelta(days=12)
            async with self.q.sessions.begin() as s: await s.execute(update(User).where(User.id==1).values(status="blocked"))
            self.assertEqual(await self.observe(),0)
            async with self.q.sessions.begin() as s: await s.execute(update(User).where(User.id==1).values(status="free"))
            await self.q._deletion()
            self.assertEqual(await self.observe(),0)
        self.assertIsNone((await self.rows(MEMBER))[0]["observed_at"])

    async def test_purge_preserves_anonymous_outcomes_without_owner_reads(self):
        await self.positive();await self.observe()
        total=await self.rows(TOTAL)
        async with self.q.sessions.begin() as s: await UserRepository(s)._delete_account(await s.get(User,1))
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("deleted owner")):
            self.assertEqual(await self.observe(),0)
            result=await self.report()
        self.assertEqual(await self.rows(MEMBER),[])
        self.assertEqual(await self.rows(TOTAL),total)
        self.assertEqual((result["cohort_accounts"],result["observed_accounts"],result["censored_accounts"]),(1,1,1))
        self.assertEqual(result["observed_d7_percent_lower_bound"],100)
        self.assertIsNone(result["d7_learning_retention"])

    async def test_raw_expiry_preserves_outcomes_and_cannot_reobserve(self):
        await self.positive();await self.observe()
        before=await self.rows(TOTAL)
        self.report_now=self.now+timedelta(days=91);self.q.tick=self.report_now
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("expired source")):
            self.assertEqual(await self.observe(),0)
            self.assertEqual(await self.baseline.aggregation_page(),((),False))
        await self.analysis.retention(execute=True,limit=1)
        self.assertEqual(await self.rows(MEMBER),[])
        self.assertEqual(await self.rows(TOTAL),before)
        result=await self.report()
        self.assertEqual((result["observed_units_lower_bound"],result["observed_d7_accounts_lower_bound"]),(1,1))
        self.assertEqual(await self.observe(),0)
        self.q.tick=self.now+timedelta(days=400)
        await self.analysis.retention(execute=True,limit=1)
        self.assertEqual(await self.rows(TOTAL),[])

    async def test_anonymous_report_is_one_select_and_never_reads_learning(self):
        await self.positive();await self.observe()
        selects=[]
        def inspect(conn,cursor,statement,*args):
            prefix=statement.lstrip().split()[0].upper()
            if prefix in {"UPDATE","INSERT","DELETE","CREATE","ALTER","DROP"}: raise AssertionError("report write")
            if prefix=="SELECT": selects.append(statement)
            if any(t in statement for t in ("course_xp_events","course_miniapp_events","smart_reminder_jobs",
                    "smart_reminder_attempts","android_push_tokens")): raise AssertionError("report personal source")
        event.listen(self.q.engine.sync_engine,"before_cursor_execute",inspect)
        try:
            with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("report personal source")):
                result=await self.report()
        finally: event.remove(self.q.engine.sync_engine,"before_cursor_execute",inspect)
        self.assertEqual(len(selects),1)
        self.assertNotIn("source_job",str(result));self.assertNotIn("user_id",str(result))
        self.assertEqual(result["observed_accounts"],1)

    async def test_limited_positive_and_flag_survive_later_source_changes(self):
        await self.positive()
        async with self.q.sessions.begin() as s:
            s.add_all([CourseXpEvent(user_id=1,activity_type="lesson",activity_ref=f"unreviewed:{i}",xp=1,
                activity_date=self.now.date(),week_start=self.now.date(),created_at=self.now+timedelta(hours=1)) for i in range(513)])
        await self.observe()
        result=await self.report()
        self.assertEqual((result["source_limited_accounts"],result["observed_d7_accounts_lower_bound"]),(1,1))
        self.assertIsNone(result["observed_d7_percent_lower_bound"])
        async with self.q.sessions.begin() as s:
            await s.execute(delete(CourseXpEvent).where(CourseXpEvent.activity_ref.like("unreviewed:%")))
        await self.observe()
        result=await self.report()
        self.assertEqual((result["source_limited_accounts"],result["observed_units_lower_bound"]),(1,1))
        self.assertEqual(result["status"],"source_coverage_limited")

    async def test_existing_worker_has_independent_budget_after_job_failure(self):
        await self.positive()
        self.observer.baseline=self.baseline
        async def stop(_): self.observer.settings.SMART_REMINDER_ANALYSIS_ENABLED=False
        with patch.object(self.observer,"reconcile_tick",side_effect=RuntimeError("synthetic-private-job")), \
                patch("app.services.smart_reminder_analysis.asyncio.sleep",side_effect=stop), \
                self.assertLogs("app.services.smart_reminder_analysis",level="WARNING") as logs:
            await self.observer.run_reconciliation()
        self.assertNotIn("synthetic-private",str(logs.output))
        self.assertEqual((await self.rows(TOTAL))[0]["observed_accounts"],1)

    async def test_failed_owner_cursor_advances_and_later_pass_retries(self):
        first=await self.enroll();second=await self.clone_job(first)
        await self.analysis.capture_job(2,second)
        self.observer.baseline=self.baseline;self.observer.batch=1
        original=self.baseline.observe_member
        async def fail(uid):
            if uid==1: raise RuntimeError("synthetic-private-owner")
            return await original(uid)
        with patch.object(self.baseline,"observe_member",side_effect=fail), \
                self.assertLogs("app.services.smart_reminder_analysis",level="WARNING") as logs:
            first=await self.observer.baseline_tick()
            second=await self.observer.baseline_tick()
        self.assertEqual((first["unavailable"],second["updated_observations"]),(1,1))
        self.assertNotIn("synthetic-private",str(logs.output))
        self.assertTrue(second["pass_finished"])
        await self.observer.baseline_tick()
        self.assertEqual((await self.rows(TOTAL))[0]["observed_accounts"],2)

    async def test_disabled_aggregation_never_touches_database(self):
        self.observer.settings.SMART_REMINDER_ANALYSIS_ENABLED=False
        with patch.object(self.observer.baseline,"aggregation_page",side_effect=AssertionError("disabled SQL")):
            self.assertIsNone(await self.observer.baseline_tick())
            await self.observer.run_reconciliation()

    async def test_restart_replay_keeps_original_denominator_and_progress(self):
        first=await self.enroll();second=await self.clone_job(first)
        await self.analysis.capture_job(2,second)
        self.observer.baseline=self.baseline;self.observer.batch=1
        await self.observer.baseline_tick()
        self.assertEqual((await self.report())["aggregation_pending_accounts"],1)
        self.observer._baseline_after=None  # process restart, durable observations remain
        await self.observer.baseline_tick();await self.observer.baseline_tick()
        total=(await self.rows(TOTAL))[0]
        self.assertEqual((total["enrolled_accounts"],total["observed_accounts"]),(2,2))

    async def test_migration_preserves_populated_unobserved_0144_and_model_parity(self):
        await self.enroll()
        def down(c):
            with Operations.context(MigrationContext.configure(c)): schema.baseline_outcomes_migration.downgrade()
        def up(c):
            with Operations.context(MigrationContext.configure(c)): schema.baseline_outcomes_migration.upgrade()
            return compare_metadata(MigrationContext.configure(c),Base.metadata)
        async with self.q.engine.begin() as c: await c.run_sync(down)
        # Read via original column names while the new columns are absent.
        async with self.q.sessions() as s:
            original=await s.execute(select(MEMBER.c.user_id,MEMBER.c.source_job_id,MEMBER.c.entered_at))
            self.assertEqual(len(original.all()),1)
        async with self.q.engine.begin() as c: self.assertEqual(await c.run_sync(up),[])
        self.assertIsNone((await self.rows(MEMBER))[0]["observed_at"])
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)

    async def test_populated_outcome_downgrade_refuses_raw_and_anonymous_only(self):
        await self.positive();await self.observe()
        def down(c):
            with Operations.context(MigrationContext.configure(c)): schema.baseline_outcomes_migration.downgrade()
        for raw in (True,False):
            if not raw:
                async with self.q.sessions.begin() as s: await s.execute(delete(MEMBER))
            async with self.q.engine.begin() as c:
                with self.assertRaisesRegex(RuntimeError,"populated baseline outcomes"): await c.run_sync(down)
        self.assertEqual((await self.rows(TOTAL))[0]["observed_units"],1)

    async def test_downgrade_refuses_any_anonymous_outcome_even_if_counter_is_damaged(self):
        await self.enroll()
        async with self.q.sessions.begin() as s:
            await s.execute(delete(MEMBER))
            await s.execute(update(TOTAL).values(observed_units=1))
        def down(c):
            with Operations.context(MigrationContext.configure(c)): schema.baseline_outcomes_migration.downgrade()
        async with self.q.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError,"populated baseline outcomes"): await c.run_sync(down)
        self.assertEqual((await self.rows(TOTAL))[0]["observed_units"],1)

    async def test_first_week_alone_is_not_materialized_before_d7_finishes(self):
        await self.positive()
        week_end,_=windows(self.now,"Etc/UTC")
        self.report_now=week_end+timedelta(seconds=1)
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("unfinished follow-up")):
            self.assertEqual(await self.observe(),0)
        result=await self.report()
        self.assertEqual(result["observed_accounts"],0)
        self.assertIsNone(result["observed_units_lower_bound"])
        self.assertIsNone(result["observed_d7_percent_lower_bound"])

    async def test_purged_latest_entry_still_delays_whole_cohort_final_rate(self):
        job=await self.enroll()
        next_month=(self.month.replace(day=28)+timedelta(days=4)).replace(day=1)
        end=datetime.combine(next_month,datetime.min.time(),timezone.utc)
        second=await self.clone_job(job,at=end-timedelta(minutes=6))
        self.q.tick=end
        await self.analysis.capture_job(2,second)
        _,first_end=windows(self.now,"Etc/UTC")
        self.report_now=max(first_end,end)
        self.assertLess(self.report_now,_utc((await self.rows(TOTAL))[0]["matures_at"]))
        await self.observe()
        async with self.q.sessions.begin() as s: await UserRepository(s)._delete_account(await s.get(User,2))
        result=await self.report()
        self.assertEqual((result["cohort_accounts"],result["observed_accounts"],result["censored_accounts"]),(2,1,1))
        self.assertIsNone(result["observed_d7_percent_lower_bound"])
        self.report_now=_utc((await self.rows(TOTAL))[0]["matures_at"])
        self.assertEqual((await self.report())["observed_d7_percent_lower_bound"],0)

    async def test_parallel_observation_counts_account_once(self):
        if not self.postgres: self.skipTest("PostgreSQL independent mature-owner transactions")
        await self.positive()
        self.assertEqual(sum(await asyncio.gather(*(self.observe() for _ in range(5)))),1)
        total=(await self.rows(TOTAL))[0]
        self.assertEqual((total["observed_accounts"],total["observed_units"],total["observed_d7_accounts"]),(1,1,1))

    async def test_real_locked_owner_timeout_releases_connection_and_does_not_starve_next(self):
        if not self.postgres: self.skipTest("PostgreSQL actual User lock and observation cancellation")
        await self.positive()
        job=(await self.rows(MEMBER))[0]["source_job_id"]
        second=await self.clone_job(job)
        await self.analysis.capture_job(2,second)
        self.observer.baseline=self.baseline;self.observer.timeout=.15
        async with self.q.sessions.begin() as blocker:
            await blocker.execute(select(User.id).where(User.id==1).with_for_update())
            with self.assertLogs("app.services.smart_reminder_analysis",level="WARNING"):
                first=await self.observer.baseline_tick()
            self.assertEqual((first["examined"],first["unavailable"],first["pass_finished"]),(1,1,False))
            self.observer.timeout=1
            self.assertEqual((await self.observer.baseline_tick())["updated_observations"],1)
        self.assertEqual((await self.observer.baseline_tick())["updated_observations"],1)
        self.assertEqual(self.q.engine.sync_engine.pool.checkedout(),0)
        self.assertEqual((await self.rows(TOTAL))[0]["observed_accounts"],2)

    async def test_parallel_accounts_share_anonymous_month_without_lost_updates(self):
        if not self.postgres: self.skipTest("PostgreSQL independent owners sharing one month")
        first=await self.enroll();second=await self.clone_job(first)
        await self.analysis.capture_job(2,second)
        await self.unit(self.now+timedelta(hours=1),uid=1)
        await self.unit(self.now+timedelta(hours=1),uid=2)
        self.assertEqual(sum(await asyncio.gather(self.observe(),self.baseline.observe_member(2))),2)
        total=(await self.rows(TOTAL))[0]
        self.assertEqual((total["enrolled_accounts"],total["observed_accounts"],total["observed_units"]),(2,2,2))

    async def test_cursor_validation_rejects_unbounded_and_boolean_inputs(self):
        for kwargs in ({"limit":0},{"limit":129},{"limit":True},{"after_user_id":True},{"after_user_id":-1}):
            with self.assertRaises(ValueError): await self.baseline.aggregation_page(**kwargs)
        with self.assertRaises(ValueError): await self.baseline.observe_member(True)


class SQLiteOutcomeTests(OutcomeChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLOutcomeTests(OutcomeChecks,unittest.IsolatedAsyncioTestCase): postgres=True
