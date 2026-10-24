"""Apple push outbox: atomic mark-important fanout, dedup and no send."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from app.admin_api.pwa_inbox_triage import create_admin_pwa_inbox_triage_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage, AdminPwaInboxTriageAudit
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.db.models.bot_feedback import BotFeedback
from app.db.models.payment import Payment
from app.db.models.message import Message
from app.db.models.user import User
from app.services.app_error_context_service import AppErrorContextService
from app.services.admin_pwa_push_dispatch import _relevant
from app.services.payment_service import PaymentService
from app.services.admin_pwa_native_reports import reserve_native_report
from app.admin_api.pwa_push_outbox import enqueue_automatic_alert
from tests import test_admin_pwa_push as fixtures


class AdminPwaPushOutboxTests(fixtures.AdminPwaApplePushTests):
    """Reuse the real subscription route, SQLite DB and passkey-admin fixture."""

    async def triage(self, *, row_id, revision, operation="mark_important"):
        app = FastAPI()
        app.include_router(create_admin_pwa_inbox_triage_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="https://hskai.app",
                               headers={"origin": "https://hskai.app"},
                               cookies={ADMIN_PWA_COOKIE_NAME: fixtures.fixtures.COOKIE}) as client:
            return await client.post("/api/admin/v1/inbox/triage", json={
                "source": "bot", "source_id": row_id,
                "operation": operation, "expected_revision": revision,
            })

    async def bot_source(self):
        async with self.sessions() as db:
            feedback = BotFeedback(user_id=1, telegram_id=1001, status="completed",
                                   disliked_text="Student's private message",
                                   completed_at=datetime.now(timezone.utc))
            db.add(feedback)
            await db.flush()
            number = feedback.id
            await db.commit()
        return number

    async def test_only_opted_in_iphone_and_mac_each_receive_content_free_event(self):
        await self.configure()
        iphone = self.subscription(count=1, platform="iphone")
        mac = self.subscription(count=2, platform="mac")
        i = await self.post("subscribe", iphone)
        m = await self.post("subscribe", mac)
        self.assertEqual(i.status_code, 200, i.text)
        self.assertEqual(m.status_code, 200, m.text)
        row_id = await self.bot_source()
        result = await self.triage(row_id=row_id, revision=0)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["priority"], "important")
        async with self.sessions() as db:
            items = (await db.scalars(select(AdminPwaPushOutbox))).all()
            self.assertEqual(len(items), 2)
            self.assertEqual({r.subscription_id for r in items},
                             {i.json()["subscription_id"], m.json()["subscription_id"]})
            self.assertEqual(len({r.event_key for r in items}), 1)
            for entry in items:
                self.assertEqual(entry.state, "pending")
                self.assertEqual(entry.attempts, 0)
                self.assertEqual(entry.source, "bot")
                self.assertEqual(entry.source_id, row_id)
                self.assertEqual(entry.triage_revision, 1)
                self.assertEqual(len(entry.event_key), 64)
                self.assertNotIn("Student", repr(vars(entry)))
                self.assertNotIn("push.apple.com", repr(vars(entry)))
        self.assertEqual((await self.triage(row_id=row_id,revision=0)).status_code,409)
        again = await self.triage(row_id=row_id,revision=1)
        self.assertEqual(again.status_code, 200, again.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),2)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit)),1)
        self.assertEqual((await self.triage(row_id=row_id,revision=1,
                                          operation="clear_important")).status_code,200)
        self.assertEqual((await self.triage(row_id=row_id,revision=2)).status_code,200)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),4)

    async def test_flag_off_and_revoked_device_never_get_queued(self):
        await self.configure()
        iphone = (await self.post("subscribe", self.subscription(count=1))).json()
        mac = (await self.post("subscribe", self.subscription(count=2,platform="mac"))).json()
        row_id = await self.bot_source()
        self.settings.ADMIN_PWA_PUSH_ENABLED = False
        self.assertEqual((await self.triage(row_id=row_id,revision=0)).status_code,200)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),0)
        self.settings.ADMIN_PWA_PUSH_ENABLED = True
        self.assertEqual((await self.post("revoke", {
            "subscription_id":iphone["subscription_id"]})).status_code,200)
        self.assertEqual((await self.triage(row_id=row_id,revision=1,
                                          operation="clear_important")).status_code,200)
        self.assertEqual((await self.triage(row_id=row_id,revision=2)).status_code,200)
        async with self.sessions() as db:
            pending = (await db.scalars(select(AdminPwaPushOutbox))).all()
            self.assertEqual([item.subscription_id for item in pending],[mac["subscription_id"]])

    async def test_every_persisted_miniapp_error_queues_opaque_per_device_event(self):
        await self.configure()
        i=await self.post("subscribe",self.subscription(count=1,platform="iphone"))
        m=await self.post("subscribe",self.subscription(count=2,platform="mac"))
        self.assertEqual(i.status_code,200,i.text)
        self.assertEqual(m.status_code,200,m.text)
        secret="https://private.example.invalid?token=DO_NOT_EXPOSE"
        for attempt in (1,2):
            async with self.sessions() as db:
                owner=await db.get(User,2)
                self.assertEqual(owner.telegram_id,2002)
                with patch("app.config.settings",self.settings):
                    saved=await AppErrorContextService(db).record_miniapp_error(
                        2002, {"source":"miniapp","message":secret,"stack":"private stack",
                               "error_name":"NetworkError","attempt":attempt})
                self.assertTrue(saved)
        async with self.sessions() as db:
            events=(await db.scalars(select(AdminPwaPushOutbox)
                .where(AdminPwaPushOutbox.source=="technical"))).all()
            self.assertEqual(len(events),4)
            self.assertEqual(len({e.event_key for e in events}),2)
            for row in events:
                self.assertTrue(await _relevant(db,row,datetime.now(timezone.utc)))
                self.assertNotIn("DO_NOT_EXPOSE",repr(vars(row)))
                self.assertNotIn("private stack",repr(vars(row)))
            messages=(await db.scalars(select(Message).where(
                Message.content_type=="app_error_context"))).all()
            self.assertEqual(len(messages),2)
            self.assertTrue(all(secret in msg.content for msg in messages))

    async def test_auto_receipt_and_error_only_one_event_per_apple_install(self):
        await self.configure()
        i=await self.post("subscribe",self.subscription(count=1,platform="iphone"))
        m=await self.post("subscribe",self.subscription(count=2,platform="mac"))
        self.assertEqual(i.status_code,200,i.text)
        self.assertEqual(m.status_code,200,m.text)
        async with self.sessions() as db:
            payment=await db.get(Payment,self.payment_id)
            with patch("app.config.settings",self.settings):
                await PaymentService(db)._queue_receipt_alert(payment)
                await PaymentService(db)._queue_receipt_alert(payment)
            await db.commit()
        with patch("app.config.settings",self.settings):
            report=await reserve_native_report(
                self.sessions, user_id=2,description="The lesson screen crashes",
                app_version="1.2.0",screen="practice",screenshot=None)
        self.assertGreater(report.report_id,0)
        async with self.sessions() as db:
            events=(await db.scalars(select(AdminPwaPushOutbox))).all()
            self.assertEqual(len(events),4)
            for source in ("payment","android"):
                rows=[event for event in events if event.source==source]
                self.assertEqual(len(rows),2)
                self.assertEqual(len({r.event_key for r in rows}),1)
                self.assertEqual({r.subscription_id for r in rows},
                                 {i.json()["subscription_id"],m.json()["subscription_id"]})
                self.assertTrue(all(r.state=="pending" and r.attempts==0 for r in rows))
                self.assertNotIn("crashes",str([(r.event_key,r.source) for r in rows]))
        self.assertEqual((await self.post("revoke", {
            "subscription_id":i.json()["subscription_id"]})).status_code,200)
        async with self.sessions() as db:
            await enqueue_automatic_alert(db,settings_obj=self.settings,
                source="payment",source_id=self.payment_id,now=datetime.now(timezone.utc))
            await db.commit()
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),4)

    async def test_auto_enqueue_flag_off_and_synthetic_database_failure_do_not_block_receipt(self):
        await self.configure()
        await self.post("subscribe", self.subscription(count=3,platform="iphone"))
        self.settings.ADMIN_PWA_PUSH_ENABLED=False
        async with self.sessions() as db:
            payment=await db.get(Payment,self.payment_id)
            with patch("app.config.settings",self.settings):
                await PaymentService(db)._queue_receipt_alert(payment)
            await db.commit()
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),0)
        self.settings.ADMIN_PWA_PUSH_ENABLED=True
        async with self.sessions() as db:
            payment=await db.get(Payment,self.payment_id)
            with patch("app.config.settings",self.settings), patch(
                "app.admin_api.pwa_push_outbox.enqueue_automatic_alert",
                side_effect=RuntimeError("synthetic failure")):
                await PaymentService(db)._queue_receipt_alert(payment)
            payment.admin_comment="receipt preserved"
            await db.commit()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment,self.payment_id)).admin_comment,"receipt preserved")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),0)

    async def test_enqueue_failure_rolls_back_triage_and_audit(self):
        await self.configure()
        self.assertEqual((await self.post("subscribe",
                                          self.subscription(count=1))).status_code,200)
        row_id = await self.bot_source()
        with patch("app.admin_api.pwa_inbox_triage.enqueue_important_triage",
                   side_effect=RuntimeError("injected database failure")):
            result=await self.triage(row_id=row_id,revision=0)
        self.assertEqual(result.status_code,503)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriage)),0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit)),0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),0)
        self.assertEqual((await self.triage(row_id=row_id,revision=0)).status_code,200)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushOutbox)),1)
