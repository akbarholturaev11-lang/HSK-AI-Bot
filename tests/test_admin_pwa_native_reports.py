"""Private durable intake, retry ownership, throttle and retention boundaries."""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.user import User
from app.services.admin_pwa_native_reports import (
    NativeReportRateLimited, finish_native_report, purge_expired_native_reports, reserve_native_report,
)
from tests import test_admin_pwa_payment_review as fixtures


class NativeReportTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def reserve(self, *, user_id=1, now=None, **overrides):
        values = dict(user_id=user_id, description="Synthetic private issue", app_version="qa", screen="course",
                      screenshot=b"\xff\xd8\xffsynthetic", now=now)
        return await reserve_native_report(self.sessions, **(values | overrides))

    async def test_failure_is_durable_and_retry_reuses_canonical_report(self):
        now = datetime.now(timezone.utc)
        first = await self.reserve(now=now)
        await finish_native_report(self.sessions, first.report_id, delivered=False)
        async with self.sessions() as db:
            row = await db.get(AdminPwaNativeReport, first.report_id)
            self.assertEqual(row.user_id, 1)  # provider-only owner, no fabricated Telegram ID
            self.assertEqual(row.notification_state, "failed")
            self.assertEqual(row.attachment_bytes, b"\xff\xd8\xffsynthetic")
        with self.assertRaises(NativeReportRateLimited):
            await self.reserve(now=now+timedelta(seconds=59), description="Another valid issue")
        retry = await self.reserve(now=now+timedelta(seconds=61))
        self.assertEqual(retry.report_id, first.report_id)
        self.assertFalse(retry.already_sent)
        await finish_native_report(self.sessions, first.report_id, delivered=True)
        await finish_native_report(self.sessions, first.report_id, delivered=False)
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaNativeReport, first.report_id)).notification_state, "sent")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaNativeReport)), 1)

    async def test_success_is_idempotent_per_owner_and_pending_attempt_has_a_lease(self):
        now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0)
        first = await self.reserve(now=now)
        with self.assertRaises(NativeReportRateLimited):
            await self.reserve(now=now+timedelta(seconds=61))
        retry = await self.reserve(now=now+timedelta(minutes=5))
        self.assertEqual(retry.report_id, first.report_id)
        await finish_native_report(self.sessions, first.report_id, delivered=True)
        sent = await self.reserve(now=now+timedelta(minutes=7))
        self.assertTrue(sent.already_sent)
        other = await self.reserve(user_id=2, now=now)
        self.assertNotEqual(other.report_id, first.report_id)
        next_day = await self.reserve(now=now+timedelta(days=1))
        self.assertNotEqual(next_day.report_id, first.report_id)

    async def test_retention_is_bounded_and_account_deletion_removes_private_content(self):
        from scripts.admin_pwa_native_report_retention import run
        now = datetime.now(timezone.utc)
        for age in (32, 31):
            await self.reserve(now=now-timedelta(days=age))
        current = await self.reserve(user_id=2, now=now)
        dry = await run(self.sessions)
        self.assertEqual(dry, {"expired_before": 2, "removed": 0, "remaining_expired": 2, "mode": "count_only"})
        async with self.sessions() as db:
            async with db.begin():
                self.assertEqual(await purge_expired_native_reports(db, now=now, limit=1), 1)
            async with db.begin():
                self.assertEqual(await purge_expired_native_reports(db, now=now), 1)
            async with db.begin():
                self.assertEqual(await purge_expired_native_reports(db, now=now), 0)
                await db.execute(delete(User).where(User.id == 2))
            self.assertIsNone(await db.get(AdminPwaNativeReport, current.report_id))

    async def test_invalid_storage_bounds_and_purge_bounds_fail_without_intake(self):
        for values in ({"description": "bad"}, {"description": "x"*2001}, {"app_version": "x"*41},
                       {"screen": "x"*81}, {"screenshot": b"html"}, {"screenshot": b"\xff\xd8\xff"+b"x"*(550*1024)},
                       {"user_id": 999}):
            with self.subTest(values=list(values)), self.assertRaises(ValueError):
                await self.reserve(**values)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaNativeReport)), 0)
            for limit in (0, True, 1001):
                with self.assertRaises(ValueError):
                    await purge_expired_native_reports(db, limit=limit)
