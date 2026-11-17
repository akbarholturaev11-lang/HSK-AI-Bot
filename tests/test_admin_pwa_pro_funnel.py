"""Task 4.1: the iPhone PWA Pro inline attempt funnel over existing rows (design D4).

Stored-row evidence on a disposable PostgreSQL schema (ANALYTICS_TEST_DATABASE_URL)
and on SQLite, which the Admin PWA browser QA uses; the route-to-Admin chain is
task 4.2.
"""
import json
import os
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.admin_api import pwa_analytics_cache as analytics
from app.admin_api.pwa_analytics_pwa_pro import pwa_pro_attempt_funnel
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.conversion_funnel_event import ConversionFunnelEvent as Funnel
from app.db.models.lava import LavaInvoice
from app.db.models.payment import Payment
from app.db.models.user import User

URL = os.environ.get("ANALYTICS_TEST_DATABASE_URL", "")
NOW = datetime.now(timezone.utc)
SECRET_IDS = ("att-paid", "att-failed", "att-click", "att-refund", "att-forged", "att-old", "contract-")


def ago(**delta):
    return NOW - timedelta(**delta)


def ui(name, user, attempt, at, **extra):
    # The PWA UI route's payload shape (json.dumps default separators).
    return Funnel(user_id=user, event_name=name, source="v3_locked_lesson", created_at=at,
                  payload_json=json.dumps({"event_id": attempt + ":" + name, "attempt_id": attempt,
                                           "plan_type": "1_month", "payment_method": "lava",
                                           "transport": "iphone_pwa", **extra}))


def started(user, attempt, at, checkout):
    return Funnel(user_id=user, event_name="pwa_pro_checkout_started", source="v3_locked_lesson", created_at=at,
                  payload_json=json.dumps({"checkout_id": checkout, "attempt_id": attempt, "plan_type": "1_month",
                                           "payment_method": "lava", "mode": "subscription",
                                           "transport": "iphone_pwa"}))


def paid(user, attempt, at, payment, invoice):
    # The ledger's row, written beside the approved payment.
    return Funnel(user_id=user, event_name="pwa_pro_checkout_paid", source="v3_locked_lesson", created_at=at,
                  payment_id=payment, payload_json=json.dumps({
                      "checkout_id": invoice, "attempt_id": attempt, "plan_type": "1_month",
                      "payment_method": "lava", "discount_source": "none", "transport": "iphone_pwa"}))


def invoice(number, user, status, *, source="pwa", kind="first", payment=None, attempt=None, at=None):
    return LavaInvoice(id=number, contract_id=f"contract-{number:026d}", kind=kind, user_id=user,
                       plan_type="1_month", currency="RUB", source=source, status=status, payment_id=payment,
                       pwa_inline_attempt_id=attempt, created_at=at or ago(hours=2),
                       paid_at=at if status != "failed" and payment else None)


def payment(number, user, status):
    return Payment(id=number, user_id=user, amount=500, currency="RUB", plan_type="1_month",
                   payment_status=status, payment_method="lava", source="pwa", base_amount=60)


