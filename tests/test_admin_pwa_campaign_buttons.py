"""Exact reviewed campaign destinations; no real recipient or provider IO."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_campaigns as api, pwa_marketing as marketing
from app.bot.keyboards.promo_button import default_promo_button_text, decode_promo_button_config
from app.db.models.ad_campaign import AdCampaign
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_outbound import AdminPwaOutboundJob as Job
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.support_contact_service import ADMIN_CONTACT_KEY
from tests import test_admin_pwa_payment_review as fixtures, test_admin_pwa_settings_postgres as pg
from tests import test_admin_pwa_campaigns as campaign_fixtures

LABELS = {'uz': 'Kursni ochish 中文', 'ru': 'Открыть курс <тест>', 'tj': 'Кушодани курс'}
BUTTON = {'action': 'url', 'labels': LABELS, 'url': 'https://example.invalid/course?a=1&b=2'}


class CampaignButtonTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    prepare = campaign_fixtures.CampaignTests.prepare
    proof = campaign_fixtures.CampaignTests.proof
    execute = campaign_fixtures.CampaignTests.execute
    dispatch = campaign_fixtures.CampaignTests.dispatch
    ad = campaign_fixtures.CampaignTests.ad

    async def contact(self, value):
        async with self.sessions() as db:
            await BotSettingRepository(db).set(ADMIN_CONTACT_KEY, value)
            await db.commit()

    async def read(self, campaign_id):
        async with self.sessions() as db:
            return (await api.read_campaigns(db, session_cookie=fixtures.COOKIE,
                request=api.CampaignRead(kind='ad', campaign_id=campaign_id), settings_obj=self.settings))['campaign']

    async def test_real_signed_url_delivers_exact_localized_markup_once_and_redacts_audit(self):
        campaign_id = await self.ad(button_config=json.dumps(BUTTON, ensure_ascii=False))
        async with self.sessions() as db:
            (await db.get(User, 2)).language = 'ru'
            await db.commit()
        detail = await self.read(campaign_id)
        self.assertTrue(detail['can_send'])
        for lang in LABELS:
            self.assertEqual(detail['buttons'][lang]['inline_keyboard'][0][0],
                             {'text': LABELS[lang], 'url': BUTTON['url']})
        command = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        self.assertEqual(detail['revision_hash'], command.expected_hash)
        saved = await self.execute(command, await self.proof(command, signed=True))
        async def send(message):
            self.assertEqual(message.reply_markup['inline_keyboard'][0][0],
                             {'text': LABELS['ru'], 'url': BUTTON['url']})
        emitter = AsyncMock(side_effect=send)
        await self.dispatch(saved['job_id'], emitter)
        await self.dispatch(saved['job_id'], emitter)
        emitter.assert_awaited_once()
        async with self.sessions() as db:
            audit = await db.get(AdminPwaCommandAudit, saved['command_id'])
            self.assertNotIn('example.invalid', audit.result_json)
            self.assertNotIn(LABELS['ru'], audit.result_json)

    async def test_contact_change_before_save_is_stale_but_later_changes_cannot_replace_snapshot(self):
        await self.contact('@first_contact')
        campaign_id = await self.ad(button_config='{"action":"contact"}')
        first_detail = await self.read(campaign_id)
        first = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        proof = await self.proof(first)
        await self.contact('@second_contact')
        second_detail = await self.read(campaign_id)
        self.assertNotEqual(first_detail['revision_hash'], second_detail['revision_hash'])
        with self.assertRaises(api.CommandError) as stale:
            await self.execute(first, proof)
        self.assertEqual(stale.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 0)
        second = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        saved = await self.execute(second, await self.proof(second, signed=True))
        await self.contact('@third_contact')
        async def send(message):
            button = message.reply_markup['inline_keyboard'][0][0]
            self.assertEqual(button['url'], 'https://t.me/second_contact')
            self.assertEqual(button['text'], default_promo_button_text('contact', message.language))
        statements = []
        def observe(conn, cursor, sql, parameters, context, many):
            statements.append(sql)
        event.listen(self.engine.sync_engine, 'before_cursor_execute', observe)
        emitter = AsyncMock(side_effect=send)
        try:
            await self.dispatch(saved['job_id'], emitter)
        finally:
            event.remove(self.engine.sync_engine, 'before_cursor_execute', observe)
        emitter.assert_awaited_once()
        self.assertFalse(any('bot_settings' in statement for statement in statements))

    async def test_button_draft_is_exact_signed_paused_configuration_without_provider_work(self):
        change = {'kind': 'campaign_draft', 'title': 'QA buttons', 'languages': ['ru'],
                  'texts': {'uz': 'QA UZ', 'ru': 'QA RU', 'tj': 'QA TJ'}, 'button': BUTTON}
        async with self.sessions() as db:
            prepared = await marketing.prepare_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.PrepareMarketing(change=change), settings_obj=self.settings)
        command = marketing.MarketingCommand.model_validate(prepared['execute_payload'])
        proof = await self.proof(command, signed=True)
        tampered = command.model_copy(update={'change': marketing.CampaignDraftChange.model_validate(
            change | {'button': BUTTON | {'url': 'https://evil.invalid/'}})})
        async with self.sessions() as db:
            with self.assertRaises(api.CommandError) as denied:
                await marketing.execute_marketing(db, session_cookie=fixtures.COOKIE,
                    request=marketing.ExecuteMarketing(**tampered.model_dump(), step_up_id=proof),
                    settings_obj=self.settings)
        self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            result = await marketing.execute_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.ExecuteMarketing(**command.model_dump(), step_up_id=proof), settings_obj=self.settings)
        async with self.sessions() as db:
            row = await db.get(AdCampaign, result['result']['id'])
            self.assertEqual(decode_promo_button_config(row.button_config), BUTTON)
            self.assertFalse(row.is_active)
            self.assertIsNone(row.next_send_at)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 0)

    async def test_unsafe_legacy_button_is_visible_but_cannot_authorize_send(self):
        for button in ({'action': 'url', 'url': 'http://legacy.invalid'},
                       {'action': 'url', 'url': 'javascript:alert(1)'}, {'action': 'unknown'}):
            campaign_id = await self.ad(button_config=json.dumps(button))
            self.assertFalse((await self.read(campaign_id))['can_send'])
            with self.assertRaises(api.CommandError):
                await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})

    def test_strict_button_input_rejects_injection_and_partial_or_overlong_labels(self):
        for value in ({'action': 'arbitrary'}, BUTTON | {'callback_data': 'payments:approve:1'},
                      BUTTON | {'url': 'https://user:secret@example.invalid/'}, BUTTON | {'url': 'tg://resolve?domain=test'},
                      BUTTON | {'url': 'https://example.invalid/\nheader'}, BUTTON | {'url': 'javascript:alert(1)'},
                      BUTTON | {'labels': {'uz': 'partial'}}, BUTTON | {'labels': LABELS | {'ru': '😀'*33}},
                      {'action': 'profile', 'url': 'https://example.invalid'}, {'action': 'url'}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                marketing.CampaignButton.model_validate(value)
        self.assertEqual(marketing.CampaignButton(action='url', url='@qa_course_bot').url,
                         'https://t.me/qa_course_bot')


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'), 'requires isolated PostgreSQL')
class CampaignButtonPostgresTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare = campaign_fixtures.CampaignTests.prepare
    proof = campaign_fixtures.CampaignTests.proof
    execute = campaign_fixtures.CampaignTests.execute
    ad = campaign_fixtures.CampaignTests.ad
    contact = CampaignButtonTests.contact

    async def test_contact_writer_lock_and_recheck_reject_stale_destination(self):
        await self.contact('@first_contact')
        campaign_id = await self.ad(button_config='{"action":"contact"}')
        command = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        proof = await self.proof(command)
        waiting = asyncio.Event()
        original = BotSettingRepository.lock_key
        async def observe(repo, key):
            if key == ADMIN_CONTACT_KEY and asyncio.current_task().get_name() == 'button-save':
                waiting.set()
            return await original(repo, key)
        async with self.sessions() as writer:
            async with writer.begin():
                await BotSettingRepository(writer).lock_key(ADMIN_CONTACT_KEY)
                await BotSettingRepository(writer).set(ADMIN_CONTACT_KEY, '@second_contact')
                with patch.object(BotSettingRepository, 'lock_key', observe):
                    saving = asyncio.create_task(self.execute(command, proof), name='button-save')
                    await asyncio.wait_for(waiting.wait(), 3)
            with self.assertRaises(api.CommandError) as stale:
                await saving
            self.assertEqual(stale.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 0)
