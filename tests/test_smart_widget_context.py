"""Shared semantic goldens, fresh SQL bridge and actual opt-in Android map."""
import asyncio
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy import event, func, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderJob, SmartReminderPreference
from app.db.models.user import User
from app.services.smart_reminder_policy import HabitCalibration, PolicyContext, VerifiedStudy, day_window
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError
from app.services.smart_widget_context import WidgetContextRequest, project_widget, widget_cache_reason
from app.services.smart_widget_context_service import SmartWidgetContextService
from tests import test_android_course_api as legacy
from tests import test_smart_reminder_policy as fixtures


UTC = timezone.utc
EPOCH = "00000000-0000-4000-8000-000000000001"
REQUEST = WidgetContextRequest(version=1, epoch=EPOCH)
BINDING = "a" * 64
GOLDENS = json.loads((Path(__file__).parent / "fixtures/smart_widget_context_v1.json").read_text())


def fixture_context(changes=None):
    values = GOLDENS["base"] | (changes or {})
    values["observed_at"] = datetime.fromisoformat(values["observed_at"])
    for key in ("saved_time", "manual_time", "quiet_start", "quiet_end"):
        if values.get(key) is not None:
            values[key] = time.fromisoformat(values[key])
    if values.get("pause_until"):
        values["pause_until"] = datetime.fromisoformat(values["pause_until"])
    values["permitted_channels"] = tuple(values["permitted_channels"])
    values["studies"] = tuple(VerifiedStudy(**(s | dict(accepted_at=datetime.fromisoformat(s["accepted_at"]))))
                              for s in values.get("studies", []))
    return PolicyContext(**values)


def view(context=None, **kwargs):
    context = context or fixture_context()
    return project_widget(context, request=REQUEST, binding=BINDING,
                          valid_until=context.observed_at + timedelta(hours=1), **kwargs)


class WidgetGoldenTests(unittest.TestCase):
    def test_shared_semantic_goldens(self):
        self.assertEqual(len(GOLDENS["cases"]), 31)
        for case in GOLDENS["cases"]:
            with self.subTest(case=case["name"]):
                qa = HabitCalibration("shared-fixture-only", 3) if case["qa_habit_calibration"] else None
                data = view(fixture_context(case["changes"]), calibration=qa).model_dump(mode="json")
                for key, expected in case["expected"].items():
                    self.assertEqual(data[key], expected, key)
                self.assertFalse(data["dispatch_allowed"])
                self.assertTrue(data["action_requires_authorization"])
                self.assertFalse(set(data) & {"user_id", "device_id", "session_id", "token", "name", "studies"})

    def test_request_version_epoch_and_immutable_no_send_contract(self):
        for version, epoch in ((True, EPOCH), (2, EPOCH), ("1", EPOCH), (1, "bad-epoch")):
            with self.assertRaises(ValueError): WidgetContextRequest(version=version, epoch=epoch)
        value = view()
        with self.assertRaises(ValueError): value.dispatch_allowed = True

    def test_auth_expiry_personal_transition_and_actual_midnight_bound_validity(self):
        context = fixture_context(dict(observed_at="2026-10-29T13:59:00+00:00"))
        self.assertEqual(view(context).valid_until, context.observed_at.replace(hour=14, minute=0))
        for zone, day, hours in (("America/New_York", "2026-03-08", 23),
                                 ("America/New_York", "2026-11-01", 25),
                                 ("Australia/Lord_Howe", "2026-10-04", 23.5)):
            start, end = day_window(zone, day)
            self.assertEqual((end-start).total_seconds(), hours*3600)
            c = fixture_context(dict(observed_at=(end-timedelta(minutes=1)).isoformat(),
                                     course_day=day, timezone_name=zone))
            self.assertEqual(view(c).valid_until, end)
        with self.assertRaises(ValueError):
            project_widget(context, request=REQUEST, binding=BINDING, valid_until=context.observed_at)

    def test_current_cache_and_all_session_context_replay_fences(self):
        value = view(); payload = value.model_dump(mode="json")
        current = dict(now=value.generated_at, binding=BINDING, epoch=EPOCH, level=value.level,
                       local_day=value.local_day, timezone_name=value.timezone_name)
        self.assertEqual(widget_cache_reason(payload, **current), "widget_context_current")
        cases = (
            ({"binding":"b"*64}, "widget_session_changed"),
            ({"epoch":"00000000-0000-4000-8000-000000000002"}, "widget_session_changed"),
            ({"level":"nhsk1"}, "widget_context_changed"),
            ({"timezone_name":"UTC"}, "widget_context_changed"),
            ({"local_day":"2026-10-30"}, "widget_context_changed"),
            ({"minimum_revision":value.revision+1}, "widget_context_replayed"),
            ({"last_generated_at":value.generated_at+timedelta(seconds=1)}, "widget_context_replayed"),
            ({"now":value.generated_at-timedelta(seconds=1)}, "widget_context_future"),
            ({"now":value.valid_until}, "widget_context_expired"),
        )
        for changes, expected in cases:
            with self.subTest(changes=changes):
                self.assertEqual(widget_cache_reason(payload, **(current | changes)), expected)

    def test_malformed_unsafe_or_unknown_snapshots_are_rejected(self):
        value = view(); data = value.model_dump(mode="json")
        current = dict(now=value.generated_at, binding=BINDING, epoch=EPOCH, level=value.level,
                       local_day=value.local_day, timezone_name=value.timezone_name)
        for changes in ({"version":2}, {"version":True}, {"dispatch_allowed":True},
                        {"dispatch_allowed":0}, {"action_requires_authorization":1},
                        {"revision":True}, {"verified_today_xp":True}, {"user_id":1},
                        {"request_epoch":"bad"}, {"policy_version":"old"},
                        {"valid_until":data["generated_at"]}, {"track":"hsk30"},
                        {"lesson_order":99}, {"phase":"completed"},
                        {"goal_state":"met"}, {"timezone_name":"bad-zone"}):
            with self.subTest(changes=changes):
                self.assertEqual(widget_cache_reason(data | changes, **current), "widget_context_invalid")


