"""OFF/deletion/revocation on real owned ledgers; provider IO is mocked only."""
import asyncio
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import insert, select, update

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.android_push import AndroidPushToken
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderCapability, SmartReminderJob
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.account_deletion_service import AccountDeletionService
from app.services.android_push_service import AndroidPushService, AndroidPushResult
from app.services.android_realtime_push_service import AndroidRealtimePushService
from app.services.course_reminder_service import CourseReminderService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from app.services.smart_reminder_legacy_backfill import SmartReminderLegacyBackfillService
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError, SmartReminderPatch, SmartReminderPreferencesService
from tests import test_smart_reminder_preferences as fixtures

PREF, CONSENT = fixtures.PREF, fixtures.CONSENT
JOB, ATTEMPT = SmartReminderJob.__table__, SmartReminderAttempt.__table__
CAP = SmartReminderCapability.__table__


class LifecycleChecks:
    postgres = False
    asyncSetUp = fixtures.PreferenceChecks.asyncSetUp
    asyncTearDown = fixtures.PreferenceChecks.asyncTearDown
    migrate = staticmethod(fixtures.PreferenceChecks.migrate)
    _rows = fixtures.PreferenceChecks._rows
    _progress = fixtures.PreferenceChecks._progress
    _deletion = fixtures.PreferenceChecks._deletion
    bearer = fixtures.PreferenceChecks.bearer
    telegram = fixtures.PreferenceChecks.telegram
    body = fixtures.PreferenceChecks.body
    send = fixtures.PreferenceChecks.send
    read = fixtures.PreferenceChecks.read

    def job(self, *, uid=2, day=0, state='pending', lease=False):
        start=datetime(2026,10,28,tzinfo=timezone.utc)+timedelta(days=day)
        return dict(id=str(uuid4()),user_id=uid,local_day=start.date(),timezone_name='Etc/UTC',
                    day_start_utc=start,day_end_utc=start+timedelta(days=1),scheduled_at=start+timedelta(hours=12),
                    expires_at=start+timedelta(hours=14),state=state,policy_version='qa-only',
                    selected_channel='android',selected_device_id=f'device-{uid}',
                    lease_token=str(uuid4()) if lease else None,lease_expires_at=start+timedelta(hours=13) if lease else None)

    def attempt(self, job, *, state='prepared'):
        return dict(id=str(uuid4()),job_id=job['id'],attempt_key=str(uuid4()),channel='android',device_id=job['selected_device_id'],
                    state=state,prepared_at=job['scheduled_at'],expires_at=job['expires_at'])

    async def seed(self, *, uid=2, flag=True, study_allowed=False):
        async with self.sessions.begin() as s:
            s.add(AndroidPushToken(device_id=f'device-{uid}',token=f'synthetic-private-{uid}',study_reminders_enabled=flag,
                                   notifications_allowed=True,timezone_name='Etc/UTC'))
            s.add(SmartReminderCapability(user_id=uid,device_id=f'device-{uid}',protocol_version=3,
                autonomous_study_disabled=True,study_notifications_allowed=study_allowed,
                observed_at=self.now,expires_at=self.now+timedelta(hours=1)))
            s.add(CourseMiniAppProfile(user_id=uid))

    async def test_global_off_cancels_unattempted_preserves_external_outcomes_and_other_owner(self):
        await self._progress(user_id=2,enabled=True)
        await self.seed()
        pending=self.job(lease=True);external=self.job(day=1,state='claimed',lease=True)
        accepted=self.job(day=2,state='provider_accepted');other=self.job(uid=3,lease=True)
        prepared=self.attempt(pending);flight=self.attempt(external,state='in_flight')
        alternate=self.attempt(external);unknown=self.attempt(external,state='unknown');done=self.attempt(accepted,state='provider_accepted')
        async with self.sessions.begin() as s:
            for job in (pending,external,accepted,other): await s.execute(insert(JOB).values(**job))
            for attempt in (prepared,flight,alternate,unknown,done): await s.execute(insert(ATTEMPT).values(**attempt))
        await self.send(self.body(master_enabled=False))
        jobs={r['id']:r for r in await self._rows(JOB)}
        attempts={r['id']:r for r in await self._rows(ATTEMPT)}
        self.assertEqual(jobs[pending['id']]['state'],'cancelled')
        self.assertEqual(jobs[external['id']]['state'],'claimed')
        self.assertEqual(jobs[accepted['id']]['state'],'provider_accepted')
        self.assertIsNone(jobs[external['id']]['lease_token'])
        self.assertEqual(jobs[other['id']]['state'],'pending')
        self.assertEqual(jobs[other['id']]['lease_token'],other['lease_token'])
        for row in (prepared,alternate): self.assertEqual(attempts[row['id']]['state'],'cancelled')
        for row in (flight,unknown,done): self.assertEqual(attempts[row['id']]['state'],row['state'])
        self.assertEqual((await self._rows(PREF))[0]['grant_epoch'],1)
        self.assertEqual(len(await self._rows(JOB)),4)
        self.assertEqual(len(await self._rows(ATTEMPT)),5)
        async with self.sessions() as s:
            self.assertFalse((await s.scalar(select(CourseProgress).where(CourseProgress.user_id==2))).reminder_enabled)
            push=await s.get(AndroidPushToken,'device-2');self.assertFalse(push.study_reminders_enabled)
            self.assertTrue(push.notifications_allowed)
            self.assertEqual(push.timezone_name,'Etc/UTC')
            self.assertTrue(await s.scalar(select(CourseMiniAppProfile.notifications_enabled).where(CourseMiniAppProfile.user_id==2)))
            self.assertFalse((await s.get(SmartReminderCapability,'device-2')).study_notifications_allowed)

    async def test_endpoint_off_changes_only_its_legacy_flag_and_no_other_consent(self):
        await self._progress(user_id=2,enabled=True)
        await self.seed()
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id='second-2',user_id=2,telegram_id=None,installation_key_hash='second-2',platform='android',app_version='qa'))
            await s.flush()
            s.add(AndroidPushToken(device_id='second-2',token='synthetic-second-2',study_reminders_enabled=True,timezone_name='Etc/UTC'))
            await s.execute(insert(CONSENT).values(user_id=2,channel='android',source_key='intent:android:second-2',
                source='user_intent',device_id='second-2',state='on',action_at=self.now))
        await self.send(self.body(study_enabled=False))
        async with self.sessions() as s:
            self.assertFalse((await s.get(AndroidPushToken,'device-2')).study_reminders_enabled)
            self.assertTrue((await s.get(AndroidPushToken,'second-2')).study_reminders_enabled)
            self.assertTrue((await s.scalar(select(CourseProgress).where(CourseProgress.user_id==2))).reminder_enabled)
        self.assertEqual([r['state'] for r in await self._rows(CONSENT) if r['source_key']=='intent:android:second-2'],['on'])

    async def test_replay_old_sync_and_backfill_cannot_clear_off_or_bump_revision(self):
        await self.seed()
        body=self.body(master_enabled=False);await self.send(body)
        before=(await self._rows(PREF),await self._rows(CONSENT))
        response=await self.client.post('/api/v3/android/push/preferences',headers=await self.bearer(),
            json={'study_reminders_enabled':True,'timezone_name':'Asia/Tashkent','notifications_allowed':False})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json(),{'ok':True})
        await self.send(body)
        async with self.sessions.begin() as s:
            await SmartReminderLegacyBackfillService(s).backfill(2)
        self.assertEqual((await self._rows(PREF),await self._rows(CONSENT)),before)
        async with self.sessions() as s:
            row=await s.get(AndroidPushToken,'device-2');self.assertFalse(row.study_reminders_enabled)
            self.assertFalse(row.notifications_allowed);self.assertEqual(row.timezone_name,'Asia/Tashkent')

    async def test_repository_refuses_unbound_legacy_on_after_opt_out(self):
        await self._progress(enabled=True)
        await self.send(self.body(master_enabled=False),tg=True)
        async with self.sessions() as s:
            progress=await s.get(CourseProgress,1)
            with self.assertRaises(SmartReminderError):
                await CourseProgressRepository(s).set_reminder(progress,True,time(9))
            await s.rollback()
        async with self.sessions() as s: self.assertFalse((await s.get(CourseProgress,1)).reminder_enabled)

    async def test_rollback_restores_job_flags_and_creates_no_committed_enrollment(self):
        await self.seed();job=self.job()
        async with self.sessions.begin() as s: await s.execute(insert(JOB).values(**job))
        actor=SmartReminderActor(2,'android',device_id='device-2',session_id='session-2')
        async with self.sessions() as s:
            await SmartReminderPreferencesService(s).patch(actor,SmartReminderPatch(**self.body(master_enabled=False)))
            self.assertEqual(await s.scalar(select(JOB.c.state)), 'cancelled')
            await s.rollback()
        self.assertEqual((await self._rows(JOB))[0]['state'],'pending')
        self.assertEqual(await self._rows(PREF),[])
        async with self.sessions() as s: self.assertTrue((await s.get(AndroidPushToken,'device-2')).study_reminders_enabled)

    async def test_logout_and_device_revocation_keep_off_but_clear_capability_and_pending_grants(self):
        await self.seed();await self.send(self.body(master_enabled=False,study_enabled=False))
        job=self.job(lease=True)
        async with self.sessions.begin() as s: await s.execute(insert(JOB).values(**job))
        token=(await self.bearer())['Authorization'].split(' ',1)[1]
        before=await self._rows(CONSENT)
        async with self.sessions() as s:
            result=await DesktopAuthService(s,self.settings).revoke(token,revoke_device=False)
        self.assertEqual(result,{'ok':True,'device_revoked':False})
        pref=(await self._rows(PREF))[0]
        self.assertEqual((pref['revision'],pref['grant_epoch'],pref['master_enabled']),(2,2,False))
        self.assertEqual(await self._rows(CONSENT),before)
        self.assertEqual(await self._rows(CAP),[])
        self.assertEqual((await self._rows(JOB))[0]['state'],'cancelled')
        async with self.sessions() as s:
            self.assertIsNone((await s.get(DesktopDevice,'device-2')).revoked_at)
            self.assertIsNotNone((await s.get(DesktopSession,'session-2')).revoked_at)

    async def test_explicit_device_revoke_invalidates_other_session_on_same_device(self):
        await self.seed();await self.send(self.body(master_enabled=True))
        async with self.sessions.begin() as s:
            s.add(DesktopSession(id='second-session',device_id='device-2',refresh_token_hash='second-hash',expires_at=self.now+timedelta(days=1)))
        token=(await self.bearer())['Authorization'].split(' ',1)[1]
        async with self.sessions() as s: await DesktopAuthService(s,self.settings).revoke(token,revoke_device=True)
        async with self.sessions() as s:
            self.assertIsNotNone((await s.get(DesktopDevice,'device-2')).revoked_at)
            self.assertIsNotNone((await s.get(DesktopSession,'second-session')).revoked_at)
        self.assertEqual(await self._rows(CAP),[])

    async def test_refresh_reuse_invalidates_once_and_successful_rotation_does_not(self):
        await self.seed();await self.send(self.body(master_enabled=False))
        original='a'*48
        async with self.sessions.begin() as s:
            auth=DesktopAuthService(s,self.settings)
            await s.execute(update(DesktopSession).where(DesktopSession.id=='session-2').values(refresh_token_hash=auth._hash('refresh',original)))
        async with self.sessions() as s: await DesktopAuthService(s,self.settings).refresh(original)
        self.assertEqual((await self._rows(PREF))[0]['revision'],1)
        for _ in range(2):
            async with self.sessions() as s:
                with self.assertRaises(DesktopAuthError) as caught: await DesktopAuthService(s,self.settings).refresh(original)
                self.assertEqual(caught.exception.code,'desktop_refresh_reuse_detected')
            pref=(await self._rows(PREF))[0]
            self.assertEqual((pref['revision'],pref['grant_epoch'],pref['master_enabled']),(2,2,False))
        self.assertEqual(await self._rows(CAP),[])

    async def test_push_unregister_is_idempotent_and_retains_study_off(self):
        await self.seed();await self.send(self.body(study_enabled=False))
        before=await self._rows(CONSENT)
        for _ in range(2):
            async with self.sessions() as s:
                await AndroidPushService(s,self.settings).unregister(device=await s.get(DesktopDevice,'device-2'))
        self.assertEqual(await self._rows(CONSENT),before)
        pref=(await self._rows(PREF))[0];self.assertEqual((pref['revision'],pref['grant_epoch']),(2,2))
        self.assertEqual(await self._rows(CAP),[])

    async def test_deletion_confirmation_invalidates_once_before_purge(self):
        await self.seed();await self.send(self.body(master_enabled=True))
        job=self.job()
        async with self.sessions.begin() as s: await s.execute(insert(JOB).values(**job))
        async with self.sessions() as s:
            service=AccountDeletionService(s,self.settings)
            receipt=await service.start(provider='session',client='qa-user-2',user=await s.get(User,2))
            first=await service.confirm(request_id=receipt['request_id'],secret=receipt['secret'])
            second=await service.confirm(request_id=receipt['request_id'],secret=receipt['secret'])
        self.assertEqual(first,second)
        self.assertEqual((await self._rows(PREF))[0]['revision'],2)
        self.assertEqual((await self._rows(JOB))[0]['state'],'cancelled')
        await self.read(status=409)

    async def test_identity_disconnect_revocation_preserves_last_login_and_consent(self):
        await self.seed();await self.send(self.body(master_enabled=False))
        async with self.sessions.begin() as s:
            s.add_all([UserIdentity(id='identity-a',user_id=2,provider='google',subject_hash='synthetic-a'),
                       UserIdentity(id='identity-b',user_id=2,provider='apple',subject_hash='synthetic-b'),
                       DesktopSession(id='other-login',device_id='device-2',refresh_token_hash='other-login-hash',expires_at=self.now+timedelta(days=1))])
        async with self.sessions.begin() as s:
            result=await IdentityLinkService(s,self.settings).unlink(identity_id='identity-a',user_id=2,keep_session_id='session-2')
        self.assertEqual(result['sessions_revoked'],1)
        async with self.sessions() as s:
            self.assertIsNone((await s.get(DesktopSession,'session-2')).revoked_at)
            self.assertIsNotNone((await s.get(DesktopSession,'other-login')).revoked_at)
        self.assertFalse((await self._rows(PREF))[0]['master_enabled'])
        self.assertEqual(await self._rows(CAP),[])

    async def test_telegram_sender_honors_fresh_smart_off_even_if_legacy_flag_is_stale_on(self):
        await self._progress(enabled=True,selected=time(14),offset=0)
        await self.send(self.body(master_enabled=False),tg=True)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status='active'))
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(reminder_enabled=True))
        now=datetime(2026,10,28,14,0,tzinfo=timezone.utc)
        async with self.sessions() as s:
            bot=AsyncMock()
            with patch('app.services.course_reminder_service.datetime',wraps=datetime) as clock:
                clock.now.return_value=now
                await CourseReminderService(s).send_due_reminders(bot)
            bot.send_message.assert_not_awaited()

    async def test_android_sender_vetoes_off_without_enrolling_other_owner(self):
        await self.seed();await self.send(self.body(master_enabled=False))
        async with self.sessions.begin() as s:
            await s.execute(update(AndroidPushToken).values(study_reminders_enabled=True))
        settings=SimpleNamespace(ANDROID_PUSH_STUDY_ENABLED=True,ANDROID_FCM_PROJECT_ID='qa-only')
        async with self.sessions() as s:
            service=AndroidRealtimePushService(s,settings);service.push.send_batch=AsyncMock(return_value=[])
            self.assertEqual(await service.send_due_study(datetime(2026,10,28,20,59,tzinfo=timezone.utc)),0)
            service.push.send_batch.assert_not_awaited()
        # No Smart state is created for a non-Smart account lifecycle event.
        async with self.sessions.begin() as s:
            await SmartReminderLifecycleService(s).invalidate(3,reason='session_logout',device_id='device-3')
        self.assertEqual({r['user_id'] for r in await self._rows(PREF)},{2})

    async def test_legacy_os_study_denial_veto_is_independent_of_account_notices(self):
        await self.seed(study_allowed=False)
        settings=SimpleNamespace(ANDROID_PUSH_STUDY_ENABLED=True,ANDROID_FCM_PROJECT_ID='qa-only')
        async with self.sessions() as session:
            service=AndroidRealtimePushService(session,settings)
            service.push.send_batch=AsyncMock(return_value=[])
            self.assertEqual(await service.send_due_study(datetime(2026,10,28,20,59,tzinfo=timezone.utc)),0)
            service.push.send_batch.assert_not_awaited()
            self.assertTrue((await session.get(AndroidPushToken,'device-2')).notifications_allowed)
        self.assertEqual(await self._rows(PREF),[])

    async def test_veto_checks_current_block_and_pending_deletion_without_new_enrollment(self):
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==2).values(status='blocked'))
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_veto(2,'android',device_id='device-2'))
        await self._deletion(owner=3,active_uid=3)
        async with self.sessions() as s:
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_veto(3,'android',device_id='device-3'))
        self.assertEqual(await self._rows(PREF),[])

    async def _typed_time(self, *, course_branch=False, off=True):
        from contextlib import ExitStack
        from app.bot.handlers.messages import handle_text_message
        from app.bot.utils.i18n import t
        from app.bot.utils.smart_reminder import INTERACTION_KEY, smart_reminder_time_keyboard
        await self._progress(enabled=False,selected=time(14),waiting="reminder_setup")
        await self.send(self.body(master_enabled=not off),tg=True)
        state=fixtures.State()
        if not off:
            async with self.sessions() as s: await smart_reminder_time_keyboard(s,state,1,'uz')
        async with self.sessions() as s:
            user=await s.get(User,1);user.language='uz';user.learning_mode='course' if course_branch else 'qa'
            await s.commit()
            progress=await s.scalar(select(CourseProgress).where(CourseProgress.user_id==1))
            message=SimpleNamespace(from_user=SimpleNamespace(id=3001),text='08:00',answer=AsyncMock())
            with ExitStack() as stack:
                stack.enter_context(patch('app.bot.handlers.messages._is_admin_flow_message',new=AsyncMock(return_value=False)))
                stack.enter_context(patch('app.bot.handlers.messages._migrate_legacy_course_mode_to_qa',new=AsyncMock()))
                stack.enter_context(patch('app.bot.handlers.messages.delete_message_safely',new=AsyncMock()))
                panel=stack.enter_context(patch('app.bot.handlers.messages._edit_reminder_panel',new=AsyncMock()))
                if course_branch:
                    repo=CourseProgressRepository(s);repo.get_by_user_id=AsyncMock(return_value=None)
                    fake=SimpleNamespace(progress_repo=repo,get_current_lesson=AsyncMock(return_value=(user,progress,SimpleNamespace(id=1),None)))
                    stack.enter_context(patch('app.bot.handlers.messages.CourseEngineService',return_value=fake))
                    stack.enter_context(patch('app.bot.handlers.messages._is_stale_course_menu_text',return_value=False))
                    stack.enter_context(patch('app.bot.handlers.messages._ensure_active_course_access',new=AsyncMock(return_value=True)))
                    stack.enter_context(patch('app.bot.handlers.messages._ensure_trial_lesson_access',new=AsyncMock(return_value=True)))
                await handle_text_message(message,state,s)
                panel.assert_awaited_once()
                if off: self.assertEqual(panel.call_args.args[2],t('course_reminder_cancelled','uz'))
        async with self.sessions() as s:
            progress=await s.scalar(select(CourseProgress).where(CourseProgress.user_id==1))
            self.assertEqual(progress.waiting_for,'none')
            self.assertEqual(progress.reminder_enabled,not off)
            self.assertEqual(progress.reminder_time,time(14) if off else time(8))
        self.assertEqual((await self.read(tg=True))['revision'],1 if off else 2)
        if off: self.assertIsNone(state.data[INTERACTION_KEY])

    async def test_early_typed_time_after_off_does_not_enable_or_leave_setup_stuck(self):
        await self._typed_time()

    async def test_course_typed_time_after_off_does_not_enable_or_leave_setup_stuck(self):
        await self._typed_time(course_branch=True)

    async def test_current_fenced_typed_time_updates_intent_and_legacy_atomically(self):
        await self._typed_time(off=False)

    async def test_study_off_preserves_existing_weekly_summary_category(self):
        await self._progress(enabled=True,offset=0)
        await self.send(self.body(master_enabled=False),tg=True)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status='active',end_date=self.now+timedelta(days=10)))
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(completed_lessons_count=1))
        async with self.sessions() as s:
            bot=AsyncMock()
            with patch('app.services.course_reminder_service.datetime',wraps=datetime) as clock:
                clock.now.return_value=datetime(2026,10,26,9,tzinfo=timezone.utc)
                await CourseReminderService(s).send_weekly_progress_reports(bot)
            bot.send_message.assert_awaited_once()

    async def test_postgres_legacy_sync_racing_off_cannot_restore_old_study_flag(self):
        if not self.postgres: self.skipTest('Requires PostgreSQL independent transactions')
        await self.seed(flag=False,study_allowed=True)
        headers=await self.bearer()
        async def legacy():
            return await self.client.post('/api/v3/android/push/preferences',headers=headers,
                json={'study_reminders_enabled':True,'timezone_name':'Asia/Tashkent','notifications_allowed':False})
        _,response=await asyncio.wait_for(asyncio.gather(self.send(self.body(master_enabled=False)),legacy()),10)
        self.assertEqual(response.status_code,200,response.text)
        pref=(await self._rows(PREF))[0]
        self.assertEqual((pref['revision'],pref['grant_epoch'],pref['master_enabled']),(1,1,False))
        async with self.sessions() as session:
            row=await session.get(AndroidPushToken,'device-2')
            self.assertFalse(row.study_reminders_enabled)
            self.assertFalse(row.notifications_allowed)
            self.assertEqual(row.timezone_name,'Asia/Tashkent')

    async def test_postgres_refresh_and_off_use_user_first_without_deadlock(self):
        if not self.postgres: self.skipTest('Requires PostgreSQL independent transactions')
        await self.send(self.body(master_enabled=True))
        original='b'*48
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopSession).where(DesktopSession.id=='session-2').values(
                refresh_token_hash=DesktopAuthService(s,self.settings)._hash('refresh',original)))
        async def refresh():
            async with self.sessions() as s: return await DesktopAuthService(s,self.settings).refresh(original)
        await asyncio.wait_for(asyncio.gather(refresh(),self.send(self.body(1,master_enabled=False))),10)
        self.assertFalse((await self._rows(PREF))[0]['master_enabled'])

    async def test_postgres_logout_racing_current_on_invalidates_pending_authorization(self):
        if not self.postgres: self.skipTest('Requires PostgreSQL independent transactions')
        await self.seed();await self.send(self.body(master_enabled=False))
        job=self.job(lease=True)
        async with self.sessions.begin() as s: await s.execute(insert(JOB).values(**job))
        headers=await self.bearer();token=headers['Authorization'].split(' ',1)[1]
        async def logout():
            async with self.sessions() as s: return await DesktopAuthService(s,self.settings).revoke(token,revoke_device=False)
        async def on(): return await self.client.patch('/api/v3/android/smart-reminder/preferences',headers=headers,json=self.body(1,master_enabled=True))
        _,response=await asyncio.wait_for(asyncio.gather(logout(),on()),10)
        self.assertIn(response.status_code,(200,401,409))
        self.assertEqual((await self._rows(JOB))[0]['state'],'cancelled')
        self.assertEqual(await self._rows(CAP),[])
        async with self.sessions() as s: self.assertIsNotNone((await s.get(DesktopSession,'session-2')).revoked_at)


class SQLiteSmartLifecycleTests(LifecycleChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.fixtures.PG_URL,'Set disposable loopback SMART_REMINDER_TEST_DATABASE_URL')
class PostgreSQLSmartLifecycleTests(LifecycleChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
