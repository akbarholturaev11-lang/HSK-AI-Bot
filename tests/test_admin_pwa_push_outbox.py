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
