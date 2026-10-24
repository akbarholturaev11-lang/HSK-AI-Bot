"""Push eligibility uses metadata only and cancels resolved automatic alerts."""
import re
from types import SimpleNamespace
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import event, select

from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.db.models.message import Message
from app.db.models.user import User
from app.services.admin_pwa_push_dispatch import _claim_one, _relevant
from tests import test_admin_pwa_payment_review as fixtures


class AdminPwaPushEligibilityTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            native = AdminPwaNativeReport(user_id=1, deduplication_key="b"*64,
                description="PRIVATE Android report", attachment_bytes=b"PRIVATE screenshot",
                app_version="QA", screen="course", notification_state="sent",
                created_at=now, last_attempt_at=now, expires_at=now+timedelta(days=30))
            technical = Message(user_id=1, role="assistant", content_type="app_error_context",
                content="PRIVATE stack https://private.invalid/?token=secret", created_at=now)
            db.add_all([native, technical])
            await db.flush()
            sources = {"android": native.id, "technical": technical.id,
                       "payment": self.payment_id}
            await db.commit()
        return now, sources

    async def test_automatic_eligibility_never_selects_content_blobs_or_receipt_metadata(self):
        now, sources = await self.seed()
        tables = ("admin_pwa_native_reports", "messages", "payments")
        statements = []

        def collect(conn, cursor, statement, parameters, context, executemany):
            lowered = statement.lower()
            for table in tables:
                if "from " + table + " " in lowered.replace("\n", " "):
                    statements.append((table, lowered))

        event.listen(self.engine.sync_engine, "before_cursor_execute", collect)
        try:
            for source, source_id in sources.items():
                async with self.sessions() as db:
                    self.assertTrue(await _relevant(db, SimpleNamespace(
                        source=source, source_id=source_id), now))
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", collect)
        self.assertEqual(len(statements), 3)
        for table, statement in statements:
            projection = statement.split("from " + table, 1)[0]
            self.assertEqual(set(re.findall(re.escape(table) + r"\.([a-z_]+)", projection)), {"id"})

    async def test_resolved_native_and_technical_alerts_are_cancelled_before_claim(self):
        now, sources = await self.seed()
        subscription_id = str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaPushSubscription(id=subscription_id, user_id=101, platform="iphone",
                endpoint_hash="a"*64, encrypted_payload="must never decrypt a resolved alert",
                created_at=now, updated_at=now))
            await db.flush()
            for source in ("android", "technical"):
                source_id = sources[source]
                db.add(AdminPwaInboxTriage(source=source, source_id=source_id,
                    status="resolved", priority="important", revision=1, updated_at=now))
                db.add(AdminPwaPushOutbox(id=str(uuid4()), subscription_id=subscription_id,
                    event_key=("b" if source == "android" else "c")*64,
                    source=source, source_id=source_id, triage_revision=1,
                    state="pending", attempts=0, created_at=now, updated_at=now,
                    next_attempt_at=now))
            await db.commit()
        self.assertIsNone(await _claim_one(self.sessions, self.settings, now, "isolated-worker"))
        async with self.sessions() as db:
            entries = (await db.scalars(select(AdminPwaPushOutbox))).all()
            self.assertEqual(len(entries), 2)
            self.assertEqual({(row.state, row.attempts) for row in entries}, {("cancelled", 0)})
            for source in ("android", "technical"):
                triage = await db.get(AdminPwaInboxTriage, (source, sources[source]))
                triage.status = "assigned"
            await db.commit()
        # A current reopened source remains eligible; cancelled delivery rows
        # are never themselves resurrected or resent by this read helper.
        for source in ("android", "technical"):
            async with self.sessions() as db:
                self.assertTrue(await _relevant(db, SimpleNamespace(
                    source=source, source_id=sources[source]), now))

    async def test_currently_blocked_admin_never_claims_an_enrolled_device_alert(self):
        now, sources = await self.seed()
        subscription_id, event_id = str(uuid4()), str(uuid4())
        async with self.sessions() as db:
            db.add(AdminPwaPushSubscription(id=subscription_id, user_id=101, platform="mac",
                endpoint_hash="d"*64, encrypted_payload="must never decrypt for a blocked admin",
                created_at=now, updated_at=now))
            await db.flush()
            db.add(AdminPwaPushOutbox(id=event_id, subscription_id=subscription_id,
                event_key="e"*64, source="technical", source_id=sources["technical"],
                triage_revision=1, state="pending", attempts=0, created_at=now,
                updated_at=now, next_attempt_at=now))
            (await db.get(User, 101)).status = " BlOcKeD "
            await db.commit()
        self.assertIsNone(await _claim_one(self.sessions, self.settings, now, "isolated-worker"))
        async with self.sessions() as db:
            entry = await db.get(AdminPwaPushOutbox, event_id)
            self.assertEqual((entry.state, entry.attempts), ("pending", 0))
