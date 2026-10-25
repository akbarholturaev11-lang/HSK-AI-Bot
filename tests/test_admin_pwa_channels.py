"""Required channels: shared commands, exact proof, bounded reads and CAS."""
import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select

from app.admin_api import pwa_channels as api
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.required_channel import RequiredChannel
from app.services.required_channel_service import RequiredChannelService
from app.repositories.bot_setting_repo import BotSettingRepository
from tests import test_admin_pwa_payment_review as fixtures
from tests import test_admin_pwa_settings as proof_fixtures
from tests import test_admin_pwa_settings_postgres as pg


class ChannelTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    proof=proof_fixtures.AdminPwaSettingsTests.proof

    async def prepare(self,change):
        async with self.sessions() as db:
            result=await api.prepare_channel(db,session_cookie=fixtures.COOKIE,
                request=api.PrepareChannel.model_validate({'change':change}),settings_obj=self.settings)
        return api.ChannelCommand.model_validate(result['operation']['payload'])

    async def execute(self,command,proof):
        async with self.sessions() as db:
            return await api.execute_channel(db,session_cookie=fixtures.COOKIE,
                request=api.ExecuteChannel(**command.model_dump(),step_up_id=proof),settings_obj=self.settings)

    async def test_signed_add_mode_toggle_delete_use_shared_rows_and_content_free_audit(self):
        command=await self.prepare({'kind':'add','chat_id':'-100123','title':'Synthetic channel',
                                   'invite_link':'https://t.me/+PRIVATE_INVITE'})
        proof=await self.proof(command,signed=True);result=await self.execute(command,proof)
        channel_id=result['channel']['id']
        for change in ({'kind':'mode','enabled':True},
                       {'kind':'state','channel_id':channel_id,'is_active':False}):
            command=await self.prepare(change);proof=await self.proof(command)
            await self.execute(command,proof)
        async with self.sessions() as db:
            service=RequiredChannelService(db)
            self.assertTrue(await service.is_enabled())
            self.assertFalse((await db.get(RequiredChannel,channel_id)).is_active)
            audits=(await db.scalars(select(AdminPwaCommandAudit))).all()
            self.assertTrue(all('PRIVATE_INVITE' not in row.result_json and 'Synthetic channel' not in row.result_json for row in audits))
        command=await self.prepare({'kind':'delete','channel_id':channel_id});proof=await self.proof(command)
        result=await self.execute(command,proof)
        self.assertEqual(result['channel'],{'deleted_id':channel_id})
        with self.assertRaises(api.CommandError):
            await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(RequiredChannel,channel_id))

    async def test_alias_aware_legacy_update_invalidates_snapshot_without_duplicate_or_proof_consumption(self):
        command=await self.prepare({'kind':'add','chat_id':'@Test_Channel','title':'PWA title'})
        self.assertEqual(command.change.chat_id,'@test_channel')
        proof=await self.proof(command)
        async with self.sessions() as db:
            await RequiredChannelService(db).add_channel(chat_id='@TEST_CHANNEL',title='Legacy title',
                                                        invite_link=None,created_by_telegram_id=9001)
            await db.commit()
        with self.assertRaises(api.CommandError) as stale:
            await self.execute(command,proof)
        self.assertEqual(stale.exception.status,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(RequiredChannel)),1)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_cross_payload_and_audit_failure_roll_back_setting_and_proof(self):
        command=await self.prepare({'kind':'mode','enabled':True});proof=await self.proof(command)
        changed=api.ChannelCommand(change=api.ChannelMode(kind='mode',enabled=False),expected_hash=command.expected_hash)
        with self.assertRaises(api.CommandError):
            await self.execute(changed,proof)
        with patch.object(api,'AdminPwaCommandAudit',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertFalse(await RequiredChannelService(db).is_enabled())
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)),0)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_read_is_bounded_keyset_no_default_writes_and_strict_transport(self):
        async with self.sessions() as db:
            db.add_all([RequiredChannel(chat_id='@qa'+str(i),title='QA') for i in range(35)])
            await db.commit()
        app=FastAPI();app.include_router(api.create_admin_pwa_channels_router(
            settings_obj=self.settings,session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app',
                headers={'origin':'https://hskai.app'},cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            first=await client.post('/api/admin/v1/channels/read',json={})
            self.assertEqual(first.status_code,200,first.text);self.assertEqual(first.headers['cache-control'],'no-store')
            data=first.json();self.assertEqual(len(data['items']),30)
            second=await client.post('/api/admin/v1/channels/read',json={'before_id':data['next_before_id']})
            self.assertEqual(len(second.json()['items']),5)
            self.assertFalse({r['id'] for r in data['items']} & {r['id'] for r in second.json()['items']})
            self.assertEqual((await client.post('/api/admin/v1/channels/read',json={'limit':999})).status_code,400)
            self.assertEqual((await client.post('/api/admin/v1/channels/read',json={},headers={'origin':'https://evil.invalid'})).status_code,403)
            self.settings.ADMIN_PWA_ENABLED=False
            self.assertEqual((await client.post('/api/admin/v1/channels/read',json={})).status_code,404)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BotSetting)),0)

    async def test_invalid_targets_and_external_invites_are_not_normalized_into_allowed_channels(self):
        for change in ({'kind':'add','chat_id':'https://t.me/name','title':'QA'},
                       {'kind':'add','chat_id':'-100123','title':'QA'},
                       {'kind':'add','chat_id':'@name','title':'QA','invite_link':'https://evil.invalid/name'},
                       {'kind':'add','chat_id':'@name','title':'QA','invite_link':'https://t.me@evil.invalid/name'},
                       {'kind':'add','chat_id':'@name','title':'QA','invite_link':'javascript:alert(1)'},
                       {'kind':'mode','enabled':1},{'kind':'state','channel_id':True,'is_active':True},
                       {'kind':'delete','channel_id':1,'sql':'anything'}):
            with self.assertRaises(ValidationError):
                api.PrepareChannel.model_validate({'change':change})


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires disposable PostgreSQL')
class ChannelPostgresTests(fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare=ChannelTests.prepare
    proof=ChannelTests.proof
    execute=ChannelTests.execute

    async def test_first_add_waits_for_legacy_alias_write_and_rejects_stale_snapshot(self):
        command=await self.prepare({'kind':'add','chat_id':'@test_channel','title':'PWA'})
        proof=await self.proof(command);waiting=asyncio.Event();task=None
        original_lock=BotSettingRepository.lock_key
        async def observe(repo,key):
            if asyncio.current_task().get_name()=='pwa-add-channel':
                waiting.set()
            await original_lock(repo,key)
        try:
            async with self.sessions() as writer:
                async with writer.begin():
                    await RequiredChannelService(writer).add_channel(chat_id='@TEST_CHANNEL',title='Legacy',
                        invite_link=None,created_by_telegram_id=9001)
                    with patch.object(BotSettingRepository,'lock_key',observe):
                        task=asyncio.create_task(self.execute(command,proof),name='pwa-add-channel')
                        await asyncio.wait_for(waiting.wait(),5)
                        self.assertFalse(task.done())
            with self.assertRaises(api.CommandError) as stale:
                await asyncio.wait_for(task,5)
            self.assertEqual(stale.exception.status,409)
            async with self.sessions() as db:
                self.assertEqual((await db.scalar(select(RequiredChannel))).title,'Legacy')
                self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')
        finally:
            if task is not None and not task.done():
                task.cancel();await asyncio.gather(task,return_exceptions=True)
