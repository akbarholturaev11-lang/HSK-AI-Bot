"""Own-device capability HTTP/CAS/lifecycle tests; no provider or real account."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from sqlalchemy import insert, select, update

from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderRouting
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService
from app.services.smart_reminder_capabilities import SmartCapabilityPatch, SmartReminderCapabilityService
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError
from tests import test_smart_reminder_lifecycle as fixtures
from tests.test_smart_reminder_legacy_backfill import PG_URL

CAP = SmartReminderCapability.__table__
URL = '/api/v3/android/smart-reminder/capability'


class CapabilityChecks:
    postgres = False
    asyncSetUp = fixtures.LifecycleChecks.asyncSetUp
    asyncTearDown = fixtures.LifecycleChecks.asyncTearDown
    migrate = staticmethod(fixtures.LifecycleChecks.migrate)
    _rows = fixtures.LifecycleChecks._rows
    _progress = fixtures.LifecycleChecks._progress
    _deletion = fixtures.LifecycleChecks._deletion
    bearer = fixtures.LifecycleChecks.bearer
    telegram = fixtures.LifecycleChecks.telegram
    body = fixtures.LifecycleChecks.body
    send = fixtures.LifecycleChecks.send
    read = fixtures.LifecycleChecks.read
    job = fixtures.LifecycleChecks.job
    attempt = fixtures.LifecycleChecks.attempt

    def observation(self, generation=0, **values):
        return dict(expected_generation=generation, protocol_version=1,
            autonomous_study_disabled=True, study_notifications_allowed=True) | values

    async def report(self, body=None, *, uid=2, status=200):
        response = await self.client.patch(URL, headers=await self.bearer(uid),
            json=self.observation() if body is None else body)
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        return response.json()

    async def capability(self, *, uid=2, status=200):
        response = await self.client.get(URL, headers=await self.bearer(uid))
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response.json()

    async def test_unknown_read_and_positive_observation_create_no_consent_cohort_or_job(self):
        before = await self.capability()
        self.assertEqual(before['generation'], 0)
        self.assertFalse(before['fresh'])
        self.assertIsNone(before['study_notifications_allowed'])
        self.assertEqual(await self._rows(CAP), [])
        result = await self.report()
        self.assertEqual(result['generation'], 1)
        self.assertTrue(result['fresh'])
        self.assertTrue(result['observation_only'])
        self.assertFalse(result['dispatch_allowed'])
        for table in (fixtures.PREF, fixtures.CONSENT, fixtures.JOB, fixtures.ATTEMPT, SmartReminderRouting.__table__):
            self.assertEqual(await self._rows(table), [])
        self.assertEqual(await self.capability(), result)
        self.assertTrue((await self.capability(uid=3))['generation'] == 0)
        self.assertFalse(any(key in result for key in ('user_id', 'device_id', 'session_id', 'token', 'job_id', 'grant')))

    async def test_observation_expiry_is_bounded_by_bearer_and_current_session(self):
        headers = await self.bearer()
        async with self.sessions() as session:
            auth = await DesktopAuthService(session, self.settings).authenticate(headers['Authorization'][7:])
        response = await self.client.patch(URL, headers=headers, json=self.observation())
        self.assertEqual(response.status_code, 200, response.text)
        until = datetime.fromisoformat(response.json()['expires_at'])
        self.assertEqual(until, datetime.fromtimestamp(auth.claims['exp'], timezone.utc))
        shorter = self.now + timedelta(seconds=30)
        async with self.sessions.begin() as session:
            await session.execute(update(DesktopSession).where(DesktopSession.id == 'session-2').values(expires_at=shorter))
        refreshed = await self.report(self.observation(1))
        self.assertEqual(datetime.fromisoformat(refreshed['expires_at']), shorter)

    async def test_expired_observation_is_read_only_and_does_not_clear_known_denial(self):
        await self.report(self.observation(study_notifications_allowed=False))
        async with self.sessions.begin() as session:
            await session.execute(update(CAP).values(observed_at=self.now-timedelta(minutes=2),
                expires_at=self.now-timedelta(minutes=1)))
        before = await self._rows(CAP)
        result = await self.capability()
        self.assertFalse(result['fresh'])
        self.assertIs(result['study_notifications_allowed'], False)
        self.assertEqual(await self._rows(CAP), before)
        async with self.sessions() as session:
            self.assertTrue(await SmartReminderLifecycleService(session).legacy_veto(2, 'android', device_id='device-2'))

    async def test_generation_cas_stops_late_allow_and_unknown_cannot_erase_denial(self):
        await self.report()
        await self.report(self.observation(1, study_notifications_allowed=False))
        before = await self._rows(CAP)
        stale = await self.report(self.observation(1), status=409)
        self.assertEqual(stale['error'], 'smart_capability_generation_conflict')
        unknown = await self.report(self.observation(2, study_notifications_allowed=None), status=409)
        self.assertEqual(unknown['error'], 'smart_capability_denial_unresolved')
        self.assertEqual(await self._rows(CAP), before)
        self.assertEqual((await self.report(self.observation(2)))['generation'], 3)

    async def test_unknown_and_unsupported_are_observations_not_implicit_permission(self):
        result = await self.report(self.observation(protocol_version=0,
            autonomous_study_disabled=None, study_notifications_allowed=None))
        self.assertIsNone(result['study_notifications_allowed'])
        self.assertIsNone(result['autonomous_study_disabled'])
        self.assertFalse(result['dispatch_allowed'])
        self.assertEqual(await self._rows(fixtures.CONSENT), [])

    async def test_loss_revokes_pending_leases_and_preserves_external_outcomes_and_notice_settings(self):
        await self.send(self.body(master_enabled=True, study_enabled=True))
        await self.report()
        pending = self.job(lease=True)
        external = self.job(day=1, state='claimed', lease=True)
        prepared = self.attempt(pending)
        started = self.attempt(external, state='in_flight')
        async with self.sessions.begin() as session:
            for row in (pending, external): await session.execute(insert(fixtures.JOB).values(**row))
            for row in (prepared, started): await session.execute(insert(fixtures.ATTEMPT).values(**row))
            session.add(AndroidPushToken(device_id='device-2', token='synthetic-unusable',
                notifications_allowed=True, study_reminders_enabled=True))
        consent = await self._rows(fixtures.CONSENT)
        before = (await self._rows(fixtures.PREF))[0]
        await self.report(self.observation(1, study_notifications_allowed=False))
        pref = (await self._rows(fixtures.PREF))[0]
        self.assertTrue(pref['master_enabled'])
        self.assertEqual(pref['grant_epoch'], before['grant_epoch'] + 1)
        self.assertEqual(await self._rows(fixtures.CONSENT), consent)
        jobs = {r['id']: r for r in await self._rows(fixtures.JOB)}
        attempts = {r['id']: r for r in await self._rows(fixtures.ATTEMPT)}
        self.assertEqual(jobs[pending['id']]['state'], 'cancelled')
        self.assertIsNone(jobs[external['id']]['lease_token'])
        self.assertEqual(attempts[prepared['id']]['state'], 'cancelled')
        self.assertEqual(attempts[started['id']]['state'], 'in_flight')
        async with self.sessions() as session:
            notice = await session.get(AndroidPushToken, 'device-2')
            self.assertTrue(notice.notifications_allowed)
            self.assertTrue(notice.study_reminders_enabled)
            self.assertTrue(await SmartReminderLifecycleService(session).legacy_veto(2, 'android', device_id='device-2'))

    async def test_positive_report_never_restores_explicit_off(self):
        await self.send(self.body(master_enabled=False, study_enabled=False))
        pref = await self._rows(fixtures.PREF)
        consent = await self._rows(fixtures.CONSENT)
        await self.report()
        self.assertEqual(await self._rows(fixtures.PREF), pref)
        self.assertEqual(await self._rows(fixtures.CONSENT), consent)
        self.assertFalse((await self.read())['effective_master_enabled'])

    async def test_rollback_or_loss_of_autonomous_fence_revokes_pending_authority(self):
        await self.report()
        pending = self.job(lease=True)
        async with self.sessions.begin() as session:
            await session.execute(insert(fixtures.JOB).values(**pending))
        await self.report(self.observation(1, autonomous_study_disabled=False))
        self.assertEqual((await self._rows(fixtures.JOB))[0]['state'], 'cancelled')

    async def test_strict_payload_rejects_forgery_extra_duplicate_missing_and_coerced_values(self):
        invalid = [self.observation(**{key: value}) for key, value in (
            ('expected_generation', True), ('expected_generation', '0'), ('protocol_version', True),
            ('protocol_version', 2), ('study_notifications_allowed', 1), ('autonomous_study_disabled', 'true'),
            ('device_id', 'device-1'), ('user_id', 1), ('session_id', 'session-1'), ('expires_at', '2099-01-01'))]
        invalid.append({k:v for k,v in self.observation().items() if k != 'study_notifications_allowed'})
        for body in invalid:
            with self.subTest(body=body): await self.report(body, status=422)
        headers = await self.bearer()
        for raw in ('{"protocol_version":1,"protocol_version":0}', '{'):
            response = await self.client.patch(URL, headers=headers | {'Content-Type':'application/json'}, content=raw)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self._rows(CAP), [])

    async def test_auth_precedes_payload_and_body_cookie_query_telegram_are_not_native_proof(self):
        response = await self.client.patch(URL, content='{', headers={'Content-Type':'application/json'})
        self.assertEqual(response.status_code, 401)
        for headers in (self.telegram(), (await self.bearer()) | self.telegram(),
            {'Cookie':'Authorization=Bearer fake'}):
            response = await self.client.get(URL, headers=headers)
            self.assertIn(response.status_code, (401,403))
        for method in ('get','patch'):
            response = await getattr(self.client, method)(URL+'?device_id=device-1', headers=await self.bearer())
            self.assertEqual(response.status_code, 422)
        response = await self.client.patch(URL, headers=await self.bearer(), content='{}')
        self.assertEqual(response.status_code, 415)
        response = await self.client.patch(URL, headers=(await self.bearer()) | {'Content-Type':'application/json'}, content='x'*4097)
        self.assertEqual(response.status_code, 413)

    async def test_current_revocation_block_and_deletion_are_rechecked_after_cached_auth(self):
        headers = await self.bearer()
        async with self.sessions() as session:
            cached = await DesktopAuthService(session, self.settings).authenticate(headers['Authorization'][7:])
        for model, condition, values, status in (
            (DesktopSession, DesktopSession.id=='session-2', {'revoked_at':self.now}, 401),
            (DesktopDevice, DesktopDevice.id=='device-2', {'revoked_at':self.now}, 401),
            (User, User.id==2, {'status':'blocked'}, 403)):
            async with self.sessions.begin() as session: await session.execute(update(model).where(condition).values(**values))
            with patch.object(DesktopAuthService, 'authenticate', return_value=cached):
                response = await self.client.patch(URL, headers=headers, json=self.observation())
            self.assertEqual(response.status_code, status, response.text)
            async with self.sessions.begin() as session:
                reset = {'status':'free'} if model is User else {'revoked_at':None}
                await session.execute(update(model).where(condition).values(**reset))
        await self._deletion(active_uid=2, owner=2)
        await self.capability(status=409)
        self.assertEqual(await self._rows(CAP), [])

    async def test_desktop_and_inconsistent_capability_owner_are_refused(self):
        async with self.sessions.begin() as session:
            await session.execute(update(DesktopDevice).where(DesktopDevice.id=='device-2').values(platform='macos'))
        await self.capability(status=403)
        async with self.sessions.begin() as session:
            await session.execute(update(DesktopDevice).where(DesktopDevice.id=='device-2').values(platform='android'))
            await session.execute(insert(CAP).values(device_id='device-2', user_id=1))
        await self.capability(status=409)
        await self.report(status=409)
        self.assertEqual((await self._rows(CAP))[0]['user_id'], 1)

    async def test_internal_write_requires_verified_bearer_deadline(self):
        actor = SmartReminderActor(2, 'android', device_id='device-2', session_id='session-2')
        for expires in (None, self.now.replace(tzinfo=None), self.now-timedelta(seconds=1)):
            with self.subTest(expires=expires), self.assertRaises(SmartReminderError):
                async with self.sessions.begin() as session:
                    await SmartReminderCapabilityService(session).patch(replace(actor,access_expires_at=expires),
                        SmartCapabilityPatch.model_validate(self.observation()))
        self.assertEqual(await self._rows(CAP), [])

    async def test_concurrent_allow_and_deny_cannot_both_overwrite_same_generation(self):
        if not self.postgres: self.skipTest('Requires PostgreSQL independent transactions')
        headers = await self.bearer()
        async def send(allowed):
            return await self.client.patch(URL, headers=headers,
                json=self.observation(study_notifications_allowed=allowed))
        results = await asyncio.wait_for(asyncio.gather(send(True), send(False)), 10)
        self.assertEqual(sorted(r.status_code for r in results), [200,409])
        self.assertEqual(len(await self._rows(CAP)), 1)
        self.assertEqual((await self.capability())['generation'], 1)


class SQLiteSmartCapabilityTests(CapabilityChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL, 'Set disposable loopback SMART_REMINDER_TEST_DATABASE_URL')
class PostgreSQLSmartCapabilityTests(CapabilityChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
