"""Actual first-ready sources, original denominators and learning-only cohorts."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest
from uuid import uuid4
from unittest.mock import patch

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, event, insert, select, update

from app.db.base import Base
from app.db.models.course_lessons import CourseLesson
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.smart_reminder_analysis import RAW_RETENTION
from app.services.smart_reminder_baseline import MEMBER, TOTAL, VERSION, SmartReminderBaselineService, windows
from app.services.smart_reminder_policy import day_window
from app.services.smart_reminder_preferences import _utc
from tests import test_smart_reminder_analysis as schema
from tests import test_smart_reminder_reservation_analysis as fixture

UTC=timezone.utc


class BaselineChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=fixture.PostgreSQLReservationAnalysisTests if self.postgres else fixture.SQLiteReservationAnalysisTests
        self.base=cls(methodName="test_source_commit_and_user_lock_release_precede_capture")
        await self.base.asyncSetUp()
        self.q,self.observer=self.base.q,self.base.observer
        self.analysis=self.observer.service
        self.now=self.q.tick
        self.month=self.now.date().replace(day=1)
        self.report_now=datetime.combine((self.month.replace(day=28)+timedelta(days=4)).replace(day=15),datetime.min.time(),UTC)
        self.baseline=SmartReminderBaselineService(self.q.sessions,clock=lambda:self.report_now)
        async with self.q.engine.begin() as c:
            await c.run_sync(MEMBER.drop);await c.run_sync(TOTAL.drop)
            def migrate(sync):
                with Operations.context(MigrationContext.configure(sync)): schema.baseline_migration.upgrade()
            await c.run_sync(migrate)

    async def asyncTearDown(self):
        if hasattr(self,"base"): await self.base.asyncTearDown()

    async def rows(self,table): return await self.base.rows(table)

    async def enroll(self):
        result=await self.q.reserve()
        self.assertEqual(result.reason,"shadow_reserved")
        self.assertFalse(result.dispatch_allowed)
        return result.job_id

    async def report(self): return await self.baseline.report(self.month)

    async def clone_job(self,job_id,*,uid=2,at=None):
        row=dict(await self.q.row(job_id))
        at=at or self.now
        day=at.date();start,end=day_window("Etc/UTC",day.isoformat())
        row.update(id=str(uuid4()),user_id=uid,local_day=day,timezone_name="Etc/UTC",
            day_start_utc=start,day_end_utc=end,created_at=at,updated_at=at,
            scheduled_at=at+timedelta(minutes=1),expires_at=at+timedelta(minutes=5))
        async with self.q.sessions.begin() as s: await s.execute(insert(schema.JOB).values(**row))
        return row["id"]

    async def unit(self,at,*,uid=1,level="hsk1",order=1,source="course_v3",xp=20):
        async with self.q.sessions.begin() as s:
            s.add(CourseXpEvent(user_id=uid,activity_type="lesson",activity_ref=f"v3-part:{level}:{order}:complete",
                xp=xp,activity_date=at.date(),week_start=at.date(),created_at=at))
            result=await CourseMiniAppAnalyticsService(s).record_server_event(event_name="lesson_completed",user_id=uid,
                source=source,level=level,lesson_order=order,dedupe_key=uuid4().hex,payload={"lesson_order":order})
            self.assertTrue(result["recorded"],result)
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==uid,
                CourseMiniAppEvent.level==level,CourseMiniAppEvent.lesson_order==order).values(created_at=at))

    async def scored(self,at,*,level="hsk2",correct=0,total=3):
        async with self.q.sessions.begin() as s:
            lesson=CourseLesson(level=level,lesson_order=1,lesson_code=uuid4().hex,title="QA")
            s.add(lesson);await s.flush()
            s.add(CourseMiniAppEvent(user_id=1,event_name="section_attempt_scored",source="course_miniapp",level=level,
                lesson_id=lesson.id,lesson_order=1,dedupe_key="section-attempt:"+uuid4().hex,created_at=at,
                payload_json=json.dumps({"section_key":"1.1","correct":correct,"total":total})))

    async def test_actual_reservation_enrolls_once_without_contacts_or_clicks(self):
        job=await self.enroll()
        member=(await self.rows(MEMBER))[0]
        self.assertEqual((member["source_job_id"],_utc(member["entered_at"])),(job,self.now))
        self.assertEqual(_utc(member["expires_at"]),self.now+RAW_RETENTION)
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)
        await self.analysis.capture_job(1,job)
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)
        self.assertEqual(await self.q.counts(),(1,0))

    async def test_disabled_capture_and_reconciliation_recover_original_entry(self):
        self.observer.settings.SMART_REMINDER_ANALYSIS_ENABLED=False
        job=await self.enroll()
        self.assertEqual(await self.rows(MEMBER),[])
        self.observer.settings.SMART_REMINDER_ANALYSIS_ENABLED=True
        self.q.tick+=timedelta(minutes=1)
        await self.observer.reconcile_tick()
        self.assertEqual(_utc((await self.rows(MEMBER))[0]["entered_at"]),self.now)
        self.assertEqual((await self.rows(MEMBER))[0]["source_job_id"],job)

    async def test_earliest_committed_source_wins_even_when_later_job_is_captured_first(self):
        self.observer.settings.SMART_REMINDER_ANALYSIS_ENABLED=False
        first=await self.enroll()
        later=await self.clone_job(first,uid=1,at=self.now+timedelta(days=1))
        self.q.tick=self.now+timedelta(days=1,minutes=1)
        await self.analysis.capture_job(1,later)
        await self.analysis.capture_job(1,first)
        self.assertEqual([(r["source_job_id"],_utc(r["entered_at"])) for r in await self.rows(MEMBER)],[(first,self.now)])
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)

    async def test_off_and_d1_both_arms_prevent_initial_enrollment(self):
        await self.q.update_pref(master_enabled=False)
        self.assertEqual((await self.q.reserve()).reason,"master_off")
        self.assertEqual(await self.rows(MEMBER),[])
        await self.q.update_pref(master_enabled=True)
        for arm in ("control","treatment"):
            async with self.q.sessions.begin() as s:
                s.add(CourseMiniAppEvent(user_id=1,event_name="d1_recovery_assigned",source="d1_recovery_v1",
                    payload_json=json.dumps({"arm":arm}),created_at=self.now))
            self.assertEqual((await self.q.reserve()).reason,"d1_holdout_active")
        self.assertEqual(await self.rows(MEMBER),[])
        self.assertEqual(await self.rows(TOTAL),[])

    async def test_atomic_member_counter_failure_leaves_committed_source_and_recovers(self):
        original=self.analysis._insert
        def broken(s,t):
            if t is TOTAL: raise RuntimeError("synthetic-private-baseline")
            return original(s,t)
        with patch.object(self.analysis,"_insert",side_effect=broken):
            with self.assertLogs("app.services.smart_reminder_analysis",level="WARNING"):
                job=await self.enroll()
        self.assertEqual(await self.rows(MEMBER),[])
        self.assertEqual(await self.q.counts(),(1,0))
        await self.observer.reconcile_tick()
        self.assertEqual((await self.rows(MEMBER))[0]["source_job_id"],job)
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)

    async def test_manual_study_and_cross_course_history_are_not_gated_by_current_progress(self):
        await self.enroll()
        d7_start,d7_end=windows(self.now,"Etc/UTC")
        await self.unit(self.now+timedelta(hours=1),order=1)
        await self.unit(self.now+timedelta(days=2),level="hsk2",order=1)
        await self.unit(d7_start+timedelta(hours=1),level="hsk3",order=1)
        async with self.q.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(level="hsk4",completed_lessons_count=0))
        result=await self.report()
        self.assertEqual(result["status"],"observed_lower_bounds")
        self.assertEqual((result["observed_units_lower_bound"],result["observed_active_days_lower_bound"]),(2,2))
        self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
        self.assertEqual(result["observed_d7_percent_lower_bound"],100)
        self.assertFalse(result["primary_kpis_available"])
        self.assertIsNone(result["d7_learning_retention"])
        self.assertFalse(result["experiment_ready"])
        self.assertFalse(result["dispatch_allowed"])
        self.assertNotIn("source_job",json.dumps(result))
        self.assertNotIn("3001",json.dumps(result))

    async def test_scored_failed_repeat_without_xp_proves_d7_once(self):
        await self.enroll()
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))
        await self.scored(d7+timedelta(hours=2))
        result=await self.report()
        self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
        self.assertEqual(result["observed_units_lower_bound"],0)

    async def test_all_original_accounts_stay_in_denominator_without_response(self):
        first=await self.enroll()
        second=await self.clone_job(first)
        await self.analysis.capture_job(2,second)
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))
        result=await self.report()
        self.assertEqual((result["cohort_accounts"],result["observed_d7_accounts_lower_bound"]),(2,1))
        self.assertEqual(result["observed_d7_percent_lower_bound"],50)

    async def test_account_deletion_removes_detail_preserves_original_denominator(self):
        first=await self.enroll();second=await self.clone_job(first)
        await self.analysis.capture_job(2,second)
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))
        if not self.postgres:
            async with self.q.engine.connect() as c: await c.exec_driver_sql("PRAGMA foreign_keys=OFF")
        async with self.q.sessions.begin() as s:
            await UserRepository(s)._delete_account(await s.get(User,2))
        result=await self.report()
        self.assertEqual(len(await self.rows(MEMBER)),1)
        self.assertEqual((result["cohort_accounts"],result["censored_accounts"]),(2,1))
        self.assertEqual(result["observed_d7_percent_lower_bound"],50)

    async def test_pre_entry_generic_open_reward_and_bad_score_do_not_prove_study(self):
        await self.enroll()
        d7,_=windows(self.now,"Etc/UTC")
        await self.unit(self.now-timedelta(seconds=1),order=1)
        await self.unit(d7+timedelta(hours=1),source="client_telemetry",order=2)
        await self.scored(d7+timedelta(hours=1),correct=True)
        async with self.q.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1,event_name="miniapp_opened",created_at=d7+timedelta(hours=1)))
            s.add(CourseXpEvent(user_id=1,activity_type="reward_chest",activity_ref="reward",xp=50,
                activity_date=d7.date(),week_start=d7.date(),created_at=d7+timedelta(hours=1)))
        result=await self.report()
        self.assertEqual((result["observed_units_lower_bound"],result["observed_d7_accounts_lower_bound"]),(0,0))
        self.assertIn("negative_learning_unknown",result["coverage_limits"])

    async def test_exact_d7_edges_and_midnight_use_frozen_calendar(self):
        await self.enroll()
        d7,end=windows(self.now,"Etc/UTC")
        await self.scored(d7)
        await self.unit(end,order=1)
        result=await self.report()
        self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
        self.assertEqual(result["observed_units_lower_bound"],0)

    async def test_immature_followup_and_open_month_do_not_publish_final_rate(self):
        await self.enroll()
        self.report_now=self.now+timedelta(hours=1)
        result=await self.report()
        self.assertEqual(result["status"],"immature_or_unavailable")
        self.assertIsNone(result["observed_d7_percent_lower_bound"])
        self.assertIsNone(result["observed_units_lower_bound"])
        self.assertEqual(result["cohort_accounts"],1)

    async def test_later_d1_overlap_is_annotated_without_dropping_member(self):
        await self.enroll()
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))
        async with self.q.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1,event_name="d1_recovery_assigned",source="d1_recovery_v1",
                created_at=self.now+timedelta(days=1),payload_json='{"arm":"control"}'))
        result=await self.report()
        self.assertEqual((result["cohort_accounts"],result["d1_overlap_accounts"]),(1,1))
        self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
        self.assertFalse(result["experiment_ready"])

    async def test_block_or_submitted_deletion_is_censored_without_reading_learning(self):
        await self.enroll()
        async with self.q.sessions.begin() as s: await s.execute(update(User).where(User.id==1).values(status="blocked"))
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("protected source")):
            result=await self.report()
        self.assertEqual((result["cohort_accounts"],result["censored_accounts"]),(1,1))
        self.assertIsNone(result["observed_d7_percent_lower_bound"])
        async with self.q.sessions.begin() as s: await s.execute(update(User).where(User.id==1).values(status="free"))
        await self.q._deletion()
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("protected source")):
            result=await self.report()
        self.assertEqual(result["censored_accounts"],1)

    async def test_retention_is_bounded_and_expired_first_entry_cannot_reenroll(self):
        job=await self.enroll()
        self.q.tick=self.now+RAW_RETENTION+timedelta(seconds=1)
        before=await self.q.row(job)
        dry=await self.analysis.retention()
        self.assertEqual((dry["expired_baseline_members"],dry["removed_baseline_members"]),(1,0))
        self.assertEqual((await self.analysis.retention(execute=True,limit=1))["removed_baseline_members"],1)
        later=await self.clone_job(job,uid=1,at=self.q.tick)
        await self.analysis.capture_job(1,later)
        self.assertEqual(await self.rows(MEMBER),[])
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)
        self.assertEqual(await self.q.row(job),before)
        self.q.tick=self.now+timedelta(days=400)
        self.assertEqual((await self.analysis.retention(execute=True,limit=1))["removed_baseline_totals"],1)

    async def test_report_is_zero_write_and_does_not_read_send_or_click_tables(self):
        await self.enroll()
        def inspect(conn,cursor,statement,*args):
            prefix=statement.lstrip().split()[0].upper()
            if prefix in {"INSERT","UPDATE","DELETE","CREATE","ALTER","DROP"}: raise AssertionError("report write")
            if any(name in statement.lower() for name in ("android_push_tokens","smart_reminder_attempts","smart_reminder_android_grants")):
                raise AssertionError("contact-dependent baseline")
        event.listen(self.q.engine.sync_engine,"before_cursor_execute",inspect)
        try: self.assertEqual(await self.report(),await self.report())
        finally: event.remove(self.q.engine.sync_engine,"before_cursor_execute",inspect)

    async def test_populated_downgrade_refuses_raw_and_anonymous_only_data(self):
        await self.enroll()
        def downgrade(c):
            with Operations.context(MigrationContext.configure(c)): schema.baseline_migration.downgrade()
        for raw in (True,False):
            if not raw:
                async with self.q.sessions.begin() as s: await s.execute(delete(MEMBER))
            async with self.q.engine.begin() as c:
                with self.assertRaisesRegex(RuntimeError,"populated baseline"): await c.run_sync(downgrade)

    async def test_populated_older_analysis_roundtrip_and_model_parity(self):
        await self.enroll()
        async with self.q.sessions.begin() as s:
            await s.execute(delete(MEMBER));await s.execute(delete(TOTAL))
        tables=(schema.JOB,schema.RESERVATION,schema.MONTHLY,schema.EVENT)
        before=[await self.rows(t) for t in tables]
        def cycle(c):
            with Operations.context(MigrationContext.configure(c)):
                schema.baseline_migration.downgrade();schema.baseline_migration.upgrade()
            return compare_metadata(MigrationContext.configure(c),Base.metadata)
        async with self.q.engine.begin() as c: self.assertEqual(await c.run_sync(cycle),[])
        self.assertEqual(before,[await self.rows(t) for t in tables])

    async def test_postgres_parallel_recovery_enrolls_once(self):
        if not self.postgres: self.skipTest("PostgreSQL independent first-ready capture")
        self.observer.settings.SMART_REMINDER_ANALYSIS_ENABLED=False
        job=await self.enroll()
        await asyncio.gather(*(self.analysis.capture_job(1,job) for _ in range(5)))
        self.assertEqual(len(await self.rows(MEMBER)),1)
        self.assertEqual((await self.rows(TOTAL))[0]["enrolled_accounts"],1)

    async def test_source_limit_withholds_derived_rates_but_keeps_verified_positive(self):
        await self.enroll()
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))
        async with self.q.sessions.begin() as s:
            s.add_all([CourseXpEvent(user_id=1,activity_type="lesson",activity_ref=f"unreviewed:{i}",xp=1,
                activity_date=self.now.date(),week_start=self.now.date(),created_at=self.now+timedelta(hours=1)) for i in range(513)])
        result=await self.report()
        self.assertEqual(result["source_limited_accounts"],1)
        self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
        self.assertIsNone(result["observed_units_lower_bound"])
        self.assertIsNone(result["observed_d7_percent_lower_bound"])

    async def test_cohort_limit_never_silently_samples_a_denominator(self):
        await self.enroll()
        _,end=windows(self.now,"Etc/UTC")
        async with self.q.sessions.begin() as s:
            s.add_all([User(id=uid,telegram_id=None,status="free") for uid in range(4,132)])
            await s.flush()
            await s.execute(insert(MEMBER),[dict(user_id=uid,protocol_version=VERSION,source_job_id=str(uuid4()),
                entered_at=self.now,timezone_name="Etc/UTC",course_key="hsk1",expires_at=self.now+RAW_RETENTION) for uid in range(4,132)])
            await s.execute(update(TOTAL).values(enrolled_accounts=129,matures_at=end))
        with patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("truncated cohort")):
            result=await self.report()
        self.assertEqual((result["status"],result["cohort_accounts"]),("cohort_over_limit",129))
        self.assertIsNone(result["observed_d7_percent_lower_bound"])

    async def test_current_timezone_changes_do_not_move_frozen_d7(self):
        await self.enroll()
        d7,_=windows(self.now,"Etc/UTC")
        await self.scored(d7+timedelta(hours=1))
        await self.q.update_pref(timezone_name="America/Los_Angeles")
        result=await self.report()
        self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
        self.assertEqual((await self.rows(MEMBER))[0]["timezone_name"],"Etc/UTC")


class CalendarTests(unittest.TestCase):
    def test_d7_uses_real_dst_midnights(self):
        start,end=windows(datetime(2026,10,25,16,tzinfo=UTC),"America/New_York")
        self.assertEqual(end-start,timedelta(hours=25))
        start,end=windows(datetime(2026,3,1,17,tzinfo=UTC),"America/New_York")
        self.assertEqual(end-start,timedelta(hours=23))


class SQLiteBaselineTests(BaselineChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLBaselineTests(BaselineChecks,unittest.IsolatedAsyncioTestCase): postgres=True