class FunnelFixture:
    async def seed(self):
        async with self.sessions() as db:
            db.add_all([User(id=1, telegram_id=None, status="active"), User(id=2, telegram_id=2002, status="free")])
            await db.flush()
            db.add_all([payment(11, 1, "approved"), payment(12, 1, "refunded"), payment(13, 1, "pending"),
                        payment(14, 2, "approved"), payment(15, 2, "approved"), payment(16, 2, "approved")])
            await db.flush()
            db.add_all([
                # Paid attempt: two invoices (the first failed), one verified payment.
                ui("pwa_pro_opened", 1, "att-paid", ago(hours=3)),
                ui("pwa_pro_plan_selected", 1, "att-paid", ago(hours=3)),
                started(1, "att-paid", ago(hours=3), 1), started(1, "att-paid", ago(hours=2, minutes=50), 2),
                paid(1, "att-paid", ago(hours=2, minutes=40), 11, 2),
                invoice(1, 1, "failed", attempt="att-paid"),
                invoice(2, 1, "paid", payment=11, attempt="att-paid", at=ago(hours=2, minutes=40)),
                # Same account: a checkout whose webhook failed, then a UI failure event.
                ui("pwa_pro_opened", 1, "att-failed", ago(hours=1)),
                ui("pwa_pro_plan_selected", 1, "att-failed", ago(hours=1)),
                started(1, "att-failed", ago(minutes=55), 3),
                ui("pwa_pro_checkout_failed", 1, "att-failed", ago(minutes=50)),
                invoice(3, 1, "failed", attempt="att-failed"),
                # A click only.
                ui("pwa_pro_opened", 1, "att-click", ago(minutes=30)),
                # Paid, then refunded.
                ui("pwa_pro_opened", 1, "att-refund", ago(days=2)),
                ui("pwa_pro_plan_selected", 1, "att-refund", ago(days=2)),
                started(1, "att-refund", ago(days=2), 4),
                paid(1, "att-refund", ago(days=2), 12, 4),
                invoice(4, 1, "refunded", payment=12, attempt="att-refund", at=ago(days=2)),
                # A paid-looking row without an approved payment is not paid.
                ui("pwa_pro_opened", 1, "att-forged", ago(days=1)),
                started(1, "att-forged", ago(days=1), 5),
                paid(1, "att-forged", ago(days=1), 13, 5),
                # Another account's attempt from before the weekly window.
                ui("pwa_pro_opened", 2, "att-old", ago(days=40)),
                # Verified PWA Lava payment with no attempt: unlinked. A renewal
                # and a Mini App invoice are not attempts at all.
                invoice(6, 2, "paid", payment=14, at=ago(days=1)),
                invoice(7, 2, "paid", kind="renewal", payment=15, at=ago(days=1)),
                invoice(8, 2, "paid", source="miniapp", payment=16, at=ago(days=1)),
            ])
            await db.commit()

    async def funnel(self, since):
        async with self.sessions() as db:
            return await pwa_pro_attempt_funnel(db, since=since, now=NOW)

    async def test_attempt_stages_payment_reversal_and_unlinked(self):
        result = await self.funnel(ago(days=7))
        # att-paid and att-refund are paid; att-forged stops at checkout. A step
        # counts attempts that reached it or a later one, so the funnel never grows.
        self.assertEqual(result, {
            "attempts": 5,
            "steps": [{"key": "opened", "attempts": 5}, {"key": "plan_selected", "attempts": 4},
                      {"key": "checkout_started", "attempts": 4}, {"key": "paid", "attempts": 2}],
            "reversed": 1, "unlinked": 1,
        })

    async def test_cohort_is_the_attempts_first_stage(self):
        self.assertEqual((await self.funnel(None))["attempts"], 6)
        # Only the click and the failed checkout started in the last two hours.
        recent = await self.funnel(ago(hours=2))
        self.assertEqual((recent["attempts"], recent["steps"][3]["attempts"]), (2, 0))

    async def test_output_has_no_attempt_invoice_or_provider_ids(self):
        encoded = json.dumps(await self.funnel(None))
        for value in SECRET_IDS:
            self.assertNotIn(value, encoded)

    async def test_history_beyond_the_detail_row_limit_is_counted_exactly(self):
        # Audit #28: the funnel is aggregated in SQL, so the 5 000-row detail
        # limit of other readers can no longer make All time unavailable.
        extra = 2600
        async with self.sessions() as db:
            db.add_all([row for index in range(extra) for row in (
                ui("pwa_pro_opened", 2, f"bulk-{index}", ago(days=3)),
                ui("pwa_pro_plan_selected", 2, f"bulk-{index}", ago(days=3)))])
            await db.commit()
        with patch("app.admin_api.pwa_analytics_learning.DETAIL_LIMIT", 3):
            result = await self.funnel(None)
        self.assertEqual(result, {
            "attempts": 6 + extra,
            "steps": [{"key": "opened", "attempts": 6 + extra}, {"key": "plan_selected", "attempts": 4 + extra},
                      {"key": "checkout_started", "attempts": 4}, {"key": "paid", "attempts": 2}],
            "reversed": 1, "unlinked": 1,
        })


@unittest.skipUnless(URL.startswith("postgresql+asyncpg://"), "set ANALYTICS_TEST_DATABASE_URL")
class PwaProAttemptFunnelTests(FunnelFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = "pwa_pro_" + uuid4().hex
        self.engine = create_async_engine(URL, connect_args={"server_settings": {"search_path": self.schema}})
        async with self.engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA " + self.schema))
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        await self.seed()

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS " + self.schema + " CASCADE"))
        await self.engine.dispose()

    async def test_section_reports_it_beside_the_legacy_funnel_and_only_for_pwa(self):
        async with self.sessions() as db:
            views = {platform: await analytics.section_projection(
                db, analytics.AnalyticsRequest(section="funnel", platform=platform, period="weekly"),
                section="funnel") for platform in ("overall", "android", "telegram", "iphone_pwa")}
        for platform in ("overall", "iphone_pwa"):
            self.assertEqual(views[platform]["metrics"]["pwa_pro_attempt_funnel"]["attempts"], 5)
            self.assertEqual(views[platform]["metric_states"]["pwa_pro_attempt_funnel"]["state"], "available")
            self.assertIn("attempt_funnel", views[platform]["metrics"])
        for platform in ("android", "telegram"):
            self.assertNotIn("pwa_pro_attempt_funnel", views[platform]["metrics"])
            self.assertEqual(views[platform]["metric_states"]["pwa_pro_attempt_funnel"],
                             {"state": "not_applicable", "reason": "not_applicable"})



class SqlitePwaProAttemptFunnelTests(FunnelFixture, unittest.IsolatedAsyncioTestCase):
    """The same reader on SQLite JSON1, as the Admin PWA browser QA runs it."""

    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.directory.name}/funnel.db")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        await self.seed()

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.directory.cleanup()

    async def test_malformed_or_non_text_attempt_ids_are_not_attempts(self):
        async with self.sessions() as db:
            db.add_all([Funnel(user_id=2, event_name="pwa_pro_opened", source="v3_locked_lesson",
                               created_at=ago(hours=1), payload_json=payload)
                        for payload in ("{not json", '{"attempt_id": 7}', '{"attempt_id": ""}', None)])
            await db.commit()
        self.assertEqual((await self.funnel(ago(days=7)))["attempts"], 5)


if __name__ == "__main__":
    unittest.main()
