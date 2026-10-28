"""Pure/source coordination and actual independent shadow worker boundaries."""
import ast
import asyncio
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import event, func, insert, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent, CLIENT_COURSE_MINIAPP_EVENT_NAMES
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.desktop import DesktopSession
from app.db.models.user import User
from app.services.course_reminder_service import CourseReminderService
from app.services.motivation_reminder_service import D1_RECOVERY_ASSIGNED_EVENT, D1_RECOVERY_EXPERIMENT, D1_RECOVERY_HOLDOUT
from app.services.smart_reminder_coordination import (
    CategoryCandidate, Contact, CoordinationCalibration, CoordinationReader, D1Scope, coordinate, read_d1_scope,
)
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError
from app.services.smart_reminder_shadow_worker import SmartReminderShadowWorker
from tests import test_smart_reminder_shadow_queue as fixtures


UTC=timezone.utc
NOW=datetime(2026,10,29,2,tzinfo=UTC)
QA=CoordinationCalibration("qa-only-no-owner-approval",timedelta(minutes=5),("study","weekly","rank"))


def candidate(category, *, due=NOW, reference=None, **changes):
    values=dict(reference=reference or category+":fixture",category=category,due_at=due,
                expires_at=due+timedelta(hours=2),eligible=True,useful=True)
    return CategoryCandidate(**(values|changes))


class CoordinationTests(unittest.TestCase):
    def test_collision_retains_weekly_identity_and_suppresses_less_useful_rank(self):
        weekly=candidate("weekly")
        result=coordinate((candidate("rank"),weekly,candidate("study")),now=NOW,calibration=QA)
        self.assertEqual([d.disposition for d in result],["candidate","defer","suppress"])
        self.assertEqual(result[1].candidate,weekly)
        self.assertEqual(result[1].proposed_at,NOW+timedelta(minutes=5))
        self.assertEqual(result[2].reason,"rank_collision")
        self.assertTrue(all(not d.dispatch_allowed and d.requires_recheck for d in result))
        self.assertTrue(all(d.calibration_version==QA.version for d in result))

    def test_weekly_with_no_later_window_is_retained_without_a_false_post_time(self):
        weekly=candidate("weekly",expires_at=NOW+timedelta(minutes=1))
        result=coordinate((candidate("study"),weekly),now=NOW,calibration=QA)
        self.assertEqual((result[1].disposition,result[1].reason),("defer","no_later_valid_window"))
        self.assertEqual(result[1].candidate,weekly)
        self.assertIsNone(result[1].proposed_at)

    def test_unconfigured_spacing_and_priority_never_become_a_production_default(self):
        result=coordinate((candidate("study"),candidate("weekly")),now=NOW)
        self.assertTrue(all(d.reason=="coordination_unconfigured" for d in result))
        self.assertTrue(all(d.disposition=="defer" for d in result))

    def test_d1_both_arms_protect_study_and_rank_across_channels(self):
        for arm in ("control","treatment"):
            scope=D1Scope(NOW+timedelta(hours=1),frozenset({arm}))
            result=coordinate((candidate("study"),candidate("rank"),candidate("weekly")),now=NOW,d1=scope,calibration=QA)
            by_category={d.candidate.category:d for d in result}
            self.assertEqual(by_category["study"].reason,"d1_holdout_active")
            self.assertEqual(by_category["rank"].reason,"d1_holdout_active")
            self.assertEqual(by_category["weekly"].disposition,"candidate")

    def test_unknown_assignment_refuses_and_expired_window_does_not_reassign(self):
        self.assertEqual(coordinate((candidate("study"),),now=NOW,d1=D1Scope(unknown=True),calibration=QA)[0].reason,"d1_assignment_unknown")
        self.assertEqual(coordinate((candidate("study"),),now=NOW,d1=D1Scope(NOW),calibration=QA)[0].disposition,"candidate")

    def test_transactional_keeps_original_route_and_eligibility_even_in_holdout(self):
        payment=candidate("transactional",eligible=False)
        result=coordinate((payment,candidate("study")),now=NOW,d1=D1Scope(unknown=True))
        external=next(d for d in result if d.candidate.category=="transactional")
        self.assertEqual(external.candidate,payment)
        self.assertEqual((external.disposition,external.reason),("external","transactional_routing_unchanged"))
        self.assertFalse(external.dispatch_allowed)

    def test_duplicates_are_account_identity_not_device_multipliers(self):
        item=candidate("study")
        self.assertEqual(len(coordinate((item,item),now=NOW,calibration=QA)),1)
        with self.assertRaises(ValueError): coordinate((item,replace(item,due_at=NOW+timedelta(minutes=1))),now=NOW)
        result=coordinate((item,),now=NOW,contacts=(Contact(item.reference,"study",NOW,"feed_record"),),calibration=QA)
        self.assertEqual(result[0].reason,"category_already_recorded")

    def test_contacts_are_not_relabelled_shown_and_do_not_include_transactional_budget(self):
        contact=Contact("possible","rank",NOW,"feed_record")
        result=coordinate((candidate("study"),),now=NOW,contacts=(contact,),calibration=QA)
        self.assertEqual(result[0].disposition,"defer")
        ignored=replace(contact,category="transactional")
        self.assertEqual(coordinate((candidate("study"),),now=NOW,contacts=(ignored,),calibration=QA)[0].disposition,"candidate")
        self.assertEqual(contact.evidence,"feed_record")

    def test_no_global_night_blackout_and_partial_history_is_explicit(self):
        self.assertEqual(coordinate((candidate("study"),),now=NOW,calibration=QA)[0].proposed_at.hour,2)
        result=coordinate((candidate("weekly"),),now=NOW,calibration=QA,coverage_limits=("contact_window_over_limit",))
        self.assertEqual((result[0].disposition,result[0].reason),("defer","coordination_history_incomplete"))

    def test_no_progress_or_expired_weekly_window_is_not_fake_success(self):
        self.assertEqual(coordinate((candidate("weekly",useful=False),),now=NOW,calibration=QA)[0].reason,"weekly_no_new_progress")
        self.assertEqual(coordinate((candidate("weekly",useful=None),),now=NOW,calibration=QA)[0].reason,"weekly_progress_unknown")
        expired=candidate("weekly",due=NOW-timedelta(days=1))
        result=coordinate((expired,),now=NOW,calibration=QA)[0]
        self.assertEqual((result.disposition,result.reason),("defer","category_window_expired"))


