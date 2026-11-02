"""Original server study units and retained reports are temporal, never causal."""
import asyncio
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from app.api.smart_reminder import create_smart_reminder_router
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_practice_service import PRACTICE_VERSION
from app.services.smart_reminder_analysis import (
    EVENT, MONTHLY, RAW_RETENTION, SmartReminderAnalysisObserver, SmartReminderAnalysisService,
)
from app.services.smart_reminder_open import SmartReminderOpenService
from app.services.smart_reminder_preferences import _utc
from tests import test_smart_reminder_analysis as storage_fixture
from tests import test_smart_reminder_learning_analysis as learning_fixture
from tests import test_smart_reminder_open as open_fixture

STAGES = {"verified_study_after_attempt", "verified_study_after_report"}


class StudyChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = learning_fixture.PostgreSQLTargetLearningTests if self.postgres else learning_fixture.SQLiteTargetLearningTests
        self.episode = cls(methodName="test_original_target_after_real_native_receipt_is_read_only_and_replay_stable")
        await self.episode.asyncSetUp()
        self.storage, self.case = self.episode.fixture, self.episode.case
        self.analysis = self.episode.analysis
        self.started, self.learned = self.episode.started, self.episode.learned
        self.report_at = self.started+timedelta(seconds=10)
        self.case.settings.SMART_REMINDER_ANALYSIS_ENABLED = True
        self.opens = SmartReminderOpenService(self.case.settings, clock=lambda:self.report_at)
        app=FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings, android_delivery_factory=self.case.service, open_service=self.opens,
            analysis_observer=SmartReminderAnalysisObserver(self.case.settings,self.case.sessions,
                clock=lambda:self.storage.moment)))
        await self.case.client.aclose()
        self.case.client=AsyncClient(transport=ASGITransport(app=app),base_url="https://study-results.test")

    async def asyncTearDown(self):
        if hasattr(self,"episode"):
            await self.episode.asyncTearDown()

    async def contact(self, *, report=True, outcome="client_posted_unverified"):
        grant=await self.episode.contact(outcome)
        if report:
            r=await self.case.client.post(f"/api/v3/android/smart-reminder/jobs/{self.case.job_id}/open",
                headers=await self.case.bearer(1),json={"version":1,"proof":grant["open_proof"]})
            self.assertEqual(r.status_code,200,r.text)
            self.assertTrue(r.json()["observed"],r.text)
        return grant

    async def lesson(self, *, source="android_course", order=5, at=None, arrived=None, changes=None):
        await self.episode.result(order=order,at=at,arrived=arrived,changes=changes)
        if source!="android_course":
            async with self.case.sessions.begin() as s:
                fields={"source":source}
                if source=="course_v3": fields["payload_json"]=json.dumps({"lesson_order":order})
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1,
                    CourseMiniAppEvent.source=="android_course",CourseMiniAppEvent.lesson_order==order).values(**fields))

    async def practice(self, *, mode="training", at=None, changes=None, uid=1, source="course_miniapp"):
        at=at or self.learned
        feature="placement" if mode=="placement" else "training_test"
        sid=f"practice:{uid}:{feature}:{mode}:{'words' if mode=='training' else 'hsk1'}:v{PRACTICE_VERSION}"
        kind="training" if mode=="training" else "test"
        async with self.case.sessions.begin() as s:
            user=await s.get(User,uid)
            await CourseGamificationService(s).award(user,activity_type=kind,activity_ref=sid+":completed",
                base_xp=8,level="hsk1")
            await CourseMiniAppAnalyticsService(s).record_server_event(event_name=kind+"_completed",
                user_id=uid,telegram_id=user.telegram_id,source=source,level="hsk1",session_id=sid,
                dedupe_key=f"practice:{feature}:completed",payload={"mode":mode,"skill":"words",
                    "score":2,"total":3}|(changes or {}))
            await s.execute(update(CourseXpEvent).where(CourseXpEvent.user_id==uid,
                CourseXpEvent.activity_ref==sid+":completed").values(created_at=at,activity_date=at.date()))
            # Actual practice writer records its server result just BEFORE XP.
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==uid,
                CourseMiniAppEvent.session_id==sid).values(created_at=at-timedelta(milliseconds=1)))
        return sid

    async def capture(self):
        return await self.analysis.capture_job(1,self.case.job_id)

    async def facts(self):
        return [r for r in await self.storage.rows(EVENT) if r["stage"] in STAGES]

    async def test_actual_native_report_lesson_and_practice_bind_original_units_once(self):
        await self.contact()
        await self.lesson()
        await self.practice(at=self.learned+timedelta(seconds=2))
        tables=(storage_fixture.JOB,storage_fixture.ATTEMPT,storage_fixture.GRANT,
            CourseXpEvent.__table__,CourseProgress.__table__,CourseMiniAppEvent.__table__)
        before=[await self.storage.rows(t) for t in tables]
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertEqual((result.learned_at,result.first_study_at,result.reported_open_at),
            (self.learned,self.learned,self.report_at))
        self.assertEqual((result.verified_study_count,result.first_study_after_report_at),(2,self.learned))
        self.assertEqual(await self.capture(),9)
        raw=await self.facts()
        self.assertEqual(len(raw),4)
        self.assertEqual(await self.capture(),0)
        self.assertEqual(await self.facts(),raw)
        self.assertEqual(before,[await self.storage.rows(t) for t in tables])
        for row in raw:
            self.assertEqual(row["channel"],"android")
            self.assertEqual(row["reason_code"],"original_server_result")
            self.assertEqual(_utc(row["expires_at"])-_utc(row["occurred_at"]),RAW_RETENTION)
        self.assertNotIn("practice:",str(raw))
        self.assertNotIn("v3-part:",str(raw))
        self.assertIn("causal_attribution_unavailable",result.coverage_limits)

    async def test_reviewed_miniapp_and_paired_desktop_lesson_sources_are_account_level(self):
        await self.contact()
        await self.lesson(source="course_v3")
        await self.lesson(source="desktop_course",order=6,at=self.learned+timedelta(seconds=2))
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertEqual(result.verified_study_count,2)
        self.assertEqual(result.learned_at,self.learned)
        self.assertEqual(await self.capture(),9)

    async def test_mock_placement_training_are_positive_units_without_faking_target_completion(self):
        await self.contact()
        for n,mode in enumerate(("mock","placement","training")):
            await self.practice(mode=mode,at=self.learned+timedelta(seconds=n))
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertIsNone(result.learned_at)
        self.assertEqual(result.reason,"target_learning_unavailable")
        self.assertEqual(result.verified_study_count,3)
        self.assertEqual(await self.capture(),12)

    async def test_manual_app_return_and_real_practice_counts_without_tapping_notification(self):
        await self.contact(report=False)
        async with self.case.sessions.begin() as session:
            await CourseMiniAppAnalyticsService(session).record_server_event(event_name="android_app_opened",
                user_id=1,source="android",level="hsk1")
        await self.practice()
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertEqual(result.verified_study_count,1)
        self.assertIsNone(result.reported_open_at)
        self.assertIsNone(result.first_study_after_report_at)
        self.assertEqual(await self.capture(),4)
        self.assertEqual({r["stage"] for r in await self.facts()},{"verified_study_after_attempt"})

    async def test_missing_or_later_report_never_turns_earlier_study_into_after_report(self):
        await self.contact(report=False)
        await self.lesson()
        self.assertEqual(await self.capture(),4)
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertIsNone(result.reported_open_at)
        self.assertIsNone(result.first_study_after_report_at)
        # A later authenticated report cannot backdate the user's click.
        grant=(await self.storage.rows(storage_fixture.GRANT))[0]
        self.report_at=self.learned+timedelta(seconds=10)
        from app.services.smart_reminder_preferences import SmartReminderActor
        proof=self.opens.proof(SmartReminderActor(1,"android",device_id="device-1",session_id="session-1"),
            self.case.job_id,grant["id"])
        r=await self.case.client.post(f"/api/v3/android/smart-reminder/jobs/{self.case.job_id}/open",
            headers=await self.case.bearer(1),json={"version":1,"proof":proof})
        self.assertTrue(r.json()["observed"])
        self.assertEqual(await self.capture(),0)
        self.assertEqual({r["stage"] for r in await self.facts()},{"verified_study_after_attempt"})
        await self.practice(at=self.report_at+timedelta(seconds=2))
        self.assertEqual(await self.capture(),4)
        self.assertEqual((await self.analysis.target_learning(1,self.case.job_id)).first_study_after_report_at,
            self.report_at+timedelta(seconds=2))

    async def test_wrong_attempt_reason_channel_or_future_report_is_not_linked(self):
        await self.contact()
        await self.lesson()
        async with self.case.sessions.begin() as s:
            await s.execute(update(EVENT).where(EVENT.c.stage=="client_reported_open").values(channel="telegram"))
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertIsNone(result.reported_open_at)
        self.assertEqual(await self.capture(),4)
        async with self.case.sessions.begin() as s:
            await s.execute(update(EVENT).where(EVENT.c.stage=="client_reported_open").values(channel="android",
                event_key="f"*64))
        self.assertIsNone((await self.analysis.target_learning(1,self.case.job_id)).reported_open_at)

    async def test_old_xp_late_receipt_equal_future_and_other_day_do_not_become_new_study(self):
        await self.contact()
        await self.lesson(at=self.started-timedelta(seconds=1),arrived=self.learned)
        self.assertEqual(await self.capture(),0)
        self.assertIsNone((await self.analysis.target_learning(1,self.case.job_id)).verified_study_count)
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseXpEvent).where(CourseXpEvent.activity_ref=="v3-part:hsk1:5:complete")
                .values(created_at=self.started))
        self.assertEqual(await self.capture(),0)
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseXpEvent).where(CourseXpEvent.activity_ref=="v3-part:hsk1:5:complete")
                .values(created_at=self.storage.moment+timedelta(seconds=1)))
        self.assertEqual(await self.capture(),0)

    async def test_untrusted_source_malformed_native_and_boolean_score_do_not_prove_study(self):
        await self.contact()
        await self.lesson(source="client_telemetry")
        await self.practice(changes={"score":True})
        self.assertEqual(await self.capture(),0)
        self.assertIsNone((await self.analysis.target_learning(1,self.case.job_id)).verified_study_count)
        async with self.case.sessions.begin() as s:
            result=await CourseMiniAppAnalyticsService(s).record_client_event(event_name="lesson_completed",
                user_id=1,source="course_v3",level="hsk1",lesson_order=5,payload={"lesson_order":5})
            self.assertFalse(result["ok"])

    async def test_foreign_practice_or_wrong_owner_session_never_counts(self):
        await self.contact()
        await self.practice(uid=2)
        self.assertEqual(await self.capture(),0)
        await self.practice()
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1,
                CourseMiniAppEvent.event_name=="training_completed").values(session_id="practice:2:training_test:training:words:v1"))
        self.assertEqual(await self.capture(),0)

    async def test_unknown_contact_or_blocked_owner_does_not_gain_new_learning_facts(self):
        await self.contact(report=False,outcome="client_outcome_unknown")
        await self.lesson()
        self.assertEqual(await self.capture(),0)
        async with self.case.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="blocked"))
        self.assertEqual(await self.capture(),0)
        self.assertEqual(await self.facts(),[])

    async def test_counter_failure_is_atomic_and_existing_reconciliation_recovers(self):
        await self.contact()
        await self.lesson()
        before=await self.storage.rows(storage_fixture.GRANT)
        original=self.analysis._insert
        def fail(session,table):
            if table is MONTHLY: raise RuntimeError("synthetic-private-study-counter")
            return original(session,table)
        with patch.object(self.analysis,"_insert",fail),self.assertRaises(RuntimeError):
            await self.capture()
        self.assertEqual(await self.facts(),[])
        self.assertEqual(await self.storage.rows(storage_fixture.GRANT),before)
        observer=SmartReminderAnalysisObserver(self.case.settings,self.case.sessions,clock=lambda:self.storage.moment)
        await observer.reconcile_tick()
        self.assertEqual(len(await self.facts()),2)
        await observer.reconcile_tick()
        self.assertEqual(len(await self.facts()),2)

    async def test_over_limit_learning_is_unavailable_not_a_truncated_positive_count(self):
        await self.contact()
        await self.lesson()
        async with self.case.sessions.begin() as s:
            s.add_all([CourseMiniAppEvent(user_id=1,source="android_course",level="hsk1",event_name="lesson_completed",
                lesson_order=5,created_at=self.learned,payload_json="{}") for _ in range(513)])
        self.assertEqual(await self.capture(),0)
        result=await self.analysis.target_learning(1,self.case.job_id)
        self.assertIsNone(result.verified_study_count)
        self.assertIn("learning_history_over_limit",result.coverage_limits)

    async def test_stage_roundtrip_preserves_old_facts_and_populated_downgrade_refuses(self):
        await self.contact()
        before=await self.storage.rows(EVENT)
        def cycle(c):
            with Operations.context(MigrationContext.configure(c)):
                storage_fixture.return_migration.downgrade()
                storage_fixture.activity_migration.downgrade()
                storage_fixture.study_migration.downgrade()
                storage_fixture.study_migration.upgrade()
                storage_fixture.activity_migration.upgrade()
                storage_fixture.return_migration.upgrade()
        async with self.case.engine.begin() as c: await c.run_sync(cycle)
        self.assertEqual(await self.storage.rows(EVENT),before)
        await self.lesson()
        await self.capture()
        def downgrade(c):
            with Operations.context(MigrationContext.configure(c)): storage_fixture.study_migration.downgrade()
        async with self.case.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError,"populated study"): await c.run_sync(downgrade)
        async with self.case.sessions.begin() as s: await s.execute(delete(EVENT).where(EVENT.c.stage.in_(STAGES)))
        async with self.case.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError,"populated study"): await c.run_sync(downgrade)

    async def test_original_ttl_and_account_purge_preserve_aggregate_without_source_reset(self):
        await self.contact();await self.lesson();await self.capture()
        self.storage.moment+=RAW_RETENTION+timedelta(seconds=1)
        await self.analysis.retention(execute=True)
        self.assertEqual(await self.facts(),[])
        self.assertEqual(len(await self.storage.rows(storage_fixture.GRANT)),1)
        self.assertEqual(await self.capture(),0)
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)
        async with self.case.sessions.begin() as s: await UserRepository(s)._delete_account(await s.get(User,1))
        self.assertEqual(await self.facts(),[])
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)

    async def test_postgres_parallel_captures_keep_one_fact_per_original_unit_and_stage(self):
        if not self.postgres: self.skipTest("PostgreSQL independent owner-locked captures")
        await self.contact();await self.lesson()
        await asyncio.gather(*(self.capture() for _ in range(5)))
        self.assertEqual(len(await self.facts()),2)
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)


