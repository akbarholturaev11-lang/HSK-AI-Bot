"""Native learners retain in-app notices without entering Telegram-only queues."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.bot_block_cause_service import BotBlockCauseService
from app.services.limit_notification_service import LimitNotificationService


class NativeTransportGuardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            session.add_all([
                User(id=uid, telegram_id=tid, language=lang, level=level, status=status,
                    payment_status="approved" if status == "active" else "none",
                    end_date=now + timedelta(days=10) if status == "active" else None)
                for uid, tid, lang, level, status in (
                    (1, None, "uz", "hsk1", "free"),
                    (2, None, "uz", "nhsk1", "free"),
                    (3, 3003, "uz", "hsk1", "free"),
                    (4, 4004, "uz", "nhsk1", "active"),
                    (5, 5005, "uz", "hsk1", "blocked"),
                    (6, 0, "uz", "hsk1", "free"),
                    (7, -7, "uz", "hsk1", "free"),
                    (8, 8008, "tj", "nhsk1", "free"),
                )
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_bot_ad_targets_require_positive_real_telegram_without_changing_existing_filters(self):
        async with self.sessions() as session:
            repo = UserRepository(session)
            self.assertEqual([user.id for user in await repo.get_ad_target_users()], [3, 8])
            self.assertEqual([user.id for user in await repo.get_ad_target_users(include_active_subscribers=True)], [3, 4, 8])
            self.assertEqual([user.id for user in await repo.get_ad_target_users(course_track="hsk20")], [3])
            self.assertEqual([user.id for user in await repo.get_ad_target_users(course_track="hsk30")], [8])
            self.assertEqual([user.id for user in await repo.get_ad_target_users(languages=["tj"])], [8])
            self.assertEqual([user.id for user in await repo.get_ad_target_users(level="nhsk1", include_active_subscribers=True)], [4, 8])
            # The general selector remains usable for universal admin/account work.
            self.assertEqual(len(await repo.get_filtered_users()), 8)

    async def test_two_native_accounts_receive_independent_deduplicated_feed_notices(self):
        async with self.sessions() as session:
            bot = SimpleNamespace(send_message=AsyncMock())
            service = LimitNotificationService(session)
            for uid in (1, 2):
                user = await session.get(User, uid)
                args = dict(level="hsk1", completed_parts=6, free_parts=6, bot=bot)
                self.assertEqual(await service.lesson_progress(user, **args), "spent")
                self.assertIsNone(await service.lesson_progress(user, **args))
            await session.commit()
            rows = (await session.scalars(select(CourseUserNotification))).all()
            self.assertEqual({(row.user_id, row.telegram_id) for row in rows}, {(1, None), (2, None)})
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row.action == "subscription" and row.key == "limit_lesson_spent" for row in rows))
            bot.send_message.assert_not_awaited()

    async def test_no_telegram_account_has_no_bot_block_diagnosis_or_telegram_queries(self):
        session = SimpleNamespace(execute=AsyncMock(side_effect=AssertionError("No Telegram history query")))
        for blocked_at in (None, datetime.now(timezone.utc)):
            user = SimpleNamespace(id=1, telegram_id=None, bot_blocked_at=blocked_at)
            result = await BotBlockCauseService(session).analyze(user)
            self.assertFalse(result["available"])
            self.assertEqual((result["key"], result["data_quality"], result["score"]), ("telegram_not_linked", "not_linked", 0))
            self.assertEqual((result["evidence"], result["alternatives"]), ([], []))
        session.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