class SourceChecks:
    postgres=False
    asyncSetUp=fixtures.QueueChecks.asyncSetUp
    asyncTearDown=fixtures.QueueChecks.asyncTearDown
    _progress=fixtures.QueueChecks._progress
    _deletion=fixtures.QueueChecks._deletion
    reserve=fixtures.QueueChecks.reserve
    claim=fixtures.QueueChecks.claim
    finish=fixtures.QueueChecks.finish
    row=fixtures.QueueChecks.row
    counts=fixtures.QueueChecks.counts
    native_actor=fixtures.QueueChecks.native_actor

    async def assign(self, *, uid=1, tid=None, arm="control", age=timedelta(hours=1), source=D1_RECOVERY_EXPERIMENT):
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=uid,telegram_id=tid,event_name=D1_RECOVERY_ASSIGNED_EVENT,
                source=source,payload_json=json.dumps({"arm":arm}),created_at=self.tick-age))

    async def scope(self, actor=None):
        actor=actor or self.actor
        async with self.sessions.begin() as s:
            from app.services.smart_reminder_preferences import SmartReminderPreferencesService
            await SmartReminderPreferencesService(s).read(actor)
            return await read_d1_scope(s,actor.user_id,self.tick)

    async def test_d1_is_server_only_and_canonical_control_vetoes_new_shadow_reservation(self):
        self.assertNotIn(D1_RECOVERY_ASSIGNED_EVENT,CLIENT_COURSE_MINIAPP_EVENT_NAMES)
        await self.assign()
        self.assertEqual((await self.reserve()).reason,"d1_holdout_active")
        self.assertEqual(await self.counts(),(0,0))
        scope=await self.scope()
        self.assertEqual(scope.arms,frozenset({"control"}))

    async def test_d1_assignment_after_claim_is_rechecked_before_completion(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        await self.assign(arm="treatment",age=timedelta(0))
        self.assertEqual((await self.finish(lease)).reason,"d1_holdout_active")
        self.assertEqual((await self.row(reserved.job_id))["state"],"cancelled")

    async def test_unowned_real_telegram_history_is_honored_but_foreign_owner_is_not(self):
        await self.assign(uid=2,tid=3001)
        self.assertIsNone((await self.scope()).reason(self.tick))
        await self.assign(uid=None,tid=3001)
        self.assertEqual((await self.scope()).reason(self.tick),"d1_holdout_active")

    async def test_native_owner_never_joins_all_null_telegram_assignments(self):
        actor=await self.native_actor()
        await self.assign(uid=3,tid=None)
        self.assertIsNone((await self.scope(actor)).reason(self.tick))
        await self.assign(uid=2,tid=None)
        self.assertEqual((await self.reserve(actor=actor)).reason,"d1_holdout_active")

    async def test_d1_end_boundary_future_unknown_and_overflow_fail_closed(self):
        await self.assign(age=D1_RECOVERY_HOLDOUT)
        self.assertIsNone((await self.scope()).reason(self.tick))
        await self.assign(age=-timedelta(hours=1))
        self.assertEqual((await self.scope()).reason(self.tick),"d1_assignment_unknown")
        with patch("app.services.smart_reminder_coordination.MAX_ASSIGNMENTS",1):
            self.assertTrue((await self.scope()).unknown)

    async def test_wrong_source_does_not_reassign_or_create_experiment(self):
        await self.assign(source="client_untrusted_other_experiment")
        self.assertIsNone((await self.scope()).reason(self.tick))
        async with self.sessions() as s:
            self.assertEqual(await s.scalar(select(func.count()).select_from(CourseMiniAppEvent)),1)

    async def test_reader_projects_no_body_and_makes_zero_writes_or_send_cursors(self):
        async with self.sessions.begin() as s:
            s.add(CourseUserNotification(user_id=1,key="lesson_time",source="course_reminder",language="uz",
                title="synthetic private",body="must not be projected",dedupe_key="study-qa",created_at=self.tick))
        sql=[]
        def capture(c,cursor,statement,parameters,ctx,many): sql.append(statement)
        event.listen(self.engine.sync_engine,"before_cursor_execute",capture)
        try:
            async with self.sessions.begin() as s:
                decisions,contacts,limits=await CoordinationReader(s).compare(self.actor,(candidate("study",due=self.tick),),
                    now=self.tick,history_since=self.since,calibration=QA)
        finally:
            event.remove(self.engine.sync_engine,"before_cursor_execute",capture)
        self.assertEqual(contacts[0].evidence,"feed_record")
        self.assertIn("legacy_contacts_incomplete",limits)
        self.assertFalse(decisions[0].dispatch_allowed)
        self.assertIn("legacy_contacts_incomplete",decisions[0].coverage_limits)
        self.assertFalse(any(x.lstrip().upper().startswith(("INSERT","UPDATE","DELETE")) for x in sql))
        self.assertFalse(any("course_user_notifications.body" in x or "course_user_notifications.title" in x for x in sql))

    async def test_source_consent_scopes_do_not_turn_study_off_into_motivation_off(self):
        from app.db.models.smart_reminder import SmartReminderPreference
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1).values(master_enabled=False))
        async with self.sessions.begin() as s:
            result,_,_=await CoordinationReader(s).compare(self.actor,tuple(candidate(c,due=self.tick) for c in ("study","rank")),
                now=self.tick,history_since=self.since,calibration=QA)
        by_category={d.candidate.category:d for d in result}
        self.assertEqual(by_category["study"].reason,"category_source_ineligible")
        self.assertEqual(by_category["rank"].disposition,"candidate")

    async def test_weekly_progress_mismatch_is_unknown_and_not_silently_discarded(self):
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="active"))
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(
                completed_lessons_count=0,weekly_progress_baseline_lessons_count=3))
        async with self.sessions.begin() as s:
            result,_,_=await CoordinationReader(s).compare(self.actor,(candidate("weekly",due=self.tick),),
                now=self.tick,history_since=self.since,calibration=QA)
        self.assertEqual((result[0].disposition,result[0].reason),("defer","weekly_progress_unknown"))

    async def test_legacy_study_and_weekly_collide_while_shadow_defers_weekly(self):
        self.tick=datetime(2026,10,26,9,tzinfo=UTC)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="active",end_date=self.now+timedelta(days=1)))
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(reminder_time=time(9),
                completed_lessons_count=3,weekly_progress_baseline_lessons_count=1))
        proposals=tuple(candidate(c,due=self.tick) for c in ("study","weekly","rank"))
        async with self.sessions.begin() as s:
            decisions,_,_=await CoordinationReader(s).compare(self.actor,proposals,now=self.tick,
                history_since=self.tick-timedelta(days=7),calibration=QA)
        self.assertEqual([d.disposition for d in decisions],["candidate","defer","suppress"])
        async with self.sessions() as s:
            bot=AsyncMock()
            service=CourseReminderService(s)
            with patch("app.services.course_reminder_service.datetime",wraps=datetime) as clock:
                clock.now.return_value=self.tick
                with patch.object(CourseReminderService,"_build_reminder_text",AsyncMock(return_value=("Synthetic continue",{}))), patch(
                        "app.services.course_reminder_service.CourseProgressSummaryService") as summary:
                    summary.return_value.summarize_completed_range=AsyncMock(return_value={"lessons":2,"vocab":3,"dialogues":1})
                    await service.send_due_reminders(bot)
                    await service.send_weekly_progress_reports(bot)
            self.assertEqual(bot.send_message.await_count,2)
        # The comparison itself consumed no legacy cursor and sent nothing.

    async def test_worker_enabled_only_evaluates_existing_jobs_with_zero_attempts(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        worker=SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True),self.sessions,clock=lambda:self.tick)
        self.assertEqual([r.reason for r in await worker.tick()],["shadow_evaluated"])
        self.assertEqual((await self.row(reserved.job_id))["state"],"completed")
        self.assertEqual(await self.counts(),(1,0))

    async def test_worker_native_actor_uses_current_owned_session_without_fabrication(self):
        actor=await self.native_actor()
        worker=SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True),self.sessions,clock=lambda:self.now)
        self.assertEqual(await worker.actor_for(2),actor)
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopSession).where(DesktopSession.id==actor.session_id).values(revoked_at=self.now))
        with self.assertRaises(SmartReminderError): await worker.actor_for(2)

    async def test_tick_timeout_after_claim_leaves_only_a_finite_recoverable_lease(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        settings=SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True)
        worker=SmartReminderShadowWorker(settings,self.sessions,clock=lambda:self.tick,timeout=3)
        entered=asyncio.Event()
        async def hang(*args,**kwargs): entered.set(); await asyncio.Event().wait()
        # Give SQL time to commit the real claim; the finish then exceeds the
        # real worker timeout and must leave only a finite lease, not an effect.
        with patch.object(worker.queue,"finish",side_effect=hang):
            task=asyncio.create_task(worker.tick())
            await asyncio.wait_for(entered.wait(),5)
            with self.assertRaises(asyncio.TimeoutError): await task
        self.assertIsNotNone((await self.row(reserved.job_id))["lease_token"])
        self.tick+=timedelta(seconds=4)
        restarted=SmartReminderShadowWorker(settings,self.sessions,clock=lambda:self.tick)
        self.assertEqual([r.reason for r in await restarted.tick()],["shadow_evaluated"])
        self.assertEqual(await self.counts(),(1,0))

    async def test_slow_or_failed_admin_poller_does_not_block_separate_real_shadow_tick(self):
        source=Path(__file__).resolve().parents[1]/"app/main.py"
        tree=ast.parse(source.read_text())
        scheduler=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="_background_scheduler")
        for fail in (False,True):
            # Each case uses a new day so completed ownership is never reset.
            self.tick=(self.tick+timedelta(days=1)).replace(hour=12); self.expiry=self.tick.replace(hour=18)
            reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
            entered=asyncio.Event(); sleeping=asyncio.Event(); sleep_count=[0]
            async def legacy_sleep(seconds):
                sleep_count[0]+=1
                if sleep_count[0]>1: await sleeping.wait()
                await asyncio.sleep(0)
            async def poller():
                entered.set()
                if fail: raise RuntimeError("synthetic Admin PWA failure")
                await asyncio.Event().wait()
            ns={"Bot":object,"asyncio":SimpleNamespace(sleep=legacy_sleep),"admin_pwa_due_campaigns":poller,"print":Mock()}
            exec(compile(ast.Module(body=[scheduler],type_ignores=[]),str(source),"exec"),ns)
            legacy=asyncio.create_task(ns["_background_scheduler"](object()))
            try:
                await asyncio.wait_for(entered.wait(),5)
                worker=SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True),self.sessions,clock=lambda:self.tick)
                self.assertEqual([r.reason for r in await worker.tick()],["shadow_evaluated"])
                self.assertFalse(legacy.done())
                self.assertEqual((await self.row(reserved.job_id))["state"],"completed")
            finally:
                legacy.cancel()
                with self.assertRaises(asyncio.CancelledError): await legacy