class TelegramStudyChecks:
    postgres=False
    result=learning_fixture.TargetLearningChecks.result

    async def asyncSetUp(self):
        cls=open_fixture.PostgreSQLTelegramOpenTests if self.postgres else open_fixture.SQLiteTelegramOpenTests
        self.episode=cls(methodName="test_actual_telegram_content_fragment_and_signed_owner_report_once")
        await self.episode.asyncSetUp()
        self.case=self.episode.case

    async def asyncTearDown(self):
        if hasattr(self,"episode"): await self.episode.asyncTearDown()

    async def test_telegram_learner_can_return_manually_without_open_report(self):
        job,_proof=await self.episode.dispatch()
        started=self.case.tick
        self.learned=started+timedelta(seconds=20)
        await self.result()
        analysis=SmartReminderAnalysisService(self.case.sessions,clock=lambda:started+timedelta(seconds=60))
        await analysis.capture_job(1,job)
        facts=[r for r in await self.case.rows(EVENT) if r["stage"] in STAGES]
        self.assertEqual({r["stage"] for r in facts},{"verified_study_after_attempt"})
        result=await analysis.target_learning(1,job)
        self.assertEqual(result.verified_study_count,1)
        self.assertIsNone(result.reported_open_at)

    async def test_actual_telegram_report_and_native_lesson_create_temporal_study_facts(self):
        job,proof=await self.episode.dispatch()
        started=self.case.tick
        self.case.tick+=timedelta(seconds=10)
        self.assertTrue((await self.episode.report(job,proof))["observed"])
        self.learned=started+timedelta(seconds=20)
        await self.result()
        analysis=SmartReminderAnalysisService(self.case.sessions,clock=lambda:started+timedelta(seconds=60))
        await analysis.capture_job(1,job)
        facts=[r for r in await self.case.rows(EVENT) if r["stage"] in STAGES]
        self.assertEqual({r["stage"] for r in facts},STAGES)
        self.assertTrue(all(r["channel"]=="telegram" for r in facts))
        self.assertEqual((await analysis.target_learning(1,job)).verified_study_count,1)


class SQLiteStudyTests(StudyChecks,unittest.IsolatedAsyncioTestCase): pass
@unittest.skipUnless(storage_fixture.PG_URL,"Owned loopback PostgreSQL required")
class PostgreSQLStudyTests(StudyChecks,unittest.IsolatedAsyncioTestCase): postgres=True
class SQLiteTelegramStudyTests(TelegramStudyChecks,unittest.IsolatedAsyncioTestCase): pass
@unittest.skipUnless(storage_fixture.PG_URL,"Owned loopback PostgreSQL required")
class PostgreSQLTelegramStudyTests(TelegramStudyChecks,unittest.IsolatedAsyncioTestCase): postgres=True
