"""Optional fresh practice proof keeps canonical rewards and APIs intact."""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from app.api.miniapp_practice import create_miniapp_practice_router
from app.api.android_features import create_android_features_router
from app.api.desktop_practice import create_desktop_practice_router
from app.db.models.course_miniapp_event import (
    CourseMiniAppEvent, SMART_PRACTICE_SOURCE, SMART_PRACTICE_STARTED, SMART_PRACTICE_SCORED,
)
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_answer_accuracy_service import CourseAnswerAccuracyService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.smart_reminder_analysis import EVENT, MONTHLY, RAW_RETENTION
from app.services.smart_reminder_baseline import windows
from app.services.smart_reminder_policy_context import read_scored_activity
from tests import test_smart_reminder_activity_analysis as fixture
from tests.test_course_miniapp_practice import question
from tests import test_smart_reminder_practice_activity as legacy


class RepeatChecks:
    postgres=False
    asyncSetUp=fixture.ActivityChecks.asyncSetUp
    asyncTearDown=fixture.ActivityChecks.asyncTearDown
    read=fixture.ActivityChecks.read
    capture=fixture.ActivityChecks.capture
    facts=fixture.ActivityChecks.facts
    session_id=staticmethod(legacy.PracticeChecks.session_id)
    original_reward=legacy.PracticeChecks.original_reward
    completion=legacy.PracticeChecks.completion

    @contextmanager
    def tracing(self, enabled=True):
        owner=self
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):
                at=getattr(owner,"trace_at",owner.at)
                return at.astimezone(tz) if tz else at.replace(tzinfo=None)
        with patch("app.services.course_miniapp_practice_service.settings",SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=enabled)), \
                patch("app.services.course_miniapp_practice_service.datetime",Clock), \
                patch("app.db.models.course_miniapp_event.datetime",Clock):
            yield

    def service(self, session, bot=None):
        service=CourseMiniAppPracticeService(session,bot)
        service._questions=AsyncMock(return_value=[question("q1")])
        service.mistakes=SimpleNamespace(record_items=AsyncMock(return_value=0))
        return service

    async def start(self, *, uid=1, mode="mock", skill="", enabled=True):
        self.trace_at=self.at-timedelta(seconds=10)
        with self.tracing(enabled):
            async with self.case.sessions() as s:
                result=await self.service(s).start(await s.get(User,uid),mode=mode,level="hsk1",lang="uz",skill=skill)
        self.assertTrue(result["ok"],result)
        return result["session"]["id"]

    async def finish(self, sid, *, uid=1, mode="mock", skill="", enabled=True, selected=1):
        self.trace_at=self.at
        with self.tracing(enabled):
            async with self.case.sessions() as s:
                return await self.service(s).complete(await s.get(User,uid),session_id=sid,
                    mode=mode,level="hsk1",lang="uz",skill=skill,
                    answers=[{"question_id":"q1","selected_index":selected}])

    async def traces(self, name=None):
        async with self.case.sessions() as s:
            query=select(CourseMiniAppEvent.__table__).where(CourseMiniAppEvent.source==SMART_PRACTICE_SOURCE)
            if name: query=query.where(CourseMiniAppEvent.event_name==name)
            return (await s.execute(query.order_by(CourseMiniAppEvent.id))).mappings().all()

    async def activity(self, *, uid=1, level="hsk1"):
        async with self.case.sessions() as s:
            return await read_scored_activity(s,uid,level=level,
                history_since=self.at-timedelta(hours=1),observed_at=self.at+timedelta(hours=1))

    async def seed_original(self, *, uid=1, mode="mock", skill=""):
        await self.original_reward(mode,uid=uid)
        await self.completion(uid=uid,mode=mode,skill=skill,at=self.at-timedelta(days=2))

    async def test_actual_distinct_repeats_all_modes_keep_original_reward_and_no_tap_activity(self):
        await self.episode.contact(report=False)
        for mode,skill in (("mock",""),("placement",""),("training","pinyin")):
            await self.seed_original(mode=mode,skill=skill)
            xp=await self.storage.rows(CourseXpEvent.__table__)
            first=await self.start(mode=mode,skill=skill)
            second=await self.start(mode=mode,skill=skill)
            self.assertNotEqual(first,second)
            self.assertLessEqual(len(first),80)
            for sid in (first,second):
                result=await self.finish(sid,mode=mode,skill=skill)
                self.assertTrue(result["ok"],result)
                self.assertTrue(result["reward"]["duplicate"])
                self.assertEqual(result["reward"]["awarded_xp"],0)
                self.assertEqual((result["score"],result["total"]),(0,1))
            self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),xp)
        self.assertEqual(len(await self.traces(SMART_PRACTICE_SCORED)),6)
        self.assertEqual((await self.read()).first_active_study_at,self.at)
        self.assertIsNone((await self.read()).verified_study_count)
        self.assertEqual(await self.capture(),2);self.assertEqual(await self.capture(),0)
        returned=await self.analysis.return_learning(1,self.case.job_id)
        self.assertEqual(returned.first_study_at,self.at)

    async def test_retained_retry_preserves_first_result_and_time_even_with_other_answers(self):
        sid=await self.start();self.assertTrue((await self.finish(sid))["ok"])
        before=await self.traces(SMART_PRACTICE_SCORED)
        self.at+=timedelta(minutes=1)
        self.assertTrue((await self.finish(sid,selected=0))["ok"])
        self.assertEqual(await self.traces(SMART_PRACTICE_SCORED),before)
        self.assertEqual(json.loads(before[0]["payload_json"])["score"],0)

    async def test_concurrent_completion_records_one_nonce_and_one_original_reward(self):
        if not self.postgres: self.skipTest("PostgreSQL independent completion transactions")
        sid=await self.start()
        self.assertTrue(all(r["ok"] for r in await asyncio.gather(self.finish(sid),self.finish(sid))))
        self.assertEqual(len(await self.traces(SMART_PRACTICE_SCORED)),1)
        self.assertEqual(len([r for r in await self.storage.rows(CourseXpEvent.__table__)
            if r["activity_ref"]==self.session_id(1,"mock")+":completed"]),1)

    async def test_start_only_and_client_forged_trace_names_are_not_study(self):
        await self.start()
        self.assertEqual((await self.activity()).times,())
        async with self.case.sessions() as s:
            for name in (SMART_PRACTICE_STARTED,SMART_PRACTICE_SCORED):
                result=await CourseMiniAppAnalyticsService(s).record_client_event(event_name=name,user_id=1)
                self.assertEqual(result["error"],"course_client_event_not_allowed")

    async def test_foreign_guessed_or_scope_mismatched_attempt_is_rejected(self):
        sid=await self.start()
        for bad,changes in ((sid,{"uid":2}), (f"practice:1:v2:{uuid4().hex}",{}),
                (sid,{"mode":"placement"}),(sid,{"mode":"training","skill":"pinyin"}),
                (sid.replace(":v2:",":v3:"),{})):
            result=await self.finish(bad,**changes)
            self.assertEqual(result.get("error"),"invalid_practice_session",result)
        self.assertEqual(await self.traces(SMART_PRACTICE_SCORED),[])

    async def test_native_only_repeat_is_owned_by_canonical_account(self):
        await self.seed_original(uid=2)
        sid=await self.start(uid=2)
        result=await self.finish(sid,uid=2)
        self.assertTrue(result["ok"],result);self.assertEqual(result["reward"]["awarded_xp"],0)
        self.assertEqual((await self.activity(uid=2)).times,(self.at,))
        self.assertEqual((await self.activity(uid=1)).times,())

    async def test_disabled_new_starts_preserve_v1_and_outstanding_v2_can_finish_after_off(self):
        v1=await self.start(enabled=False)
        self.assertEqual(v1,self.session_id(1,"mock"));self.assertEqual(await self.traces(),[])
        v2=await self.start()
        result=await self.finish(v2,enabled=False)
        self.assertTrue(result["ok"],result)
        self.assertEqual(await self.traces(SMART_PRACTICE_SCORED),[])

    async def test_optional_trace_write_failure_never_discards_learning(self):
        original=CourseMiniAppAnalyticsService._record
        failing=SMART_PRACTICE_STARTED
        async def record(service,**kwargs):
            if kwargs.get("event_name")==failing: raise RuntimeError("synthetic capture failure")
            return await original(service,**kwargs)
        with patch.object(CourseMiniAppAnalyticsService,"_record",record):
            fallback=await self.start()
            self.assertEqual(fallback,self.session_id(1,"mock"))
            sid=await self.start(enabled=False)
            self.assertTrue((await self.finish(sid))["ok"])
        sid=await self.start();failing=SMART_PRACTICE_SCORED
        with patch.object(CourseMiniAppAnalyticsService,"_record",record):
            result=await self.finish(sid)
        self.assertTrue(result["ok"],result)
        self.assertEqual(await self.traces(SMART_PRACTICE_SCORED),[])

    async def test_changed_bank_or_expired_future_untrusted_receipt_cannot_grade(self):
        sid=await self.start()
        rows=await self.traces(SMART_PRACTICE_STARTED);row=rows[0]
        payload=json.loads(row["payload_json"])
        changes=({"created_at":self.at-RAW_RETENTION},{"created_at":self.at+timedelta(seconds=1)},
            {"source":"client"},{"payload_json":"{}"},
            {"payload_json":json.dumps(payload|{"question_sha256":"0"*64})},
            {"payload_json":json.dumps(payload|{"max_part":True})})
        for change in changes:
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row["id"]).values(**(dict(row)|change)))
            self.assertEqual((await self.finish(sid)).get("error"),"invalid_practice_session",change)
        self.assertEqual(await self.traces(SMART_PRACTICE_SCORED),[])

    async def test_progress_and_language_change_use_original_window_and_digest(self):
        sid=await self.start()
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(completed_lessons_count=40))
        self.trace_at=self.at
        with self.tracing():
            async with self.case.sessions() as s:
                service=self.service(s)
                result=await service.complete(await s.get(User,1),session_id=sid,mode="mock",level="hsk1",lang="ru",skill="",
                    answers=[{"question_id":"q1","selected_index":1}])
                self.assertTrue(result["ok"],result)
                self.assertEqual(service._questions.await_args.args[2],"uz")
                self.assertEqual(service._questions.await_args.kwargs["max_part"],5)

    async def test_profile_accuracy_and_new_payloads_do_not_duplicate_canonical_learning(self):
        for _ in range(2): self.assertTrue((await self.finish(await self.start()))["ok"])
        async with self.case.sessions() as s:
            result=await CourseAnswerAccuracyService(s).summarize(user_id=1)
        self.assertEqual(result["overall"]["total"],1)
        for row in await self.traces():
            payload=json.loads(row["payload_json"])
            for private in ("questions","answers","wrong","job_id","token","telegram_id","user_id"):
                self.assertNotIn(private,payload)

    async def test_retention_deletes_only_expired_technical_rows_in_bounded_pages(self):
        sid=await self.start()
        await self.finish(sid)
        original_xp=await self.storage.rows(CourseXpEvent.__table__)
        async with self.case.sessions.begin() as s:
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.source==SMART_PRACTICE_SOURCE)
                .values(created_at=self.storage.moment-RAW_RETENTION))
        self.assertEqual((await self.analysis.retention())["expired_practice_traces"],2)
        self.assertEqual(len(await self.traces()),2)
        for expected in (1,0):
            self.assertEqual((await self.analysis.retention(execute=True,limit=1))["removed_practice_traces"],1)
            self.assertEqual(len(await self.traces()),expected)
        self.assertEqual(await self.storage.rows(CourseXpEvent.__table__),original_xp)
        self.assertEqual((await self.finish(sid)).get("error"),"invalid_practice_session")
        async with self.case.sessions() as s:
            self.assertEqual(len((await s.execute(select(CourseMiniAppEvent.id).where(CourseMiniAppEvent.event_name=="test_completed"))).all()),1)

    async def test_account_purge_removes_traces_but_preserves_anonymous_facts(self):
        await self.episode.contact(report=False)
        await self.finish(await self.start());await self.capture()
        before=await self.storage.rows(MONTHLY)
        async with self.case.sessions.begin() as s: await UserRepository(s)._delete_account(await s.get(User,1))
        self.assertEqual(await self.traces(),[])
        self.assertEqual(await self.storage.rows(MONTHLY),before)

    async def test_signed_miniapp_roundtrip_passes_opaque_id_to_real_grader(self):
        app=FastAPI()
        app.include_router(create_miniapp_practice_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings,service_factory=self.service))
        async with AsyncClient(transport=ASGITransport(app=app),base_url="https://practice.test") as client:
            body=dict(mode="mock",level="hsk1",language="uz",skill="")
            headers=self.case.telegram(uid=3001)
            with self.tracing():
                response=await client.post("/api/v3/practice/start",headers=headers,json=body)
                self.assertEqual(response.status_code,200,response.text)
                sid=response.json()["session"]["id"]
                response=await client.post("/api/v3/practice/complete",headers=headers,json=body|{
                    "session_id":sid,"answers":[{"question_id":"q1","selected":1}]})
            self.assertEqual(response.status_code,200,response.text)
            self.assertTrue(response.json()["ok"],response.text)
        self.assertEqual(len(await self.traces(SMART_PRACTICE_SCORED)),1)

    async def test_android_and_paired_desktop_apis_roundtrip_the_same_opaque_protocol(self):
        app=FastAPI()
        app.include_router(create_android_features_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings,practice_service_factory=self.service))
        app.include_router(create_desktop_practice_router(session_factory=self.case.sessions,
            settings_obj=self.case.settings,service_factory=self.service))
        async with AsyncClient(transport=ASGITransport(app=app),base_url="https://native-practice.test") as client:
            body=dict(mode="mock",level="hsk1",language="uz",skill="")
            for platform,adapter in (("android","android"),("macos","desktop"),("windows","desktop")):
                async with self.case.sessions.begin() as s:
                    await s.execute(update(DesktopDevice).where(DesktopDevice.id=="device-1").values(platform=platform))
                headers=await self.case.bearer(1)
                with self.tracing():
                    response=await client.post(f"/api/v3/{adapter}/practice/start",headers=headers,json=body)
                    self.assertEqual(response.status_code,200,response.text)
                    sid=response.json()["session"]["id"]
                    self.assertIn(":v2:",sid)
                    response=await client.post(f"/api/v3/{adapter}/practice/complete",headers=headers,json=body|{
                        "session_id":sid,"answers":[{"question_id":"q1","selected":1}]})
                self.assertEqual(response.status_code,200,response.text)
                self.assertTrue(response.json()["ok"],response.text)
        self.assertEqual(len(await self.traces(SMART_PRACTICE_SCORED)),3)

    async def test_current_access_refusal_cannot_create_start_or_scored_trace(self):
        self.trace_at=self.at
        with self.tracing():
            async with self.case.sessions() as s:
                service=self.service(s)
                service._gate=AsyncMock(return_value={"allowed":False,"error":"ad_authorization_required"})
                result=await service.start(await s.get(User,1),mode="mock",level="hsk1",lang="uz")
                self.assertFalse(result["ok"])
        self.assertEqual(await self.traces(),[])
        sid=await self.start()
        with self.tracing():
            async with self.case.sessions() as s:
                service=self.service(s)
                service._gate=AsyncMock(return_value={"allowed":False,"error":"ad_authorization_required"})
                result=await service.complete(await s.get(User,1),session_id=sid,mode="mock",level="hsk1",lang="uz",skill="",
                    answers=[{"question_id":"q1","selected_index":1}])
                self.assertEqual(result.get("error"),"ad_authorization_required")
        self.assertEqual(await self.traces(SMART_PRACTICE_SCORED),[])

    async def test_scored_source_requires_strict_original_owner_scope_protocol_and_scores(self):
        await self.seed_original()
        await self.finish(await self.start())
        row=(await self.traces(SMART_PRACTICE_SCORED))[0]
        payload=json.loads(row["payload_json"])
        self.assertEqual((await self.activity()).times,(self.at,))
        for change in ({"source":"course_miniapp"},{"user_id":2},{"level":"hsk2"},
                {"dedupe_key":"forged"},{"session_id":row["session_id"].replace("practice:1:","practice:2:")},
                *({"payload_json":json.dumps(payload|bad)} for bad in (
                    {"score":True},{"total":0},{"attempt_protocol":3},{"mode":["mock"]},
                    {"skill":"pinyin"},{"started_at":None},
                    {"started_at":(self.at+timedelta(seconds=1)).isoformat()},
                    {"started_at":self.at.replace(tzinfo=None).isoformat()}))):
            async with self.case.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.id==row["id"]).values(**(dict(row)|change)))
            self.assertEqual((await self.activity()).times,(),change)

    async def test_baseline_d7_uses_repeat_trace_independently_of_old_xp_and_legacy_completion(self):
        from tests import test_smart_reminder_baseline as baseline
        checks=baseline.PostgreSQLBaselineTests if self.postgres else baseline.SQLiteBaselineTests
        case=checks(methodName="test_scored_failed_repeat_without_xp_proves_d7_once")
        await case.asyncSetUp()
        original_case,original_at=self.case,self.at
        try:
            await case.enroll()
            d7,_=windows(case.now,"Etc/UTC")
            old=case.now-timedelta(days=2)
            async with case.q.sessions.begin() as s:
                s.add(CourseXpEvent(user_id=1,activity_type="test",activity_ref=self.session_id(1,"mock")+":completed",
                    xp=10,activity_date=old.date(),week_start=old.date(),created_at=old))
            self.case,self.at=case.q,d7+timedelta(minutes=1)
            result=await self.finish(await self.start())
            self.assertTrue(result["ok"],result)
            self.assertEqual(result["reward"]["awarded_xp"],0)
            async with case.q.sessions.begin() as s:
                await s.execute(delete(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name=="test_completed"))
            report=await case.report()
            self.assertEqual(report["observed_d7_accounts_lower_bound"],1)
            self.assertEqual(report["observed_units_lower_bound"],0)
        finally:
            self.case,self.at=original_case,original_at
            await case.asyncTearDown()


class SQLiteRepeatTests(RepeatChecks,unittest.IsolatedAsyncioTestCase): pass
class PostgreSQLRepeatTests(RepeatChecks,unittest.IsolatedAsyncioTestCase): postgres=True