class WidgetSourceChecks:
    postgres = False
    asyncTearDown = fixtures.PolicyContextChecks.asyncTearDown
    _progress = fixtures.PolicyContextChecks._progress
    _deletion = fixtures.PolicyContextChecks._deletion
    study = fixtures.PolicyContextChecks.study

    async def asyncSetUp(self):
        await fixtures.PolicyContextChecks.asyncSetUp(self)
        self.tick = self.moment
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id="widget-device", user_id=1, platform="android", app_version="qa",
                                installation_key_hash="widget-qa"))
            await s.flush()
            s.add(DesktopSession(id="widget-login", device_id="widget-device", refresh_token_hash="widget-qa",
                                 expires_at=self.now+timedelta(days=1)))
        self.actor = SmartReminderActor(1, "android", device_id="widget-device", session_id="widget-login")

    async def load(self, *, actor=None, session=None, until=None, expected_level="hsk1", clock=None):
        async def run(s):
            return await SmartWidgetContextService(s, clock=clock or (lambda:self.tick)).project(
                actor or self.actor, REQUEST, authenticated_until=until or self.tick+timedelta(hours=1),
                expected_level=expected_level)
        if session is not None: return await run(session)
        async with self.sessions.begin() as s: return await run(s)

    async def test_source_read_is_zero_write_and_contains_no_raw_owner_or_history(self):
        statements=[]
        def capture(c, cursor, sql, parameters, ctx, many): statements.append(sql)
        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try: result = await self.load()
        finally: event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        self.assertEqual((result["phase"], result["time_source"]), ("before_study", "saved"))
        self.assertFalse(any(s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for s in statements))
        raw=json.dumps(result)
        for secret in ("widget-device", "widget-login", '"user_id"', '"studies"', '"telegram_id"'):
            self.assertNotIn(secret, raw)
        async with self.sessions() as s:
            for model in (SmartReminderJob, SmartReminderAttempt):
                self.assertEqual(await s.scalar(select(func.count()).select_from(model)), 0)
            self.assertEqual(await s.scalar(select(SmartReminderPreference.revision).where(
                SmartReminderPreference.user_id==1)), 2)

    async def test_native_only_off_and_os_unknown_still_return_permitted_progress(self):
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(telegram_id=None))
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1).values(master_enabled=False))
        result=await self.load()
        self.assertEqual((result["phase"], result["reason"], result["completed_parts"]), ("neutral", "study_off", 0))
        self.assertFalse(result["dispatch_allowed"])

    async def test_server_receipt_completes_goal_but_reward_and_open_do_not(self):
        await self.study(kind="reward", xp=100)
        self.assertEqual((await self.load())["goal_state"], "not_proven")
        await self.study(order=1, xp=20)
        result=await self.load()
        self.assertEqual((result["goal_state"], result["phase"], result["verified_today_xp"]), ("met", "completed", 20))

    async def test_current_revocation_wins_over_stale_orm_and_other_device_proof(self):
        async with self.sessions.begin() as s:
            cached=await s.get(DesktopSession,"widget-login")
            await s.execute(update(DesktopSession).where(DesktopSession.id==cached.id).values(
                revoked_at=self.now).execution_options(synchronize_session=False))
            self.assertIsNone(cached.revoked_at)
            with self.assertRaises(SmartReminderError): await self.load(session=s)
        with self.assertRaises(SmartReminderError): await self.load(actor=replace(self.actor,user_id=2))

    async def test_blocked_and_submitted_deletion_accounts_refuse(self):
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="blocked"))
        with self.assertRaisesRegex(SmartReminderError,"smart_account_blocked"): await self.load()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="free"))
        await self._deletion()
        with self.assertRaisesRegex(SmartReminderError,"smart_account_deletion_pending"): await self.load()

    async def test_wrong_course_expired_auth_and_non_native_bridge_refuse(self):
        with self.assertRaisesRegex(SmartReminderError,"course_context_changed"):
            await self.load(expected_level="hsk2")
        with self.assertRaisesRegex(SmartReminderError,"widget_auth_expired"):
            await self.load(until=self.tick)
        with self.assertRaisesRegex(SmartReminderError,"android_device_required"):
            await self.load(actor=SmartReminderActor(1,"telegram",telegram_id=3001))
        ticks=iter((self.tick,self.tick+timedelta(hours=1)))
        with self.assertRaisesRegex(SmartReminderError,"widget_auth_expired"):
            await self.load(clock=lambda:next(ticks),until=self.tick+timedelta(hours=1))

    async def test_unflushed_changes_do_not_rewrite_saved_context(self):
        async with self.sessions.begin() as s:
            pref=await s.scalar(select(SmartReminderPreference).where(SmartReminderPreference.user_id==1))
            pref.manual_time_local=time(3)
            pref.time_mode="manual_locked"
            result=await self.load(session=s)
            self.assertEqual((result["time_source"],result["time_local"]),("saved","14:00"))
            await s.rollback()

    async def test_current_native_session_changes_opaque_binding_without_raw_ids(self):
        first=await self.load()
        async with self.sessions.begin() as s:
            s.add(DesktopSession(id="second-widget-login",device_id=self.actor.device_id,
                refresh_token_hash="second-widget-qa",expires_at=self.now+timedelta(days=1)))
        second=await self.load(actor=replace(self.actor,session_id="second-widget-login"))
        self.assertNotEqual(first["binding"],second["binding"])
        self.assertEqual(widget_cache_reason(first,now=self.tick,binding=second["binding"],epoch=EPOCH,
            level=second["level"],local_day=second["local_day"],timezone_name=second["timezone_name"]),
            "widget_session_changed")

    async def test_postgres_waiting_reader_observes_new_learning_after_user_lock(self):
        if not self.postgres: self.skipTest("PostgreSQL User row-lock race")
        entered=asyncio.Event()
        async with self.sessions.begin() as holder:
            await holder.execute(select(User.id).where(User.id==1).with_for_update())
            def capture(c,cursor,sql,parameters,ctx,many):
                if "FOR UPDATE" in sql: entered.set()
            event.listen(self.engine.sync_engine,"before_cursor_execute",capture)
            task=asyncio.create_task(self.load())
            try:
                await asyncio.wait_for(entered.wait(),5)
                await asyncio.sleep(0.03)
                self.assertFalse(task.done())
                self.tick+=timedelta(minutes=1)
                await holder.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(completed_lessons_count=1))
                holder.add(CourseXpEvent(user_id=1,activity_type="lesson",activity_ref="v3-part:hsk1:1:complete",xp=20,
                    activity_date=self.tick.date(),week_start=self.tick.date(),created_at=self.tick))
                holder.add(CourseMiniAppEvent(user_id=1,level="hsk1",event_name="lesson_completed",lesson_order=1,
                    source="android_course",created_at=self.tick))
                await holder.commit()
                result=await asyncio.wait_for(task,10)
                self.assertEqual((result["phase"],result["verified_today_xp"]),("completed",20))
            finally:
                event.remove(self.engine.sync_engine,"before_cursor_execute",capture)
                if not task.done():
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError): await task


