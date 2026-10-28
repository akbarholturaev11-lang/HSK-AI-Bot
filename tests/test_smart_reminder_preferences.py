"""Real auth/HTTP/CAS, migration and bot interaction tests on isolated engines."""
import asyncio
import hashlib
import hmac
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import time as walltime
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, insert, select, update

from app.api.android_push import create_android_push_router
from app.api.smart_reminder import create_smart_reminder_router
from app.bot.handlers.course import course_set_reminder_time_handler, course_cancel_reminder_setup_handler
from app.bot.utils.smart_reminder import INTERACTION_KEY, smart_reminder_time_keyboard
from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderJob, SmartReminderAttempt, SmartReminderMutation
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.desktop_auth_service import DesktopAuthService
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderPatch, SmartReminderPreferencesService
from tests import test_smart_reminder_legacy_backfill as fixtures

PREF, CONSENT = fixtures.PREF, fixtures.CONSENT
MUTATION = SmartReminderMutation.__table__
# The repository's Alembic package is not a Python package; load the actual file.
from importlib.util import spec_from_file_location, module_from_spec
_spec = spec_from_file_location('smart_mutation_migration', Path(__file__).resolve().parents[1] / 'alembic/versions/0134_smart_reminder_mutations.py')
MIGRATION = module_from_spec(_spec)
_spec.loader.exec_module(MIGRATION)
TG = '/api/v3/smart-reminder/preferences'
ANDROID = '/api/v3/android/smart-reminder/preferences'


class State:
    def __init__(self): self.data = {}
    async def get_data(self): return self.data.copy()
    async def update_data(self, **values): self.data.update(values)