class SQLiteSourceTests(SourceChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.fixtures.fixtures.PG_URL,"Disposable loopback PostgreSQL not configured")
class PostgreSQLSourceTests(SourceChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True


class WorkerBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_tick_and_run_have_zero_sql_or_queue_calls(self):
        factory=Mock(side_effect=AssertionError("disabled worker touched SQL"))
        worker=SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=False),factory)
        worker.queue.drain=AsyncMock(side_effect=AssertionError("disabled worker drained"))
        self.assertEqual(await worker.tick(),())
        await worker.run()
        factory.assert_not_called(); worker.queue.drain.assert_not_awaited()

    async def test_timeout_is_bounded_and_shutdown_does_not_swallow_cancellation(self):
        worker=SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True),Mock(),timeout=0.02,interval=0.001)
        async def hang(*args,**kwargs): await asyncio.Event().wait()
        worker.queue.drain=AsyncMock(side_effect=hang)
        with self.assertRaises(asyncio.TimeoutError): await worker.tick()
        task=asyncio.create_task(worker.run())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task

    async def test_runtime_exception_is_isolated_and_loop_continues(self):
        worker=SmartReminderShadowWorker(SimpleNamespace(SMART_REMINDER_SHADOW_ENABLED=True),Mock(),interval=0.001)
        retried=asyncio.Event(); calls=[0]
        async def tick():
            calls[0]+=1
            if calls[0]==1: raise RuntimeError("synthetic tick failure")
            retried.set(); return ()
        worker.tick=tick
        task=asyncio.create_task(worker.run())
        try: await asyncio.wait_for(retried.wait(),1)
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        self.assertGreaterEqual(calls[0],2)

    async def test_actual_lifespan_wires_separate_disabled_task_and_cancels_it(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/"app/main.py").read_text())
        lifespan=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="lifespan")
        segment=ast.unparse(lifespan)
        self.assertIn("SmartReminderShadowWorker(settings, async_session_maker).run()",segment)
        self.assertIn("smart_shadow_task.cancel()",segment)
        self.assertIn("await smart_shadow_task",segment)
        self.assertIn("getattr(settings, 'SMART_REMINDER_SHADOW_ENABLED', False)",segment)
        from app.config import Settings
        self.assertFalse(Settings.model_fields["SMART_REMINDER_SHADOW_ENABLED"].default)
