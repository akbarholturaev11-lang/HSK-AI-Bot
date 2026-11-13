"""Diagnostic Inbox privacy, pagination and version-aware triage on PostgreSQL."""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriageAudit
from app.services.monitoring import catalog
from app.services.monitoring.intake import ingest, ingest_server, parse_batch
from tests.monitoring_chain import PG_URL, admin_client, client_event, pg_sessions

LIST = "/api/admin/v1/inbox/list"
TRIAGE = "/api/admin/v1/inbox/triage"


async def record(sessions, *, build=40, owner=1, feature="lessons", failure="api_5xx", site="lesson_open", at=None):
    events, rejected = parse_batch({"schema": "diag.v1", "events": [
        client_event(feature, failure, site, app_version=f"1.8.{build}", build=build),
    ]}, platform="android")
    assert not rejected
    async with sessions() as db, db.begin():
        result = await ingest(db, owner_user_id=owner, events=events, now=at)
        return result.touched[0][0].id


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"), "requires disposable monitoring PostgreSQL")
class MonitoringAdminInboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_versioned_reopen_is_audited_and_never_sends_a_learner_notice(self):
        async with pg_sessions(PG_URL) as sessions, admin_client(sessions) as admin:
            incident = await record(sessions)
            command = {"source": "diagnostic", "source_id": incident}
            for revision, operation, status in ((0, "mark_read", "read"), (1, "resolve", "resolved")):
                reply = await admin.post(TRIAGE, json={**command, "expected_revision": revision, "operation": operation})
                self.assertEqual(reply.status_code, 200, reply.text)
                self.assertEqual(reply.json()["status"], status)
                self.assertFalse(reply.json()["notice_queued"])
                self.assertNotIn("assigned_to_user_id", reply.json())
            self.assertEqual(await record(sessions, build=39), incident)
            listing = (await admin.post(LIST, json={"source": "diagnostic", "status": "resolved"})).json()
            self.assertEqual(listing["items"][0]["occurrences"], 2)
            self.assertIsNone(listing["items"][0]["reopened_at"])
            self.assertEqual(await record(sessions, build=40), incident)
            self.assertEqual(await record(sessions, build=41), incident)
            listing = (await admin.post(LIST, json={"source": "diagnostic", "platform": "android"})).json()
            row, = listing["items"]
            self.assertEqual((row["triage_status"], row["reopened_version"], row["last_version"]),
                             ("read", "1.8.40", "1.8.41"))
            self.assertEqual((row["occurrences"], row["affected_accounts"], row["channels"]), (4, 1, ["play"]))
            async with sessions() as db:
                audit = (await db.execute(select(AdminPwaInboxTriageAudit.operation,
                    AdminPwaInboxTriageAudit.actor_user_id).order_by(AdminPwaInboxTriageAudit.created_at))).all()
                self.assertEqual(audit, [("mark_read", 2), ("resolve", 2), ("reopen", None)])
                self.assertEqual(await db.scalar(select(func.count()).select_from(AccountNoticeDelivery)), 0)
            for operation in ("mark_important", "resolve_fixed"):
                reply = await admin.post(TRIAGE, json={**command, "operation": operation, "expected_revision": 3})
                self.assertEqual(reply.status_code, 400, reply.text)

    async def test_projection_keeps_priority_in_cursor_and_reports_partial_and_unknown(self):
        now = datetime.now(timezone.utc)
        async with pg_sessions(PG_URL) as sessions, admin_client(sessions) as admin:
            old = await record(sessions, at=now - timedelta(days=catalog.RECEIPT_RETENTION_DAYS + 1))
            self.assertEqual(await record(sessions, at=now - timedelta(minutes=2)), old)
            normal = await record(sessions, failure="restore_failed", site="progress", at=now - timedelta(minutes=1))
            backend_args = dict(feature_code="voice_practice", failure_code="provider_failed", site_code="voice_provider")
            async with sessions() as db, db.begin():
                backend = (await ingest_server(db, **backend_args, now=now - timedelta(minutes=3))).touched[0][0].id

            cursor, rows = None, []
            for _ in range(3):
                reply = await admin.post(LIST, json={"source": "diagnostic", "limit": 1, "before": cursor})
                self.assertEqual(reply.status_code, 200, reply.text)
                rows.extend(reply.json()["items"])
                cursor = reply.json()["next_before"]
            self.assertIsNone(cursor)
            self.assertEqual([row["source_id"] for row in rows], [old, backend, normal])
            self.assertEqual((rows[0]["affected_state"], rows[0]["affected_accounts"]), ("partial", 1))
            self.assertEqual((rows[1]["affected_state"], rows[1]["affected_accounts"]), ("unknown", None))
            self.assertEqual(rows[2]["affected_state"], "within_retention")
            reply = await admin.post(LIST, json={"source": "diagnostic", "priority": "important", "platform": "android"})
            self.assertEqual([row["source_id"] for row in reply.json()["items"]], [old])
            reply = await admin.post(LIST, json={"source": "diagnostic", "user_id": 1})
            self.assertEqual(reply.json()["items"], [])
            reply = await admin.post(TRIAGE, json={"source": "diagnostic", "source_id": backend,
                                                 "operation": "resolve", "expected_revision": 0})
            self.assertEqual(reply.status_code, 200, reply.text)
            async with sessions() as db, db.begin():
                await ingest_server(db, **backend_args)
            reply = await admin.post(LIST, json={"source": "diagnostic", "platform": "server"})
            self.assertEqual(reply.json()["items"][0]["triage_status"], "read")
            admin.cookies.clear()
            reply = await admin.post(LIST, json={"source": "diagnostic"})
            self.assertEqual(reply.status_code, 401)
            self.assertNotIn("items", reply.json())
