"""Purge follows the canonical owner even when old Telegram metadata conflicts."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.ai_usage import AIUsageBudget, AIUsageEvent
from app.db.models.android_push import AndroidPushToken
from app.db.models.bot_feedback import BotFeedback
from app.db.models.bot_outbound_event import BotOutboundEvent
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_ad import CourseAdView
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_pilot_event import CoursePilotEvent
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.entitlement_shadow_event import EntitlementShadowEvent
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.trial_risk_event import TrialRiskEvent
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.repositories.user_repo import UserRepository


class NativePurgeOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.admin = None
        url = os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL")
        if url:
            self.schema = "native_purge_" + uuid4().hex
            self.admin = create_async_engine(url)
            async with self.admin.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(url, connect_args={"server_settings": {"search_path": self.schema + ",public"}})
        else:
            self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
            @event.listens_for(self.engine.sync_engine, "connect")
            def foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([User(id=1, telegram_id=1001), User(id=2, telegram_id=None), User(id=3, telegram_id=1003)])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.admin:
            async with self.admin.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin.dispose()

    def records(self, uid, tid, suffix):
        return [
            AIUsageBudget(user_id=uid, user_telegram_id=tid, plan_type="fixture", amount=1, currency="usd",
                window_started_at=self.now, starts_at=self.now, ends_at=self.now + timedelta(days=1)),
            AIUsageEvent(user_id=uid, user_telegram_id=tid, source="fixture", model="fixture"),
            VoicePracticeSession(id="voice-" + suffix, user_id=uid, user_telegram_id=tid,
                role="friend", level="hsk1", language="uz", voice="alloy"),
            AccountNoticeDelivery(user_id=uid, telegram_id=tid, key="fixture", title="Notice", body="Fixture", status="failed"),
            BotOutboundEvent(user_id=uid, telegram_id=tid, source="fixture", status="sent"),
            BotReachabilityEvent(user_id=uid, telegram_id=tid, source="fixture", event_type="reachable"),
            ConversionFunnelEvent(user_id=uid, telegram_id=tid, event_name="lesson_started"),
            CourseMiniAppEvent(user_id=uid, telegram_id=tid, event_name="lesson_started"),
            CoursePilotEvent(user_id=uid, telegram_id=tid, level="hsk1", lesson_order=1, event_type="opened", step_name="start"),
            CourseUserNotification(user_id=uid, telegram_id=tid, key="fixture-" + suffix, title="Notice", body="Fixture"),
            SubscriptionEntryEvent(user_id=uid, telegram_id=tid, source="fixture"),
            CourseAdView(user_id=uid, user_telegram_id=tid, level="hsk1", lesson_order=1, placement="screen_center", watched_seconds=7),
            EntitlementShadowEvent(user_id=uid, telegram_id=tid, action="fixture-" + suffix, client="android", day_key="2026-10-18", agree=True),
        ]

    async def test_foreign_canonical_rows_survive_conflicting_telegram_metadata(self):
        async with self.sessions() as session:
            owned = self.records(1, 1003, "own")
            foreign = self.records(2, 1001, "foreign")
            legacy = self.records(None, 1001, "legacy")
            # NULL owners are legal only for legacy-capable tables.
            legacy = [row for row in legacy if row.__table__.c.user_id.nullable]
            session.add_all(owned + foreign + legacy)
            session.add_all([TrialRiskEvent(user_id=uid, telegram_id=tid, client="android", source="fixture")
                for uid, tid in ((1, 1003), (2, 1001))])
            session.add_all([BotFeedback(user_id=uid, telegram_id=tid) for uid, tid in ((1, 1003), (2, 1001))])
            await session.flush()
            keep = [(type(row), row.id) for row in foreign]
            removed = [(type(row), row.id) for row in owned + legacy]
            await session.commit()
            self.assertTrue(await UserRepository(session).delete_by_user_id(1))
            await session.commit()
            session.expire_all()
            for model, pk in keep:
                with self.subTest(table=model.__tablename__, expected="foreign preserved"):
                    row = await session.get(model, pk)
                    self.assertIsNotNone(row)
                    self.assertEqual(row.user_id, 2)
            for model, pk in removed:
                with self.subTest(table=model.__tablename__, expected="owner erased"):
                    self.assertIsNone(await session.get(model, pk))
            for model in (TrialRiskEvent, BotFeedback):
                self.assertEqual([row.user_id for row in await session.scalars(select(model))], [2])

    async def test_devices_and_pending_links_do_not_follow_foreign_telegram_metadata(self):
        async with self.sessions() as session:
            for uid, tid in ((1, None), (2, 1001)):
                session.add(DesktopDevice(id=f"device-{uid}", user_id=uid, telegram_id=tid,
                    installation_key_hash=f"install-{uid}", platform="android", app_version="1"))
            await session.flush()
            for uid in (1, 2):
                session.add_all([DesktopSession(id=f"session-{uid}", device_id=f"device-{uid}",
                    refresh_token_hash=f"refresh-{uid}", expires_at=self.now + timedelta(days=1)),
                    AndroidPushToken(device_id=f"device-{uid}", token=f"token-{uid}")])
            for label, bound, approved in (("own", 1, 1), ("foreign", 2, 2), ("legacy", None, None)):
                session.add(DesktopLinkRequest(id=label, bind_user_id=bound, approved_user_id=approved,
                    approved_telegram_id=1001, display_code_hash=label, polling_secret_hash=label,
                    installation_key_hash=label, platform="android", app_version="1", expires_at=self.now))
            await session.commit()
            await UserRepository(session).delete_by_user_id(1)
            await session.commit()
            for model, field in ((DesktopDevice, "id"), (DesktopSession, "id"), (AndroidPushToken, "device_id"), (DesktopLinkRequest, "id")):
                rows = list(await session.scalars(select(model)))
                self.assertEqual([getattr(row, field) for row in rows], [{DesktopDevice: "device-2", DesktopSession: "session-2",
                    AndroidPushToken: "device-2", DesktopLinkRequest: "foreign"}[model]])

    async def test_personal_campaigns_and_referrer_links_keep_canonical_precedence(self):
        async with self.sessions() as session:
            (await session.get(User, 2)).referrer_id = 3
            (await session.get(User, 2)).referred_by_telegram_id = 1001
            (await session.get(User, 3)).referrer_id = 1
            (await session.get(User, 3)).referred_by_telegram_id = 1003
            for cid, uid, tid in ((1, 1, None), (2, 2, 1001), (3, None, 1001), (4, None, None)):
                session.add(DiscountCampaign(id=cid, target_user_id=uid, target_telegram_id=tid,
                    title="fixture", percent=10, starts_at=self.now, ends_at=self.now + timedelta(days=1)))
            await session.commit()
            await UserRepository(session).delete_by_user_id(1)
            await session.commit()
            self.assertEqual({row.id for row in await session.scalars(select(DiscountCampaign))}, {2, 4})
            self.assertEqual(((await session.get(User, 2)).referrer_id, (await session.get(User, 2)).referred_by_telegram_id), (3, 1001))
            self.assertEqual(((await session.get(User, 3)).referrer_id, (await session.get(User, 3)).referred_by_telegram_id), (None, None))

    async def test_financial_retention_resolves_payment_owner_before_ledger_metadata(self):
        async with self.sessions() as session:
            session.add_all([Payment(id=pid, user_id=uid, user_telegram_id=tid, plan_type="1_month", amount=95,
                payment_status="approved") for pid, uid, tid in ((1, 1, None), (2, 2, 1001), (3, None, 1003))])
            await session.flush()
            session.add_all([PortfolioTransaction(id=pid, payment_id=pid, transaction_type="profit", source="subscription_profit",
                user_telegram_id=1001, amount_usd=9.5) for pid in (1, 2, 3)])
            await session.commit()
            await UserRepository(session).delete_by_user_id(1)
            await session.commit()
            self.assertEqual([(row.id, row.user_id, row.user_telegram_id, row.amount) for row in await session.scalars(select(Payment).order_by(Payment.id))],
                [(1, None, -1, 95), (2, 2, 1001, 95), (3, None, 1003, 95)])
            self.assertEqual([(row.id, row.user_telegram_id, row.amount_usd) for row in await session.scalars(select(PortfolioTransaction).order_by(PortfolioTransaction.id))],
                [(1, -1, 9.5), (2, 1001, 9.5), (3, 1001, 9.5)])

    async def test_native_shadow_and_personal_discount_purge_keeps_other_null_accounts(self):
        async with self.sessions() as session:
            (await session.get(User, 1)).telegram_id = None
            for uid in (1, 2):
                session.add_all([EntitlementShadowEvent(user_id=uid, action="chat", client="android", day_key="2026-10-18", agree=True),
                    DiscountCampaign(target_user_id=uid, title="fixture", percent=10, starts_at=self.now, ends_at=self.now + timedelta(days=1))])
            await session.commit()
            await UserRepository(session).delete_by_user_id(1)
            await session.commit()
            self.assertEqual([row.user_id for row in await session.scalars(select(EntitlementShadowEvent))], [2])
            self.assertEqual([row.target_user_id for row in await session.scalars(select(DiscountCampaign))], [2])
