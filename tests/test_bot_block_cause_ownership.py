"""Telegram block diagnostics use canonical history without foreign attribution."""

from datetime import datetime, timedelta, timezone
import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.bot_outbound_event import BotOutboundEvent
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.services.bot_block_cause_service import BotBlockCauseService


class BotBlockCauseOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.blocked_at = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=4004, status="free", bot_blocked_at=self.blocked_at,
                     created_at=self.blocked_at - timedelta(hours=1)),
                User(id=2, telegram_id=2002, status="free"),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_post_attachment_app_activity_includes_canonical_null_history_only(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = BotBlockCauseService(session)
            session.add(CourseMiniAppEvent(user_id=2, telegram_id=4004, event_name="desktop_app_opened",
                created_at=self.blocked_at + timedelta(minutes=1)))
            await session.flush()
            self.assertIsNone(await service._app_continuation_candidate(user, self.blocked_at))
            session.add(CourseMiniAppEvent(user_id=1, telegram_id=None, event_name="android_app_opened",
                created_at=self.blocked_at + timedelta(minutes=2)))
            await session.flush()
            result = await service._app_continuation_candidate(user, self.blocked_at)
            self.assertEqual(result["key"], "channel_migration")
            self.assertTrue(any("Android" in line for line in result["evidence"]))
            self.assertFalse(any("Desktop" in line for line in result["evidence"]))

    async def test_friction_uses_canonical_pre_attachment_history_and_rejects_foreign_metadata(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = BotBlockCauseService(session)
            session.add(ConversionFunnelEvent(user_id=2, telegram_id=4004, event_name="paywall_seen",
                created_at=self.blocked_at - timedelta(minutes=1)))
            await session.flush()
            self.assertIsNone(await service._friction_candidate(user, self.blocked_at))
            session.add(ConversionFunnelEvent(user_id=1, telegram_id=None, event_name="limit_hit",
                created_at=self.blocked_at - timedelta(minutes=5)))
            await session.flush()
            result = await service._friction_candidate(user, self.blocked_at)
            self.assertEqual(result["key"], "paywall_or_limit")
            self.assertTrue(any("limit" in line for line in result["evidence"]))
            self.assertFalse(any("to'lov oynasi" in line for line in result["evidence"]))

    async def test_onboarding_lesson_state_is_canonical_after_telegram_attachment(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = BotBlockCauseService(session)
            session.add(CourseMiniAppEvent(user_id=2, telegram_id=4004, event_name="lesson_started",
                created_at=self.blocked_at - timedelta(minutes=1)))
            await session.flush()
            self.assertIsNotNone(await service._onboarding_candidate(user, self.blocked_at))
            session.add(CourseMiniAppEvent(user_id=1, telegram_id=None, event_name="android_lesson_started",
                created_at=self.blocked_at - timedelta(minutes=5)))
            await session.flush()
            self.assertIsNone(await service._onboarding_candidate(user, self.blocked_at))

    async def test_foreign_outbound_rows_do_not_inflate_notification_pressure(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = BotBlockCauseService(session)
            for minute in (1, 2, 3, 4):
                session.add(BotOutboundEvent(user_id=2, telegram_id=4004, source="broadcast", status="sent",
                    created_at=self.blocked_at - timedelta(minutes=minute)))
            await session.flush()
            self.assertIsNone(await service._notification_candidate(user, self.blocked_at))
            session.add(BotOutboundEvent(user_id=1, telegram_id=4004, source="course_reminder", status="sent",
                created_at=self.blocked_at - timedelta(minutes=5)))
            await session.flush()
            result = await service._notification_candidate(user, self.blocked_at)
            self.assertEqual((result["key"], result["score"]), ("notification_pressure", 58))
            self.assertTrue(any("1 ta" in line for line in result["evidence"]))

    async def test_reachability_episode_ignores_foreign_owner_but_keeps_unowned_legacy_transport(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = BotBlockCauseService(session)
            session.add(BotReachabilityEvent(user_id=2, telegram_id=4004, event_type="blocked",
                source="my_chat_member_blocked", created_at=self.blocked_at))
            await session.flush()
            self.assertIsNone(await service._current_episode_event(user, self.blocked_at))
            legacy = BotReachabilityEvent(user_id=None, telegram_id=4004, event_type="blocked",
                source="broadcast", created_at=self.blocked_at)
            session.add(legacy)
            await session.flush()
            episode = await service._current_episode_event(user, self.blocked_at)
            self.assertEqual(episode.id, legacy.id)
