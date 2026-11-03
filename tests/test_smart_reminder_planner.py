"""Real SQL planner→native/TG protocols; only reviewed synthetic feeds, no provider."""
import asyncio
from dataclasses import replace
from datetime import timedelta, timezone
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import delete, event, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderConsent, SmartReminderRouting
from app.services.notification_template_service import KEY_SMART_STUDY, NotificationTemplateService
from app.services.smart_reminder_android import GRANT
from app.services.smart_reminder_planner import SmartReminderPlanner
from app.services.smart_reminder_preferences import SmartReminderActor
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from app.services.smart_reminder_telegram import _android_inventory
from tests import test_smart_reminder_android as native
from tests import test_smart_reminder_telegram as telegram
from tests.test_smart_reminder_cadence import QA
from tests.test_smart_reminder_legacy_backfill import PG_URL


class PlannerGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_off_and_missing_prerequisites_do_zero_sql_and_io(self):
        sessions=Mock(side_effect=AssertionError('unconfigured SQL'))
        feed=AsyncMock()
        for options,expected in (({'coverage_reader':feed},'planner_disabled'),
                ({'enabled':1,'coverage_reader':feed},'planner_disabled'),
                ({'enabled':True,'coverage_reader':feed},'cadence_calibration_unconfigured'),
                ({'enabled':True,'calibration':QA},'learning_coverage_unavailable')):
            result=await SmartReminderPlanner(SimpleNamespace(),sessions,**options).prepare(
                None,history_since=None,expected_level=None,expires_at=None)
            self.assertEqual(result.reason,expected)
            self.assertFalse(result.dispatch_allowed)
        sessions.assert_not_called();feed.assert_not_called()


