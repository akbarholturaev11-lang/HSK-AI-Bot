"""24 elapsed hours, no click gate, distinct contact/global-unit grains."""
import asyncio
from datetime import datetime, timedelta, timezone
import unittest
from uuid import uuid4
from zoneinfo import ZoneInfo
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, event, insert, update

from app.db.models.user import User
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent
from app.repositories.user_repo import UserRepository
from app.services.smart_reminder_analysis import EVENT, MONTHLY, RAW_RETENTION, RETURN_WINDOW, SmartReminderAnalysisObserver
from app.services.smart_reminder_policy import day_window
from app.services.smart_reminder_preferences import _utc
from tests import test_smart_reminder_analysis as schema
from tests import test_smart_reminder_activity_analysis as fixture

STAGES={"contact_study_24h","study_unit_24h"}
UTC=timezone.utc


class ReturnChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=fixture.PostgreSQLActivityAnalysisTests if self.postgres else fixture.SQLiteActivityAnalysisTests
        self.base=cls(methodName="test_failed_no_xp_manual_return_is_one_study_day_not_completed_unit")
        await self.base.asyncSetUp()
        self.case,self.storage,self.analysis=self.base.case,self.base.storage,self.base.analysis
        await self.base.episode.contact(report=False)
        self.contact_at=datetime(2026,10,29,23,50,tzinfo=UTC)
        await self.rebase(self.contact_at)
        self.at=self.contact_at+timedelta(minutes=20)
        self.storage.moment=self.at+timedelta(minutes=1)

    async def asyncTearDown(self):
        if hasattr(self,"base"): await self.base.asyncTearDown()

    async def rebase(self,at,zone="Etc/UTC"):
        old=_utc((await self.storage.rows(schema.ATTEMPT))[0]["started_at"])
        delta=at-old
        snapshots={table:await self.storage.rows(table) for table in (schema.JOB,schema.ATTEMPT,schema.GRANT)}
        async with self.case.sessions.begin() as s:
            for table,rows in snapshots.items():
                for row in rows:
                    values={k:_utc(v)+delta for k,v in row.items() if isinstance(v,datetime)}
                    if table is schema.JOB:
                        day=at.astimezone(ZoneInfo(zone)).date()
                        start,end=day_window(zone,day.isoformat())
                        values.update(local_day=day,timezone_name=zone,day_start_utc=start,day_end_utc=end)
                    await s.execute(update(table).where(table.c.id==row["id"]).values(**values))
        self.contact_at=at
        self.storage.moment=at+timedelta(minutes=30)

    async def second_contact(self,*,channel="android",confirmed=True):
        job=dict((await self.storage.rows(schema.JOB))[0])
        attempt=dict((await self.storage.rows(schema.ATTEMPT))[0])
        grant=dict((await self.storage.rows(schema.GRANT))[0])
        at=self.contact_at+timedelta(minutes=15)
        day=at.astimezone(ZoneInfo(job["timezone_name"])).date()
        start,end=day_window(job["timezone_name"],day.isoformat())
        jid,aid,gid=str(uuid4()),str(uuid4()),str(uuid4())
        expiry=at+timedelta(minutes=5)
        job.update(id=jid,local_day=day,day_start_utc=start,day_end_utc=end,created_at=at,
            updated_at=at+timedelta(seconds=1),scheduled_at=at,expires_at=expiry)
        attempt.update(id=aid,job_id=jid,attempt_key=uuid4().hex*2,prepared_at=at,
            started_at=at,resolved_at=at+timedelta(seconds=1) if confirmed else None,expires_at=expiry)
        if channel=="telegram":
            job.update(selected_channel="telegram",selected_device_id=None,policy_version="smart-telegram-v1:synthetic")
            attempt.update(channel="telegram",device_id=None,state="provider_accepted" if confirmed else "in_flight")
        else:
            attempt.update(state="client_posted_unverified" if confirmed else "in_flight")
            grant.update(id=gid,job_id=jid,attempt_id=aid,claim_request_id=str(uuid4()),
                issued_at=at,expires_at=expiry,received_at=at+timedelta(seconds=1) if confirmed else None,
                receipt_id=str(uuid4()) if confirmed else None,
                receipt_outcome="client_posted_unverified" if confirmed else None)
        async with self.case.sessions.begin() as s:
            await s.execute(insert(schema.JOB).values(**job))
            await s.execute(insert(schema.ATTEMPT).values(**attempt))
            if channel=="android": await s.execute(insert(schema.GRANT).values(**grant))
        return jid,aid

    async def read(self,job=None,uid=1):
        return await self.analysis.return_learning(uid,job or self.case.job_id)

    async def capture(self,job=None):
        return await self.analysis.capture_job(1,job or self.case.job_id)

    async def facts(self):
        return [r for r in await self.storage.rows(EVENT) if r["stage"] in STAGES]

    async def lesson(self,*,at=None,arrived=None):
        await self.base.episode.lesson(at=at or self.at,arrived=arrived)

    async def test_2350_contact_0010_manual_study_counts_without_changing_local_day(self):
        await self.lesson()
        result=await self.read()
        self.assertEqual((result.contact_at,result.window_end_at,result.first_study_at),
            (self.contact_at,self.contact_at+RETURN_WINDOW,self.at))
        self.assertEqual(result.verified_study_count,1)
        self.assertFalse(result.window_elapsed)
        old=await self.analysis.target_learning(1,self.case.job_id)
        self.assertIsNone(old.first_active_study_at)
        self.assertIsNone(old.verified_study_count)
        self.assertIsNone(old.reported_open_at)
        self.assertEqual(await self.capture(),2)
        raw=await self.facts()
        self.assertEqual({r["stage"] for r in raw},STAGES)
        self.assertEqual(await self.capture(),0)
        self.assertFalse(any(r["stage"]=="study_day_after_attempt" for r in await self.storage.rows(EVENT)))
        for row in raw:
            self.assertEqual(_utc(row["occurred_at"]),self.at)
            self.assertEqual(_utc(row["expires_at"]),self.at+RAW_RETENTION)
        self.assertNotIn("v3-part:",str(raw))

    async def test_failed_no_xp_study_after_midnight_is_only_positive_contact(self):
        await self.base.section(at=self.at)
        result=await self.read()
        self.assertEqual(result.first_study_at,self.at)
        self.assertIsNone(result.verified_study_count)
        self.assertEqual(await self.capture(),1)
        self.assertEqual({r["stage"] for r in await self.facts()},{"contact_study_24h"})
        self.assertIn("negative_learning_coverage_unknown",result.coverage_limits)

    async def test_exact_24h_is_included_and_elapsed_is_not_complete_coverage(self):
        end=self.contact_at+RETURN_WINDOW
        self.storage.moment=end+timedelta(seconds=1)
        await self.lesson(at=end)
        result=await self.read()
        self.assertEqual(result.first_study_at,end)
        self.assertTrue(result.window_elapsed)
        self.assertEqual(await self.capture(),2)
        self.assertIn("primary_cohort_metrics_unavailable",result.coverage_limits)

    async def test_just_after_24h_and_pre_contact_equal_future_are_unavailable(self):
        end=self.contact_at+RETURN_WINDOW
        self.storage.moment=end+timedelta(seconds=1)
        for at in (self.contact_at-timedelta(seconds=1),self.contact_at,
                   end+timedelta(microseconds=1),self.storage.moment+timedelta(seconds=1)):
            await self.base.section(at=at)
        result=await self.read()
        self.assertIsNone(result.first_study_at)
        self.assertIsNone(result.verified_study_count)
        self.assertTrue(result.window_elapsed)
        self.assertEqual(await self.capture(),0)
        self.assertEqual(await self.facts(),[])

    async def test_late_server_receipt_corroborates_original_unit_without_moving_time(self):
        end=self.contact_at+RETURN_WINDOW
        self.storage.moment=end+timedelta(minutes=10)
        await self.lesson(at=end-timedelta(seconds=1),arrived=end+timedelta(minutes=5))
        result=await self.read()
        self.assertEqual(result.first_study_at,end-timedelta(seconds=1))
        self.assertEqual(result.verified_study_count,1)
        self.assertEqual(await self.capture(),2)
        self.assertTrue(all(_utc(r["occurred_at"])==end-timedelta(seconds=1) for r in await self.facts()))

    async def test_dst_short_and_long_days_still_use_24_elapsed_hours(self):
        for at,length in ((datetime(2026,3,8,6,30,tzinfo=UTC),23),(datetime(2026,11,1,5,30,tzinfo=UTC),25)):
            with self.subTest(day_hours=length):
                await self.rebase(at,"America/New_York")
                end=at+RETURN_WINDOW
                self.storage.moment=end+timedelta(seconds=1)
                await self.base.section(at=end)
                result=await self.read()
                self.assertEqual(result.window_end_at-at,RETURN_WINDOW)
                self.assertEqual(result.first_study_at,end)
                job=(await self.storage.rows(schema.JOB))[0]
                self.assertEqual(_utc(job["day_end_utc"])-_utc(job["day_start_utc"]),timedelta(hours=length))
                async with self.case.sessions.begin() as s:
                    await s.execute(delete(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name=="section_attempt_scored"))

    async def test_overlapping_contacts_keep_one_global_unit_and_two_contact_windows(self):
        other,_=await self.second_contact()
        await self.lesson()
        await self.capture()
        await self.capture(other)
        facts=await self.facts()
        self.assertEqual(sum(r["stage"]=="contact_study_24h" for r in facts),2)
        unit=[r for r in facts if r["stage"]=="study_unit_24h"]
        self.assertEqual(len(unit),1)
        self.assertEqual(unit[0]["job_id"],self.case.job_id)
        self.assertEqual((await self.read(other)).verified_study_count,1) # Per-window projection, not summed globally.
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"]=="study_unit_24h"),1)

    async def test_reverse_cross_channel_capture_preserves_first_recorded_provenance(self):
        other,_=await self.second_contact(channel="telegram")
        await self.lesson()
        await self.capture(other)
        await self.capture()
        unit=[r for r in await self.facts() if r["stage"]=="study_unit_24h"]
        self.assertEqual([(r["job_id"],r["channel"]) for r in unit],[(other,"telegram")])
        before=await self.facts()
        self.assertEqual(await self.capture(other),0)
        self.assertEqual(await self.capture(),0)
        self.assertEqual(await self.facts(),before)

    async def test_late_contact_confirmation_cannot_duplicate_or_reassign_original_unit(self):
        other,aid=await self.second_contact(channel="telegram",confirmed=False)
        await self.lesson()
        await self.capture()
        original=[r for r in await self.facts() if r["stage"]=="study_unit_24h"]
        self.assertIsNone((await self.read(other)).first_study_at)
        async with self.case.sessions.begin() as s:
            await s.execute(update(schema.ATTEMPT).where(schema.ATTEMPT.c.id==aid).values(
                state="provider_accepted",resolved_at=self.storage.moment))
        await self.capture(other)
        self.assertEqual(original,[r for r in await self.facts() if r["stage"]=="study_unit_24h"])
        self.assertEqual(sum(r["stage"]=="contact_study_24h" for r in await self.facts()),2)

    async def test_source_projection_is_read_only_and_capture_does_not_change_learning(self):
        await self.lesson()
        tables=(schema.JOB,schema.ATTEMPT,schema.GRANT,CourseXpEvent.__table__,CourseMiniAppEvent.__table__)
        before=[await self.storage.rows(t) for t in tables]
        def inspect(conn,cursor,statement,*args):
            if statement.lstrip().split()[0].upper() in {"INSERT","UPDATE","DELETE","CREATE","DROP","ALTER"}:
                raise AssertionError("Projection must not write")
        event.listen(self.case.engine.sync_engine,"before_cursor_execute",inspect)
        try:
            self.assertEqual(await self.read(),await self.read())
        finally: event.remove(self.case.engine.sync_engine,"before_cursor_execute",inspect)
        await self.capture()
        self.assertEqual(before,[await self.storage.rows(t) for t in tables])

    async def test_foreign_owner_bad_course_client_only_and_unpaired_scores_are_unavailable(self):
        await self.base.section(uid=2,at=self.at)
        await self.base.section(level="hsk2",at=self.at)
        await self.base.section(name="section_completed",at=self.at)
        await self.base.section(payload={"section_key":"vocab","correct":True,"total":3},at=self.at)
        self.assertIsNone((await self.read()).first_study_at)
        self.assertEqual((await self.read(uid=2)).reason,"learning_job_unavailable")
        self.assertEqual(await self.capture(),0)
        with self.assertRaises(ValueError): await self.analysis.return_learning(True,self.case.job_id)

    async def test_unknown_contact_and_contact_outside_frozen_day_are_not_24h_authority(self):
        async with self.case.sessions.begin() as s:
            await s.execute(update(schema.ATTEMPT).values(state="unknown"))
        await self.lesson()
        self.assertIsNone((await self.read()).first_study_at)
        await self.capture() # A changed delivery outcome may produce its own older-stage fact.
        self.assertEqual(await self.facts(),[])
        async with self.case.sessions.begin() as s:
            await s.execute(update(schema.ATTEMPT).values(state="client_posted_unverified"))
            await s.execute(update(schema.JOB).values(
                day_start_utc=self.contact_at.replace(hour=0,minute=0)+timedelta(seconds=1)))
        self.assertEqual((await self.read()).reason,"learning_window_unavailable")
        self.assertEqual(await self.facts(),[])

    async def test_block_and_submitted_deletion_prevent_new_return_detail(self):
        await self.lesson()
        async with self.case.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="blocked"))
        self.assertEqual((await self.read()).reason,"learning_owner_unavailable")
        await self.capture()
        self.assertEqual(await self.facts(),[])
        async with self.case.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="active"))
        await self.case._deletion()
        self.assertEqual(await self.capture(),0)
        self.assertEqual(await self.facts(),[])

    async def test_atomic_failure_and_existing_reconciliation_recover_new_stages(self):
        await self.lesson()
        original=self.analysis._insert
        def broken(s,t):
            if t is MONTHLY: raise RuntimeError("synthetic-private-counter")
            return original(s,t)
        with patch.object(self.analysis,"_insert",side_effect=broken):
            with self.assertRaises(RuntimeError): await self.capture()
        self.assertEqual(await self.facts(),[])
        observer=SmartReminderAnalysisObserver(self.case.settings,self.case.sessions,clock=lambda:self.storage.moment)
        await observer.reconcile_tick()
        self.assertEqual({r["stage"] for r in await self.facts()},STAGES)
        await observer.reconcile_tick()
        self.assertEqual(len(await self.facts()),2)

    async def test_original_retention_and_account_purge_preserve_anonymous_counts(self):
        await self.lesson()
        await self.capture()
        self.storage.moment=self.at+RAW_RETENTION+timedelta(seconds=1)
        await self.analysis.retention(execute=True)
        self.assertEqual(await self.facts(),[])
        self.assertEqual(await self.capture(),0)
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)
        async with self.case.sessions.begin() as s:
            await UserRepository(s)._delete_account(await s.get(User,1))
        self.assertEqual(await self.facts(),[])

    async def test_account_purge_removes_live_detail_without_removing_monthly_counts(self):
        await self.lesson()
        await self.capture()
        self.assertEqual(len(await self.facts()),2)
        async with self.case.sessions.begin() as s:
            await UserRepository(s)._delete_account(await s.get(User,1))
        self.assertEqual(await self.facts(),[])
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)

    async def test_populated_migration_roundtrip_preserves_old_facts_and_source(self):
        # Same-day original study creates real older-stage facts as well.
        await self.lesson(at=self.contact_at+timedelta(minutes=1))
        await self.capture()
        async with self.case.sessions.begin() as s:
            await s.execute(delete(EVENT).where(EVENT.c.stage.in_(STAGES)))
            await s.execute(delete(MONTHLY).where(MONTHLY.c.stage.in_(STAGES)))
        tables=(EVENT,MONTHLY,schema.JOB,schema.ATTEMPT,schema.GRANT,CourseXpEvent.__table__)
        before=[await self.storage.rows(t) for t in tables]
        def cycle(c):
            with Operations.context(MigrationContext.configure(c)):
                schema.baseline_outcomes_migration.downgrade()
                schema.baseline_migration.downgrade()
                schema.return_migration.downgrade();schema.return_migration.upgrade()
                schema.baseline_migration.upgrade()
                schema.baseline_outcomes_migration.upgrade()
        async with self.case.engine.begin() as c: await c.run_sync(cycle)
        self.assertEqual(before,[await self.storage.rows(t) for t in tables])
        self.assertEqual(await self.capture(),2)

    async def test_raw_and_anonymous_only_new_stages_refuse_downgrade(self):
        await self.lesson()
        await self.capture()
        def downgrade(c):
            with Operations.context(MigrationContext.configure(c)): schema.return_migration.downgrade()
        for raw in (True,False):
            if not raw:
                async with self.case.sessions.begin() as s:
                    await s.execute(delete(EVENT).where(EVENT.c.stage.in_(STAGES)))
            async with self.case.engine.begin() as c:
                with self.assertRaisesRegex(RuntimeError,"populated return"): await c.run_sync(downgrade)

    async def test_postgres_concurrent_overlapping_capture_counts_one_global_unit(self):
        if not self.postgres: self.skipTest("PostgreSQL independent owner locks")
        other,_=await self.second_contact(channel="telegram")
        await self.lesson()
        await asyncio.gather(*(self.capture(job) for job in (other,self.case.job_id,other,self.case.job_id)))
        facts=await self.facts()
        self.assertEqual(sum(r["stage"]=="study_unit_24h" for r in facts),1)
        self.assertEqual(sum(r["stage"]=="contact_study_24h" for r in facts),2)
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"]=="study_unit_24h"),1)


class SQLiteReturnAnalysisTests(ReturnChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLReturnAnalysisTests(ReturnChecks,unittest.IsolatedAsyncioTestCase): postgres=True
