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
            # CASE may inspect private context in SQL, but must not project
            # raw diagnostic text or Telegram identity back into Python.
            self.assertIn("case ", projection)
            self.assertNotIn("messages.content as ", projection)
            self.assertNotIn("messages.content,", projection)
            self.assertNotIn("messages.telegram_id", projection)

    async def test_onboarding_explanations_use_recovery_result_not_http_success(self):
        now = datetime.now(timezone.utc) - timedelta(seconds=1)
        scenarios = (
            ("onboarding_recovered", "course_level_change_requires_placement", True),
            ("onboarding_placement_required", "course_level_change_requires_placement", False),
            ("onboarding_timeout", "onboarding_save_timeout", False),
            ("onboarding_unconfirmed", "onboarding_failed", False),
        )
        ids = {}
        async with self.sessions() as db:
            for expected, error_code, recovered in scenarios:
                # Historical app_error_context format from the actual producer.
                content = (
                    "APP ERROR KONTEXTI:\n"
                    "- source: miniapp\n"
                    "- level: \n"
                    "- event_source: course_v3_onboarding\n"
                    "- block_no: \n"
                    "- mode: \n"
                    "- error_name: OnboardingSaveResponseError\n"
                    f"- error_message: {error_code}\n"
                    "- url: https://private.invalid/?token=SECRET\n"
                    "- created_at: 2026-10-26T15:59:15Z\n"
                    "- stack: PRIVATE_STACK\n"
                    '- extra: {"recovered": ' + ("true" if recovered else "false") +
                    ', "track": "hsk20"}'
                )
                marker = Message(user_id=1, role="assistant", content_type="app_error_context",
                                 content=content, created_at=now)
                db.add(marker)
                await db.flush()
                ids[marker.id] = expected
            # Unrecognized records must never pass arbitrary text to the UI.
            unknown = Message(user_id=1, role="assistant", content_type="app_error_context",
                              content="PRIVATE diagnostic stack, token=SECRET", created_at=now)
            db.add(unknown)
            await db.flush()
            ids[unknown.id] = "unknown"
            await db.commit()

        async with self.sessions() as db:
            payload = await unified_inbox(db, InboxRequest(source="technical"))
        actual = {row["source_id"]: row["technical_code"] for row in payload["items"]}
        self.assertEqual(actual, ids)
        for row in payload["items"]:
            self.assertEqual(row["message"], "Mini App technical error")
            self.assertNotIn("SECRET", str(row))
            self.assertNotIn("PRIVATE_STACK", str(row))
            self.assertNotIn("private.invalid", str(row))
