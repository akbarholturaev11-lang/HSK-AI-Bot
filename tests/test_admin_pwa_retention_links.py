"""Native retention removes triage state in the same bounded source batch."""
from datetime import datetime, timedelta, timezone
import unittest
from uuid import uuid4

from sqlalchemy import event, func, select

from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage, AdminPwaInboxTriageAudit
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.services.admin_pwa_native_reports import purge_expired_native_reports, reserve_native_report
from tests import test_admin_pwa_payment_review as fixtures


class RetentionLinksTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def test_oldest_bounded_batch_removes_only_matching_state_and_preserves_audit(self):
        now = datetime.now(timezone.utc)
        ids = []
        for age in (32, 31, 0):
            report = await reserve_native_report(self.sessions, user_id=1,
                description="Synthetic private report", app_version="qa", screen="course",
                screenshot=b"\xff\xd8\xffprivate", now=now-timedelta(days=age))
            ids.append(report.report_id)
        async with self.sessions() as db:
            for source, source_id in [("android", value) for value in ids]+[("bot", ids[0])]:
                db.add(AdminPwaInboxTriage(source=source, source_id=source_id, status="resolved",
                    priority="normal", updated_at=now, revision=1))
            audit_id = str(uuid4())
            db.add(AdminPwaInboxTriageAudit(id=audit_id, source="android", source_id=ids[0],
                operation="resolve", actor_user_id=101, created_at=now))
            await db.commit()
        statements = []
        def record(conn, cursor, statement, parameters, context, many):
            statements.append(statement.lower())
        event.listen(self.engine.sync_engine, "before_cursor_execute", record)
        try:
            async with self.sessions() as db:
                async with db.begin():
                    self.assertEqual(await purge_expired_native_reports(db, now=now, limit=1), 1)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", record)
        reads = [q.split("from", 1)[0] for q in statements if q.lstrip().startswith("select ")]
        self.assertEqual(len(reads), 1)
        self.assertFalse(any("attachment_bytes" in q or "description" in q for q in reads))
        async with self.sessions() as db:
            self.assertIsNone(await db.get(AdminPwaNativeReport, ids[0]))
            self.assertIsNone(await db.get(AdminPwaInboxTriage, ("android", ids[0])))
            self.assertIsNotNone(await db.get(AdminPwaInboxTriage, ("bot", ids[0])))
            self.assertIsNotNone(await db.get(AdminPwaInboxTriageAudit, audit_id))
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaNativeReport)), 2)
            self.assertIsNotNone(await db.get(AdminPwaInboxTriage, ("android", ids[2])))
        # Caller owns commit: a later failure must restore source and state.
        async with self.sessions() as db:
            with self.assertRaises(RuntimeError):
                async with db.begin():
                    self.assertEqual(await purge_expired_native_reports(db, now=now), 1)
                    raise RuntimeError("synthetic rollback")
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(AdminPwaNativeReport, ids[1]))
            self.assertIsNotNone(await db.get(AdminPwaInboxTriage, ("android", ids[1])))
