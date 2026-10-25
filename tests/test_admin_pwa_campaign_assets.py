"""Owned staging, exact media commands and bounded provider attempts on isolated SQL."""
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import event, func, inspect, select

from app.admin_api import pwa_campaign_assets as api, pwa_marketing as marketing, pwa_campaigns as campaigns
from app.admin_api.pwa_outbound import dispatch_message_batch
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_campaign_asset import AdminPwaCampaignAsset as Asset
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.admin_api.pwa_step_up import begin_step_up, verify_step_up
from app.db.models.ad_campaign import AdCampaign
from app.db.models.user import User
from app.services.admin_broadcast_service import AdminBroadcastService
from tests import test_admin_pwa_payment_review as fixtures, test_admin_pwa_settings as proofs
from tests import test_admin_pwa_settings_postgres as pg
from tests.test_admin_pwa_webauthn_crypto_vectors import make_assertion

ROOT = Path(__file__).resolve().parents[1]
VIDEO = (ROOT / 'tests/fixtures/admin_pwa_course_ad_test.mp4').read_bytes()


class CampaignAssetTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown
    async def proof(self, command, *, signed=False):
        if not signed:
            return await proofs.AdminPwaSettingsTests.proof(self, command)
        async with self.sessions() as db:
            started = await begin_step_up(db, session_cookie=fixtures.COOKIE,
                settings_obj=self.settings, **command.operation())
        async with self.sessions() as db:
            step = await db.get(AdminPwaStepUp, started.step_up_id)
            count = await db.scalar(select(AdminPwaCredential.sign_count))
            challenge = bytes(step.challenge)
        async with self.sessions() as db:
            self.assertTrue(await verify_step_up(db, session_cookie=fixtures.COOKIE,
                step_up_id=started.step_up_id, settings_obj=self.settings,
                credential=make_assertion(self.key, challenge=challenge, sign_count=count+1)))
        return started.step_up_id

    @staticmethod
    def photo():
        buffer = BytesIO()
        Image.new('RGB', (8, 6), (12, 108, 116)).save(buffer, format='PNG')
        return buffer.getvalue()

    async def post(self, data, *, content_type='image/png', upload=None, cookie=fixtures.COOKIE, origin='https://hskai.app'):
        app = FastAPI()
        app.include_router(api.create_admin_pwa_campaign_assets_router(settings_obj=self.settings,
            session_factory=self.sessions, upload=upload or AsyncMock(return_value='PRIVATE_server_file_id')))
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app') as client:
            return await client.post('/api/admin/v1/campaign-assets', content=data, headers={
                'Content-Type': content_type, 'Origin': origin,
                'Cookie': api.ADMIN_PWA_COOKIE_NAME + '=' + cookie})

    async def ready(self, *, media_type='photo'):
        raw = self.photo() if media_type == 'photo' else VIDEO
        async with self.sessions() as db:
            asset_id, _ = await api.reserve_campaign_upload(db, cookie=fixtures.COOKIE,
                media_type=media_type, content_hash=hashlib.sha256(raw).hexdigest(),
                byte_count=len(raw), settings_obj=self.settings)
        async with self.sessions() as db:
            return await api.finish_campaign_upload(db, cookie=fixtures.COOKIE, asset_id=asset_id,
                file_id='PRIVATE_server_file_id', settings_obj=self.settings)

    def change(self, asset, **overrides):
        return dict(kind='campaign_draft', title='QA media', languages=['uz', 'ru', 'tj'],
            texts={'uz': 'QA <UZ>', 'ru': 'QA 中文 RU', 'tj': 'QA TJ'},
            button={'action': 'course'}, asset_id=asset['asset_id'], asset_hash=asset['asset_hash']) | overrides

    async def command(self, asset):
        async with self.sessions() as db:
            prepared = await marketing.prepare_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.PrepareMarketing(change=self.change(asset)), settings_obj=self.settings)
        return marketing.MarketingCommand.model_validate(prepared['execute_payload'])

    async def execute_asset(self, command, proof):
        async with self.sessions() as db:
            return await marketing.execute_marketing(db, session_cookie=fixtures.COOKIE,
                request=marketing.ExecuteMarketing(**command.model_dump(), step_up_id=proof), settings_obj=self.settings)

    async def test_private_upload_commits_reservation_before_io_and_returns_no_provider_id(self):
        active = 0
        paths = []
        def checkout(*args):
            nonlocal active
            active += 1
        def checkin(*args):
            nonlocal active
            active -= 1
        event.listen(self.engine.sync_engine, 'checkout', checkout)
        event.listen(self.engine.sync_engine, 'checkin', checkin)
        async def upload(media):
            self.assertEqual(active, 0, 'provider IO must not hold a database connection')
            self.assertEqual(media.actor_telegram_id, 9001)
            self.assertEqual(Path(media.path).read_bytes(), self.photo())
            paths.append(media.path)
            async with self.sessions() as db:
                self.assertEqual((await db.scalar(select(Asset))).status, 'uploading')
            return 'PRIVATE_server_file_id'
        try:
            result = await self.post(self.photo(), upload=upload)
        finally:
            event.remove(self.engine.sync_engine, 'checkout', checkout)
            event.remove(self.engine.sync_engine, 'checkin', checkin)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn('no-store', result.headers['cache-control'])
        self.assertNotIn('PRIVATE', result.text)
        self.assertEqual(result.json()['content_hash'], hashlib.sha256(self.photo()).hexdigest())
        self.assertTrue(all(not Path(path).exists() for path in paths))
        async with self.sessions() as db:
            self.assertEqual((await db.scalar(select(Asset))).status, 'ready')
        self.assertTrue(all(column.type.__class__.__name__ != 'LargeBinary' for column in Asset.__table__.columns))

    async def test_real_video_is_bounded_encoded_outside_db_and_not_saved_as_blob(self):
        async def upload(media):
            self.assertEqual(media.media_type, 'video')
            self.assertLessEqual(Path(media.path).stat().st_size, api.VIDEO_MAX)
            self.assertIn(b'ftyp', Path(media.path).read_bytes()[:32])
            return 'PRIVATE_video_file_id'
        sender = AsyncMock(side_effect=upload)
        result = await self.post(VIDEO, content_type='video/mp4', upload=sender)
        self.assertEqual(result.status_code, 200, result.text)
        sender.assert_awaited_once()
        self.assertEqual(result.json()['media_type'], 'video')

    async def test_invalid_and_oversized_files_are_rejected_without_provider_work(self):
        sender = AsyncMock()
        for raw, media, status in ((b'not an image', 'image/png', 400),
                (b'x' * (api.PHOTO_MAX + 1), 'image/png', 413),
                (b'#EXTM3U\nhttp://127.0.0.1:9/private\n', 'video/mp4', 422),
                (b'<svg/>', 'image/svg+xml', 415)):
            with self.subTest(media=media, size=len(raw)):
                result = await self.post(raw, content_type=media, upload=sender)
                self.assertEqual(result.status_code, status, result.text)
        sender.assert_not_awaited()
        denied = await self.post(self.photo(), origin='https://evil.invalid', upload=sender)
        self.assertEqual(denied.status_code, 403)
        denied = await self.post(self.photo(), cookie='invalid', upload=sender)
        self.assertEqual(denied.status_code, 401)

    async def test_provider_uncertainty_is_failed_once_and_cannot_authorize_send(self):
        sender = AsyncMock(side_effect=TimeoutError('PRIVATE provider uncertainty'))
        result = await self.post(self.photo(), upload=sender)
        self.assertEqual(result.status_code, 503)
        sender.assert_awaited_once()
        async with self.sessions() as db:
            row = await db.scalar(select(Asset))
            self.assertEqual(row.status, 'failed')
            with self.assertRaises(api.CommandError):
                await api.owned_campaign_asset(db, cookie=fixtures.COOKIE, asset_id=row.id, settings_obj=self.settings)

    async def test_different_session_even_same_admin_cannot_read_or_use_asset(self):
        asset = await self.ready()
        cookie = 'N' * 64
        async with self.sessions() as db:
            db.add(AdminPwaSession(id=str(uuid4()), user_id=101, auth_method='webauthn',
                token_hash=hashlib.sha256(cookie.encode()).hexdigest(), expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
            await db.commit()
        async with self.sessions() as db:
            with self.assertRaises(api.CommandError):
                await api.owned_campaign_asset(db, cookie=cookie, asset_id=asset['asset_id'], settings_obj=self.settings)
        async with self.sessions() as db:
            with self.assertRaises(api.CommandError):
                await marketing.prepare_marketing(db, session_cookie=cookie,
                    request=marketing.PrepareMarketing(change=self.change(asset)), settings_obj=self.settings)

    async def test_exact_signed_asset_is_consumed_with_draft_then_sent_once_with_its_button(self):
        for media_type in ('photo', 'video'):
            asset = await self.ready(media_type=media_type)
            command = await self.command(asset)
            saved = await self.execute_asset(command, await self.proof(command, signed=True))
            campaign_id = saved['result']['id']
            async with self.sessions() as db:
                row = await db.get(AdCampaign, campaign_id)
                self.assertEqual((row.content_type, row.media_file_id), (media_type, 'PRIVATE_server_file_id'))
                self.assertFalse(row.is_active)
                self.assertEqual((await db.get(Asset, asset['asset_id'])).status, 'used')
                self.assertIsNotNone((await db.get(Asset, asset['asset_id'])).command_id)
            async with self.sessions() as db:
                prepared = await campaigns.prepare_campaign(db, session_cookie=fixtures.COOKIE,
                    request=campaigns.PrepareCampaign(change={'kind': 'ad_send', 'campaign_id': campaign_id}),
                    settings_obj=self.settings)
            send = campaigns.CampaignCommand.model_validate(prepared['execute_payload'])
            async with self.sessions() as db:
                queued = await campaigns.execute_campaign(db, session_cookie=fixtures.COOKIE,
                    request=campaigns.ExecuteCampaign(**send.model_dump(), step_up_id=await self.proof(send)),
                    settings_obj=self.settings)
            async def emit(message):
                self.assertEqual(message.photo_file_id if media_type == 'photo' else message.video_file_id,
                                 'PRIVATE_server_file_id')
                self.assertEqual(message.reply_markup['inline_keyboard'][0][0]['callback_data'], 'promo:action:course')
            emitter = AsyncMock(side_effect=emit)
            await dispatch_message_batch(job_id=queued['job_id'], session_factory=self.sessions, settings_obj=self.settings, emit=emitter)
            await dispatch_message_batch(job_id=queued['job_id'], session_factory=self.sessions, settings_obj=self.settings, emit=emitter)
            emitter.assert_awaited_once()

    async def test_release_media_binds_prompt_and_is_consumed_atomically(self):
        from app.db.models.release_feedback import ReleaseFeedbackCampaign
        for media_type in ('photo', 'video'):
            asset = await self.ready(media_type=media_type)
            change = dict(kind='release_create', title='QA release media',
                texts={'uz':'QA UZ','ru':'QA RU','tj':'QA TJ'},
                asset_id=asset['asset_id'], asset_hash=asset['asset_hash'])
            async with self.sessions() as db:
                prepared = await campaigns.prepare_campaign(db, session_cookie=fixtures.COOKIE,
                    request=campaigns.PrepareCampaign(change=change), settings_obj=self.settings)
            command = campaigns.CampaignCommand.model_validate(prepared['execute_payload'])
            proof = await self.proof(command, signed=True)
            async with self.sessions() as db:
                saved = await campaigns.execute_campaign(db, session_cookie=fixtures.COOKIE,
                    request=campaigns.ExecuteCampaign(**command.model_dump(), step_up_id=proof), settings_obj=self.settings)
            async with self.sessions() as db:
                self.assertEqual((await db.get(Asset, asset['asset_id'])).status, 'used')
                row = await db.get(ReleaseFeedbackCampaign, saved['campaign']['id'])
                self.assertEqual((row.content_type, row.media_file_id), (media_type, 'PRIVATE_server_file_id'))
            emitter = AsyncMock(return_value=123)
            await dispatch_message_batch(job_id=saved['job_id'], session_factory=self.sessions,
                settings_obj=self.settings, emit=emitter)
            await dispatch_message_batch(job_id=saved['job_id'], session_factory=self.sessions,
                settings_obj=self.settings, emit=emitter)
            emitter.assert_awaited_once()
            message = emitter.await_args.args[0]
            self.assertEqual(message.photo_file_id if media_type=='photo' else message.video_file_id, 'PRIVATE_server_file_id')
            self.assertIn('relfb:', json.dumps(message.reply_markup))
        asset = await self.ready()
        async with self.sessions() as db:
            with self.assertRaises(campaigns.CommandError):
                await campaigns.prepare_campaign(db, session_cookie=fixtures.COOKIE,
                    request=campaigns.PrepareCampaign(change=dict(kind='release_create',title='QA',
                        texts={lang:'x'*1024 for lang in ('uz','ru','tj')},
                        asset_id=asset['asset_id'],asset_hash=asset['asset_hash'])), settings_obj=self.settings)

    async def test_audit_failure_preserves_ready_asset_and_proof_and_creates_no_campaign(self):
        asset = await self.ready()
        command = await self.command(asset)
        proof = await self.proof(command)
        def fail(*args):
            raise RuntimeError('synthetic audit failure')
        event.listen(AdminPwaCommandAudit, 'before_insert', fail)
        try:
            with self.assertRaises(RuntimeError):
                await self.execute_asset(command, proof)
        finally:
            event.remove(AdminPwaCommandAudit, 'before_insert', fail)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Asset, asset['asset_id'])).status, 'ready')
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaign)), 0)

    async def test_quota_survives_expired_staging_cleanup_and_referenced_provider_media_is_retained(self):
        assets = [await self.ready() for _ in range(20)]
        sender = AsyncMock()
        result = await self.post(self.photo(), upload=sender)
        self.assertEqual(result.status_code, 429)
        sender.assert_not_awaited()
        async with self.sessions() as db:
            self.assertEqual(await api.purge_expired_campaign_assets(db, now=datetime.now(timezone.utc)+timedelta(minutes=16)), 0)
            await db.commit()
        command = await self.command(assets[0])
        saved = await self.execute_asset(command, await self.proof(command))
        async with self.sessions() as db:
            self.assertEqual(await api.purge_expired_campaign_assets(db, limit=5,
                now=datetime.now(timezone.utc)+timedelta(hours=2)), 5)
            await db.commit()
            self.assertEqual((await db.get(AdCampaign, saved['result']['id'])).media_file_id, 'PRIVATE_server_file_id')

    def test_caption_limits_and_asset_pairs_do_not_accept_provider_references(self):
        asset = {'asset_id': str(uuid4()), 'asset_hash': 'a' * 64}
        for values in (self.change(asset, texts={'uz': '🧪'*600, 'ru': 'ok', 'tj': 'ok'}),
                       self.change(asset, asset_hash=None), self.change(asset, media_file_id='PRIVATE_file')):
            with self.assertRaises(ValidationError):
                marketing.CampaignDraftChange.model_validate(values)


class CampaignProviderAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_sender_returns_media_receipt_and_preserves_markup(self):
        bot = type('Bot', (), {'send_video': AsyncMock(return_value='video-receipt'),
                              'send_photo': AsyncMock(return_value='photo-receipt'),
                              'send_message': AsyncMock(return_value='text-receipt')})()
        service = AdminBroadcastService(bot, None)
        for media, expected in (('photo', 'photo-receipt'), ('video', 'video-receipt'), ('text', 'text-receipt')):
            result = await service._send_one(1001, text='QA', content_type=media,
                media_file_id='PRIVATE_file' if media != 'text' else None, reply_markup='reviewed-markup')
            self.assertEqual(result, expected)
        self.assertEqual(bot.send_video.await_args.kwargs['reply_markup'], 'reviewed-markup')


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'), 'requires isolated PostgreSQL')
class CampaignAssetPostgresTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown = pg.AdminPwaSettingsPostgresTests.asyncTearDown
    ready = CampaignAssetTests.ready
    photo = staticmethod(CampaignAssetTests.photo)
    change = CampaignAssetTests.change
    command = CampaignAssetTests.command
    execute_asset = CampaignAssetTests.execute_asset
    proof = CampaignAssetTests.proof

    async def test_proof_expiry_during_asset_row_wait_rolls_back_asset_campaign_and_audit(self):
        asset = await self.ready()
        command = await self.command(asset)
        proof = await self.proof(command)
        async with self.sessions() as db:
            (await db.get(AdminPwaStepUp, proof)).expires_at = datetime.now(timezone.utc)+timedelta(seconds=2)
            await db.commit()
        waiting = asyncio.Event()
        original = api.owned_campaign_asset
        async def observe(*args, **kwargs):
            if kwargs.get('lock'):
                waiting.set()
            return await original(*args, **kwargs)
        async with self.sessions() as blocker:
            async with blocker.begin():
                await blocker.scalar(select(Asset).where(Asset.id == asset['asset_id']).with_for_update())
                with patch.object(api, 'owned_campaign_asset', observe):
                    saving = asyncio.create_task(self.execute_asset(command, proof))
                    await asyncio.wait_for(waiting.wait(), 3)
                    await asyncio.sleep(2.1)
            with self.assertRaises(api.CommandError) as denied:
                await saving
            self.assertEqual(denied.exception.status, 403)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Asset, asset['asset_id'])).status, 'ready')
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, 'verified')
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdCampaign)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_real_migration_has_exact_metadata_columns_and_refuses_nonempty_downgrade(self):
        import importlib.util
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        spec = importlib.util.spec_from_file_location('campaign_asset_migration', ROOT/'alembic/versions/0131_admin_pwa_campaign_assets.py')
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        await self.ready()
        async with self.engine.begin() as connection:
            def nonempty(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    with self.assertRaisesRegex(RuntimeError, 'Archive campaign asset'):
                        migration.downgrade()
            await connection.run_sync(nonempty)
            await connection.execute(Asset.__table__.delete())
            def recreate(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    migration.downgrade()
                    migration.upgrade()
            await connection.run_sync(recreate)
            columns = await connection.run_sync(lambda sync: {c['name'] for c in inspect(sync).get_columns(Asset.__tablename__)})
            self.assertEqual(columns, set(Asset.__table__.columns.keys()))
