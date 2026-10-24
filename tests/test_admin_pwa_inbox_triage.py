"""Atomic, authorized inbox triage and append-only audit regression tests."""
import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from app.admin_api.pwa_inbox_triage import create_admin_pwa_inbox_triage_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage, AdminPwaInboxTriageAudit
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
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

    async def test_three_sources_read_assign_priority_resolve_reopen_and_audit(self):
        ids = await self.seed()
        for source, source_id in ids.items():
            initial = (await self.post("inbox/list", {"source": source})).json()["items"][0]
            self.assertEqual(initial["triage_status"], "new")
            self.assertEqual(initial["triage_priority"], "normal")
            self.assertEqual(initial["triage_revision"], 0)
            expected = 0
            for operation, status, priority in (
                ("mark_read", "read", "normal"),
                ("assign_self", "assigned", "normal"),
                ("mark_important", "assigned", "important"),
                ("resolve", "resolved", "important"),
                ("reopen", "assigned", "important"),
                ("clear_important", "assigned", "normal"),
            ):
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
            self.assertEqual(final["triage_revision"], 6)
            self.assertEqual(final["triage_assigned_to"], 101)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaInboxTriage)), 3)
            audits = (await db.scalars(select(AdminPwaInboxTriageAudit))).all()
            self.assertEqual(len(audits), 18)
            self.assertTrue(all(a.actor_user_id == 101 for a in audits))
            self.assertTrue(all(a.operation in ("mark_read", "assign_self", "mark_important",
                                                "resolve", "reopen", "clear_important") for a in audits))
            self.assertNotIn("private", repr([(a.operation, a.source_id) for a in audits]))

    async def test_unread_badge_is_source_authoritative_and_important_filter_is_paged(self):
        ids = await self.seed()
        initial = await self.post("inbox/unread-count", {})
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()["unread_count"], 3)
        self.assertFalse(initial.json()["capped"])
        self.assertNotIn("description", initial.text)
        self.assertNotIn("private", initial.text)
        self.assertEqual((await self.post("inbox/list", {"priority":"important"})).json()["items"], [])
        marked = await self.post("inbox/triage", {
            "source":"android","source_id":ids["android"],
            "operation":"mark_important","expected_revision":0})
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 3)
        important = (await self.post("inbox/list", {"priority":"important","limit":1})).json()
        self.assertEqual([(x["source"],x["source_id"]) for x in important["items"]],
                         [("android",ids["android"])])
        self.assertIsNone(important["next_before"])
        marked = await self.post("inbox/triage", {
            "source":"bot","source_id":ids["bot"],"operation":"mark_read",
            "expected_revision":0})
        self.assertEqual(marked.status_code, 200)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 2)
        marked = await self.post("inbox/triage", {
            "source":"release","source_id":ids["release"],
            "operation":"resolve","expected_revision":0})
        self.assertEqual(marked.status_code, 200)
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 1)
        now=datetime.now(timezone.utc)
        async with self.sessions() as db:
            native=await db.get(AdminPwaNativeReport,ids["android"])
            native.expires_at=now-timedelta(seconds=1)
            await db.commit()
        self.assertEqual((await self.post("inbox/unread-count", {})).json()["unread_count"], 0)
        self.assertEqual((await self.post("inbox/list", {"priority":"important"})).json()["items"], [])
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
