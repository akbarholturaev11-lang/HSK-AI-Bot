"""Existing practice receipts prove activity without rewriting grading or XP."""
from datetime import timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from sqlalchemy import insert, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService, PRACTICE_VERSION, TRAINING_SKILLS
from app.services.smart_reminder_baseline import windows
from app.services.smart_reminder_policy_context import read_scored_activity
from tests import test_smart_reminder_activity_analysis as fixture
from tests.test_course_miniapp_practice import question


class PracticeChecks:
    postgres=False
    asyncSetUp=fixture.ActivityChecks.asyncSetUp
    asyncTearDown=fixture.ActivityChecks.asyncTearDown
    read=fixture.ActivityChecks.read
    capture=fixture.ActivityChecks.capture
    facts=fixture.ActivityChecks.facts
    quiz=fixture.ActivityChecks.quiz

    @staticmethod
    def session_id(uid,mode,level="hsk1",skill=""):
        feature="placement" if mode=="placement" else "training_test"
        return f"practice:{uid}:{feature}:{mode}:{skill if mode=='training' else level}:v{PRACTICE_VERSION}"

    async def completion(self,*,uid=1,mode="mock",skill="",level="hsk1",at=None,payload=None,**changes):
        feature="placement" if mode=="placement" else "training_test"
        fields=dict(event_name="training_completed" if mode=="training" else "test_completed",
            user_id=uid,source="course_miniapp",level=level,session_id=self.session_id(uid,mode,level,skill),
            dedupe_key=f"practice:{feature}:completed",
            payload={"mode":mode,"skill":skill,"score":0,"total":1} if payload is None else payload)
        fields.update(changes)
        async with self.case.sessions.begin() as s:
            result=await CourseMiniAppAnalyticsService(s).record_server_event(**fields)
            self.assertTrue(result["recorded"],result)
            row=await s.scalar(select(CourseMiniAppEvent.id).where(CourseMiniAppEvent.user_id==uid,
                CourseMiniAppEvent.event_name==fields["event_name"],CourseMiniAppEvent.dedupe_key==fields["dedupe_key"]))
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(created_at=at or self.at))
        return row

    async def scored(self,*,uid=1,level="hsk1",since=None,until=None):
        async with self.case.sessions() as s:
            return await read_scored_activity(s,uid,level=level,history_since=since or self.at-timedelta(hours=1),
                observed_at=until or self.at+timedelta(hours=1))

    async def grade(self,mode,*,uid=1):
        skill="pinyin" if mode=="training" else ""
        sid=self.session_id(uid,mode,skill=skill)
        async with self.case.sessions() as s:
            service=CourseMiniAppPracticeService(s)
            service._questions=AsyncMock(return_value=[question("graded-q1")])
            service.mistakes=SimpleNamespace(record_items=AsyncMock(return_value=0))
            result=await service.complete(await s.get(User,uid),session_id=sid,mode=mode,level="hsk1",lang="uz",skill=skill,
                answers=[{"question_id":"graded-q1","selected_index":1}],gate_checked=True)
            self.assertTrue(result["ok"],result)
            self.assertEqual((result["score"],result["total"]),(0,1))
            feature="placement" if mode=="placement" else "training_test"
            row=await s.scalar(select(CourseMiniAppEvent.id).where(CourseMiniAppEvent.user_id==uid,
                CourseMiniAppEvent.event_name==("training_completed" if mode=="training" else "test_completed"),
                CourseMiniAppEvent.dedupe_key==f"practice:{feature}:completed"))
        return result,row

    async def original_reward(self,mode,*,uid=1):
        sid=self.session_id(uid,mode,skill="pinyin" if mode=="training" else "")
        old=self.at-timedelta(days=2)
        async with self.case.sessions.begin() as s:
            s.add(CourseXpEvent(user_id=uid,activity_type="training" if mode=="training" else "test",
                activity_ref=sid+":completed",xp=8,activity_date=old.date(),week_start=old.date(),created_at=old))

    async def test_actual_shared_grader_records_all_modes_without_fresh_xp(self):
        await self.episode.contact(report=False)
        for n,mode in enumerate(("mock","placement","training")):
            await self.original_reward(mode)
            before=await self.storage.rows(CourseXpEvent.__table__)
            result,row=await self.grade(mode)
            self.assertTrue(result["reward"]["duplicate"])
            self.assertEqual(result["reward"]["awarded_xp"],0)
            self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),before)
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(created_at=self.at+timedelta(seconds=n)))
        self.assertEqual((await self.scored()).times,tuple(self.at+timedelta(seconds=n) for n in range(3)))
        projection=await self.read()
        self.assertEqual(projection.first_active_study_at,self.at)
        self.assertIsNone(projection.verified_study_count)
        self.assertIsNone(projection.reported_open_at)
        self.assertEqual(await self.capture(),2)
        self.assertEqual(await self.capture(),0)
        self.assertEqual({r["stage"] for r in await self.facts()},{"study_day_after_attempt"})

    async def test_native_only_owner_uses_same_real_grader_and_canonical_receipt(self):
        async with self.case.sessions() as s:
            self.assertIsNone((await s.get(User,2)).telegram_id)
        await self.original_reward("mock",uid=2)
        result,row=await self.grade("mock",uid=2)
        self.assertEqual(result["reward"]["awarded_xp"],0)
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(created_at=self.at))
        self.assertEqual((await self.scored(uid=2)).times,(self.at,))
        self.assertEqual((await self.scored(uid=1)).times,())

    async def test_retry_preserves_old_result_time_and_does_not_invent_repeat_activity(self):
        await self.original_reward("mock")
        _,row=await self.grade("mock")
        old=self.at-timedelta(days=1)
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(created_at=old))
        before=await self.storage.rows(CourseMiniAppEvent.__table__)
        result,same=await self.grade("mock")
        self.assertEqual(same,row);self.assertTrue(result["reward"]["duplicate"])
        self.assertEqual(await self.storage.rows(CourseMiniAppEvent.__table__),before)
        evidence=await self.scored()
        self.assertEqual(evidence.times,())
        self.assertIn("repeat_practice_and_partial_voice_unavailable",evidence.coverage_limits)

    async def test_all_five_supported_training_skills_match_actual_protocol(self):
        for uid,skill in enumerate(sorted(TRAINING_SKILLS),start=10):
            async with self.case.sessions.begin() as s: s.add(User(id=uid,telegram_id=None,status="free"))
            await self.completion(uid=uid,mode="training",skill=skill)
            self.assertEqual((await self.scored(uid=uid)).times,(self.at,))

    async def test_foreign_owner_source_or_course_never_establishes_activity(self):
        row=await self.completion()
        async with self.case.sessions() as s:
            original=dict((await s.execute(select(CourseMiniAppEvent.__table__).where(CourseMiniAppEvent.id==row))).mappings().one())
        for changes in ({"source":"client_telemetry"},{"source":"android"},{"source":"desktop_course"},
                {"source":"course_hsk_exam"},{"user_id":2},{"level":"hsk2"},{"level":"nhsk1"},
                {"session_id":self.session_id(2,"mock")},{"dedupe_key":"practice:training_test:other"}):
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(**(original|changes)))
            self.assertEqual((await self.scored()).times,(),changes)

    async def test_mode_skill_event_scope_and_future_version_are_not_inferred(self):
        row=await self.completion(mode="training",skill="pinyin")
        original={"mode":"training","skill":"pinyin","score":0,"total":1}
        for fields,payload in (({"event_name":"test_completed"},original),
                ({},{**original,"mode":"mock"}),({},{**original,"skill":"words"}),
                ({},{**original,"skill":"listening"}),({},{**original,"mode":["training"]}),
                ({"session_id":self.session_id(1,"training",skill="pinyin")[:-1]+"2"},original),
                ({"session_id":self.session_id(1,"training",skill="pinyin")[:-2]+"v01"},original)):
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(**({
                    "event_name":"training_completed","session_id":self.session_id(1,"training",skill="pinyin"),
                    "payload_json":json.dumps(payload)}|fields)))
            self.assertEqual((await self.scored()).times,())

    async def test_boolean_bad_score_percent_only_and_nonobject_payload_are_rejected(self):
        row=await self.completion()
        for payload in ({"score":True,"total":1},{"score":0,"total":True},{"score":"0","total":1},
                {"score":-1,"total":1},{"score":2,"total":1},{"score":0,"total":0},
                {"score":0,"total":1001},{"percent":50,"total":2},[],None):
            value={"mode":"mock","skill":"",**payload} if isinstance(payload,dict) else payload
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(payload_json=json.dumps(value)))
            self.assertEqual((await self.scored()).times,())

    async def test_client_cannot_record_terminal_practice_events(self):
        async with self.case.sessions() as s:
            for name in ("test_completed","training_completed","practice_attempt_scored"):
                result=await CourseMiniAppAnalyticsService(s).record_client_event(event_name=name,user_id=1)
                self.assertEqual(result["error"],"course_client_event_not_allowed")

    async def test_original_source_time_respects_inclusive_reader_bounds(self):
        row=await self.completion()
        self.assertEqual((await self.scored(since=self.at,until=self.at)).times,(self.at,))
        for at in (self.at-timedelta(seconds=1),self.at+timedelta(seconds=1)):
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row).values(created_at=at))
            self.assertEqual((await self.scored(since=self.at,until=self.at)).times,())

    async def test_activity_capture_is_read_only_for_learning_and_private_payloads(self):
        await self.episode.contact(report=False)
        await self.completion()
        tables=(fixture.schema.JOB,fixture.schema.ATTEMPT,fixture.schema.GRANT,CourseProgress.__table__,
            CourseXpEvent.__table__,CourseMiniAppEvent.__table__)
        before=[await self.storage.rows(t) for t in tables]
        self.assertEqual((await self.read()).first_active_study_at,self.at)
        await self.capture()
        self.assertEqual(before,[await self.storage.rows(t) for t in tables])
        for row in await self.facts():
            self.assertNotIn("score",row);self.assertNotIn("payload_json",row)
            self.assertNotIn("practice:",str(row))

    async def test_over_limit_events_remain_unknown_while_independent_quiz_proves_activity(self):
        await self.completion()
        async with self.case.sessions.begin() as s:
            await s.execute(insert(CourseMiniAppEvent.__table__),[dict(user_id=1,event_name="test_completed",source="course_miniapp",
                level="hsk1",session_id=self.session_id(1,"mock"),dedupe_key=f"unreviewed:{i}",
                created_at=self.at,payload_json='{"mode":"mock","skill":"","score":0,"total":1}') for i in range(512)])
        evidence=await self.scored()
        self.assertEqual(evidence.times,());self.assertIn("scored_events_over_limit",evidence.coverage_limits)
        await self.quiz()
        evidence=await self.scored()
        self.assertEqual(evidence.times,(self.at,));self.assertIn("scored_events_over_limit",evidence.coverage_limits)

    async def test_24_hour_contact_window_uses_practice_without_units_or_clicks(self):
        await self.episode.contact(report=False)
        await self.completion()
        evidence=await self.analysis.return_learning(1,self.case.job_id)
        self.assertEqual(evidence.first_study_at,self.at)
        self.assertIsNone(evidence.verified_study_count)

    async def test_baseline_d7_uses_stored_practice_without_new_xp(self):
        from tests import test_smart_reminder_baseline as baseline
        checks=baseline.PostgreSQLBaselineTests if self.postgres else baseline.SQLiteBaselineTests
        case=checks(methodName="test_scored_failed_repeat_without_xp_proves_d7_once")
        await case.asyncSetUp()
        try:
            await case.enroll()
            d7,_=windows(case.now,"Etc/UTC")
            async with case.q.sessions.begin() as s:
                await CourseMiniAppAnalyticsService(s).record_server_event(event_name="test_completed",user_id=1,
                    level="hsk1",session_id=self.session_id(1,"mock"),dedupe_key="practice:training_test:completed",
                    payload={"mode":"mock","skill":"","score":0,"total":1})
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name=="test_completed").values(created_at=d7+timedelta(hours=1)))
            report=await case.report()
            self.assertEqual(report["observed_d7_accounts_lower_bound"],1)
            self.assertEqual(report["observed_units_lower_bound"],0)
        finally: await case.asyncTearDown()


class SQLitePracticeTests(PracticeChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLPracticeTests(PracticeChecks,unittest.IsolatedAsyncioTestCase): postgres=True