class PreferenceChecks:
    postgres = False
    _progress = fixtures.BackfillChecks._progress
    _deletion = fixtures.BackfillChecks._deletion
    _rows = fixtures.BackfillChecks._rows

    @staticmethod
    def migrate(c, operation):
        with Operations.context(MigrationContext.configure(c)):
            getattr(MIGRATION, operation)()

    async def asyncSetUp(self):
        await fixtures.BackfillChecks.asyncSetUp(self)
        async with self.engine.begin() as c:
            await c.run_sync(MUTATION.drop)
            await c.run_sync(self.migrate, 'upgrade')
        self.settings = SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET='smart-preference-test-only-'+'x'*40,
                                        BOT_TOKEN='123456789:synthetic-smart-preference-only', BOT_USERNAME='test_bot')
        async with self.sessions.begin() as s:
            for uid in (1, 2, 3):
                s.add(DesktopDevice(id=f'device-{uid}', user_id=uid, telegram_id=3001 if uid==1 else None,
                                    installation_key_hash=f'synthetic-{uid}', platform='android', app_version='qa'))
            await s.flush()
            for uid in (1, 2, 3):
                s.add(DesktopSession(id=f'session-{uid}', device_id=f'device-{uid}', refresh_token_hash=f'synthetic-refresh-{uid}',
                                     expires_at=self.now+timedelta(days=1)))
        app = FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=self.sessions, settings_obj=self.settings))
        app.include_router(create_android_push_router(session_factory=self.sessions, settings_obj=self.settings))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='https://smart.test')

    async def asyncTearDown(self):
        await self.client.aclose()
        await fixtures.BackfillChecks.asyncTearDown(self)

    async def bearer(self, uid=2):
        async with self.sessions() as s:
            token, _ = DesktopAuthService(s, self.settings)._access_token(
                desktop_session=await s.get(DesktopSession, f'session-{uid}'), device=await s.get(DesktopDevice, f'device-{uid}'))
        return {'Authorization': 'Bearer '+token}

    def telegram(self, *, age=0, uid=3001):
        params={'auth_date':str(int(walltime.time())-age), 'user':json.dumps({'id':uid})}
        check='\n'.join(f'{k}={v}' for k,v in sorted(params.items()))
        key=hmac.new(b'WebAppData', self.settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        params['hash']=hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
        return {'X-Telegram-Init-Data':urlencode(params)}

    def body(self, revision=0, **changes):
        return dict(request_id=str(uuid4()), expected_revision=revision) | changes

    async def send(self, body, *, tg=False, uid=2, status=200):
        response=await self.client.patch(TG if tg else ANDROID, json=body,
                                         headers=self.telegram() if tg else await self.bearer(uid))
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response.json()

    async def read(self, *, tg=False, uid=2, status=200):
        response=await self.client.get(TG if tg else ANDROID,
                                       headers=self.telegram() if tg else await self.bearer(uid))
        self.assertEqual(response.status_code,status,response.text)
        self.assertEqual(response.headers['cache-control'],'no-store')
        return response.json()

    async def assert_no_grants(self):
        for model in (SmartReminderJob, SmartReminderAttempt):
            self.assertEqual(await self._rows(model.__table__), [])

    async def test_reads_are_read_only_dual_views_and_native_has_no_telegram_enrollment(self):
        await self._progress()
        tg=await self.read(tg=True)
        native=await self.read()
        self.assertEqual(tg['revision'],0)
        self.assertTrue(tg['effective_master_enabled'])
        self.assertEqual(tg['legacy_time_local'],'14:00:00')
        self.assertFalse(tg['dispatch_allowed'])
        self.assertFalse(native['channels']['telegram']['transport_available'])
        self.assertFalse(native['effective_master_enabled'])
        self.assertEqual(await self._rows(PREF),[])
        self.assertEqual(await self._rows(CONSENT),[])
        self.assertEqual(await self._rows(MUTATION),[])

    async def test_same_account_shared_revision_and_stale_on_cannot_override_off(self):
        await self._progress()
        ack=await self.send(self.body(master_enabled=False),tg=True)
        self.assertEqual(ack['applied_revision'],1)
        android=await self.read(uid=1)
        self.assertFalse(android['master_enabled'])
        self.assertEqual(android['revision'],1)
        conflict=await self.send(self.body(master_enabled=True),uid=1,status=409)
        self.assertEqual(conflict['revision'],1)
        self.assertFalse((await self.read(tg=True))['master_enabled'])
        self.assertEqual((await self._rows(PREF))[0]['grant_epoch'],1)
        await self.assert_no_grants()

    async def test_retry_returns_original_ack_even_after_later_off_without_restoring_state(self):
        original=self.body(master_enabled=True)
        ack=await self.send(original)
        self.assertEqual(await self.send(original),ack)
        await self.send(self.body(1,master_enabled=False))
        self.assertEqual(await self.send(original),ack)
        current=await self.read()
        self.assertEqual(current['revision'],2)
        self.assertFalse(current['master_enabled'])
        self.assertEqual(len(await self._rows(MUTATION)),2)

    async def test_retry_identity_cannot_change_body_or_authenticated_actor(self):
        original=self.body(master_enabled=True)
        await self.send(original,tg=True)
        await self.send(original | {'master_enabled':False},tg=True,status=409)
        await self.send(original,uid=1,status=409)
        self.assertEqual((await self.read(tg=True))['revision'],1)

    async def test_master_on_creates_no_channel_consent_and_endpoint_off_survives(self):
        await self.send(self.body(master_enabled=True))
        current=await self.read()
        self.assertFalse(current['effective_master_enabled'])
        self.assertEqual(current['channels']['android']['this_device_consent'],'unknown')
        await self.send(self.body(1,study_enabled=False))
        await self.send(self.body(2,master_enabled=True))
        current=await self.read()
        self.assertFalse(current['effective_master_enabled'])
        self.assertEqual(current['channels']['android']['this_device_consent'],'off')
        self.assertEqual((await self.read(tg=True))['revision'],0)

    async def test_current_endpoint_on_resolves_legacy_only_and_never_creates_os_capability(self):
        await self._progress(enabled=False)
        await self.send(self.body(study_enabled=True),tg=True)
        self.assertEqual((await self.read(tg=True))['channels']['telegram']['consent'],'on')
        await self.send(self.body(study_enabled=True))
        current=await self.read()
        self.assertEqual(current['channels']['android']['this_device_consent'],'on')
        self.assertEqual(current['channels']['android']['study_os_permission'],'unknown')
        self.assertFalse(current['channels']['android']['eligible'])
        self.assertFalse(current['channels']['telegram']['transport_available'])
        self.assertFalse(current['dispatch_allowed'])
        await self.assert_no_grants()

    async def test_known_os_denial_is_retained_and_unrelated_owner_is_untouched(self):
        from app.db.models.smart_reminder import SmartReminderCapability
        async with self.sessions.begin() as s:
            s.add(SmartReminderCapability(device_id='device-2',user_id=2,study_notifications_allowed=False))
            await s.execute(insert(PREF).values(user_id=3,master_enabled=False,revision=7,grant_epoch=9))
        await self.send(self.body(study_enabled=True))
        self.assertEqual((await self.read())['channels']['android']['study_os_permission'],'denied')
        other=[r for r in await self._rows(PREF) if r['user_id']==3][0]
        self.assertEqual((other['revision'],other['grant_epoch'],other['master_enabled']),(7,9,False))

    async def test_strict_payload_rejections_leave_no_partial_import_or_receipt(self):
        invalid=[{}, {'master_enabled':'true'}, {'master_enabled':1}, {'master_enabled':None},
                 {'study_enabled':None}, {'expected_revision':True,'master_enabled':False},
                 {'expected_revision':0.0,'master_enabled':False}, {'user_id':3,'master_enabled':True},
                 {'device_id':'device-3','study_enabled':True}, {'timezone_name':'Not/A_Zone'},
                 {'timezone_name':None}, {'time_mode':'manual_locked'}, {'manual_time_local':'12:00'},
                 {'time_mode':'manual_locked','manual_time_local':'25:00','timezone_name':'Etc/UTC'},
                 {'channel_mode':'manual_locked'}, {'preferred_channel':'telegram'},
                 {'quiet_start':'22:00'}, {'quiet_start':'22:00','quiet_end':None},
                 {'quiet_start':'02:00','quiet_end':'02:00'}, {'pause_until':'2026-10-29T10:00:00'},
                 {'master_enabled':True,'unexpected':'x'}, {'master_enabled':True,'request_id':'bad'}]
        for changes in invalid:
            with self.subTest(changes=changes):
                await self.send(self.body(**changes),status=422)
        for table in (PREF,CONSENT,MUTATION): self.assertEqual(await self._rows(table),[])

    async def test_json_duplicates_media_and_size_are_rejected(self):
        headers=await self.bearer()
        raw=json.dumps(self.body(master_enabled=False))[:-1]+',"master_enabled":true}'
        for content, kind, expected in ((raw,'application/json',422), ('{}','text/plain',415),
                                         ('x'*4097,'application/json',413), ('[]','application/json',422)):
            response=await self.client.patch(ANDROID,content=content,headers=headers | {'Content-Type':kind})
            self.assertEqual(response.status_code,expected,response.text)
        self.assertEqual(await self._rows(PREF),[])

    async def test_manual_time_channel_quiet_and_pause_are_deliberate_and_clearable(self):
        body=self.body(time_mode='manual_locked',manual_time_local='02:00',timezone_name='Asia/Kathmandu',
                       channel_mode='manual_locked',preferred_channel='android',quiet_start='03:00',quiet_end='04:00',
                       pause_until='2026-10-29T08:00:00+05:45')
        await self.send(body)
        current=await self.read()
        self.assertEqual(current['manual_time_local'],'02:00:00')
        self.assertEqual(current['timezone_name'],'Asia/Kathmandu')
        self.assertEqual(current['time_mode'],'manual_locked')
        self.assertEqual(current['preferred_channel'],'android')
        await self.send(self.body(1,time_mode='auto',channel_mode='auto',quiet_start=None,quiet_end=None,pause_until=None))
        current=await self.read()
        for key in ('manual_time_local','preferred_channel','quiet_start','quiet_end','pause_until'): self.assertIsNone(current[key])

    async def test_bad_auth_stale_proof_and_owner_parameters_are_denied(self):
        for path,headers in ((TG,{}),(ANDROID,{}),(TG,self.telegram(age=86401)),(TG,self.telegram(age=-120)),
                             (TG,self.telegram(uid=9999)),(TG,self.telegram() | await self.bearer(1)),
                             (ANDROID,await self.bearer() | self.telegram()),
                             (TG,{'X-Telegram-Init-Data':self.telegram()['X-Telegram-Init-Data']+'&user=%7B%7D'})):
            response=await self.client.get(path,headers=headers)
            self.assertIn(response.status_code,(401,404),response.text)
        response=await self.client.get(ANDROID+'?user_id=3',headers=await self.bearer())
        self.assertEqual(response.status_code,422)
        self.assertEqual(await self._rows(PREF),[])

    async def test_revoked_expired_foreign_session_and_desktop_platform_are_denied(self):
        changes=[(DesktopDevice,{'revoked_at':self.now},401),
                 (DesktopSession,{'revoked_at':self.now},401),
                 (DesktopSession,{'expires_at':self.now-timedelta(seconds=1)},401),
                 (DesktopDevice,{'user_id':3},401),(DesktopDevice,{'platform':'windows'},403)]
        headers=await self.bearer()
        for model,values,status in changes:
            with self.subTest(values=values):
                async with self.sessions.begin() as s:
                    before=dict((await s.execute(select(model.__table__).where(model.id==('device-2' if model is DesktopDevice else 'session-2')))).mappings().one())
                    await s.execute(update(model).where(model.id==before['id']).values(**values))
                response=await self.client.get(ANDROID,headers=headers)
                self.assertEqual(response.status_code,status,response.text)
                async with self.sessions.begin() as s:
                    await s.execute(update(model).where(model.id==before['id']).values(**{k:before[k] for k in values}))
        self.assertEqual(await self._rows(PREF),[])

    async def test_current_block_unknown_status_and_submitted_deletion_are_denied(self):
        for status in ('blocked','unknown'):
            async with self.sessions.begin() as s:
                await s.execute(update(User).where(User.id==2).values(status=status))
            await self.read(status=403)
            await self.send(self.body(master_enabled=True),status=403)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==2).values(status='free'))
        await self._deletion(owner=2,active_uid=2)
        await self.read(status=409)
        await self.send(self.body(master_enabled=True),status=409)
        self.assertEqual(await self._rows(PREF),[])

    async def test_legacy_push_response_and_motivation_stay_independent_after_smart_off(self):
        from app.db.models.android_push import AndroidPushToken
        async with self.sessions.begin() as s:
            s.add(AndroidPushToken(device_id='device-2',token='synthetic-private-token-only',study_reminders_enabled=False,timezone_name='Etc/UTC'))
            s.add(CourseMiniAppProfile(user_id=2))
        await self.send(self.body(master_enabled=False))
        before=(await self._rows(PREF),await self._rows(CONSENT))
        response=await self.client.post('/api/v3/android/push/preferences',headers=await self.bearer(),
                                        json={'study_reminders_enabled':True,'timezone_name':'Asia/Tashkent','notifications_allowed':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json(),{'ok':True})
        self.assertEqual((await self._rows(PREF),await self._rows(CONSENT)),before)
        async with self.sessions() as s: self.assertTrue(await s.scalar(select(CourseMiniAppProfile.notifications_enabled).where(CourseMiniAppProfile.user_id==2)))

    async def test_caller_rollback_no_autoflush_and_account_purge_preserve_other_receipt(self):
        actor=SmartReminderActor(2,'android',device_id='device-2',session_id='session-2')
        async with self.sessions() as s:
            pending=CourseMiniAppProfile(user_id=3);s.add(pending)
            await SmartReminderPreferencesService(s).patch(actor,SmartReminderPatch(**self.body(master_enabled=False)))
            self.assertIn(pending,s.new)
            await s.rollback()
        self.assertEqual(await self._rows(PREF),[])
        self.assertEqual(await self._rows(MUTATION),[])
        await self.send(self.body(master_enabled=False))
        await self.send(self.body(master_enabled=True),uid=3)
        async with self.sessions.begin() as s:
            self.assertTrue(await UserRepository(s).delete_by_user_id(2))
        receipts=await self._rows(MUTATION)
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]['user_id'],3)

    async def test_real_receipt_migration_matches_model_and_refuses_populated_downgrade(self):
        async with self.engine.begin() as c:
            def diff(sync):
                ctx=MigrationContext.configure(sync,opts={'compare_server_default':True,
                    'include_object':lambda obj,name,kind,reflected,other:kind!='table' or name==MUTATION.name})
                return compare_metadata(ctx,Base.metadata)
            self.assertEqual(await c.run_sync(diff),[])
            await c.run_sync(self.migrate,'downgrade')
            self.assertEqual(await c.scalar(select(User.id).where(User.id==2)),2)
            await c.run_sync(self.migrate,'upgrade')
        await self.send(self.body(master_enabled=False))
        async with self.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError,'Archive Smart mutation receipts'):
                await c.run_sync(self.migrate,'downgrade')
        self.assertEqual(len(await self._rows(MUTATION)),1)

    async def test_bot_fence_current_callback_retry_cancel_and_unbound_callback(self):
        await self._progress(enabled=False,selected=time(9))
        await self.send(self.body(master_enabled=True),tg=True)
        state=State()
        async with self.sessions() as s:
            keyboard=await smart_reminder_time_keyboard(s,state,1,'uz')
        data=keyboard.inline_keyboard[0][1].callback_data
        self.assertLessEqual(len(data.encode()),64)
        callback=SimpleNamespace(from_user=SimpleNamespace(id=3001),data=data,answer=AsyncMock(),message=SimpleNamespace())
        with patch('app.bot.handlers.course.edit_callback_workflow_message',new=AsyncMock()):
            async with self.sessions() as s:
                await course_set_reminder_time_handler(callback,state,s)
        self.assertEqual((await self.read(tg=True))['revision'],2)
        async with self.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(reminder_enabled=False))
        async with self.sessions() as s:
            await course_set_reminder_time_handler(callback,state,s)
        async with self.sessions() as s:
            self.assertFalse((await s.get(CourseProgress,1)).reminder_enabled)
        callback.data='course:reminder_time:20:00'
        async with self.sessions() as s:
            await course_set_reminder_time_handler(callback,state,s)
        self.assertEqual((await self.read(tg=True))['revision'],2)
        with patch('app.bot.handlers.course.edit_callback_workflow_message',new=AsyncMock()):
            async with self.sessions() as s:
                await course_cancel_reminder_setup_handler(callback,state,s)
        self.assertIsNone(state.data[INTERACTION_KEY])
        self.assertEqual((await self.read(tg=True))['revision'],2)

    async def test_off_after_picker_creation_rejects_old_callback_without_legacy_on(self):
        await self._progress(enabled=False)
        await self.send(self.body(master_enabled=True),tg=True)
        state=State()
        async with self.sessions() as s:
            keyboard=await smart_reminder_time_keyboard(s,state,1,'uz')
        await self.send(self.body(1,master_enabled=False),tg=True)
        callback=SimpleNamespace(from_user=SimpleNamespace(id=3001),data=keyboard.inline_keyboard[0][0].callback_data,answer=AsyncMock())
        async with self.sessions() as s:
            await course_set_reminder_time_handler(callback,state,s)
        current=await self.read(tg=True)
        self.assertFalse(current['master_enabled'])
        self.assertEqual(current['revision'],2)
        async with self.sessions() as s: self.assertFalse((await s.get(CourseProgress,1)).reminder_enabled)

    async def test_cached_native_context_does_not_bypass_fresh_revocation_check(self):
        from app.services.smart_reminder_preferences import SmartReminderError
        headers=await self.bearer()
        async with self.sessions() as s:
            context=await DesktopAuthService(s,self.settings).authenticate(headers['Authorization'].split(' ',1)[1])
            actor=SmartReminderActor(context.user.id,'android',device_id=context.device.id,session_id=context.session.id)
            await s.execute(update(DesktopDevice.__table__).where(DesktopDevice.id=='device-2').values(revoked_at=self.now))
            self.assertIsNone(context.device.revoked_at)  # deliberately stale identity map
            with self.assertRaises(SmartReminderError) as caught:
                await SmartReminderPreferencesService(s).patch(actor,SmartReminderPatch(**self.body(master_enabled=True)))
            self.assertEqual(caught.exception.status,401)
            await s.rollback()
        self.assertEqual(await self._rows(PREF),[])

    async def test_bot_legacy_picker_cannot_override_explicit_manual_lock(self):
        await self._progress(enabled=False)
        await self.send(self.body(time_mode='manual_locked',manual_time_local='02:00',timezone_name='Etc/UTC'),tg=True)
        state=State()
        async with self.sessions() as s:
            keyboard=await smart_reminder_time_keyboard(s,state,1,'uz')
        callback=SimpleNamespace(from_user=SimpleNamespace(id=3001),data=keyboard.inline_keyboard[0][0].callback_data,answer=AsyncMock())
        async with self.sessions() as s:
            await course_set_reminder_time_handler(callback,state,s)
        current=await self.read(tg=True)
        self.assertEqual((current['revision'],current['manual_time_local']),(1,'02:00:00'))
        async with self.sessions() as s: self.assertFalse((await s.get(CourseProgress,1)).reminder_enabled)

    async def test_two_requests_with_one_revision_cannot_both_apply(self):
        if not self.postgres: self.skipTest('Requires PostgreSQL independent transactions')
        headers=await self.bearer()
        async def send(body): return await self.client.patch(ANDROID,headers=headers,json=body)
        responses=await asyncio.wait_for(asyncio.gather(send(self.body(master_enabled=False)),send(self.body(master_enabled=True))),10)
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        self.assertEqual(len(await self._rows(MUTATION)),1)
        self.assertEqual((await self.read())['revision'],1)

    async def test_two_identical_retries_apply_only_once(self):
        if not self.postgres: self.skipTest('Requires PostgreSQL independent transactions')
        headers=await self.bearer();body=self.body(master_enabled=False)
        async def send(): return await self.client.patch(ANDROID,headers=headers,json=body)
        responses=await asyncio.wait_for(asyncio.gather(send(),send()),10)
        self.assertEqual([r.status_code for r in responses],[200,200])
        self.assertEqual(responses[0].json(),responses[1].json())
        self.assertEqual(len(await self._rows(MUTATION)),1)
        self.assertEqual((await self.read())['revision'],1)


class SQLiteSmartPreferenceTests(PreferenceChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.PG_URL,'Set disposable loopback SMART_REMINDER_TEST_DATABASE_URL')
class PostgreSQLSmartPreferenceTests(PreferenceChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