class NativePlannerChecks:
    postgres=False

    async def asyncSetUp(self):
        cls=native.PostgreSQLAndroidProtocolTests if self.postgres else native.SQLiteAndroidProtocolTests
        self.q=cls(methodName='test_due_is_non_persisting_and_claim_commits_once_before_response')
        await self.q.asyncSetUp()
        self.actor=SmartReminderActor(1,'android',device_id='device-1',session_id='session-1')
        self.due_clock=self.q.now.replace(second=0,microsecond=0)
        if self.due_clock.hour==0 and self.due_clock.minute==0:
            self.due_clock+=timedelta(minutes=1)
            self.q.tick=self.q.now
        else:
            self.q.tick=self.due_clock-timedelta(seconds=1)
        self.q.since=self.q.tick-timedelta(days=30)
        async with self.q.sessions.begin() as session:
            await session.execute(delete(JOB).where(JOB.c.id==self.q.job_id))  # Unused owned QA seed only.
            await session.execute(update(SmartReminderCapability).where(SmartReminderCapability.user_id==1)
                .values(observed_at=self.q.tick-timedelta(seconds=1)))
            await session.execute(update(SmartReminderConsent).where(SmartReminderConsent.user_id==1,
                SmartReminderConsent.channel=='telegram').values(state='off'))
            for row in (await session.scalars(select(CourseXpEvent).where(CourseXpEvent.user_id==1))).all():
                row.created_at=row.created_at.replace(hour=self.due_clock.hour,minute=self.due_clock.minute,
                    second=0,microsecond=0)
            for row in (await session.scalars(select(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1))).all():
                row.created_at=row.created_at.replace(hour=self.due_clock.hour,minute=self.due_clock.minute,
                    second=0,microsecond=0)
        self.q.options['admission_reader']=self.admission
        await self.reviewed()

    async def asyncTearDown(self):
        await self.q.asyncTearDown()

    async def reviewed(self):
        async with self.q.sessions.begin() as session:
            self.q.inventory,_=await _android_inventory(session,1,self.q.tick)
            await session.execute(update(SmartReminderRouting).where(SmartReminderRouting.user_id==1).values(
                held_at=self.q.tick-timedelta(seconds=2),verified_at=self.q.tick-timedelta(seconds=1),
                verified_until=self.q.expiry,inventory_sha256=self.q.inventory,evidence_sha256='c'*64))

    async def admission(self,session,actor,job_id,now):
        value=await self.q.admission(session,actor,job_id,now)
        return replace(value,user_id=actor.user_id,job_id=job_id,device_id=actor.device_id,session_id=actor.session_id,
            verified_at=self.q.tick-timedelta(seconds=1),valid_until=self.q.expiry)

    def planner(self,**overrides):
        return SmartReminderPlanner(self.q.settings,self.q.sessions,**(dict(enabled=True,calibration=QA,
            coverage_reader=self.q.learning,android_admission_reader=self.admission,clock=lambda:self.q.tick)|overrides))

    async def prepare(self,**overrides):
        return await self.planner(**overrides).prepare(self.actor,history_since=self.q.since,
            expected_level='hsk1',expires_at=self.q.expiry)

    async def no_delivery(self):
        self.assertEqual(await self.q.rows(GRANT),[])
        self.assertEqual(await self.q.rows(ATTEMPT),[])

    async def test_single_device_plan_commits_without_grant_then_real_auth_claim_and_receipt(self):
        sql=[]
        def capture(c,cursor,statement,parameters,ctx,many): sql.append(str(parameters))
        event.listen(self.q.engine.sync_engine,'before_cursor_execute',capture)
        try: planned=await self.prepare()
        finally: event.remove(self.q.engine.sync_engine,'before_cursor_execute',capture)
        self.assertEqual((planned.reason,planned.channel,planned.device_id),('planned','android','device-1'))
        self.assertFalse(planned.dispatch_allowed)
        self.assertFalse(any('android_course' in params for params in sql))
        await self.no_delivery()
        self.assertEqual((await self.q.rows(JOB))[0]['state'],'pending')
        self.q.job_id=planned.job_id;self.q.tick=self.due_clock
        grant=await self.q.claim()
        self.assertTrue(grant['dispatch_allowed'])
        result,_=await self.q.receipt(grant)
        self.assertEqual(result['outcome'],'client_posted_unverified')
        self.assertEqual((await self.prepare()).reason,'planner_intent_frozen')
        self.assertEqual(len(await self.q.rows(JOB)),1)
        self.assertEqual(len(await self.q.rows(GRANT)),1)

    async def test_repeat_and_restart_acknowledge_selection_without_reranking(self):
        first=await self.prepare();before=await self.q.rows(JOB)
        self.assertEqual(first.reason,'planned')
        second=await self.prepare()
        self.assertEqual((second.reason,second.job_id,second.device_id),('already_planned',first.job_id,'device-1'))
        self.assertEqual(await self.q.rows(JOB),before)
        await self.no_delivery()

    async def second_phone(self):
        await self.q.second_installation()
        async with self.q.sessions.begin() as session:
            session.add(SmartReminderConsent(user_id=1,device_id='device-2',channel='android',state='on',
                source_key='intent:android:device-2',source='user_intent'))
            rows=(await session.scalars(select(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1,
                CourseMiniAppEvent.event_name=='lesson_completed'))).all()
            for row in rows:
                row.source='android_course'
                row.payload_json=json.dumps({'device_id':'device-2','result':{'ok':True,'duplicate':False,
                    'completed_lesson':row.lesson_order,'gamification':{'duplicate':False,'awarded_xp':1}}})
        await self.reviewed()

    async def test_verified_most_used_phone_is_bound_and_only_that_phone_can_claim(self):
        await self.second_phone()
        result=await self.prepare()
        self.assertEqual((result.reason,result.device_id),('planned','device-2'))
        await self.no_delivery()
        self.q.job_id=result.job_id;self.q.tick=self.due_clock
        await self.q.claim(uid=1,status=404)
        grant=await self.q.claim(uid=2)
        self.assertTrue(grant['dispatch_allowed'])
        await self.q.receipt(grant,uid=2)
        self.assertEqual(len(await self.q.rows(GRANT)),1)

    async def test_preferred_device_changes_during_read_cannot_bind_an_alternate(self):
        await self.second_phone()
        async def learning(session,actor,since,now):
            await session.execute(update(SmartReminderConsent).where(SmartReminderConsent.user_id==1,
                SmartReminderConsent.device_id=='device-2').values(state='off'))
            return await self.q.learning(session,actor,since,now)
        self.assertEqual((await self.prepare(coverage_reader=learning)).reason,'consent_or_permission_unavailable')
        row=(await self.q.rows(JOB))[0]
        self.assertEqual((row['state'],row['selected_device_id']),('cancelled',None))
        await self.no_delivery()

    async def test_planner_disabled_during_read_keeps_shadow_without_binding(self):
        planner=None
        async def learning(session,actor,since,now):
            planner.enabled=False
            return await self.q.learning(session,actor,since,now)
        planner=self.planner(coverage_reader=learning)
        result=await planner.prepare(self.actor,history_since=self.q.since,expected_level='hsk1',expires_at=self.q.expiry)
        self.assertEqual(result.reason,'planner_disabled')
        row=(await self.q.rows(JOB))[0]
        self.assertEqual((row['state'],row['selected_channel']),('shadow',None))
        await self.no_delivery()

    async def test_d1_holdout_created_during_read_still_cancels_before_binding(self):
        from app.services.motivation_reminder_service import D1_RECOVERY_ASSIGNED_EVENT,D1_RECOVERY_EXPERIMENT
        async def learning(session,actor,since,now):
            session.add(CourseMiniAppEvent(user_id=1,event_name=D1_RECOVERY_ASSIGNED_EVENT,
                source=D1_RECOVERY_EXPERIMENT,payload_json=json.dumps({'arm':'control'}),created_at=now))
            await session.flush()
            return await self.q.learning(session,actor,since,now)
        self.assertEqual((await self.prepare(coverage_reader=learning)).reason,'d1_holdout_active')
        self.assertEqual((await self.q.rows(JOB))[0]['state'],'cancelled')
        await self.no_delivery()

    async def test_unreviewed_and_admin_off_do_not_create_any_intent(self):
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderRouting).values(verified_at=None,verified_until=None,evidence_sha256=None))
        self.assertEqual((await self.prepare()).reason,'planner_review_unavailable')
        self.assertEqual(await self.q.rows(JOB),[])
        await self.reviewed()
        async with self.q.sessions.begin() as session:
            await NotificationTemplateService(session).update_text(KEY_SMART_STUDY,enabled=False,
                text_uz='',text_ru='',text_tj='',updated_by=None)
        self.assertEqual((await self.prepare()).reason,'admin_study_disabled')
        self.assertEqual(await self.q.rows(JOB),[])
        await self.no_delivery()

    async def test_missing_admission_or_complete_learning_never_binds_pending(self):
        result=await self.prepare(android_admission_reader=None)
        self.assertEqual(result.reason,'android_admission_unavailable')
        self.assertEqual((await self.q.rows(JOB))[0]['state'],'shadow')
        self.q.coverage=False
        self.assertEqual((await self.prepare()).reason,'learning_coverage_unavailable')
        self.assertEqual((await self.q.rows(JOB))[0]['state'],'shadow')
        await self.no_delivery()

    async def test_expired_or_changed_inventory_cannot_be_treated_as_review(self):
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderCapability).where(SmartReminderCapability.user_id==1)
                .values(generation=2))
        self.assertEqual((await self.prepare()).reason,'planner_review_unavailable')
        self.assertEqual(await self.q.rows(JOB),[])
        await self.no_delivery()

    async def test_admin_pause_during_learning_read_is_rechecked_before_binding(self):
        async def learning(session,actor,since,now):
            await NotificationTemplateService(session).update_text(KEY_SMART_STUDY,enabled=False,
                text_uz='',text_ru='',text_tj='',updated_by=None)
            return await self.q.learning(session,actor,since,now)
        self.assertEqual((await self.prepare(coverage_reader=learning)).reason,'admin_study_disabled')
        self.assertEqual((await self.q.rows(JOB))[0]['state'],'cancelled')
        await self.no_delivery()

    async def test_read_delay_past_authority_expiry_does_not_bind(self):
        async def learning(session,actor,since,now):
            result=await self.q.learning(session,actor,since,now)
            self.q.tick=self.q.expiry+timedelta(microseconds=1)
            return result
        self.assertNotEqual((await self.prepare(coverage_reader=learning)).reason,'planned')
        self.assertNotEqual((await self.q.rows(JOB))[0]['state'],'pending')
        await self.no_delivery()

    async def test_atomic_binding_failure_leaves_original_shadow_recoverable(self):
        with patch('app.services.smart_reminder_planner.update',side_effect=RuntimeError('synthetic binding failure')):
            with self.assertRaises(RuntimeError): await self.prepare()
        original=(await self.q.rows(JOB))[0]
        self.assertEqual((original['state'],original['selected_channel']),('shadow',None))
        planned=await self.prepare()
        self.assertEqual((planned.reason,planned.job_id),('planned',original['id']))
        self.assertEqual(len(await self.q.rows(JOB)),1)
        await self.no_delivery()

    async def test_manual_unavailable_channel_cannot_fall_back_to_phone(self):
        from app.db.models.smart_reminder import SmartReminderPreference
        async with self.q.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1)
                .values(channel_mode='manual_locked',preferred_channel='telegram'))
        self.assertEqual((await self.prepare()).reason,'manual_channel_unavailable')
        self.assertEqual(await self.q.rows(JOB),[])
        await self.no_delivery()

    async def test_postgres_concurrent_planners_bind_exactly_one_day_without_grants(self):
        if not self.postgres: self.skipTest('Independent PostgreSQL transactions required')
        results=await asyncio.wait_for(asyncio.gather(self.prepare(),self.prepare()),15)
        self.assertEqual(sorted(r.reason for r in results),['already_planned','planned'])
        self.assertEqual(len({r.job_id for r in results}),1)
        self.assertEqual(len(await self.q.rows(JOB)),1)
        await self.no_delivery()


