"""Atomic, authorized inbox triage and append-only audit regression tests."""
import unittest
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select, update

from app.admin_api.pwa_inbox_triage import create_admin_pwa_inbox_triage_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage, AdminPwaInboxTriageAudit
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.bot_feedback import BotFeedback
from app.db.models.message import Message
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


class AdminPwaInboxTriageTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def post(self, path, body, *, cookie=fixtures.COOKIE, origin="https://hskai.app"):
        app = FastAPI()
        app.include_router(create_admin_pwa_read_router(
            settings_obj=self.settings, session_factory=self.sessions))
        app.include_router(create_admin_pwa_inbox_triage_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
                               headers={"origin": origin},
                               cookies={ADMIN_PWA_COOKIE_NAME: cookie} if cookie else {}) as client:
            return await client.post("/api/admin/v1/" + path, json=body)

    async def seed(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        async with self.sessions() as db:
            db.add(ReleaseFeedbackCampaign(id=701, title="QA release", send_at=now))
            await db.flush()
            bot = BotFeedback(user_id=1, telegram_id=1001, disliked_text="private bot report",
                              status="completed", completed_at=now)
            rel = ReleaseFeedbackResponse(campaign_id=701, user_telegram_id=2002,
                                          rating=4, comment_text="private release", completed_at=now)
            native = AdminPwaNativeReport(
                user_id=2, deduplication_key="z" * 64, description="private Android screenshot",
                app_version="QA", screen="course", attachment_bytes=b"private image",
                notification_state="sent", created_at=now, last_attempt_at=now,
                expires_at=now + timedelta(days=30))
            db.add_all([bot, rel, native])
            await db.flush()
            ids = {"bot": bot.id, "release": rel.id, "android": native.id}
            await db.commit()
        return ids

    async def test_android_fixed_action_enqueues_single_owner_only_push_receipt(self):
        ids = await self.seed()
        report_id = ids["android"]
        fixed = await self.post("inbox/triage", {
            "source": "android", "source_id": report_id,
            "operation": "resolve_fixed", "fix_kind": "server",
            "expected_revision": 0,
        })
        self.assertEqual(fixed.status_code, 200, fixed.text)
        self.assertEqual(fixed.json()["status"], "resolved")
        self.assertTrue(fixed.json()["notice_queued"])
        async with self.sessions() as db:
            notices = (await db.scalars(select(AccountNoticeDelivery))).all()
            self.assertEqual(len(notices), 1)
            row = notices[0]
            self.assertEqual((row.user_id, row.telegram_id), (2, 2002))
            self.assertEqual((row.status, row.action, row.key),
                             ("fix_queued", "course", "daily_limit_renewed"))
            self.assertNotIn("private Android screenshot", row.title + row.body)
        repeated = await self.post("inbox/triage", {
            "source": "android", "source_id": report_id,
            "operation": "resolve_fixed", "fix_kind": "server",
            "expected_revision": 1,
        })
        self.assertEqual(repeated.status_code, 409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AccountNoticeDelivery)), 1)

    async def test_published_newer_apk_fix_does_not_autoflush_provisional_row(self):
        ids = await self.seed()
        async with self.sessions() as db:
            (await db.get(AdminPwaNativeReport, ids["android"])).app_version = "1.7.21"
            await db.commit()
        published = SimpleNamespace(
            can_self_update=True, version_name="1.7.22",
        )
        with patch("app.admin_api.pwa_inbox_triage.AndroidReleaseService.serve",
                   new_callable=AsyncMock, return_value=published):
            fixed = await self.post("inbox/triage", {
                "source": "android", "source_id": ids["android"],
                "operation": "resolve_fixed", "fix_kind": "app_update",
                "expected_revision": 0,
            })
        self.assertEqual(fixed.status_code, 200, fixed.text)
        async with self.sessions() as db:
            notice = (await db.scalars(select(AccountNoticeDelivery))).one()
            self.assertIn("versiya", notice.body.lower())
            self.assertEqual(notice.user_id, 2)

    async def test_unrelated_inbox_actions_never_enqueue_a_fixed_notice(self):
        ids = await self.seed()
        bad = await self.post("inbox/triage", {
            "source": "bot", "source_id": ids["bot"],
            "operation": "resolve_fixed", "fix_kind": "server",
            "expected_revision": 0,
        })
        self.assertEqual(bad.status_code, 400)
        invalid = await self.post("inbox/triage", {
            "source": "android", "source_id": ids["android"],
            "operation": "mark_read", "fix_kind": "server",
            "expected_revision": 0,
        })
        self.assertEqual(invalid.status_code, 400)
        unpublished = await self.post("inbox/triage", {
            "source": "android", "source_id": ids["android"],
            "operation": "resolve_fixed", "fix_kind": "app_update",
            "expected_revision": 0,
        })
        self.assertEqual(unpublished.status_code, 409)
        marked = await self.post("inbox/triage", {
            "source": "android", "source_id": ids["android"],
            "operation": "resolve", "expected_revision": 0,
        })
        self.assertEqual(marked.status_code, 200, marked.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AccountNoticeDelivery)), 0)

    async def test_technical_alert_is_private_triable_and_never_arbitrary_message(self):
        from app.db.models.message import Message
        now = datetime.now(timezone.utc)
        secret = "https://private.invalid/?token=DO_NOT_SHOW\\nstack=password"
        async with self.sessions() as db:
            rows = [
                Message(user_id=1, role="assistant", content=secret,
                        content_type="app_error_context", created_at=now),
                Message(user_id=1, role="user", content=secret,
                        content_type="text", created_at=now),
                Message(user_id=1, role="assistant", content=secret,
                        content_type="app_error_context", created_at=now-timedelta(days=31)),
            ]
            db.add_all(rows)
            await db.flush()
            technical_id, user_text_id, expired_id = [r.id for r in rows]
            await db.commit()
        listed = await self.post("inbox/list", {"source": "technical"})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(len(listed.json()["items"]), 1)
        self.assertEqual(listed.json()["items"][0]["source_id"], technical_id)
        self.assertEqual(listed.json()["items"][0]["message"], "Mini App technical error")
        self.assertEqual(listed.json()["items"][0]["triage_priority"], "important")
        self.assertNotIn("DO_NOT_SHOW", listed.text)
        before = (await self.post("inbox/unread-count", {})).json()["unread_count"]
        marked = await self.post("inbox/triage", {"source": "technical",
            "source_id": technical_id, "operation": "mark_read", "expected_revision": 0})
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertEqual(marked.json()["revision"], 1)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], before-1)
        resolved = await self.post("inbox/triage", {"source": "technical",
            "source_id": technical_id, "operation": "resolve", "expected_revision": 1})
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["status"], "resolved")
        for source_id in (user_text_id,expired_id):
            rejected = await self.post("inbox/triage", {"source":"technical",
                "source_id":source_id,"operation":"mark_read","expected_revision":0})
            self.assertEqual(rejected.status_code,403,rejected.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(
                AdminPwaInboxTriageAudit).where(
                    AdminPwaInboxTriageAudit.source=="technical")), 2)

    async def test_three_sources_read_assign_priority_resolve_reopen_and_audit(self):
        ids = await self.seed()
        for source, source_id in ids.items():
            initial = (await self.post("inbox/list", {"source": source})).json()["items"][0]
            self.assertEqual(initial["triage_status"], "new")
            self.assertEqual(initial["triage_priority"], "important" if source=="android" else "normal")
            self.assertEqual(initial["triage_revision"], 0)
            expected = 0
            operations = [
                ("mark_read", "read", "normal"),
                ("assign_self", "assigned", "normal"),
                ("mark_important", "assigned", "important"),
                ("resolve", "resolved", "important"),
                ("reopen", "assigned", "important"),
                ("clear_important", "assigned", "normal"),
            ]
            if source=="android":
                operations=[("clear_important", "new", "normal"), *operations]
            for operation, status, priority in operations:
                reply = await self.post("inbox/triage", {
                    "source": source, "source_id": source_id,
                    "operation": operation, "expected_revision": expected})
                self.assertEqual(reply.status_code, 200, (source, operation, reply.text))
                data = reply.json()
                self.assertEqual(data["status"], status)
                self.assertEqual(data["priority"], priority)
                self.assertEqual(data["revision"], expected + 1)
                self.assertEqual(reply.headers["cache-control"], "no-store")
                expected += 1
            final = (await self.post("inbox/list", {"source": source})).json()["items"][0]
            self.assertEqual(final["triage_status"], "assigned")
            self.assertEqual(final["triage_revision"], 7 if source=="android" else 6)
            self.assertEqual(final["triage_assigned_to"], 101)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriage)), 3)
            audits = (await db.scalars(select(AdminPwaInboxTriageAudit))).all()
            self.assertEqual(len(audits), 19)
            self.assertTrue(all(a.actor_user_id == 101 for a in audits))
            self.assertTrue(all(a.operation in ("mark_read", "assign_self", "mark_important",
                                                "resolve", "reopen", "clear_important") for a in audits))
            self.assertNotIn("private", repr([(a.operation, a.source_id) for a in audits]))

    async def test_unread_badge_is_source_authoritative_and_important_filter_is_paged(self):
        ids = await self.seed()
        initial = await self.post("inbox/unread-count", {})
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()["unread_count"], 4)
        self.assertFalse(initial.json()["capped"])
        self.assertNotIn("description", initial.text)
        self.assertNotIn("private", initial.text)
        important=(await self.post("inbox/list", {"priority":"important"})).json()["items"]
        self.assertEqual({row["source"] for row in important}, {"android","payment"})
        self.assertTrue(all(row["triage_priority"]=="important" for row in important))
        # No opt-in push flag here: read/triage changes cannot send.
        marked = await self.post("inbox/triage", {
            "source":"android","source_id":ids["android"],
            "operation":"clear_important","expected_revision":0})
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 4)
        important = (await self.post("inbox/list", {"priority":"important","limit":1})).json()
        self.assertEqual([x["source"] for x in important["items"]], ["payment"])
        self.assertIsNotNone(important["next_before"])  # Android remains auto-important despite legacy clear.
        marked = await self.post("inbox/triage", {
            "source":"bot","source_id":ids["bot"],"operation":"mark_read",
            "expected_revision":0})
        self.assertEqual(marked.status_code, 200)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 3)
        marked = await self.post("inbox/triage", {
            "source":"release","source_id":ids["release"],
            "operation":"resolve","expected_revision":0})
        self.assertEqual(marked.status_code, 200)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 2)
        now=datetime.now(timezone.utc)
        async with self.sessions() as db:
            native=await db.get(AdminPwaNativeReport,ids["android"])
            native.expires_at=now-timedelta(seconds=1)
            await db.commit()
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 1)
        self.assertEqual([r["source"] for r in (await self.post("inbox/list",
                  {"priority":"important"})).json()["items"]], ["payment"])
        self.assertEqual((await self.post("inbox/list", {"priority":"unknown"})).status_code, 400)
        for body in ({"source":"bot"},{"limit":1},{"user_id":1},{"arbitrary":"sql"}):
            self.assertEqual((await self.post("inbox/unread-count", body)).status_code, 400)
        for cookie,origin,code in ((None,"https://hskai.app",401),
                                   ("T"*64,"https://hskai.app",401),
                                   (fixtures.COOKIE,"https://evil.example",403)):
            self.assertEqual((await self.post("inbox/unread-count", {},cookie=cookie,
                                               origin=origin)).status_code, code)

    async def test_unread_count_caps_at_99_plus_instead_of_claiming_exact_total(self):
        async with self.sessions() as db:
            db.add_all([BotFeedback(user_id=1,telegram_id=1001,
                                     disliked_text="new",status="completed")
                        for _ in range(105)])
            await db.commit()
        count=(await self.post("inbox/unread-count", {})).json()
        self.assertEqual(count["unread_count"],99)
        self.assertTrue(count["capped"])
        self.assertEqual(count["count_limit"],99)

    async def test_one_tap_bulk_read_is_bounded_audited_and_keeps_future_alerts_new(self):
        await self.seed()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        async with self.sessions() as db:
            db.add_all([
                BotFeedback(
                    user_id=1, telegram_id=1001,
                    disliked_text="old subscriber feedback", status="completed",
                    completed_at=now - timedelta(minutes=1),
                )
                for _ in range(204)
            ])
            # Unfinished questionnaire must not consume the reset batch or badge.
            db.add_all([
                BotFeedback(user_id=1, telegram_id=1001, status="pending")
                for _ in range(30)
            ])
            await db.commit()
        first = await self.post("inbox/mark-all-read", {})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["updated"], 200)
        self.assertTrue(first.json()["has_more"])
        cutoff = first.json()["cutoff"]
        second = await self.post("inbox/mark-all-read", {"cutoff": cutoff})
        self.assertEqual(second.status_code, 200, second.text)
        self.assertFalse(second.json()["has_more"])
        self.assertGreaterEqual(second.json()["updated"], 4)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 0)
        self.assertEqual((await self.post("inbox/mark-all-read", {"cutoff": cutoff})).json()["updated"], 0)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(
                select(func.count()).select_from(BotFeedback)
                .where(BotFeedback.status == "pending")), 30)
            self.assertGreaterEqual(await db.scalar(
                select(func.count()).select_from(AdminPwaInboxTriageAudit)
                .where(AdminPwaInboxTriageAudit.operation == "mark_read")), 208)
        async with self.sessions() as db:
            db.add(BotFeedback(
                user_id=1, telegram_id=1001, status="completed",
                disliked_text="fresh subscriber feedback",
                completed_at=datetime.now(timezone.utc) + timedelta(seconds=1),
            ))
            await db.commit()
        # The first request's cutoff must never touch newer completed reports.
        later = await self.post("inbox/mark-all-read", {"cutoff": cutoff})
        self.assertEqual(later.json()["updated"], 0)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 1)

    async def test_bulk_mark_read_requires_real_admin_session_and_strict_payload(self):
        for body in ({"cutoff": "yesterday"}, {"cutoff": "2026-10-26T07:25:00"},
                     {"status": "all"}, {"cutoff": True}):
            self.assertEqual((await self.post("inbox/mark-all-read", body)).status_code, 400)
        for cookie, origin, code in ((None, "https://hskai.app", 401),
                                      ("X"*64, "https://hskai.app", 403),
                                      (fixtures.COOKIE, "https://evil.invalid", 403)):
            response = await self.post("inbox/mark-all-read", {},
                                       cookie=cookie, origin=origin)
            self.assertEqual(response.status_code, code, response.text)
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        self.assertEqual((await self.post(
            "inbox/mark-all-read", {"cutoff": future})).status_code, 409)

    async def test_stale_revision_noop_invalid_operation_and_missing_source(self):
        ids = await self.seed()
        target = {"source": "bot", "source_id": ids["bot"], "operation": "mark_read",
                  "expected_revision": 0}
        self.assertEqual((await self.post("inbox/triage", target)).status_code, 200)
        stale = await self.post("inbox/triage", target)
        self.assertEqual(stale.status_code, 409)
        noop = await self.post("inbox/triage", {**target, "expected_revision": 1})
        self.assertEqual(noop.status_code, 200)
        self.assertEqual(noop.json()["revision"], 1)
        for body in ({**target, "operation": "delete"},
                     {**target, "expected_revision": True},
                     {**target, "expected_revision": -1},
                     {**target, "assigned_to_user_id": 2},
                     {**target, "source_id": "1"}):
            self.assertEqual((await self.post("inbox/triage", body)).status_code, 400)
        self.assertEqual((await self.post("inbox/triage", {
            **target, "source_id": 2147483647})).status_code, 403)
        self.assertEqual((await self.post("inbox/triage", {
            **target, "operation": "reopen", "expected_revision": 1})).status_code, 409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit)), 1)


    async def test_passkey_feedback_detail_shows_user_context_without_leaking_inbox_ids(self):
        ids = await self.seed()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        async with self.sessions() as db:
            user = await db.get(User, 1)
            user.telegram_id = 1001
            user.full_name = "Feedback Learner"
            user.language = "tj"
            user.level = "hsk4"
            user.learning_mode = "qa"
            user.created_at = now - timedelta(days=150)
            basic = await db.get(BotFeedback, ids["bot"])
            basic.liked_code = "course"
            basic.liked_text = "Режими курс"
            basic.disliked_code = "limits"
            basic.disliked_text = "Лимитҳо каманд"
            basic.reward_granted_at = now
            paid = BotFeedback(
                user_id=1, telegram_id=1001, status="completed", language="tj",
                liked_code="paid_worth", liked_text="Стоила того — посоветую другу",
                disliked_code="paid_daily", disliked_text="Ежедневная практика",
                completed_at=now,
            )
            unfinished = BotFeedback(
                user_id=1, telegram_id=1001, status="pending",
                liked_code="course", liked_text="draft"
            )
            db.add_all([paid, unfinished])
            await db.flush()
            paid_id, unfinished_id = paid.id, unfinished.id
            await db.commit()

        listed = await self.post("inbox/list", {"source": "bot"})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertNotIn("telegram_id", listed.text)
        self.assertNotIn("Feedback Learner", listed.text)

        free = await self.post("inbox/feedback-detail", {"source": "bot", "source_id": ids["bot"]})
        self.assertEqual(free.status_code, 200, free.text)
        self.assertEqual(free.headers["cache-control"], "no-store")
        self.assertEqual(free.json()["name"], "Feedback Learner")
        self.assertEqual(free.json()["telegram_id"], 1001)
        self.assertEqual(free.json()["user_id"], 1)
        self.assertEqual(free.json()["language"], "tj")
        self.assertEqual(free.json()["level"], "hsk4")
        self.assertEqual(free.json()["mode"], "qa")
        self.assertGreaterEqual(free.json()["bot_days"], 149)
        self.assertEqual(free.json()["feedback_parts"]["liked"], "Режими курс")
        self.assertEqual(free.json()["feedback_parts"]["disliked"], "Лимитҳо каманд")
        self.assertFalse(free.json()["feedback_parts"]["paid"])
        self.assertTrue(free.json()["reward_granted"])

        subscriber = await self.post("inbox/feedback-detail", {"source": "bot", "source_id": paid_id})
        self.assertEqual(subscriber.status_code, 200, subscriber.text)
        self.assertTrue(subscriber.json()["feedback_parts"]["paid"])
        self.assertEqual(subscriber.json()["feedback_parts"]["disliked"], "Ежедневная практика")
        self.assertIsNone(subscriber.json()["reward_granted"])

        release = await self.post("inbox/feedback-detail", {"source": "release", "source_id": ids["release"]})
        self.assertEqual(release.status_code, 200, release.text)
        self.assertEqual(release.json()["telegram_id"], 2002)
        self.assertEqual(release.json()["rating"], 4)
        self.assertEqual(release.json()["message"], "private release")

        self.assertEqual((await self.post("inbox/feedback-detail", {
            "source": "bot", "source_id": unfinished_id})).status_code, 404)
        self.assertEqual((await self.post("inbox/feedback-detail", {
            "source": "payment", "source_id": self.payment_id})).status_code, 400)
        self.assertEqual((await self.post("inbox/feedback-detail", {
            "source": "bot", "source_id": -1})).status_code, 400)
        self.assertEqual((await self.post("inbox/feedback-detail", {
            "source": "bot", "source_id": paid_id}, cookie=None)).status_code, 401)
        self.assertEqual((await self.post("inbox/feedback-detail", {
            "source": "bot", "source_id": paid_id}, origin="https://evil.example")).status_code, 403)
        async with self.sessions() as db:
            await db.execute(update(AdminPwaSession).values(auth_method="google_telegram"))
            await db.commit()
        self.assertEqual((await self.post("inbox/feedback-detail", {
            "source": "bot", "source_id": paid_id})).status_code, 401)

    async def test_fail_closed_for_cookie_origin_flag_expiry_and_non_passkey_session(self):
        ids = await self.seed()
        command = {"source": "android", "source_id": ids["android"],
                   "operation": "resolve", "expected_revision": 0}
        for cookie, origin, expected in (
            (None, "https://hskai.app", 401),
            ("X" * 64, "https://hskai.app", 403),
            (fixtures.COOKIE, "https://evil.example", 403),
        ):
            self.assertEqual((await self.post("inbox/triage", command, cookie=cookie,
                                               origin=origin)).status_code, expected)
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertEqual((await self.post("inbox/triage", command)).status_code, 404)
        self.settings.ADMIN_PWA_ENABLED = True
        async with self.sessions() as db:
            row = await db.get(AdminPwaNativeReport, ids["android"])
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=2)
            await db.commit()
        self.assertEqual((await self.post("inbox/triage", command)).status_code, 403)
        self.assertEqual((await self.post("inbox/list", {"source": "android"})).json()["items"], [])
        async with self.sessions() as db:
            await db.execute(update(AdminPwaSession).values(auth_method="google_telegram"))
            await db.commit()
        self.assertEqual((await self.post("inbox/triage", {
            "source": "bot", "source_id": ids["bot"], "operation": "mark_read",
            "expected_revision": 0})).status_code, 403)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriageAudit)), 0)

    async def test_technical_triage_never_selects_private_message_content(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        async with self.sessions() as db:
            marker = Message(user_id=1, role="assistant", content_type="app_error_context",
                             content="PRIVATE STACK and URL token", created_at=now)
            bad = Message(user_id=1, role="user", content_type="app_error_context",
                          content="not eligible", created_at=now)
            db.add_all([marker, bad])
            await db.flush()
            safe_id, bad_id = marker.id, bad.id
            await db.commit()
        statements = []
        def collect(conn, cursor, statement, parameters, context, executemany):
            if "from messages" in statement.lower():
                statements.append(statement.lower())
        event.listen(self.engine.sync_engine, "before_cursor_execute", collect)
        try:
            response = await self.post("inbox/triage", {
                "source": "technical", "source_id": safe_id,
                "operation": "mark_read", "expected_revision": 0})
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", collect)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "read")
        self.assertNotIn("PRIVATE", response.text)
        self.assertTrue(statements)
        # Eligibility may filter by content_type; only the SELECT projection
        # must exclude the private content column and ORM hydration.
        self.assertFalse(any("messages.content" in statement.split("from messages", 1)[0]
                             for statement in statements), statements)
        listed = (await self.post("inbox/list", {"source": "technical"})).json()
        self.assertEqual(listed["items"][0]["triage_status"], "read")
        self.assertNotIn("PRIVATE", str(listed))
        self.assertEqual((await self.post("inbox/triage", {
            "source": "technical", "source_id": bad_id,
            "operation": "mark_read", "expected_revision": 0})).status_code, 403)

    async def test_source_locks_select_only_eligibility_metadata_without_text_or_blob(self):
        ids = await self.seed()
        ids["payment"] = self.payment_id
        allowed = {
            "bot_feedbacks": {"id"},
            "release_feedback_responses": {"id"},
            "admin_pwa_native_reports": {"id", "expires_at"},
            "payments": {"id", "payment_status", "screenshot_file_id"},
        }
        statements = []

        def collect(conn, cursor, statement, parameters, context, executemany):
            lowered = statement.lower()
            for table in allowed:
                if "from " + table + " " in lowered.replace("\n", " "):
                    statements.append((table, lowered))

        event.listen(self.engine.sync_engine, "before_cursor_execute", collect)
        try:
            for source, source_id in ids.items():
                response = await self.post("inbox/triage", {
                    "source": source, "source_id": source_id,
                    "operation": "mark_read", "expected_revision": 0})
                self.assertEqual(response.status_code, 200, response.text)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", collect)

        self.assertEqual(len(statements), 4, statements)
        for table, statement in statements:
            projection = statement.split("from " + table, 1)[0]
            selected = set(re.findall(re.escape(table) + r"\.([a-z_]+)", projection))
            self.assertEqual(selected, allowed[table], statement)
