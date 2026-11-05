"""Template review binds every locale without expanding the step-up body limit."""
import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select, text

from app.admin_api import pwa_notifications as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.notification_template import NotificationTemplate
from app.db.models.smart_reminder import SmartReminderRouting
from app.db.models.smart_reminder_analysis import SmartReminderAnalysisMonthly
from app.services.notification_template_service import NotificationTemplateService, default_text
from app.services.smart_reminder_runtime import build_rules_runtime
from app.repositories.bot_setting_repo import BotSettingRepository
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg


class NotificationTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    proof = proofs.AdminPwaSettingsTests.proof

    async def test_smart_readout_only_uses_current_anonymous_month_and_preserves_missing_vs_zero(self):
        month = datetime.now(timezone.utc).date().replace(day=1)
        async with self.sessions.begin() as db:
            db.add_all([SmartReminderAnalysisMonthly(month=month,stage='contact_study_24h',channel=channel,fact_count=count)
                        for channel,count in [('telegram',2),('android',3)]])
            db.add(SmartReminderAnalysisMonthly(month=month,stage='study_day_after_attempt',channel='android',fact_count=0))
            db.add(SmartReminderAnalysisMonthly(month=month-timedelta(days=1),stage='study_unit_24h',channel='android',fact_count=99))
            db.add(SmartReminderAnalysisMonthly(month=month,stage='client_reported_open',channel='android',fact_count=88))
        statements=[]
        def collect(_, __, statement, *args): statements.append(statement.lower())
        event.listen(self.engine.sync_engine,'before_cursor_execute',collect)
        try:
            async with self.sessions() as db:
                result=await api.read_notices(db,session_cookie=fixtures.COOKIE,
                    request=api.NoticeRead(key='smart_study'),settings_obj=self.settings)
        finally: event.remove(self.engine.sync_engine,'before_cursor_execute',collect)
        self.assertEqual(result['smart'],dict(month=month.strftime('%Y-%m'),observation_enabled=False,
            android_ready=False,telegram_ready=False,current_reviews=0,
            rollout=dict(generation=0,stage=0,cohort_count=4,status='waiting',next_stage_at=None,
                heartbeat_at=None,error_at=None,error_code=None),
            counts=dict(study_day_after_attempt=0,contact_study_24h=5,study_unit_24h=None)))
        self.assertTrue(result['template']['enabled'])
        json.dumps(result)  # PostgreSQL SUM(bigint) must also be JSON-safe.
        self.assertFalse(any('smart_reminder_jobs' in q or 'smart_reminder_analysis_events' in q for q in statements))
        self.assertFalse(any(q.lstrip().startswith(('insert ','update ','delete ')) for q in statements))
        self.settings.SMART_REMINDER_ANALYSIS_ENABLED=True
        async with self.sessions() as db:
            on=await api.read_notices(db,session_cookie=fixtures.COOKIE,request=api.NoticeRead(key='smart_study'),settings_obj=self.settings)
        self.assertTrue(on['smart']['observation_enabled'])

    async def test_smart_status_uses_registered_runtime_and_only_unexpired_review_count(self):
        now = datetime.now(timezone.utc)
        async with self.sessions.begin() as db:
            owners = list(await db.scalars(select(api.User.id).order_by(api.User.id).limit(2)))
            self.assertEqual(len(owners), 2)
            for owner, until in zip(owners, (now+timedelta(hours=1), now-timedelta(seconds=1))):
                db.add(SmartReminderRouting(user_id=owner, state='held', generation=1,
                    preference_revision=0, grant_epoch=0, telegram_binding='a'*64,
                    inventory_sha256='b'*64, held_at=now-timedelta(days=2),
                    verified_at=now-timedelta(days=1), verified_until=until, evidence_sha256='c'*64))
        self.settings.SMART_REMINDER_ENABLED = True
        self.settings.SMART_REMINDER_TELEGRAM_ENABLED = False
        app = FastAPI()
        app.include_router(api.create_admin_pwa_notifications_router(settings_obj=self.settings,
            session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app',
                headers={'origin':'https://hskai.app'}, cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            async def read():
                response = await client.post('/api/admin/v1/notifications/read',json={'key':'smart_study'})
                self.assertEqual(response.status_code, 200)
                return response.json()['smart']
            self.assertFalse((await read())['android_ready'])
            runtime = build_rules_runtime(self.settings, self.sessions, object())
            runtime.bind(app)
            app.state.smart_reminder_runtime = runtime
            status = await read()
            self.assertTrue(status['android_ready'])
            self.assertFalse(status['telegram_ready'])
            self.assertEqual(status['current_reviews'], 1)
            self.settings.SMART_REMINDER_TELEGRAM_ENABLED = True
            self.assertTrue((await read())['telegram_ready'])

    async def test_smart_pause_uses_real_signed_cas_and_cannot_be_replayed_or_bypass_revocation(self):
        command=await self.prepare(key='smart_study',enabled=False,text_uz='',text_ru='',text_tj='')
        proof=await self.proof(command,signed=True)
        result=await self.execute(command,proof)
        self.assertFalse(result['template']['enabled'])
        async with self.sessions() as db:
            self.assertFalse(await NotificationTemplateService(db).is_enabled('smart_study'))
        with self.assertRaises(api.CommandError): await self.execute(command,proof)
        command=await self.prepare(key='smart_study',text_uz='',text_ru='',text_tj='')
        proof=await self.proof(command)
        self.settings.admin_id_list=[]
        with self.assertRaises(api.CommandError): await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertFalse(await NotificationTemplateService(db).is_enabled('smart_study'))

    async def test_signed_smart_off_pauses_and_on_restarts_rollout_at_stage_one(self):
        from app.db.models.smart_reminder import SmartReminderRollout
        now=datetime.now(timezone.utc)
        async with self.sessions.begin() as db:
            db.add(SmartReminderRollout(id=1,generation=2,stage=3,status='active',
                stage_started_at=now-timedelta(hours=5),heartbeat_at=now))
        async def state():
            async with self.sessions() as db:
                row=(await db.execute(select(SmartReminderRollout.__table__))).mappings().one()
                return row['generation'],row['stage'],row['status']
        command=await self.prepare(key='smart_study',enabled=False,text_uz='',text_ru='',text_tj='')
        await self.execute(command,await self.proof(command,signed=True))
        self.assertEqual(await state(),(2,3,'paused'))
        command=await self.prepare(key='smart_study',enabled=True,text_uz='',text_ru='',text_tj='')
        await self.execute(command,await self.proof(command))
        self.assertEqual(await state(),(3,1,'active'))
        command=await self.prepare(key='smart_study',enabled=True,text_uz='Dars {lesson}',text_ru='',text_tj='')
        await self.execute(command,await self.proof(command))
        self.assertEqual(await state(),(3,1,'active'))  # Text-only edits keep the stage.

    async def test_smart_template_uses_existing_signed_editor_without_becoming_motivation_trigger(self):
        from app.services.notification_template_service import KEY_SMART_STUDY, MOTIVATION_KEYS, TEMPLATE_KEYS
        self.assertNotIn(KEY_SMART_STUDY, MOTIVATION_KEYS)
        self.assertIn(KEY_SMART_STUDY, TEMPLATE_KEYS)
        command = await self.prepare(key=KEY_SMART_STUDY, text_uz="Dars {lesson}",
                                     text_ru="Урок {lesson}", text_tj="Дарси {lesson}")
        result = await self.execute(command, await self.proof(command, signed=True))
        self.assertEqual(result['template']['effective_texts']['tj'], "Дарси {lesson}")
        with self.assertRaises(ValidationError):
            api.PrepareNotice(key=KEY_SMART_STUDY, enabled=True,
                text_uz="{minutes}", text_ru="", text_tj="")

    async def prepare(self, **overrides):
        values = dict(key='daily_goal', enabled=True, text_uz='PRIVATE {minutes}',
                      text_ru='Минуты: {minutes}', text_tj='Дақиқа: {minutes}') | overrides
        async with self.sessions() as db:
            result = await api.prepare_notice(db, session_cookie=fixtures.COOKIE,
                request=api.PrepareNotice(**values), settings_obj=self.settings)
        return api.NoticeCommand.model_validate(result['execute_payload'])

    async def execute(self, command, proof):
        async with self.sessions() as db:
            return await api.execute_notice(db, session_cookie=fixtures.COOKIE,
                request=api.ExecuteNotice(**command.model_dump(), step_up_id=proof), settings_obj=self.settings)

    async def test_large_three_locale_text_has_compact_real_es256_proof_and_no_plaintext_audit(self):
        command = await self.prepare(text_uz='汉'*2000+' {minutes}', text_ru='я'*2000+' {minutes}',
                                     text_tj='қ'*2000+' {minutes}')
        self.assertGreater(len(command.model_dump_json().encode()), 4096)
        self.assertLess(len(json.dumps(command.operation()).encode()), 4096)
        proof = await self.proof(command, signed=True)
        result = await self.execute(command, proof)
        self.assertEqual(result['template']['effective_texts']['uz'], command.text_uz)
        with self.assertRaises(api.CommandError):
            await self.execute(command, proof)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(NotificationTemplate)), 1)
            audit = await db.get(AdminPwaCommandAudit, result['command_id'])
            self.assertNotIn('汉', audit.result_json)
            self.assertEqual(audit.action, 'notifications.update')

    async def test_actual_content_tamper_and_changed_fallback_cannot_reuse_proof(self):
        command = await self.prepare(text_ru=''); proof = await self.proof(command)
        for changed in (command.model_copy(update={'text_uz':'different {minutes}'}),
                        command.model_copy(update={'enabled':False})):
            with self.assertRaises(api.CommandError) as denied:
                await self.execute(changed, proof)
            self.assertEqual(denied.exception.status, 403)
        with patch.object(api, 'default_text', return_value='new catalog default'):
            with self.assertRaises(api.CommandError) as denied:
                await self.execute(command, proof)
        self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(NotificationTemplate)), 0)

    async def test_blank_uses_shared_default_and_disabled_does_not_change_delivery_semantics(self):
        command = await self.prepare(enabled=False, text_ru='   ')
        result = await self.execute(command, await self.proof(command))
        self.assertEqual(result['template']['effective_texts']['ru'], default_text(command.key, 'ru'))
        async with self.sessions() as db:
            row = await db.scalar(select(NotificationTemplate))
            self.assertIsNone(row.text_ru)
            self.assertIsNone(await NotificationTemplateService(db).resolve(command.key, 'ru'))

    async def test_unsafe_placeholders_and_utf16_caption_limit_are_rejected(self):
        base = dict(key='daily_goal', enabled=True, text_uz='', text_ru='', text_tj='')
        for value in ('{unknown}', '{minutes.__class__}', '{minutes[0]}', '{minutes!r}',
                      '{minutes:9999999999}', '{', '\ud800', '\x00'):
            with self.assertRaises(ValidationError):
                api.PrepareNotice(**(base | {'text_uz':value}))
        async with self.sessions() as db:
            await NotificationTemplateService(db).set_media('daily_goal', media_type='photo', media_path='private.jpg')
            await db.commit()
        with self.assertRaises(api.CommandError) as too_long:
            await self.prepare(text_uz='😀'*513)
        self.assertEqual(str(too_long.exception), 'admin_pwa_notice_too_long')

    async def test_media_or_text_changes_stale_confirmation_and_audit_failure_roll_back(self):
        command = await self.prepare(); proof = await self.proof(command)
        async with self.sessions() as db:
            await NotificationTemplateService(db).set_media(command.key, media_type='video', media_path='private.mp4')
            await db.commit()
        with self.assertRaises(api.CommandError) as stale:
            await self.execute(command, proof)
        self.assertEqual(stale.exception.status, 409)
        command = await self.prepare(); proof = await self.proof(command)
        with patch.object(api, 'AdminPwaCommandAudit', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                await self.execute(command, proof)
        async with self.sessions() as db:
            self.assertIsNone((await db.scalar(select(NotificationTemplate))).text_uz)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')

    async def test_fixed_read_does_not_create_defaults_or_expose_media_and_transport_checks_origin(self):
        async with self.sessions() as db:
            await NotificationTemplateService(db).set_media('daily_goal', media_type='photo', media_path='PRIVATE-PATH.jpg')
            await db.commit()
        app = FastAPI(); app.include_router(api.create_admin_pwa_notifications_router(
            settings_obj=self.settings, session_factory=self.sessions))
        statements = []
        def collect(conn, cursor, statement, parameters, context, many): statements.append(statement.lower())
        event.listen(self.engine.sync_engine, 'before_cursor_execute', collect)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app',
                    headers={'origin':'https://hskai.app'}, cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
                response = await client.post('/api/admin/v1/notifications/read', json={})
                self.assertEqual(len(response.json()['items']), 6)
                response = await client.post('/api/admin/v1/notifications/read', json={'key':'daily_goal'})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['template']['has_media'])
                self.assertNotIn('PRIVATE-PATH', response.text)
                self.assertIn('no-store', response.headers['cache-control'])
                self.assertEqual((await client.post('/api/admin/v1/notifications/read', json={'key':'unknown'})).status_code, 400)
                self.assertEqual((await client.post('/api/admin/v1/notifications/read', json={},
                    headers={'origin':'https://evil.invalid'})).status_code, 403)
                self.settings.admin_id_list = []
                self.assertEqual((await client.post('/api/admin/v1/notifications/read', json={})).status_code, 401)
                self.settings.ADMIN_PWA_ENABLED = False
                self.assertEqual((await client.post('/api/admin/v1/notifications/read', json={})).status_code, 404)
        finally:
            event.remove(self.engine.sync_engine, 'before_cursor_execute', collect)
        self.assertFalse(any(q.lstrip().startswith(('insert ', 'update ', 'delete ')) for q in statements))


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class NotificationPostgresTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare = NotificationTests.prepare
    proof = NotificationTests.proof
    execute = NotificationTests.execute
    test_smart_readout_only_uses_current_anonymous_month_and_preserves_missing_vs_zero = NotificationTests.test_smart_readout_only_uses_current_anonymous_month_and_preserves_missing_vs_zero

    async def test_final_authorization_waits_for_signed_pause_to_commit(self):
        command = await self.prepare(key='smart_study',enabled=False,text_uz='',text_ru='',text_tj='')
        proof = await self.proof(command,signed=True)
        changed = asyncio.Event()
        release = asyncio.Event()
        authorizing = asyncio.Event()
        update = NotificationTemplateService.update_text
        lock = BotSettingRepository.lock_key

        async def wait_before_commit(service,*args,**kwargs):
            row = await update(service,*args,**kwargs)
            changed.set()
            await release.wait()
            return row

        async def observe(repo,key,*,shared=False):
            if shared:
                authorizing.set()
            return await lock(repo,key,shared=shared)

        async def authorize():
            async with self.sessions.begin() as db:
                return await NotificationTemplateService(db).is_enabled('smart_study',authorize=True)

        tasks = []
        try:
            with patch.object(NotificationTemplateService,'update_text',wait_before_commit), \
                    patch.object(BotSettingRepository,'lock_key',observe):
                saving = asyncio.create_task(self.execute(command,proof))
                tasks.append(saving)
                await asyncio.wait_for(changed.wait(), 5)
                checking = asyncio.create_task(authorize())
                tasks.append(checking)
                await asyncio.wait_for(authorizing.wait(), 5)
                async with self.sessions() as probe:
                    async with asyncio.timeout(3):
                        while not await probe.scalar(text(
                                "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory'"
                                " AND mode = 'ShareLock' AND NOT granted AND database = "
                                "(SELECT oid FROM pg_database WHERE datname = current_database()))")):
                            await asyncio.sleep(0.02)
                self.assertFalse(checking.done())
                release.set()
                self.assertFalse((await asyncio.wait_for(saving, 5))['template']['enabled'])
                self.assertFalse(await asyncio.wait_for(checking, 5))
        finally:
            release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)

    async def test_legacy_first_insert_serializes_and_rejects_old_absent_snapshot(self):
        command = await self.prepare(); proof = await self.proof(command)
        waiting = asyncio.Event(); original = BotSettingRepository.lock_key
        async def observe(repo, key):
            if asyncio.current_task().get_name() == 'pwa-notice-save': waiting.set()
            return await original(repo, key)
        task = None
        try:
            async with self.sessions() as legacy:
                async with legacy.begin():
                    await NotificationTemplateService(legacy).update_text(command.key, text_uz='legacy',
                        text_ru='', text_tj='', enabled=True, updated_by=None)
                    with patch.object(BotSettingRepository, 'lock_key', observe):
                        task = asyncio.create_task(self.execute(command, proof), name='pwa-notice-save')
                        await asyncio.wait_for(waiting.wait(), 5)
                        self.assertFalse(task.done())
            with self.assertRaises(api.CommandError) as stale:
                await asyncio.wait_for(task, 5)
            self.assertEqual(stale.exception.status, 409)
            async with self.sessions() as db:
                self.assertEqual((await db.scalar(select(NotificationTemplate))).text_uz, 'legacy')
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
                self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)
        finally:
            if task is not None and not task.done():
                task.cancel(); await asyncio.gather(task, return_exceptions=True)
