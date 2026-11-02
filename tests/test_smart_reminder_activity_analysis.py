"""Positive scored study days, separate from XP/completion units and clicks."""
import asyncio
from datetime import timedelta
import json
import unittest
from uuid import uuid4
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, select, update
from unittest.mock import AsyncMock, patch

from app.db.models.course_attempts import CourseAttempt
from app.db.models.course_lessons import CourseLesson
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.repositories.course_attempt_repo import CourseAttemptRepository
from app.repositories.user_repo import UserRepository
from app.services.course_hsk_exam_service import CourseHskExamService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_lesson_flow_service import CourseMiniAppLessonFlowService
from app.services.smart_reminder_analysis import EVENT, MONTHLY, RAW_RETENTION, SmartReminderAnalysisObserver
from app.services.smart_reminder_preferences import _utc
from tests import test_smart_reminder_analysis as schema
from tests import test_smart_reminder_study_analysis as fixture

STAGES = {"study_day_after_attempt", "study_day_after_report"}


class ActivityChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = fixture.PostgreSQLStudyTests if self.postgres else fixture.SQLiteStudyTests
        self.episode = cls(methodName="test_manual_app_return_and_real_practice_counts_without_tapping_notification")
        await self.episode.asyncSetUp()
        self.case, self.storage, self.analysis = self.episode.case, self.episode.storage, self.episode.analysis
        self.at = self.episode.learned
        async with self.case.sessions.begin() as s:
            lesson = CourseLesson(level="hsk1", lesson_order=5, lesson_code="smart-activity-qa", title="QA")
            s.add(lesson)
            await s.flush()
            self.lesson_id = lesson.id

    async def asyncTearDown(self):
        if hasattr(self, "episode"):
            await self.episode.asyncTearDown()

    async def section(self, *, at=None, uid=1, level="hsk1", source="course_miniapp",
                      name="section_attempt_scored", payload=None, **changes):
        async with self.case.sessions.begin() as s:
            key = "section-attempt:" + uuid4().hex
            fields = dict(event_name=name, source=source, user_id=uid, level=level,
                lesson_id=self.lesson_id, lesson_order=5, dedupe_key=key,
                payload={"section_key":"vocab", "correct":0, "total":3, "percent":0} if payload is None else payload)
            fields.update(changes)
            result = await CourseMiniAppAnalyticsService(s).record_server_event(**fields)
            self.assertTrue(result["recorded"], result)
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==uid,
                CourseMiniAppEvent.dedupe_key==fields["dedupe_key"]).values(created_at=at or self.at))

    async def quiz(self, *, uid=1, at=None, source="miniapp_server_graded", kind="quiz", payload=None):
        async with self.case.sessions.begin() as s:
            row = await CourseAttemptRepository(s).create(user_id=uid, lesson_id=self.lesson_id,
                attempt_type=kind, step_name="miniapp_quiz", score=0, passed=False, ai_feedback=None,
                answers_json=json.dumps(payload if payload is not None else
                    {"source":source,"score":0,"total":3,"percent":0,"answers":[]}))
            row.created_at = at or self.at

    async def exam(self, *, at=None, uid=1, payload=None, **changes):
        sid = CourseHskExamService._session_id(uid, "hsk1", "uz", uuid4().hex)
        async with self.case.sessions.begin() as s:
            fields=dict(event_name="test_completed",source="course_hsk_exam",user_id=uid,level="hsk1",
                session_id=sid,dedupe_key=sid+":completed",payload=CourseHskExamService._completed_event_payload(
                    {"score":0,"total":40,"percent":0,"passed":False,"material_version":2,
                     "material_id":"hsk1:exam:static-v1","reward":{"awarded_xp":0,"duplicate":True}}
                    if payload is None else payload))
            fields.update(changes)
            result=await CourseMiniAppAnalyticsService(s).record_server_event(**fields)
            self.assertTrue(result["recorded"],result)
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==uid,
                CourseMiniAppEvent.dedupe_key==fields["dedupe_key"]).values(created_at=at or self.at))

    async def capture(self):
        return await self.analysis.capture_job(1,self.case.job_id)

    async def facts(self):
        return [r for r in await self.storage.rows(EVENT) if r["stage"] in STAGES]

    async def read(self):
        return await self.analysis.target_learning(1,self.case.job_id)

    async def test_failed_no_xp_manual_return_is_one_study_day_not_completed_unit(self):
        await self.episode.contact(report=False)
        await self.section()
        source_tables=(schema.JOB,schema.ATTEMPT,schema.GRANT,CourseMiniAppEvent.__table__,
                       CourseAttempt.__table__,CourseXpEvent.__table__)
        before=[await self.storage.rows(t) for t in source_tables]
        result=await self.read()
        self.assertEqual(result.first_active_study_at,self.at)
        self.assertIsNone(result.first_active_study_after_report_at)
        self.assertIsNone(result.verified_study_count)
        self.assertIsNone(result.learned_at)
        self.assertEqual(await self.capture(),1)
        self.assertEqual(await self.capture(),0)
        self.assertEqual({r["stage"] for r in await self.facts()},{"study_day_after_attempt"})
        self.assertEqual(before,[await self.storage.rows(t) for t in source_tables])
        self.assertIn("negative_learning_coverage_unknown",result.coverage_limits)

    async def test_repeated_section_quiz_and_exam_without_xp_do_not_inflate_day(self):
        await self.episode.contact()
        original_xp=await self.storage.rows(CourseXpEvent.__table__)
        await self.section()
        await self.quiz(at=self.at+timedelta(seconds=1))
        await self.exam(at=self.at+timedelta(seconds=2))
        self.assertEqual(await self.capture(),2)
        before=await self.facts()
        await self.section(at=self.at+timedelta(seconds=3))
        self.assertEqual(await self.capture(),0)
        self.assertEqual(before,await self.facts())
        self.assertIsNone((await self.read()).verified_study_count)
        self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),original_xp)
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)
        for row in before:
            self.assertEqual(row["reason_code"],"verified_server_activity")
            self.assertEqual(_utc(row["occurred_at"]),self.at)
            self.assertEqual(_utc(row["expires_at"]),self.at+RAW_RETENTION)
        self.assertNotIn("answers",str(before))

    async def test_actual_section_grader_commits_failed_repeat_without_xp(self):
        from tests.test_course_miniapp_lesson_flow import CourseMiniAppLessonFlowBuilderTests
        await self.episode.contact(report=False)
        original_xp=await self.storage.rows(CourseXpEvent.__table__)
        async with self.case.sessions() as s:
            user,lesson=await s.get(User,1),await s.get(CourseLesson,self.lesson_id)
            lesson.lesson_order=1
            await s.commit()
            service=CourseMiniAppLessonFlowService(s)
            payload=CourseMiniAppLessonFlowBuilderTests.payload()
            service._context=AsyncMock(return_value=(user,SimpleNamespace(),lesson,""))
            service._completed_section_keys=AsyncMock(return_value={"1.1"})
            service.lesson_service=SimpleNamespace(get_payload=AsyncMock(return_value=payload))
            service.mistakes=SimpleNamespace(record_items=AsyncMock(return_value=0))
            sections=service._section_plan(payload,level="hsk1",lesson_order=1)
            section=next(x for x in sections if x["section_key"]=="1.2")
            cards=service._build_cards(service._section_payload(payload,section),lang="ru",lesson_order=1)
            responses=[]
            for card in cards:
                if not card.get("required"): continue
                if "correct_index" in card:
                    response={"selected_index":(card["correct_index"]+1)%len(card["options"])}
                elif "answer_tokens" in card:
                    response={"answer_tokens":["invalid-answer"]}
                else:
                    response={"completed":True}
                responses.append({"card_id":card["id"]}|response)
            for _ in range(2):
                result=await service.complete_flow(user.telegram_id,level="hsk1",lesson_order=1,
                    lang="ru",responses=responses,section_key="1.2")
                self.assertEqual(result.get("error"),"lesson_score_too_low",result)
            await s.execute(update(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name=="section_attempt_scored").values(created_at=self.at))
            await s.commit()
        self.assertEqual(await self.capture(),1)
        self.assertEqual((await self.read()).first_active_study_at,self.at)
        self.assertIsNone((await self.read()).verified_study_count)
        self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),original_xp)

    async def test_each_reviewed_source_can_independently_prove_study(self):
        await self.episode.contact(report=False)
        for make in (self.section,self.quiz,self.exam):
            await make()
            self.assertEqual((await self.read()).first_active_study_at,self.at)
            async with self.case.sessions.begin() as s:
                await s.execute(delete(CourseMiniAppEvent))
                await s.execute(delete(CourseAttempt))

    async def test_later_activity_after_report_counts_without_rewriting_primary_day(self):
        await self.episode.contact(report=False)
        early=self.episode.started+timedelta(seconds=5)
        await self.section(at=early)
        self.assertEqual(await self.capture(),1)
        primary=await self.facts()
        grant=(await self.storage.rows(schema.GRANT))[0]
        from app.services.smart_reminder_preferences import SmartReminderActor
        proof=self.episode.opens.proof(SmartReminderActor(1,"android",device_id="device-1",session_id="session-1"),
            self.case.job_id,grant["id"])
        r=await self.case.client.post(f"/api/v3/android/smart-reminder/jobs/{self.case.job_id}/open",
            headers=await self.case.bearer(1),json={"version":1,"proof":proof})
        self.assertTrue(r.json()["observed"])
        self.assertEqual(await self.capture(),0)
        await self.quiz()
        self.assertEqual(await self.capture(),1)
        result=await self.read()
        self.assertEqual((result.first_active_study_at,result.first_active_study_after_report_at),(early,self.at))
        self.assertIn(primary[0],await self.facts())

    async def test_foreign_source_course_lesson_and_client_events_do_not_prove_study(self):
        await self.episode.contact()
        await self.section(uid=2)
        await self.section(source="android_telemetry")
        await self.section(level="hsk2")
        await self.section(lesson_order=6)
        await self.section(name="section_completed")
        await self.section(dedupe_key="client-key")
        await self.quiz(source="ai_feedback")
        await self.quiz(kind="homework")
        await self.exam(session_id=CourseHskExamService._session_id(2,"hsk1","uz","other"))
        self.assertEqual(await self.capture(),0)
        self.assertIsNone((await self.read()).first_active_study_at)
        async with self.case.sessions.begin() as s:
            for name in ("section_attempt_scored","test_completed"):
                result=await CourseMiniAppAnalyticsService(s).record_client_event(event_name=name,user_id=1)
                self.assertFalse(result["ok"])

    async def test_bad_scores_and_percent_only_are_not_graded_activity(self):
        await self.episode.contact()
        for pair in ({"correct":True,"total":3}, {"correct":0,"total":0}, {"correct":4,"total":3},
                     {"percent":100}, {"correct":"1","total":3}):
            await self.section(payload={"section_key":"vocab"}|pair)
        for payload in ({"source":"miniapp_server_graded","score":True,"total":3},
                        {"source":"miniapp_server_graded","percent":100}):
            await self.quiz(payload=payload)
        await self.exam(payload={"score":0,"total":40})
        self.assertEqual(await self.capture(),0)
        self.assertIsNone((await self.read()).first_active_study_at)

    async def test_before_equal_future_and_end_boundary_do_not_count(self):
        await self.episode.contact()
        job=(await self.storage.rows(schema.JOB))[0]
        for at in (self.episode.started-timedelta(seconds=1),self.episode.started,
                   self.storage.moment+timedelta(seconds=1),_utc(job["day_end_utc"])):
            await self.section(at=at)
        self.assertEqual(await self.capture(),0)
        self.assertIsNone((await self.read()).first_active_study_at)

    async def test_missing_contact_unknown_outcome_or_blocked_owner_no_day(self):
        await self.section()
        self.assertEqual(await self.capture(),1) # Existing reservation only.
        await self.episode.contact(report=False,outcome="client_outcome_unknown")
        self.assertEqual(await self.facts(),[])
        self.assertIsNone((await self.read()).first_active_study_at)
        async with self.case.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="blocked"))
        await self.capture()
        self.assertEqual(await self.facts(),[])

    async def test_scored_source_limit_is_unknown_but_independent_quiz_can_prove_day(self):
        await self.episode.contact()
        async with self.case.sessions.begin() as s:
            s.add_all([CourseMiniAppEvent(user_id=1,source="course_miniapp",level="hsk1",
                event_name="section_attempt_scored",lesson_id=self.lesson_id,lesson_order=5,
                dedupe_key="section-attempt:"+uuid4().hex,created_at=self.at,
                payload_json=json.dumps({"section_key":"vocab","correct":0,"total":3})) for _ in range(513)])
        result=await self.read()
        self.assertIsNone(result.first_active_study_at)
        self.assertIn("scored_events_over_limit",result.coverage_limits)
        await self.quiz()
        self.assertEqual((await self.read()).first_active_study_at,self.at)
        self.assertEqual(await self.capture(),2)

    async def test_quiz_limit_does_not_create_fake_zero_or_hide_independent_exam(self):
        await self.episode.contact(report=False)
        async with self.case.sessions.begin() as s:
            s.add_all([CourseAttempt(user_id=1,lesson_id=self.lesson_id,attempt_type="quiz",created_at=self.at,
                answers_json='{"source":"miniapp_server_graded","score":0,"total":3}') for _ in range(513)])
        result=await self.read()
        self.assertIsNone(result.first_active_study_at)
        self.assertIn("scored_quizzes_over_limit",result.coverage_limits)
        await self.exam()
        self.assertEqual((await self.read()).first_active_study_at,self.at)

    async def test_counter_failure_rolls_back_day_and_reconciliation_recovers(self):
        await self.episode.contact()
        await self.section()
        original=self.analysis._insert
        def broken(s,t):
            if t is MONTHLY: raise RuntimeError("synthetic-private-counter")
            return original(s,t)
        with patch.object(self.analysis,"_insert",side_effect=broken):
            with self.assertRaises(RuntimeError): await self.capture()
        self.assertEqual(await self.facts(),[])
        observer=SmartReminderAnalysisObserver(self.case.settings,self.case.sessions,clock=lambda:self.storage.moment)
        await observer.reconcile_tick()
        self.assertEqual(len(await self.facts()),2)
        await observer.reconcile_tick()
        self.assertEqual(len(await self.facts()),2)

    async def test_populated_upgrade_roundtrip_preserves_old_facts_and_sources(self):
        await self.episode.contact()
        await self.section()
        tables=(EVENT,MONTHLY,schema.JOB,schema.ATTEMPT,schema.GRANT,CourseMiniAppEvent.__table__)
        before=[await self.storage.rows(t) for t in tables]
        def cycle(c):
            with Operations.context(MigrationContext.configure(c)):
                schema.activity_migration.downgrade()
                schema.activity_migration.upgrade()
        async with self.case.engine.begin() as c: await c.run_sync(cycle)
        self.assertEqual(before,[await self.storage.rows(t) for t in tables])
        self.assertEqual(await self.capture(),2)

    async def test_new_raw_and_anonymous_only_stages_refuse_downgrade(self):
        await self.episode.contact()
        await self.section()
        await self.capture()
        def downgrade(c):
            with Operations.context(MigrationContext.configure(c)): schema.activity_migration.downgrade()
        for raw in (True,False):
            if not raw:
                async with self.case.sessions.begin() as s:
                    await s.execute(delete(EVENT).where(EVENT.c.stage.in_(STAGES)))
            async with self.case.engine.begin() as c:
                with self.assertRaisesRegex(RuntimeError,"populated activity"): await c.run_sync(downgrade)

    async def test_original_expiry_and_purge_do_not_resurrect_or_erase_source(self):
        await self.episode.contact()
        await self.section()
        await self.capture()
        source=await self.storage.rows(CourseMiniAppEvent.__table__)
        self.storage.moment=self.at+RAW_RETENTION+timedelta(seconds=1)
        await self.analysis.retention(execute=True)
        self.assertEqual(await self.facts(),[])
        self.assertEqual(await self.capture(),0)
        self.assertEqual(source,await self.storage.rows(CourseMiniAppEvent.__table__))
        async with self.case.sessions.begin() as s:
            await UserRepository(s)._delete_account(await s.get(User,1))
        self.assertEqual(await self.facts(),[])
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)

    async def test_submitted_deletion_prevents_new_detail(self):
        await self.episode.contact()
        await self.section()
        await self.case._deletion()
        self.assertEqual(await self.capture(),0)
        self.assertEqual(await self.facts(),[])

    async def test_canonical_account_purge_removes_retained_day_detail(self):
        await self.episode.contact()
        await self.section()
        await self.capture()
        self.assertEqual(len(await self.facts()),2)
        async with self.case.sessions.begin() as s:
            await UserRepository(s)._delete_account(await s.get(User,1))
        self.assertEqual(await self.facts(),[])
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)

    async def test_postgres_concurrent_capture_counts_each_day_stage_once(self):
        if not self.postgres: self.skipTest("PostgreSQL owner serialization")
        await self.episode.contact()
        await self.section()
        await asyncio.gather(*(self.capture() for _ in range(5)))
        self.assertEqual(len(await self.facts()),2)
        self.assertEqual(sum(r["fact_count"] for r in await self.storage.rows(MONTHLY) if r["stage"] in STAGES),2)


class SQLiteActivityAnalysisTests(ActivityChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLActivityAnalysisTests(ActivityChecks,unittest.IsolatedAsyncioTestCase): postgres=True
