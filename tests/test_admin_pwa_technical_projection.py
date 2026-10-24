"""Technical events stay usable without selecting private diagnostic content."""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import event

from app.admin_api.pwa_inbox import InboxRequest, unified_inbox
from app.db.models.message import Message
from tests import test_admin_pwa_payment_review as fixtures


class AdminPwaTechnicalProjectionTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def test_untriaged_event_survives_all_source_and_important_inbox_reads(self):
        now = datetime.now(timezone.utc) - timedelta(seconds=1)
        secret = "PRIVATE diagnostic stack https://private.invalid/?token=secret"
        async with self.sessions() as db:
            marker = Message(user_id=1, role="assistant", content_type="app_error_context",
                             content=secret, created_at=now)
            db.add(marker)
            await db.flush()
            marker_id = marker.id
            await db.commit()

        statements = []

        def collect(conn, cursor, statement, parameters, context, executemany):
            lowered = statement.lower()
            if "from messages" in lowered:
                statements.append(lowered)

        event.listen(self.engine.sync_engine, "before_cursor_execute", collect)
        try:
            for source in ("technical", "all"):
                async with self.sessions() as db:
                    result = await unified_inbox(db, InboxRequest(source=source, priority="important"))
                rows = [item for item in result["items"] if item["source"] == "technical"]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["source_id"], marker_id)
                self.assertEqual(rows[0]["message"], "Mini App technical error")
                self.assertEqual(rows[0]["triage_status"], "new")
                self.assertEqual(rows[0]["triage_priority"], "important")
                self.assertEqual(rows[0]["triage_revision"], 0)
                self.assertFalse(rows[0]["has_attachment"])
                self.assertFalse(rows[0]["image_preview_available"])
                self.assertNotIn("PRIVATE", str(result))
                self.assertNotIn("token=secret", str(result))
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", collect)

        self.assertEqual(len(statements), 2)
        for statement in statements:
            projection = statement.split("from messages", 1)[0]
            self.assertNotIn("messages.content", projection)
            self.assertNotIn("messages.telegram_id", projection)
