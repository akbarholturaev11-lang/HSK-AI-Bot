"""Signed campaign configuration and bounded durable provider attempts; no live IO."""
import asyncio
from datetime import datetime, timedelta, timezone
import html
import json
import os
import unittest
from unittest.mock import AsyncMock
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event, func, select

from app.admin_api import pwa_campaigns as api, pwa_outbound as outbound
from app.db.models.ad_campaign import AdCampaign, AdCampaignDelivery
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_outbound import AdminPwaOutboundJob as Job, AdminPwaOutboundRecipient as Recipient
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackDelivery
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.ad_campaign_repo import AdCampaignRepository
from app.services.broadcast_translation_service import encode_localized_broadcast_text
from app.services.discount_service import DiscountService
from tests import test_admin_pwa_payment_review as fixtures, test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg

TEXTS = {'uz': 'Yangi 中文 kurs <test>', 'ru': 'Новый курс <тест>', 'tj': 'Курси нави чинӣ <санҷиш>'}
RELEASE = {'kind': 'release_create', 'title': 'PRIVATE QA release', 'texts': TEXTS,
           'feature_key': 'course', 'filters': {'languages': ['uz', 'ru', 'tj']}}
DISCOUNT = {'kind': 'discount_create', 'copies': {
    lang: {'title': 'PRIVATE ' + lang + ' <offer>', 'reason': 'PRIVATE reason & ' + lang} for lang in TEXTS},
    'percent': 20, 'duration_hours': 24, 'target_user_id': 1, 'quota_total': 1}


class CampaignTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def prepare(self, change):
        async with self.sessions() as db:
            result = await api.prepare_campaign(db, session_cookie=fixtures.COOKIE,
                request=api.PrepareCampaign.model_validate({'change': change}), settings_obj=self.settings)
        return api.CampaignCommand.model_validate(result['execute_payload'])

    async def proof(self, command, *, signed=False):
        return await proofs.AdminPwaSettingsTests.proof(self, command, signed=signed)

    async def execute(self, command, proof):
        async with self.sessions() as db:
            return await api.execute_campaign(db, session_cookie=fixtures.COOKIE,
                request=api.ExecuteCampaign(**command.model_dump(), step_up_id=proof), settings_obj=self.settings)

    async def dispatch(self, job, emit, **kw):
        return await outbound.dispatch_message_batch(job_id=job, session_factory=self.sessions,
            settings_obj=self.settings, emit=emit, **kw)

    async def ad(self, **overrides):
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            row = await AdCampaignRepository(db).create(title='PRIVATE Ad',
                message_text=encode_localized_broadcast_text({lang: html.escape(text, quote=False)
                                                            for lang, text in TEXTS.items()}),
                content_type='text', media_file_id=None, starts_at=now, ends_at=now + timedelta(days=1),
                send_count_total=1, is_active=False, **overrides)
            await db.commit()
            return row.id

    async def test_real_signed_release_has_committed_claim_markup_legacy_evidence_and_no_access_side_effect(self):
        command = await self.prepare(RELEASE)
        self.assertEqual(command.audience_count, 1)
        proof = await self.proof(command, signed=True)
        result = await self.execute(command, proof)
        campaign_id, job_id = result['campaign']['id'], result['job_id']
        async def emit(message):
            self.assertEqual(message.telegram_id, 2002)
            self.assertNotIn('<test>', message.text)
            markup = message.reply_markup['inline_keyboard']
            self.assertEqual(markup[0][0]['callback_data'], f'relfb:{campaign_id}:try')
            self.assertEqual(len(markup[1]), 5)
            async with self.sessions() as db:
                self.assertEqual((await db.get(Recipient, (job_id, 2))).status, 'attempting')
                evidence = await db.scalar(select(ReleaseFeedbackDelivery))
                self.assertEqual(evidence.status, 'attempting')
                self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'consumed')
                self.assertEqual((await db.get(User, 2)).status, 'free')
                self.assertEqual(await db.scalar(select(func.count()).select_from(DiscountCampaign)), 0)
            return 123
        sender = AsyncMock(side_effect=emit)
        await self.dispatch(job_id, sender)
        await self.dispatch(job_id, sender)
        sender.assert_awaited_once()
        async with self.sessions() as db:
            row = await db.get(ReleaseFeedbackCampaign, campaign_id)
            self.assertEqual((row.status, row.sent_count, row.failed_count), ('sent', 1, 0))
            self.assertEqual((row.discount_percent, row.discount_hours, row.trial_access_minutes), (20, 24, 30))
            self.assertEqual(await api.ReleaseFeedbackRepository(db).list_due_campaigns(), [])
            evidence = await db.scalar(select(ReleaseFeedbackDelivery))
            self.assertEqual((evidence.status, evidence.message_id), ('sent', 123))
            audit = await db.get(AdminPwaCommandAudit, result['command_id'])
            self.assertNotIn('PRIVATE', audit.result_json)
            self.assertNotIn(TEXTS['tj'], audit.result_json)
        with self.assertRaises(api.CommandError):
            await self.execute(command, proof)

    async def test_paused_ad_uses_one_shared_reserved_round_and_never_activates_legacy_scheduler(self):
        campaign_id = await self.ad()
        command = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        saved = await self.execute(command, await self.proof(command, signed=True))
        async with self.sessions() as db:
            row = await db.get(AdCampaign, campaign_id)
            self.assertFalse(row.is_active)
            self.assertIsNone(row.next_send_at)
            self.assertEqual(row.rounds_sent, 1)
            self.assertEqual(await AdCampaignRepository(db).list_due(), [])
            self.assertEqual((await db.scalar(select(AdCampaignDelivery))).status, 'pending')
        sender = AsyncMock(side_effect=RuntimeError('PRIVATE provider uncertainty'))
        await self.dispatch(saved['job_id'], sender)
        await self.dispatch(saved['job_id'], sender)
        sender.assert_awaited_once()
        async with self.sessions() as db:
            self.assertEqual((await db.scalar(select(AdCampaignDelivery))).status, 'uncertain')
        with self.assertRaises(api.CommandError):
            await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})

    async def test_native_personal_discount_preserves_identity_no_send_or_fake_payment_and_exact_copy(self):
        command = await self.prepare({**DISCOUNT, 'payment_method': 'visa'})
        proof = await self.proof(command, signed=True)
        saved = await self.execute(command, proof)
        self.assertIsNone(saved['job_id'])
        async with self.sessions() as db:
            row = await db.get(DiscountCampaign, saved['campaign']['id'])
            self.assertEqual(row.target_user_id, 1)
            self.assertIsNone(row.target_telegram_id)
            self.assertFalse(row.notify_enabled)
            self.assertFalse(row.is_active)
            self.assertEqual(row.percent, 20)
            self.assertEqual(row.quota_total, 1)
            self.assertEqual(row.title_ru, DISCOUNT['copies']['ru']['title'])
            self.assertEqual((await db.get(User, 1)).status, 'free')
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 0)
        change = {'kind': 'discount_state', 'campaign_id': saved['campaign']['id'], 'is_active': True}
        command = await self.prepare(change)
        result = await self.execute(command, await self.proof(command))
        self.assertTrue(result['campaign']['is_active'])
        async with self.sessions() as db:
            self.assertEqual(await api.DiscountCampaignRepository(db).list_due_notifications(), [])
            account = await db.get(User, 1)
            selected = await DiscountService(db).get_best_discount(user=account, plan_type='1_month',
                payment_method='visa', include_admin_campaigns=True)
            self.assertEqual((selected.campaign_id, selected.percent), (saved['campaign']['id'], 20))
            self.assertEqual(selected.title_ru, DISCOUNT['copies']['ru']['title'])

    async def test_qr_discount_cannot_be_active_before_exact_campaign_qr_upload(self):
        command = await self.prepare({**DISCOUNT, 'payment_method': 'alipay', 'plan_type': '1_month'})
        saved = await self.execute(command, await self.proof(command, signed=True))
        change = {'kind': 'discount_state', 'campaign_id': saved['campaign']['id'], 'is_active': True}
        command = await self.prepare(change)
        with self.assertRaisesRegex(api.CommandError, 'admin_pwa_payment_qr_required'):
            await self.execute(command, await self.proof(command))
        async with self.sessions() as db:
            row = await db.get(DiscountCampaign, saved['campaign']['id'])
            self.assertFalse(row.is_active)

    async def test_stale_state_and_audience_and_tampered_copy_preserve_proof_and_prevent_writes(self):
        command = await self.prepare(RELEASE)
        proof = await self.proof(command)
        tampered = command.model_copy(update={'change': api.ReleaseCreate(**(RELEASE | {'title': 'altered'}))})
        with self.assertRaises(api.CommandError) as denied:
            await self.execute(tampered, proof)
        self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            (await db.get(User, 2)).language = 'ru'
            await db.commit()
        with self.assertRaises(api.CommandError) as denied:
            await self.execute(command, proof)
        self.assertEqual(denied.exception.status, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(ReleaseFeedbackCampaign)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 0)

    async def test_filter_drift_or_legacy_edit_skips_before_claim_without_provider_io(self):
        campaign_id = await self.ad(target_track='hsk20')
        command = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        saved = await self.execute(command, await self.proof(command))
        async with self.sessions() as db:
            (await db.get(User, 2)).level = 'nhsk1'
            await db.commit()
        sender = AsyncMock()
        await self.dispatch(saved['job_id'], sender)
        sender.assert_not_awaited()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Recipient, (saved['job_id'], 2))).status, 'skipped')
        command = await self.prepare(RELEASE)
        saved = await self.execute(command, await self.proof(command))
        async with self.sessions() as db:
            (await db.get(ReleaseFeedbackCampaign, saved['campaign']['id'])).feature_key = 'image'
            await db.commit()
        await self.dispatch(saved['job_id'], sender)
        sender.assert_not_awaited()

    async def test_audit_failure_rolls_back_shared_campaign_proof_job_and_delivery(self):
        command = await self.prepare(RELEASE)
        proof = await self.proof(command)
        def fail(*args):
            raise RuntimeError('synthetic audit unavailable')
        event.listen(AdminPwaCommandAudit, 'before_insert', fail)
        try:
            with self.assertRaises(RuntimeError):
                await self.execute(command, proof)
        finally:
            event.remove(AdminPwaCommandAudit, 'before_insert', fail)
        async with self.sessions() as db:
            for model in (Job, ReleaseFeedbackCampaign, ReleaseFeedbackDelivery, AdminPwaCommandAudit):
                self.assertEqual(await db.scalar(select(func.count()).select_from(model)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')

    async def test_bounded_audience_rejects_1001_and_reads_project_only_one_metadata_page(self):
        async with self.sessions() as db:
            db.add_all([User(telegram_id=3000+i, status='free') for i in range(1001)])
            await db.commit()
        with self.assertRaises(api.CommandError) as denied:
            await self.prepare(RELEASE)
        self.assertEqual(str(denied.exception), 'admin_pwa_message_too_many_targets')
        sql = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            sql.append(statement)
        event.listen(self.engine.sync_engine, 'before_cursor_execute', capture)
        try:
            async with self.sessions() as db:
                page = await api.read_campaigns(db, session_cookie=fixtures.COOKIE,
                    request=api.CampaignRead(kind='discount'), settings_obj=self.settings)
        finally:
            event.remove(self.engine.sync_engine, 'before_cursor_execute', capture)
        self.assertEqual(page['items'], [])
        query = next(statement for statement in sql if 'FROM discount_campaigns' in statement)
        self.assertIn('LIMIT', query)
        self.assertNotIn('reason', query)
        self.assertNotIn('notify_media_file_id', query)

    async def test_stop_and_retention_do_not_resend_or_erase_content_free_audit(self):
        command = await self.prepare(RELEASE)
        saved = await self.execute(command, await self.proof(command))
        async with self.sessions() as db:
            await outbound.stop_message(db, session_cookie=fixtures.COOKIE,
                request=outbound.RunMessage(job_id=saved['job_id']), settings_obj=self.settings)
        sender = AsyncMock()
        await self.dispatch(saved['job_id'], sender)
        sender.assert_not_awaited()
        async with self.sessions() as db:
            self.assertEqual((await db.get(ReleaseFeedbackCampaign, saved['campaign']['id'])).status, 'stopped')
            self.assertEqual((await db.scalar(select(ReleaseFeedbackDelivery))).status, 'skipped')
            async with db.begin_nested():
                await outbound.purge_expired_message_jobs(db, now=datetime.now(timezone.utc)+timedelta(hours=2))
            await db.commit()
            self.assertIsNone(await db.get(Job, saved['job_id']))
            self.assertIsNotNone(await db.get(AdminPwaCommandAudit, saved['command_id']))

    async def test_stop_during_claim_preserves_one_late_provider_ack_without_authorizing_more(self):
        command = await self.prepare(RELEASE)
        saved = await self.execute(command, await self.proof(command))
        async def send(message):
            async with self.sessions() as db:
                await outbound.stop_message(db, session_cookie=fixtures.COOKIE,
                    request=outbound.RunMessage(job_id=saved['job_id']), settings_obj=self.settings)
            return 789
        sender = AsyncMock(side_effect=send)
        await self.dispatch(saved['job_id'], sender)
        await self.dispatch(saved['job_id'], sender)
        sender.assert_awaited_once()
        async with self.sessions() as db:
            row = await db.get(ReleaseFeedbackCampaign, saved['campaign']['id'])
            self.assertEqual((row.status, row.sent_count, row.failed_count), ('stopped', 1, 0))
            evidence = await db.scalar(select(ReleaseFeedbackDelivery))
            self.assertEqual((evidence.status, evidence.message_id), ('sent', 789))

    async def test_changed_transport_skips_the_original_legacy_reservation(self):
        campaign_id = await self.ad()
        command = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        saved = await self.execute(command, await self.proof(command))
        async with self.sessions() as db:
            (await db.get(User, 2)).telegram_id = 9999
            await db.commit()
        sender = AsyncMock()
        await self.dispatch(saved['job_id'], sender)
        sender.assert_not_awaited()
        async with self.sessions() as db:
            row = await db.scalar(select(AdCampaignDelivery))
            self.assertEqual((row.user_telegram_id, row.status), (2002, 'skipped'))

    async def test_http_origin_body_cookie_and_default_flags_fail_closed(self):
        app = FastAPI()
        app.include_router(api.create_admin_pwa_campaigns_router(settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app') as client:
            headers = {'Origin': 'https://hskai.app', 'Cookie': 'hsk_admin_pwa='+fixtures.COOKIE}
            # Use the actual canonical cookie name, not an alternate auth mechanism.
            headers['Cookie'] = api.ADMIN_PWA_COOKIE_NAME + '=' + fixtures.COOKIE
            response = await client.post('/api/admin/v1/campaigns/prepare', headers=headers, json={'change': RELEASE})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('no-store', response.headers['cache-control'])
            foreign = await client.post('/api/admin/v1/campaigns/prepare',
                headers=headers | {'Origin': 'https://evil.invalid'}, json={'change': RELEASE})
            self.assertEqual(foreign.status_code, 403)
            self.settings.ADMIN_PWA_ENABLED = False
            denied = await client.post('/api/admin/v1/campaigns/read', headers=headers, json={'kind': 'ad'})
            self.assertEqual(denied.status_code, 404)

    def test_strict_payload_disallows_arbitrary_assets_schedules_scopes_and_implicit_translation(self):
        invalid = [RELEASE | {'media_file_id': 'PRIVATE'}, RELEASE | {'send_at': 'tomorrow'},
                   RELEASE | {'texts': {'uz': 'only one'}}, RELEASE | {'feature_key': 'arbitrary'},
                   DISCOUNT | {'percent': 91}, DISCOUNT | {'percent': True}, DISCOUNT | {'notify_enabled': True},
                   DISCOUNT | {'target_telegram_id': 1}, DISCOUNT | {'audience_status': 'free'},
                   DISCOUNT | {'duration_hours': 721}, DISCOUNT | {'plan_type': 'invented'},
                   DISCOUNT | {'copies': {**DISCOUNT['copies'], 'ru': {'title': '&'*121}}}]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                api.PrepareCampaign.model_validate({'change': change})


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'), 'requires isolated PostgreSQL test URL')
class CampaignPostgresTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare = CampaignTests.prepare
    proof = CampaignTests.proof
    execute = CampaignTests.execute
    dispatch = CampaignTests.dispatch
    ad = CampaignTests.ad

    async def test_two_valid_proofs_cannot_queue_the_same_ad_round_twice(self):
        campaign_id = await self.ad()
        command = await self.prepare({'kind': 'ad_send', 'campaign_id': campaign_id})
        first, second = await self.proof(command), await self.proof(command)
        results = await asyncio.gather(self.execute(command, first), self.execute(command, second), return_exceptions=True)
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(sum(isinstance(result, api.CommandError) for result in results), 1)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaignDelivery)), 1)
            self.assertEqual((await db.get(AdCampaign, campaign_id)).rounds_sent, 1)

    async def test_proof_expiring_during_recipient_lock_wait_rolls_back_everything(self):
        command = await self.prepare(RELEASE)
        proof = await self.proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaStepUp, proof)).expires_at = datetime.now(timezone.utc)+timedelta(seconds=2)
            await db.commit()
        waiting = asyncio.Event()
        original = UserRepository.get_filtered_users
        async def observe(repo, **kwargs):
            if kwargs.get('for_update'):
                waiting.set()
            return await original(repo, **kwargs)
        async with self.sessions() as blocker:
            async with blocker.begin():
                await blocker.scalar(select(User).where(User.id == 2).with_for_update())
                with patch.object(UserRepository, 'get_filtered_users', observe):
                    saving = asyncio.create_task(self.execute(command, proof))
                    await asyncio.wait_for(waiting.wait(), 4)
                    await asyncio.sleep(2.1)
            with self.assertRaises(api.CommandError) as denied:
                await saving
            self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(ReleaseFeedbackCampaign)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Job)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')

    async def test_two_drainers_commit_one_release_claim_before_io(self):
        command = await self.prepare(RELEASE)
        saved = await self.execute(command, await self.proof(command))
        entered, release = asyncio.Event(), asyncio.Event()
        async def emit(message):
            entered.set()
            await asyncio.wait_for(release.wait(), 3)
            return 456
        sender = AsyncMock(side_effect=emit)
        first = asyncio.create_task(self.dispatch(saved['job_id'], sender))
        await asyncio.wait_for(entered.wait(), 3)
        self.assertFalse(await self.dispatch(saved['job_id'], sender))
        release.set()
        await first
        sender.assert_awaited_once()
        async with self.sessions() as db:
            row = await db.get(ReleaseFeedbackCampaign, saved['campaign']['id'])
            self.assertEqual((row.status, row.sent_count), ('sent', 1))