class SQLiteWidgetSourceTests(WidgetSourceChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.fixtures.PG_URL, "Disposable loopback PostgreSQL not configured")
class PostgreSQLWidgetSourceTests(WidgetSourceChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class WidgetMapTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = legacy.AndroidCourseApiTests.asyncSetUp
    asyncTearDown = legacy.AndroidCourseApiTests.asyncTearDown
    _bearer = legacy.AndroidCourseApiTests._bearer

    async def test_legacy_map_has_no_projection_or_new_smart_queries(self):
        headers=await self._bearer(); statements=[]
        def capture(c,cursor,sql,parameters,ctx,many): statements.append(sql)
        event.listen(self.engine.sync_engine,"before_cursor_execute",capture)
        try: response=await self.client.get("/api/v3/android/course/map",headers=headers)
        finally: event.remove(self.engine.sync_engine,"before_cursor_execute",capture)
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotIn("widget_context",response.json())
        self.assertFalse(any("smart_reminder_" in sql for sql in statements))

    async def test_actual_authenticated_map_opt_in_is_additive_and_passive(self):
        headers=await self._bearer()
        async with self.sessions.begin() as s:
            s.add(SmartReminderPreference(user_id=1,master_enabled=False,timezone_name="Etc/UTC",legacy_time_local=time(2)))
        response=await self.client.get("/api/v3/android/course/map",headers=headers,
            params=dict(tz=0,widget_context_version="1",widget_context_epoch=EPOCH))
        self.assertEqual(response.status_code,200,response.text)
        data=response.json(); context=data["widget_context"]
        self.assertEqual(context["request_epoch"],EPOCH)
        self.assertEqual((context["phase"],context["reason"]),("neutral","study_off"))
        self.assertIn("progress",data); self.assertIn("units",data)
        self.assertEqual(response.headers["cache-control"],"no-store")
        async with self.sessions() as s:
            auth=await legacy.DesktopAuthService(s,legacy._settings()).authenticate(headers["Authorization"][7:])
            self.assertLessEqual(datetime.fromisoformat(context["valid_until"]),datetime.fromtimestamp(auth.claims["exp"],UTC))
            for model in (SmartReminderJob,SmartReminderAttempt):
                self.assertEqual(await s.scalar(select(func.count()).select_from(model)),0)

    async def test_opt_in_rejects_malformed_duplicate_and_owner_selected_queries(self):
        headers=await self._bearer()
        normal=[("widget_context_version","1"),("widget_context_epoch",EPOCH)]
        bad=[normal[:1],normal[1:],[normal[0],("widget_context_epoch","bad")],
             [("widget_context_version","2"),normal[1]],normal+[normal[0]],normal+[normal[1]],
             normal+[("user_id","2")],normal+[("tz","0"),("tz","1")]]
        for params in bad:
            with self.subTest(params=params):
                response=await self.client.get("/api/v3/android/course/map",headers=headers,params=params)
                self.assertEqual(response.status_code,422,response.text)

    async def test_opt_in_requires_real_native_auth_and_current_account(self):
        params=dict(widget_context_version="1",widget_context_epoch=EPOCH)
        response=await self.client.get("/api/v3/android/course/map",params=params,headers={"Cookie":"session=unused"})
        self.assertEqual(response.status_code,401)
        async with self.sessions() as s:
            token=await legacy.AndroidCourseServiceTests._token(self,s,platform="macos")
        response=await self.client.get("/api/v3/android/course/map",params=params,headers={"Authorization":"Bearer "+token})
        self.assertEqual(response.status_code,403,response.text)
        headers=await self._bearer()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="blocked"))
        response=await self.client.get("/api/v3/android/course/map",params=params,headers=headers)
        self.assertEqual(response.status_code,403,response.text)

    async def test_opt_in_foundation_cannot_return_a_locked_lesson_action(self):
        headers=await self._bearer()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(level="beginner"))
            s.add(SmartReminderPreference(user_id=1,timezone_name="Etc/UTC",legacy_time_local=time(2)))
        response=await self.client.get("/api/v3/android/course/map",params=dict(
            widget_context_version="1",widget_context_epoch=EPOCH),headers=headers)
        self.assertEqual(response.status_code,200,response.text)
        context=response.json()["widget_context"]
        self.assertEqual((context["action"],context["reason"],context["lesson_order"]),
                         ("foundation","foundation_required",None))