class SQLiteNativePlannerTests(NativePlannerChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLNativePlannerTests(NativePlannerChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True


class TelegramPlannerChecks:
    postgres=False
    async def asyncSetUp(self):
        cls=telegram.PostgreSQLTelegramTests if self.postgres else telegram.SQLiteTelegramTests
        self.q=cls(methodName='test_admin_pause_after_prepare_stops_provider')
        await self.q.asyncSetUp()
        await self.q.active()

    async def asyncTearDown(self): await self.q.asyncTearDown()

    async def test_real_tg_plan_has_no_attempt_until_existing_claim_and_dispatch(self):
        planner=SmartReminderPlanner(self.q.settings,self.q.sessions,enabled=True,calibration=QA,
            coverage_reader=self.q.service.coverage_reader,clock=lambda:self.q.tick)
        result=await planner.prepare(self.q.actor,history_since=self.q.since,
            expected_level='hsk1',expires_at=self.q.expiry)
        self.assertEqual((result.reason,result.channel,result.device_id),('planned','telegram',None))
        self.assertEqual(await self.q.rows(ATTEMPT),[])
        self.q.bot.send_message.assert_not_called()
        self.q.tick=self.q.tick.replace(hour=14)
        lease=await self.q.claim(result.job_id)
        self.assertEqual(lease.reason,'telegram_claimed')
        self.assertEqual((await self.q.dispatch(lease)).reason,'telegram_provider_accepted')
        self.assertEqual(self.q.bot.send_message.await_count,1)
        self.assertFalse(result.dispatch_allowed)

    async def test_provider_flag_off_does_not_reserve_or_change_review(self):
        self.q.settings.SMART_REMINDER_TELEGRAM_ENABLED=False
        planner=SmartReminderPlanner(self.q.settings,self.q.sessions,enabled=True,calibration=QA,
            coverage_reader=self.q.service.coverage_reader,clock=lambda:self.q.tick)
        before=await self.q.rows(SmartReminderRouting.__table__)
        result=await planner.prepare(self.q.actor,history_since=self.q.since,
            expected_level='hsk1',expires_at=self.q.expiry)
        self.assertEqual(result.reason,'telegram_dispatch_disabled')
        self.assertEqual(await self.q.rows(JOB),[])
        self.assertEqual(await self.q.rows(SmartReminderRouting.__table__),before)


class SQLiteTelegramPlannerTests(TelegramPlannerChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL,'Disposable loopback PostgreSQL required')
class PostgreSQLTelegramPlannerTests(TelegramPlannerChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
