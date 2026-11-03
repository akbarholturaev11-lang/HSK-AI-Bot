"""Private completed voice activity is separate from XP units and exact turns."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import unittest

from sqlalchemy import event, insert, select, update

from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.ai_service import AIUsageResult
from app.services.smart_reminder_baseline import windows
from app.services.smart_reminder_policy_context import read_scored_activity
from app.services.voice_practice_service import VoicePracticeError, VoicePracticeService
from tests import test_smart_reminder_activity_analysis as fixture


class VoiceChecks:
    postgres=False
    asyncSetUp=fixture.ActivityChecks.asyncSetUp
    asyncTearDown=fixture.ActivityChecks.asyncTearDown
    read=fixture.ActivityChecks.read
    capture=fixture.ActivityChecks.capture
    facts=fixture.ActivityChecks.facts
    quiz=fixture.ActivityChecks.quiz

    async def voice(self, **changes):
        fields=dict(id=str(uuid4()),user_id=1,user_telegram_id=None,role="friend",level="hsk1",
            language="uz",voice="female",mode="turn",status="completed",turn_count=1,
            started_at=self.at-timedelta(seconds=10),ended_at=self.at,
            history=[{"user":"synthetic private transcript"}],corrections=["synthetic private correction"])
        fields.update(changes)
        async with self.case.sessions.begin() as s:
            s.add(VoicePracticeSession(**fields))
        return fields["id"]

    async def activity(self, *, uid=1,level="hsk1",since=None,until=None):
        async with self.case.sessions() as s:
            return await read_scored_activity(s,uid,level=level,
                history_since=since or self.at-timedelta(hours=1),observed_at=until or self.at+timedelta(hours=1))

    async def actual_flow(self, *, uid=1, mode="turn", empty=False, failed=False):
        sid=await self.voice(user_id=uid,mode=mode,status="active",turn_count=0,ended_at=None,history=[],corrections=[])
        at=self.at
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None): return at.astimezone(tz) if tz else at.replace(tzinfo=None)
        async with self.case.sessions() as s:
            actor=await s.get(User,uid)
            service=VoicePracticeService(s)
            reply=dict(chinese_reply="你好！",pinyin="nǐ hǎo",translation="Salom",correction=None,error_type="none",suggestions=[])
            usage=AIUsageResult(content="{}",model="gpt-4o-mini",prompt_tokens=10,completion_tokens=10,total_tokens=20)
            service._generate_reply=AsyncMock(return_value=(reply,usage))
            if failed: service._generate_reply.side_effect=VoicePracticeError("AI_FAILED","synthetic AI failure",502)
            with patch("app.services.voice_practice_service.settings",SimpleNamespace(ai_enabled=mode=="turn")), \
                    patch("app.services.voice_practice_service.datetime",Clock):
                if not empty:
                    if failed:
                        with self.assertRaises(VoicePracticeError):
                            await service.process_message(actor,session_id=sid,audio_bytes=b"",filename="",text="你好")
                    elif mode=="turn":
                        await service.process_message(actor,session_id=sid,audio_bytes=b"",filename="",text="你好")
                    else:
                        # Same input boundary as the authenticated server provider relay;
                        # enrichment is optional and not required to persist a real turn.
                        await service.process_live_turn(actor,session_id=sid,transcription="你好",
                            assistant_text="你好！",provider_usage=usage)
                result=await service.end_session(actor,sid)
        return sid,result

    async def test_actual_server_turn_and_end_count_without_click_or_completed_unit(self):
        await self.episode.contact(report=False)
        _,result=await self.actual_flow()
        self.assertEqual(result["message_count"],1)
        self.assertFalse(result["completed"])  # Seven-turn UI milestone is not an activity threshold.
        self.assertIsNotNone(result["reward"])
        evidence=await self.read()
        self.assertEqual(evidence.first_active_study_at,self.at)
        self.assertIsNone(evidence.verified_study_count)
        self.assertIsNone(evidence.reported_open_at)
        self.assertEqual(await self.capture(),2)
        self.assertEqual(await self.capture(),0)
        self.assertEqual({r["stage"] for r in await self.facts()},{"study_day_after_attempt"})

    async def test_actual_live_turn_survives_optional_enrichment_without_a_new_grade(self):
        _,result=await self.actual_flow(mode="live")
        self.assertEqual(result["message_count"],1)
        self.assertEqual((await self.activity()).times,(self.at,))

    async def test_empty_or_failed_actual_session_does_not_prove_study_or_award_xp(self):
        before=await self.storage.rows(CourseXpEvent.__table__)
        for changes in ({"empty":True},{"failed":True}):
            _,result=await self.actual_flow(**changes)
            self.assertEqual(result["message_count"],0)
            self.assertIsNone(result["reward"])
        self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),before)
        self.assertEqual((await self.activity()).times,())

    async def test_native_only_real_flow_has_canonical_ownership(self):
        async with self.case.sessions() as s: self.assertIsNone((await s.get(User,2)).telegram_id)
        await self.actual_flow(uid=2)
        self.assertEqual((await self.activity(uid=2)).times,(self.at,))
        self.assertEqual((await self.activity(uid=1)).times,())

    async def test_foreign_null_owner_status_mode_course_and_bad_times_are_excluded(self):
        sid=await self.voice()
        defaults=dict(user_id=1,user_telegram_id=None,status="completed",mode="turn",level="hsk1",turn_count=1,
            started_at=self.at-timedelta(seconds=10),ended_at=self.at)
        async with self.case.sessions() as s: tid=(await s.get(User,1)).telegram_id
        for changes in ({"user_id":2},{"user_id":None,"user_telegram_id":tid},
                {"status":"active"},{"status":"abandoned"},{"mode":"unknown"},{"turn_count":0},{"turn_count":-1},
                {"level":"hsk2"},{"level":"beginner"},{"level":"hsk1_2"},{"level":"nhsk4"},
                {"ended_at":None},{"ended_at":self.at-timedelta(minutes=1)},
                {"started_at":self.at-timedelta(hours=2)}, {"ended_at":self.at+timedelta(hours=2)}):
            async with self.case.sessions.begin() as s:
                await s.execute(update(VoicePracticeSession).where(VoicePracticeSession.id==sid).values(**(defaults|changes)))
            self.assertEqual((await self.activity()).times,(),changes)

    async def test_noncanonical_session_identity_is_not_inferred(self):
        for sid in ("legacy",str(uuid4()).upper(),"00000000-0000-1000-8000-000000000000"):
            await self.voice(id=sid)
        self.assertEqual((await self.activity()).times,())

    async def test_reviewed_new_track_and_account_wide_reads_preserve_exact_course(self):
        await self.voice(level="nhsk1")
        self.assertEqual((await self.activity()).times,())
        self.assertEqual((await self.activity(level="nhsk1")).times,(self.at,))
        self.assertEqual((await self.activity(level=None)).times,(self.at,))

    async def test_inclusive_raw_bounds_and_cross_midnight_are_conservative(self):
        since=self.at.replace(hour=23,minute=50,second=0,microsecond=0)
        ended=since+timedelta(minutes=20)
        sid=await self.voice(started_at=since,ended_at=ended)
        self.assertEqual((await self.activity(since=since,until=ended)).times,(ended,))
        async with self.case.sessions.begin() as s:
            await s.execute(update(VoicePracticeSession).where(VoicePracticeSession.id==sid).values(started_at=since-timedelta(microseconds=1)))
        self.assertEqual((await self.activity(since=since,until=ended)).times,())

    async def test_minimal_queries_and_capture_preserve_private_learning_sources(self):
        await self.episode.contact(report=False)
        sid=await self.voice()
        before=await self.storage.rows(VoicePracticeSession.__table__)
        xp=await self.storage.rows(CourseXpEvent.__table__)
        queries=[]
        def observe(conn,cursor,statement,parameters,context,executemany):
            if "voice_practice_sessions" in statement: queries.append(statement)
        event.listen(self.case.engine.sync_engine,"before_cursor_execute",observe)
        try:
            await self.read();await self.capture()
        finally: event.remove(self.case.engine.sync_engine,"before_cursor_execute",observe)
        self.assertTrue(queries)
        for sql in queries:
            self.assertTrue(sql.lstrip().upper().startswith("SELECT"),sql)
            for private in (".history",".corrections",".target_words",".review_words",".plan_json",".live_resumption_handle"):
                self.assertNotIn(private,sql)
        self.assertEqual(await self.storage.rows(VoicePracticeSession.__table__),before)
        self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),xp)
        for fact in await self.facts():
            self.assertNotIn(sid,str(fact));self.assertNotIn("synthetic private",str(fact))

    async def test_voice_overflow_keeps_independent_quiz_positive_and_unknown_coverage(self):
        async with self.case.sessions.begin() as s:
            await s.execute(insert(VoicePracticeSession.__table__),[dict(id=str(uuid4()),user_id=1,role="friend",
                level="hsk1",language="uz",voice="female",mode="turn",status="completed",turn_count=1,
                started_at=self.at-timedelta(seconds=1),ended_at=self.at) for _ in range(513)])
        result=await self.activity()
        self.assertEqual(result.times,())
        self.assertIn("completed_voice_over_limit",result.coverage_limits)
        await self.quiz()
        result=await self.activity()
        self.assertEqual(result.times,(self.at,))
        self.assertIn("completed_voice_over_limit",result.coverage_limits)

    async def test_24_hour_contact_accepts_voice_without_xp_or_tapping(self):
        await self.episode.contact(report=False)
        await self.voice()
        result=await self.analysis.return_learning(1,self.case.job_id)
        self.assertEqual(result.first_study_at,self.at)
        self.assertIsNone(result.verified_study_count)
        self.assertIn("partial_practice_and_voice_unavailable",result.coverage_limits)

    async def test_baseline_d7_counts_completed_voice_without_inventing_units(self):
        from tests import test_smart_reminder_baseline as baseline
        checks=baseline.PostgreSQLBaselineTests if self.postgres else baseline.SQLiteBaselineTests
        case=checks(methodName="test_scored_failed_repeat_without_xp_proves_d7_once")
        await case.asyncSetUp()
        try:
            await case.enroll()
            d7,_=windows(case.now,"Etc/UTC")
            async with case.q.sessions.begin() as s:
                s.add(VoicePracticeSession(id=str(uuid4()),user_id=1,role="friend",level="hsk1",language="uz",voice="female",
                    mode="turn",status="completed",turn_count=1,started_at=d7+timedelta(minutes=1),ended_at=d7+timedelta(minutes=2)))
            result=await case.report()
            self.assertEqual(result["observed_d7_accounts_lower_bound"],1)
            self.assertEqual(result["observed_units_lower_bound"],0)
        finally: await case.asyncTearDown()


class SQLiteVoiceTests(VoiceChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLVoiceTests(VoiceChecks,unittest.IsolatedAsyncioTestCase): postgres=True
