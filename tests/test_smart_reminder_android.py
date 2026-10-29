"""Dormant Android protocol: real native auth/SQL, synthetic reviewed inputs."""
import asyncio
from datetime import datetime, time, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event, insert, select, update

from app.api.smart_reminder import create_smart_reminder_router
from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderConsent, SmartReminderPreference, SmartReminderRouting
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService
from app.services.smart_reminder_android import AndroidAdmission, GRANT, SmartReminderAndroidService
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderPatch, SmartReminderPreferencesService
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB, day_window
from app.services.smart_reminder_telegram import LearningCoverage, _android_inventory
from tests import test_smart_reminder_policy as fixtures
from tests.test_smart_reminder_cadence import QA
from tests.test_smart_reminder_preferences import PreferenceChecks
from tests.test_smart_reminder_legacy_backfill import PG_URL

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('android_grants_0136',ROOT/'alembic/versions/0136_smart_android_grants.py')
MIGRATION = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MIGRATION)
BASE = '/api/v3/android/smart-reminder'


class AndroidChecks:
    postgres = False
    _progress = fixtures.PolicyContextChecks._progress
    _deletion = fixtures.PolicyContextChecks._deletion
    study = fixtures.PolicyContextChecks.study
    bearer = PreferenceChecks.bearer
    telegram = PreferenceChecks.telegram

    @staticmethod
    def migrate(connection, operation):
        with Operations.context(MigrationContext.configure(connection)):
            getattr(MIGRATION,operation)()

    async def asyncSetUp(self):
        await fixtures.PolicyContextChecks.asyncSetUp(self)
        self.tick = self.now
        self.moment = self.tick
        self.since = self.tick-timedelta(days=30)
        start,end = day_window('Etc/UTC',self.tick.date().isoformat())
        self.expiry = min(self.tick+timedelta(minutes=5),end)
        self.job_id, self.epoch = str(uuid4()),str(uuid4())
        self.enabled = True
        self.review_changes = {}
        self.coverage = True
        self.options = {}
        self.settings = SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET='synthetic-android-claims-'+'x'*40,
            BOT_TOKEN='123456789:synthetic-test-only',BOT_USERNAME='test_bot')
        async with self.engine.begin() as c:
            await c.run_sync(GRANT.drop)
            await c.run_sync(self.migrate,'upgrade')
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status='active',payment_status='approved',
                end_date=self.now+timedelta(days=2)))
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1)
                .values(legacy_time_local=self.tick.time().replace(second=0,microsecond=0,tzinfo=None)))
            for uid in (1,2):
                s.add(DesktopDevice(id=f'device-{uid}',user_id=uid,platform='android',
                    installation_key_hash=f'qa-only-install-{uid}',app_version='synthetic'))
            await s.flush()
            for uid in (1,2):
                s.add(DesktopSession(id=f'session-{uid}',device_id=f'device-{uid}',
                    refresh_token_hash=f'qa-only-refresh-{uid}',expires_at=self.now+timedelta(days=1)))
            s.add(SmartReminderConsent(user_id=1,device_id='device-1',channel='android',
                source_key='intent:android:device-1',source='user_intent',state='on'))
            s.add(SmartReminderCapability(user_id=1,device_id='device-1',generation=1,protocol_version=1,
                autonomous_study_disabled=True,study_notifications_allowed=True,
                observed_at=self.tick-timedelta(seconds=1),expires_at=self.expiry))
            s.add(SmartReminderRouting(user_id=1,state='held',generation=1,preference_revision=2,grant_epoch=1,
                telegram_binding='a'*64,held_at=self.tick-timedelta(seconds=1)))
            s.add(AndroidPushToken(device_id='device-1',token='synthetic-no-provider',timezone_name='Etc/UTC',
                notifications_allowed=True,study_reminders_enabled=False))
            await s.execute(insert(JOB).values(id=self.job_id,user_id=1,local_day=self.tick.date(),timezone_name='Etc/UTC',
                day_start_utc=start,day_end_utc=end,scheduled_at=self.tick.replace(second=0,microsecond=0),
                expires_at=self.expiry,state='pending',policy_version=self.service(s).policy_version,
                preference_revision=2,grant_epoch=1,course_key='hsk1',lesson_order=5,
                selected_channel='android',selected_device_id='device-1'))
        for n in range(1,5): await self.study(order=n,days_ago=5-n,xp=1)
        async with self.sessions() as s: self.inventory,_=await _android_inventory(s,1,self.tick)
        app = FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=self.sessions,settings_obj=self.settings,
            android_delivery_factory=self.service))
        self.client = AsyncClient(transport=ASGITransport(app=app),base_url='https://claims.test')

    async def asyncTearDown(self):
        await self.client.aclose()
        await fixtures.PolicyContextChecks.asyncTearDown(self)

    async def admission(self, session, actor, job_id, now):
        return AndroidAdmission(**(dict(user_id=1,job_id=self.job_id,device_id='device-1',session_id='session-1',
            generation=1,preference_revision=2,grant_epoch=1,verified_at=self.now-timedelta(seconds=1),
            valid_until=self.expiry,history_since=self.since,evidence_sha256='b'*64,
            inventory_sha256=self.inventory,
            legacy_quiesced=True,legacy_outcomes_reconciled=True,other_study_fenced=True)|self.review_changes))

    async def learning(self, session, actor, since, now):
        return LearningCoverage(actor.user_id,since,now,'qa-complete-only') if self.coverage else None

    async def second_installation(self, *, capable=True):
        """Synthetic same-account installation, never a real fleet attestation."""
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopDevice).where(DesktopDevice.id=='device-2').values(
                user_id=1, app_version='synthetic-compatible' if capable else 'synthetic-legacy-unknown'))
            if capable:
                s.add(SmartReminderCapability(user_id=1,device_id='device-2',generation=1,protocol_version=1,
                    autonomous_study_disabled=True,study_notifications_allowed=True,
                    observed_at=self.tick-timedelta(seconds=1),expires_at=self.expiry))
            s.add(AndroidPushToken(device_id='device-2',token='synthetic-other-no-provider',timezone_name='Etc/UTC',
                notifications_allowed=True,study_reminders_enabled=False))
        async with self.sessions() as s:
            self.inventory,_=await _android_inventory(s,1,self.tick)

    def service(self, session):
        return SmartReminderAndroidService(session,**(dict(enabled=self.enabled,admission_reader=self.admission,
            calibration=QA,coverage_reader=self.learning,clock=lambda:self.tick)|self.options))

    def body(self, **changes):
        return dict(version=1,request_id=str(uuid4()),local_epoch=self.epoch,
            capability_generation=1,preference_revision=2,grant_epoch=1)|changes

    async def claim(self, body=None, *, uid=1,status=200):
        response = await self.client.post(f'{BASE}/jobs/{self.job_id}/claim',headers=await self.bearer(uid),
            json=self.body() if body is None else body)
        self.assertEqual(response.status_code,status,response.text)
        self.assertEqual(response.headers['cache-control'],'no-store')
        return response.json()

    async def due(self):
        response = await self.client.get(BASE+'/due',headers=await self.bearer(1))
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def rows(self, table):
        async with self.sessions() as s: return (await s.execute(select(table))).mappings().all()

    async def no_grant(self):
        self.assertEqual(await self.rows(GRANT),[])
        self.assertEqual(await self.rows(ATTEMPT),[])

    async def receipt(self, grant, outcome='client_posted_unverified', *, body=None,status=200,uid=1):
        data = dict(version=1,grant_id=grant['grant_id'],receipt_id=str(uuid4()),local_epoch=self.epoch,outcome=outcome)
        response = await self.client.post(f'{BASE}/jobs/{self.job_id}/receipt',headers=await self.bearer(uid),json=body or data)
        self.assertEqual(response.status_code,status,response.text)
        return response.json(),data

    async def test_due_is_non_persisting_and_claim_commits_once_before_response(self):
        before = await self.rows(JOB)
        due = await self.due()
        self.assertEqual(due['job_id'],self.job_id)
        self.assertFalse(due['dispatch_allowed'])
        self.assertNotIn('grant_id',due)
        self.assertEqual(await self.rows(JOB),before)
        await self.no_grant()
        body = self.body()
        grant = await self.claim(body)
        self.assertTrue(grant['dispatch_allowed'],grant)
        self.assertEqual(grant['local_epoch'],self.epoch)
        self.assertEqual((await self.rows(ATTEMPT))[0]['state'],'in_flight')
        self.assertEqual((await self.rows(GRANT))[0]['admission_sha256'],'b'*64)
        for retry in (body,self.body()):
            result = await self.claim(retry)
            self.assertFalse(result['dispatch_allowed'])
            self.assertNotIn('grant_id',result)
        self.assertEqual(len(await self.rows(GRANT)),1)
        self.assertEqual(len(await self.rows(ATTEMPT)),1)
        self.assertNotIn('job_id',await self.due())

    async def test_lost_response_and_expired_grant_never_authorize_reclaim(self):
        body = self.body()
        self.assertTrue((await self.claim(body))['dispatch_allowed'])  # Discard this response as a network loss.
        self.tick = self.expiry+timedelta(microseconds=1)
        self.assertFalse((await self.claim(body))['dispatch_allowed'])
        self.assertEqual(len(await self.rows(GRANT)),1)

    async def test_receipt_is_truthful_immutable_idempotent_and_creates_no_learning(self):
        grant = await self.claim()
        result,body = await self.receipt(grant)
        retry,_ = await self.receipt(grant,body=body)
        self.assertEqual(result,retry)
        self.assertFalse(result['dispatch_allowed'])
        self.assertEqual((await self.rows(ATTEMPT))[0]['state'],'client_posted_unverified')
        self.assertEqual((await self.rows(JOB))[0]['state'],'unknown')
        await self.receipt(grant,body=body|{'outcome':'client_declined_before_post'},status=409)
        await self.receipt(grant,body=body|{'receipt_id':str(uuid4())},status=409)
        for outcome in ('verified_shown','read','lesson_completed'):
            await self.receipt(grant,body=body|{'outcome':outcome},status=422)

    async def test_expiry_off_and_disabled_dispatch_still_accept_original_historical_receipt(self):
        grant = await self.claim()
        async with self.sessions.begin() as s:
            await SmartReminderPreferencesService(s).patch(SmartReminderActor(1,'telegram',telegram_id=3001),
                SmartReminderPatch(request_id=str(uuid4()),expected_revision=2,master_enabled=False))
        self.enabled=False
        self.tick=self.expiry+timedelta(microseconds=1)
        result,_ = await self.receipt(grant,'client_outcome_unknown')
        self.assertEqual(result['outcome'],'client_outcome_unknown')
        self.assertEqual((await self.rows(ATTEMPT))[0]['state'],'unknown')

    async def test_definite_client_decline_is_not_an_alternate_grant_or_daily_budget_refund(self):
        grant = await self.claim()
        await self.receipt(grant,'client_declined_before_post')
        self.assertEqual((await self.rows(ATTEMPT))[0]['state'],'confirmed_not_displayed')
        self.assertFalse((await self.claim())['dispatch_allowed'])
        self.assertEqual(len(await self.rows(GRANT)),1)

    async def test_other_device_session_epoch_and_owner_cannot_claim_or_ack(self):
        await self.claim(uid=2,status=404)
        grant = await self.claim()
        _,body = await self.receipt(grant,body=dict(version=1,grant_id=grant['grant_id'],receipt_id=str(uuid4()),
            local_epoch=str(uuid4()),outcome='client_posted_unverified'),status=404)
        await self.receipt(grant,uid=2,status=404)
        async with self.sessions.begin() as s:
            s.add(DesktopSession(id='replacement-session',device_id='device-1',refresh_token_hash='synthetic-replacement',
                expires_at=self.now+timedelta(days=1)))
        async with self.sessions() as s:
            token,_ = DesktopAuthService(s,self.settings)._access_token(
                desktop_session=await s.get(DesktopSession,'replacement-session'),device=await s.get(DesktopDevice,'device-1'))
        response = await self.client.post(f'{BASE}/jobs/{self.job_id}/receipt',headers={'Authorization':'Bearer '+token},json=body|{'local_epoch':self.epoch})
        self.assertEqual(response.status_code,404,response.text)

    async def test_current_off_denied_stale_epoch_and_incomplete_learning_fail_closed(self):
        for changes in ({'capability_generation':2},{'preference_revision':1},{'grant_epoch':0}):
            await self.claim(self.body(**changes),status=409)
        self.coverage=False
        self.assertFalse((await self.claim())['dispatch_allowed'])
        self.coverage=True
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderCapability).values(study_notifications_allowed=False))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_android_consent_and_manual_telegram_override_are_not_bypassed_by_other_channel(self):
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderConsent).where(SmartReminderConsent.channel=='android').values(state='off'))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_manual_telegram_choice_overrides_positive_android_capability(self):
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1)
                .values(channel_mode='manual_locked',preferred_channel='telegram'))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_native_only_learner_needs_no_telegram_identity(self):
        async with self.sessions.begin() as s: await s.execute(update(User).where(User.id==1).values(telegram_id=None))
        self.assertTrue((await self.claim())['dispatch_allowed'])

    async def test_incomplete_runtime_registration_cannot_be_enabled_by_a_switch(self):
        for key in ('admission_reader','calibration','coverage_reader'):
            self.options={key:None}
            self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_expired_unknown_or_autonomous_capability_never_gets_a_grant(self):
        for changes in ({'study_notifications_allowed':None},{'autonomous_study_disabled':False},
            {'protocol_version':0},{'observed_at':self.tick-timedelta(minutes=2),'expires_at':self.tick-timedelta(minutes=1)}):
            async with self.sessions.begin() as s:
                await s.execute(update(SmartReminderCapability).where(SmartReminderCapability.device_id=='device-1')
                    .values(protocol_version=1,study_notifications_allowed=True,autonomous_study_disabled=True,
                        observed_at=self.tick-timedelta(seconds=1),expires_at=self.expiry))
                await s.execute(update(SmartReminderCapability).where(SmartReminderCapability.device_id=='device-1').values(**changes))
            self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_verified_goal_current_access_and_course_are_rechecked(self):
        with patch('app.services.smart_reminder_policy_context.LessonAccessService.status',
                   new=AsyncMock(return_value={'allowed':False})):
            result=await self.claim()
        self.assertEqual(result['reason'],'target_inaccessible')
        async with self.sessions.begin() as s: await s.execute(update(JOB).where(JOB.c.id==self.job_id).values(state='pending'))
        await self.study(order=5,xp=20)
        async with self.sessions.begin() as s:
            await s.execute(update(CourseXpEvent).where(CourseXpEvent.user_id==1,
                CourseXpEvent.activity_ref=='v3-part:hsk1:5:complete').values(created_at=self.tick,activity_date=self.tick.date()))
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id==1,
                CourseMiniAppEvent.event_name=='lesson_completed',CourseMiniAppEvent.lesson_order==5).values(created_at=self.tick))
        self.assertEqual((await self.claim())['reason'],'goal_completed')
        await self.no_grant()

    async def test_d1_control_and_treatment_both_preserve_holdout(self):
        for arm in ('control','treatment'):
            async with self.sessions.begin() as s:
                await s.execute(delete(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name=='d1_recovery_assigned'))
                await s.execute(update(JOB).where(JOB.c.id==self.job_id).values(state='pending'))
                s.add(CourseMiniAppEvent(user_id=1,event_name='d1_recovery_assigned',source='d1_recovery_v1',
                    payload_json='{"arm":"'+arm+'"}',created_at=self.tick))
            self.assertEqual((await self.claim())['reason'],'d1_holdout_active')
        await self.no_grant()

    async def test_known_legacy_android_contact_prevents_another_same_day_attempt(self):
        async with self.sessions.begin() as s:
            await s.execute(update(AndroidPushToken).where(AndroidPushToken.device_id=='device-1')
                .values(last_study_push_day=self.tick.date().isoformat()))
        self.assertEqual((await self.claim())['reason'],'legacy_study_already_attempted')
        await self.no_grant()

    async def test_new_installation_or_session_invalidates_prior_fencing_review(self):
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id='new-install',user_id=1,platform='android',
                installation_key_hash='synthetic-new-install',app_version='synthetic'))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        async with self.sessions.begin() as s:
            await s.execute(delete(DesktopDevice).where(DesktopDevice.id=='new-install'))
            s.add(DesktopSession(id='new-session',device_id='device-1',refresh_token_hash='synthetic-extra-session',
                expires_at=self.now+timedelta(days=1)))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_expiry_during_grant_persistence_withholds_response_and_keeps_tombstone(self):
        def wait(connection,cursor,statement,parameters,context,many):
            if statement.startswith('INSERT INTO smart_reminder_android_grants'): self.tick=self.expiry
        event.listen(self.engine.sync_engine,'before_cursor_execute',wait)
        try: result=await self.claim()
        finally: event.remove(self.engine.sync_engine,'before_cursor_execute',wait)
        self.assertEqual(result['reason'],'android_expired_before_response')
        self.assertFalse(result['dispatch_allowed'])
        self.assertNotIn('grant_id',result)
        self.assertEqual(len(await self.rows(GRANT)),1)
        self.assertEqual((await self.rows(ATTEMPT))[0]['state'],'cancelled')
        self.assertFalse((await self.claim())['dispatch_allowed'])

    async def test_window_expiry_during_validation_is_checked_again_before_issuance(self):
        original=self.learning
        async def slow(session,actor,since,now):
            result=await original(session,actor,since,now)
            self.tick=self.expiry
            return result
        self.options={'coverage_reader':slow}
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_grant_deadline_cannot_cross_upcoming_quiet_boundary(self):
        boundary=self.tick.replace(second=0,microsecond=0)+timedelta(minutes=1)
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1).values(
                quiet_start=boundary.time().replace(tzinfo=None),
                quiet_end=(boundary+timedelta(hours=1)).time().replace(tzinfo=None)))
        grant=await self.claim()
        self.assertTrue(grant['dispatch_allowed'],grant)
        self.assertLessEqual(datetime.fromisoformat(grant['expires_at']),boundary)

    async def test_review_binds_sticky_hold_owner_device_session_generation_and_expiry(self):
        for change in ({'user_id':2},{'device_id':'device-2'},{'session_id':'other-session'},
            {'generation':2},{'preference_revision':3},{'grant_epoch':2},{'valid_until':self.tick}):
            self.review_changes=change
            self.assertFalse((await self.claim())['dispatch_allowed'])
        self.review_changes={}
        async with self.sessions.begin() as s:
            await s.execute(delete(SmartReminderRouting))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_default_real_router_cannot_activate_even_with_positive_capability_and_job(self):
        app=FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=self.sessions,settings_obj=self.settings))
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://default.test') as client:
            headers=await self.bearer(1)
            due=await client.get(BASE+'/due',headers=headers)
            claim=await client.post(f'{BASE}/jobs/{self.job_id}/claim',headers=headers,json=self.body())
            self.assertFalse(due.json()['dispatch_allowed'])
            self.assertFalse(claim.json()['dispatch_allowed'])
        await self.no_grant()

    async def test_malformed_and_forged_payloads_are_refused_before_state_change(self):
        for change in ({'version':True},{'capability_generation':True},{'local_epoch':'invalid'},
            {'device_id':'device-2'},{'user_id':2},{'admission':True},{'verified_shown':True}):
            await self.claim(self.body(**change),status=422)
        response=await self.client.post(f'{BASE}/jobs/{self.job_id}/claim',headers={'Content-Type':'application/json'},content='{')
        self.assertEqual(response.status_code,401)
        headers=(await self.bearer(1))|{'Content-Type':'application/json'}
        response=await self.client.post(f'{BASE}/jobs/{self.job_id}/claim',headers=headers,content='{"version":1,"version":1}')
        self.assertEqual(response.status_code,422)
        await self.no_grant()

    async def test_revocation_deletion_and_blocked_state_refuse_claim_and_receipt(self):
        grant=await self.claim()
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopSession).where(DesktopSession.id=='session-1').values(revoked_at=self.now))
        await self.receipt(grant,status=401)
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopSession).where(DesktopSession.id=='session-1').values(revoked_at=None))
            await s.execute(update(User).where(User.id==1).values(status='blocked'))
        await self.receipt(grant,status=403)
        async with self.sessions.begin() as s: await s.execute(update(User).where(User.id==1).values(status='active'))
        await self._deletion(active_uid=1,owner=1)
        await self.receipt(grant,status=409)

    async def test_two_installations_same_account_only_selected_session_can_claim_or_receipt(self):
        await self.second_installation()
        other=await self.client.get(BASE+'/due',headers=await self.bearer(2))
        self.assertEqual(other.status_code,200)
        self.assertNotIn('job_id',other.json())
        grant=await self.claim()
        self.assertTrue(grant['dispatch_allowed'],grant)
        await self.claim(uid=2,status=404)
        await self.receipt(grant,uid=2,status=404)
        await self.receipt(grant)
        self.assertEqual(len(await self.rows(GRANT)),1)
        self.assertEqual(len(await self.rows(ATTEMPT)),1)

    async def test_unknown_other_installation_is_excluded_even_with_latest_version_metadata(self):
        await self.second_installation(capable=False)
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopDevice).where(DesktopDevice.id=='device-2').values(app_version='999.999.999'))
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_second_installation_permission_loss_invalidates_old_review_without_an_alternate(self):
        await self.second_installation()
        old_review=self.inventory
        headers=await self.bearer(2)
        response=await self.client.patch(BASE+'/capability',headers=headers,json=dict(
            expected_generation=1,protocol_version=1,autonomous_study_disabled=True,study_notifications_allowed=False))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.inventory,old_review)  # The reviewed snapshot is intentionally stale.
        self.assertFalse((await self.claim())['dispatch_allowed'])
        await self.no_grant()

    async def test_mode_is_read_only_sticky_observation_and_not_authority(self):
        headers = await self.bearer(1)
        response = await self.client.get(BASE+'/mode', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.json(), dict(ok=True, version=1, dispatch_allowed=False, server_claim_required=True))
        other = await self.client.get(BASE+'/mode', headers=await self.bearer(2))
        self.assertEqual(other.status_code, 200)
        self.assertFalse(other.json()['server_claim_required'])
        await self.no_grant()
        async with self.sessions.begin() as s:
            await s.execute(delete(SmartReminderRouting))
            await s.execute(update(SmartReminderCapability).values(autonomous_study_disabled=False))
        self.assertFalse((await self.client.get(BASE+'/mode',headers=headers)).json()['server_claim_required'])
        async with self.sessions.begin() as s:
            # Old positive observation stays sticky even after its TTL expires.
            await s.execute(update(SmartReminderCapability).values(autonomous_study_disabled=True,expires_at=self.tick))
        self.assertTrue((await self.client.get(BASE+'/mode',headers=headers)).json()['server_claim_required'])
        self.assertEqual((await self.client.get(BASE+'/mode')).status_code, 401)
        self.assertEqual((await self.client.get(BASE+'/mode?user_id=2',headers=headers)).status_code, 422)

    async def test_schema_matches_and_populated_downgrade_refuses_while_purge_cascades(self):
        async with self.engine.begin() as c:
            diffs=await c.run_sync(lambda sync:compare_metadata(MigrationContext.configure(sync),Base.metadata))
            self.assertEqual(diffs,[])
        await self.claim()
        with self.assertRaisesRegex(RuntimeError,'Retain Android'):
            async with self.engine.begin() as c: await c.run_sync(self.migrate,'downgrade')
        async with self.sessions.begin() as s: await s.execute(delete(User).where(User.id==1))
        self.assertEqual(await self.rows(GRANT),[])
        async with self.engine.begin() as c:
            await c.run_sync(self.migrate,'downgrade')
            await c.run_sync(self.migrate,'upgrade')

    async def test_session_cleanup_retains_issuance_tombstone_and_uncertain_attempt(self):
        await self.claim()
        async with self.sessions.begin() as s: await s.execute(delete(DesktopSession).where(DesktopSession.id=='session-1'))
        self.assertIsNone((await self.rows(GRANT))[0]['session_id'])
        self.assertEqual((await self.rows(ATTEMPT))[0]['state'],'in_flight')

    async def test_two_native_triggers_receive_only_one_committed_grant(self):
        if not self.postgres: self.skipTest('PostgreSQL independent claim transactions')
        headers=await self.bearer(1)
        async def send():
            return await self.client.post(f'{BASE}/jobs/{self.job_id}/claim',headers=headers,json=self.body())
        responses=await asyncio.wait_for(asyncio.gather(send(),send()),10)
        self.assertEqual([r.status_code for r in responses],[200,200])
        self.assertEqual(sum(r.json()['dispatch_allowed'] for r in responses),1)
        self.assertEqual(len(await self.rows(GRANT)),1)

    async def test_postgres_off_queued_first_wins_over_waiting_claim(self):
        if not self.postgres: self.skipTest('PostgreSQL User lock ordering')
        headers=await self.bearer(1)
        waiting=asyncio.Event()
        def capture(connection,cursor,statement,parameters,context,many):
            if 'users.id' in statement and 'FOR UPDATE' in statement: waiting.set()
        task=None
        try:
            async with self.sessions.begin() as s:
                await s.execute(select(User.id).where(User.id==1).with_for_update())
                event.listen(self.engine.sync_engine,'before_cursor_execute',capture)
                task=asyncio.create_task(self.client.post(f'{BASE}/jobs/{self.job_id}/claim',headers=headers,json=self.body()))
                await asyncio.wait_for(waiting.wait(),5)
                await SmartReminderPreferencesService(s).patch(SmartReminderActor(1,'telegram',telegram_id=3001),
                    SmartReminderPatch(request_id=str(uuid4()),expected_revision=2,master_enabled=False))
            result=await asyncio.wait_for(task,10)
            self.assertEqual(result.status_code,200,result.text)
            self.assertFalse(result.json()['dispatch_allowed'])
            await self.no_grant()
        finally:
            event.remove(self.engine.sync_engine,'before_cursor_execute',capture)
            if task and not task.done(): task.cancel()

    async def test_postgres_conflicting_receipts_are_serialized(self):
        if not self.postgres: self.skipTest('PostgreSQL independent receipt transactions')
        grant=await self.claim()
        headers=await self.bearer(1)
        async def send(outcome):
            return await self.client.post(f'{BASE}/jobs/{self.job_id}/receipt',headers=headers,json=dict(
                version=1,grant_id=grant['grant_id'],receipt_id=str(uuid4()),local_epoch=self.epoch,outcome=outcome))
        results=await asyncio.wait_for(asyncio.gather(send('client_posted_unverified'),send('client_declined_before_post')),10)
        self.assertEqual(sorted(r.status_code for r in results),[200,409])


class SQLiteAndroidProtocolTests(AndroidChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL,'Set disposable loopback SMART_REMINDER_TEST_DATABASE_URL')
class PostgreSQLAndroidProtocolTests(AndroidChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
