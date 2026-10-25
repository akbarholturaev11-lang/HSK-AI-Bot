"""Template review binds every locale without expanding the step-up body limit."""
import asyncio
import json
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_notifications as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.notification_template import NotificationTemplate
from app.services.notification_template_service import NotificationTemplateService, default_text
from app.repositories.bot_setting_repo import BotSettingRepository
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg


class NotificationTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    proof = proofs.AdminPwaSettingsTests.proof

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
                self.assertEqual(len(response.json()['items']), 5)
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
