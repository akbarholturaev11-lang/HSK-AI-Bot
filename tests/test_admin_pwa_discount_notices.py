"""Signed discount notices preserve shared checkout and Android/Play delivery."""
import asyncio
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import event, func, select

from app.admin_api import pwa_campaigns as api, pwa_discount_notices as notices, pwa_outbound as outbound
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_outbound import AdminPwaOutboundJob as Job, AdminPwaOutboundRecipient as Recipient
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.android_push_service import AndroidPushService, AndroidPushResult
from app.services.discount_service import DiscountService
from app.services.notification_delivery_service import NotificationDeliveryService, TelegramNotice
from tests import test_admin_pwa_campaigns as fixtures, test_admin_pwa_settings_postgres as pg


class DiscountNoticeTests(fixtures.fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.CampaignTests.asyncSetUp
    asyncTearDown=fixtures.CampaignTests.asyncTearDown
    prepare=fixtures.CampaignTests.prepare
    proof=fixtures.CampaignTests.proof
    execute=fixtures.CampaignTests.execute

    async def offer(self, **overrides):
        command=await self.prepare(fixtures.DISCOUNT|{'target_user_id':2,'is_active':True}|overrides)
        result=await self.execute(command,await self.proof(command))
        return result['campaign']['id']

    async def queued(self, campaign_id):
        command=await self.prepare({'kind':'discount_send','campaign_id':campaign_id})
        return await self.execute(command,await self.proof(command))

    async def device(self, user_id=1, *, allowed=True):
        self.settings.ANDROID_PUSH_NOTICES_ENABLED=True
        self.settings.ANDROID_FCM_PROJECT_ID='synthetic-project'
        key=str(uuid4())
        async with self.sessions() as db:
            db.add(DesktopDevice(id=key,user_id=user_id,telegram_id=None,installation_key_hash=key,
                platform='android',app_version='1.0'))
            await db.flush()
            db.add(AndroidPushToken(device_id=key,token='synthetic-'+key,notifications_allowed=allowed))
            await db.commit()
        return key

    async def test_exact_single_notice_is_claimed_before_io_and_never_grants_access(self):
        campaign_id=await self.offer()
        result=await self.queued(campaign_id)
        async def emit(message):
            self.assertEqual(message.notice_key,'discount_offer')
            self.assertEqual((message.user_id,message.telegram_id),(2,2002))
            self.assertIn('&lt;offer&gt;',message.text)
            self.assertIn('PRIVATE reason &amp;',message.text)
            self.assertNotIn('PRIVATE',str(message.reply_markup))
            async with self.sessions() as db:
                self.assertEqual((await db.get(Recipient,(result['job_id'],2))).status,'attempting')
                self.assertFalse((await db.get(DiscountCampaign,campaign_id)).notify_enabled)
        sender=AsyncMock(side_effect=emit)
        await asyncio.gather(*[outbound.dispatch_message_batch(job_id=result['job_id'],session_factory=self.sessions,
            settings_obj=self.settings,emit=sender) for _ in range(2)])
        sender.assert_awaited_once()
        with self.assertRaises(api.CommandError):
            await self.prepare({'kind':'discount_send','campaign_id':campaign_id})
        async with self.sessions() as db:
            self.assertEqual((await db.get(User,2)).status,'free')
            self.assertIsNone((await db.get(User,2)).end_date)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Payment)),1)
            offer=await db.get(DiscountCampaign,campaign_id)
            self.assertEqual((offer.notification_sent_count,offer.notification_failed_count),(1,0))

    async def test_native_only_and_blocked_bot_accounts_remain_reachable_via_existing_android_policy(self):
        await self.device(1)
        campaign_id=await self.offer(target_user_id=1)
        result=await self.queued(campaign_id)
        sender=AsyncMock()
        await outbound.dispatch_message_batch(job_id=result['job_id'],session_factory=self.sessions,settings_obj=self.settings,emit=sender)
        sender.assert_awaited_once()
        self.assertIsNone(sender.await_args.args[0].telegram_id)
        self.assertEqual(sender.await_args.args[0].user_id,1)

    async def test_offer_drift_and_audit_failure_preserve_proof_and_one_round_reservation(self):
        campaign_id=await self.offer()
        command=await self.prepare({'kind':'discount_send','campaign_id':campaign_id});proof=await self.proof(command)
        async with self.sessions() as db:
            (await db.get(DiscountCampaign,campaign_id)).percent=25;await db.commit()
        with self.assertRaises(api.CommandError):await self.execute(command,proof)
        async with self.sessions() as db:
            self.assertIsNone((await db.get(DiscountCampaign,campaign_id)).notification_sent_at)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')
        command=await self.prepare({'kind':'discount_send','campaign_id':campaign_id});proof=await self.proof(command)
        def fail(*args):raise RuntimeError('synthetic audit failure')
        event.listen(AdminPwaCommandAudit,'before_insert',fail)
        try:
            with self.assertRaises(RuntimeError):await self.execute(command,proof)
        finally:event.remove(AdminPwaCommandAudit,'before_insert',fail)
        async with self.sessions() as db:
            self.assertIsNone((await db.get(DiscountCampaign,campaign_id)).notification_sent_at)
            self.assertEqual((await db.get(AdminPwaStepUp,proof)).status,'verified')

    async def test_live_offer_expiry_or_new_usage_skips_and_uncertainty_never_replays(self):
        for mutation in ('expiry','usage','uncertain'):
            campaign_id=await self.offer()
            result=await self.queued(campaign_id)
            async with self.sessions() as db:
                if mutation=='expiry':(await db.get(DiscountCampaign,campaign_id)).ends_at=datetime.now(timezone.utc)-timedelta(seconds=1)
                if mutation=='usage':db.add(Payment(user_id=2,amount=10,currency='TJS',plan_type='1_month',
                    payment_method='visa',payment_status='pending',discount_campaign_id=campaign_id))
                await db.commit()
            sender=AsyncMock(side_effect=TimeoutError('synthetic uncertainty'))
            for _ in range(2):
                await outbound.dispatch_message_batch(job_id=result['job_id'],session_factory=self.sessions,settings_obj=self.settings,emit=sender)
            self.assertEqual(sender.await_count,1 if mutation=='uncertain' else 0)

    async def test_stop_during_one_provider_attempt_keeps_its_late_receipt_and_counts(self):
        campaign_id=await self.offer();result=await self.queued(campaign_id)
        started,release=asyncio.Event(),asyncio.Event()
        async def provider(message):
            started.set();await release.wait()
        task=asyncio.create_task(outbound.dispatch_message_batch(job_id=result['job_id'],session_factory=self.sessions,
            settings_obj=self.settings,emit=provider))
        await asyncio.wait_for(started.wait(),3)
        async with self.sessions() as db:
            await outbound.stop_message(db,session_cookie=fixtures.fixtures.COOKIE,
                request=outbound.RunMessage(job_id=result['job_id']),settings_obj=self.settings)
        release.set();await task
        async with self.sessions() as db:
            row=await db.get(DiscountCampaign,campaign_id)
            self.assertEqual((row.notification_sent_count,row.notification_failed_count),(1,0))
            self.assertEqual((await db.get(Job,result['job_id'])).status,'closed')

    async def test_production_adapter_uses_native_canonical_notice_and_unknown_push_has_no_auto_fallback(self):
        await self.device(1);campaign_id=await self.offer(target_user_id=1)
        result=await self.queued(campaign_id)
        bot=SimpleNamespace(send_message=AsyncMock())
        async def unknown(*args,**kwargs):raise TimeoutError('synthetic unknown FCM')
        async def emit(message):
            return await notices.emit_discount_notice(message,session_factory=self.sessions,settings_obj=self.settings,bot=bot)
        with patch.object(AndroidPushService,'send_batch',side_effect=unknown) as push:
            for _ in range(2):
                await outbound.dispatch_message_batch(job_id=result['job_id'],session_factory=self.sessions,settings_obj=self.settings,emit=emit)
            push.assert_awaited_once()
        async with self.sessions() as db:
            row=await db.scalar(select(AccountNoticeDelivery))
            self.assertEqual(row.user_id,1);self.assertIsNone(row.fallback_due_at)
            self.assertEqual((await db.get(Recipient,(result['job_id'],1))).status,'uncertain')
            self.assertEqual(await NotificationDeliveryService(db,self.settings).send_due_fallbacks(bot,
                now=datetime.now(timezone.utc)+timedelta(hours=1)),0)
        bot.send_message.assert_not_awaited()

    async def test_bounded_sql_matches_shared_repeat_quota_and_canonical_legacy_usage(self):
        campaign_id=await self.offer(target_user_id=None,quota_total=2,repeat_interval_days=2)
        async with self.sessions() as db:
            # An old same-user payment permits repeat but keeps the global slot rules.
            db.add(Payment(user_id=None,user_telegram_id=2002,amount=10,currency='TJS',plan_type='1_month',
                payment_method='visa',payment_status='approved',discount_campaign_id=campaign_id,
                submitted_at=datetime.now(timezone.utc)-timedelta(days=3)))
            await db.commit()
        async with self.sessions() as db:
            row=await db.get(DiscountCampaign,campaign_id)
            users=await notices.notice_users(db,row,self.settings)
            self.assertEqual([u.id for u in users],[2])
            for user in users:
                service=DiscountService(db)
                self.assertTrue(service._matches_campaign(row,user,'1_month','visa'))
                choice=await service._campaign_choice(row,user,datetime.now(timezone.utc))
                self.assertEqual(choice.campaign_id,campaign_id)
            row.quota_total=1;await db.commit()
        async with self.sessions() as db:
            # Own prior reservation is excluded, exactly as the shared checkout.
            row=await db.get(DiscountCampaign,campaign_id)
            self.assertEqual([u.id for u in await notices.notice_users(db,row,self.settings)],[2])
            row.repeat_interval_days=None;await db.commit()
        async with self.sessions() as db:
            self.assertEqual(await notices.notice_users(db,await db.get(DiscountCampaign,campaign_id),self.settings),[])

    async def test_audience_is_one_bounded_query_and_native_fanout_is_capped(self):
        campaign_id=await self.offer(target_user_id=None,quota_total=None)
        for _ in range(9):await self.device(1)
        queries=[]
        def record(conn,cursor,statement,*args):queries.append(statement)
        async with self.sessions() as db:
            offer=await db.get(DiscountCampaign,campaign_id)
            event.listen(self.engine.sync_engine,'before_cursor_execute',record)
            try:
                users=await notices.notice_users(db,offer,self.settings)
            finally:event.remove(self.engine.sync_engine,'before_cursor_execute',record)
            self.assertEqual([u.id for u in users],[1,2])
            self.assertEqual(len(queries),1)
            self.assertEqual(len(await NotificationDeliveryService(db,self.settings)._android_targets(await db.get(User,1),limit=8)),8)

    async def test_shared_delivery_releases_sql_before_tg_and_native_io_and_preserves_silent_play_ack(self):
        active=0
        def checkout(*args):
            nonlocal active
            active+=1
        def checkin(*args):
            nonlocal active
            active-=1
        event.listen(self.engine.sync_engine,'checkout',checkout);event.listen(self.engine.sync_engine,'checkin',checkin)
        async def provider(**kwargs):self.assertEqual(active,0)
        bot=SimpleNamespace(send_message=AsyncMock(side_effect=provider))
        try:
            async with self.sessions() as db:
                user=await db.get(User,2)
                result=await NotificationDeliveryService(db,self.settings).deliver(bot,user,key='discount_offer',lang='uz',
                    telegram=TelegramNotice(text='QA'),reason='discount_notification',release_before_io=True)
                self.assertEqual(result,'telegram');await db.commit()
            device=await self.device(1)
            async def push(*args,**kwargs):
                self.assertEqual(active,0);return [AndroidPushResult(True)]
            with patch.object(AndroidPushService,'send_batch',side_effect=push):
                async with self.sessions() as db:
                    user=await db.get(User,1)
                    result=await NotificationDeliveryService(db,self.settings).deliver(bot,user,key='discount_offer',lang='uz',
                        telegram=TelegramNotice(text='QA offer'),reason='discount_notification',release_before_io=True)
                    self.assertEqual(result,'android');await db.commit()
                async with self.sessions() as db:
                    row=await db.scalar(select(AccountNoticeDelivery))
                    self.assertEqual(row.user_id,1);self.assertIsNone(row.telegram_id)
                    self.assertEqual(row.key,'discount_offer')
                    # Play's existing client consumes suppressed offers as shown=True.
                    self.assertTrue(await NotificationDeliveryService(db,self.settings).acknowledge(row.id,
                        telegram_id=await db.get(User,1),device_id=device,shown=True))
                async with self.sessions() as db:
                    self.assertEqual(await NotificationDeliveryService(db,self.settings).send_due_fallbacks(bot,
                        now=datetime.now(timezone.utc)+timedelta(hours=1)),0)
            bot.send_message.assert_awaited_once()
        finally:
            event.remove(self.engine.sync_engine,'checkout',checkout);event.remove(self.engine.sync_engine,'checkin',checkin)


@unittest.skipUnless(os.environ.get('ADMIN_PWA_TEST_DATABASE_URL'),'requires isolated PostgreSQL')
class DiscountNoticePostgresTests(fixtures.fixtures.PaymentFixtures,unittest.IsolatedAsyncioTestCase):
    asyncSetUp=pg.AdminPwaSettingsPostgresTests.asyncSetUp
    asyncTearDown=pg.AdminPwaSettingsPostgresTests.asyncTearDown
    prepare=DiscountNoticeTests.prepare
    proof=DiscountNoticeTests.proof
    execute=DiscountNoticeTests.execute
    offer=DiscountNoticeTests.offer
    queued=DiscountNoticeTests.queued
    test_exact_single_notice_is_claimed_before_io_and_never_grants_access=DiscountNoticeTests.test_exact_single_notice_is_claimed_before_io_and_never_grants_access
    test_bounded_sql_matches_shared_repeat_quota_and_canonical_legacy_usage=DiscountNoticeTests.test_bounded_sql_matches_shared_repeat_quota_and_canonical_legacy_usage
