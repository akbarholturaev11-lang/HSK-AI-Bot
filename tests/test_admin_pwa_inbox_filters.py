"""Source-correct inbox date/status filters and cross-source keyset pages."""
import unittest
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from app.admin_api.pwa_inbox import InboxRequest, unified_inbox
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.message import Message
from app.db.models.payment import Payment
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from tests import test_admin_pwa_payment_review as fixtures


class AdminPwaInboxFilterTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def read(self, **body):
        async with self.sessions() as db:
            return await unified_inbox(db, InboxRequest.model_validate(body))

    async def seed_sources(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        ids = {name: [] for name in ("bot", "release", "android", "technical", "payment")}
        async with self.sessions() as db:
            db.add(ReleaseFeedbackCampaign(id=701, title="Filter QA", send_at=now))
            await db.flush()
            # Keep the unrelated fixture payment outside these windows.
            (await db.get(Payment, self.payment_id)).submitted_at = now - timedelta(days=90)
            for days in (2, 10, 40):
                stamp = now - timedelta(days=days)
                rows = {
                    # Completion, not draft creation, is the Bot inbox date.
                    "bot": BotFeedback(user_id=1, telegram_id=1001, status="completed",
                        disliked_text="Filter QA", created_at=now-timedelta(days=60), completed_at=stamp),
                    "release": ReleaseFeedbackResponse(campaign_id=701, user_telegram_id=1000+days,
                        rating=3, comment_text="Filter QA", completed_at=stamp),
                    "android": AdminPwaNativeReport(user_id=1, deduplication_key=str(days).zfill(64),
                        description="Filter QA", app_version="QA", screen="course",
                        notification_state="sent", created_at=stamp, last_attempt_at=stamp,
                        expires_at=stamp+timedelta(days=30)),
                    "technical": Message(user_id=1, role="assistant", content_type="app_error_context",
                        content="PRIVATE diagnostic", created_at=stamp),
                    "payment": Payment(user_id=1, amount=100, currency="TJS", plan_type="1_month",
                        payment_method="visa", payment_status="pending", screenshot_file_id="QA receipt",
                        submitted_at=stamp),
                }
                db.add_all(rows.values())
                await db.flush()
                for name, row in rows.items():
                    ids[name].append(row.id)
            await db.commit()
        return now, ids

    async def test_periods_use_each_source_timestamp_and_preserve_retention(self):
        _, ids = await self.seed_sources()
        for source, source_ids in ids.items():
            for period, count in (("weekly", 1), ("monthly", 2)):
                data = await self.read(source=source, period=period)
                self.assertEqual([r["source_id"] for r in data["items"]], source_ids[:count],
                                 (source, period, data))
            data = await self.read(source=source)
            expected = source_ids[:2] if source in ("android", "technical") else source_ids
            if source == "payment":
                expected = expected + [self.payment_id]
            self.assertEqual([r["source_id"] for r in data["items"]], expected, source)

    async def test_status_filters_apply_before_limit_and_untriaged_means_new(self):
        now, ids = await self.seed_sources()
        async with self.sessions() as db:
            # Several newer nonmatches must not hide the older matching row
            # when the source page size is one.
            for source, source_ids in ids.items():
                for source_id in source_ids[:2]:
                    db.add(AdminPwaInboxTriage(source=source, source_id=source_id,
                        status="read", priority="normal", revision=1, updated_at=now))
            db.add(AdminPwaInboxTriage(source="bot", source_id=ids["bot"][2],
                status="resolved", priority="normal", revision=1, updated_at=now))
            assigned = BotFeedback(user_id=1, telegram_id=1001, status="completed",
                disliked_text="Assigned QA", completed_at=now-timedelta(days=1))
            new = BotFeedback(user_id=1, telegram_id=1001, status="completed",
                disliked_text="New QA", completed_at=now-timedelta(days=3))
            db.add_all([assigned, new])
            await db.flush()
            assigned_id, new_id = assigned.id, new.id
            db.add(AdminPwaInboxTriage(source="bot", source_id=assigned_id,
                status="assigned", priority="normal", assigned_to_user_id=101,
                revision=1, updated_at=now))
            await db.commit()
        expected = {"new": new_id, "assigned": assigned_id, "resolved": ids["bot"][2],
                    "read": ids["bot"][0]}
        for status, source_id in expected.items():
            data = await self.read(source="bot", status=status, limit=1)
            self.assertEqual(data["items"][0]["source_id"], source_id, status)
            self.assertEqual(data["items"][0]["triage_status"], status)
        # Completed financial rows cannot become assigned/resolved through
        # payment triage; their source-specific eligibility still applies.
        self.assertEqual((await self.read(source="payment", status="assigned"))["items"], [])

    async def test_period_status_keysets_do_not_drop_tied_cross_source_rows(self):
        _, ids = await self.seed_sources()
        full = await self.read(period="monthly", status="new")
        expected = [(r["source"], r["source_id"]) for r in full["items"]]
        self.assertEqual(len(expected), 10)
        actual, before = [], None
        for _ in range(12):
            page = await self.read(period="monthly", status="new", limit=1, before=before)
            actual.extend((r["source"], r["source_id"]) for r in page["items"])
            before = page["next_before"]
            if before is None:
                break
        self.assertEqual(actual, expected)
        self.assertEqual(len(set(actual)), 10)

    def test_filter_payload_is_strict_and_defaults_preserve_existing_reads(self):
        query = InboxRequest.model_validate({})
        self.assertEqual((query.status, query.period), ("all", "all_time"))
        for body in ({"status": "unread"}, {"status": True}, {"status": None},
                     {"period": "daily"}, {"period": 7}, {"period": None},
                     {"platform": "iphone"}):
            with self.assertRaises(ValidationError):
                InboxRequest.model_validate(body)
