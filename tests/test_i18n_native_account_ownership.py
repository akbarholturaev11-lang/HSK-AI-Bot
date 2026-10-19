"""Native P3 ownership: provider-only accounts never share NULL Telegram events.

This stage validates canonical user-owned event semantics and migration/model
contracts without simulating provider OAuth, payments or production migration.
"""
import unittest
from datetime import datetime, timezone

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401 — register related table metadata
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.services.account_identity import owner_clause
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService


class NativeP3OwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=None, full_name="Google test account",
                     language="uz", level="nhsk2", created_at=now,
                     last_active_at=now),
                User(id=2, telegram_id=None, full_name="Apple test account",
                     language="tj", level="nhsk2", created_at=now,
                     last_active_at=now),
                User(id=3, telegram_id=3003, full_name="Telegram legacy account",
                     language="ru", level="nhsk2", created_at=now,
                     last_active_at=now),
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_two_provider_accounts_reuse_same_event_key_without_collision(self):
        async with self.sessions() as session:
            analytics = CourseMiniAppAnalyticsService(session)
            payload = dict(event_name="lesson_completed", lesson_order=16,
                           level="nhsk2", dedupe_key="native-course-complete:same-event")
            for uid in (1, 2):
                first = await analytics.record_server_event(
                    user_id=uid, telegram_id=None, **payload)
                self.assertTrue(first["ok"], first)
                self.assertTrue(first["recorded"], first)
                repeated = await analytics.record_server_event(
                    user_id=uid, telegram_id=None, **payload)
                self.assertTrue(repeated["ok"], repeated)
                self.assertFalse(repeated["recorded"])
                self.assertTrue(repeated["duplicate"])
            await session.commit()
            saved = (await session.execute(select(CourseMiniAppEvent))).scalars().all()
            self.assertEqual(len(saved), 2)
            self.assertEqual({row.user_id for row in saved}, {1, 2})
            self.assertTrue(all(row.telegram_id is None for row in saved))
            for uid in (1, 2):
                owner = await session.get(User, uid)
                mine = (await session.execute(
                    select(CourseMiniAppEvent).where(
                        owner_clause(CourseMiniAppEvent, owner, telegram_column="telegram_id")
                    )
                )).scalars().all()
                self.assertEqual(len(mine), 1)
                self.assertEqual(mine[0].user_id, uid)

    async def test_telegram_legacy_fallback_cannot_override_another_owner(self):
        async with self.sessions() as session:
            session.add_all([
                CourseMiniAppEvent(
                    user_id=None, telegram_id=3003, event_name="lesson_completed",
                    dedupe_key="legacy-tg-only",
                ),
                CourseMiniAppEvent(
                    user_id=1, telegram_id=3003, event_name="lesson_completed",
                    dedupe_key="stale-transport-must-not-win",
                ),
            ])
            await session.commit()
            telegram = await session.get(User, 3)
            owned = (await session.execute(select(CourseMiniAppEvent).where(
                owner_clause(CourseMiniAppEvent, telegram, telegram_column="telegram_id")
            ))).scalars().all()
            self.assertEqual([item.dedupe_key for item in owned], ["legacy-tg-only"])
            # A numeric legacy Telegram caller also must not own an explicitly
            # canonical row of another user, even if the metadata is stale.
            owned_by_number = (await session.execute(select(CourseMiniAppEvent).where(
                owner_clause(CourseMiniAppEvent, 3003, telegram_column="telegram_id")
            ))).scalars().all()
            self.assertEqual([item.dedupe_key for item in owned_by_number], ["legacy-tg-only"])
            google = await session.get(User, 1)
            google_owned = (await session.execute(select(CourseMiniAppEvent).where(
                owner_clause(CourseMiniAppEvent, google, telegram_column="telegram_id")
            ))).scalars().all()
            self.assertEqual([item.dedupe_key for item in google_owned], ["stale-transport-must-not-win"])

    def test_native_schema_contract_and_linear_migration_head(self):
        self.assertTrue(User.__table__.c.telegram_id.nullable)
        self.assertTrue(CourseMiniAppEvent.__table__.c.telegram_id.nullable)
        self.assertIn(
            "uq_course_miniapp_events_user_event_dedupe",
            {c.name for c in CourseMiniAppEvent.__table__.constraints},
        )
        script = ScriptDirectory.from_config(Config("alembic.ini"))
        self.assertEqual(script.get_heads(), ["0104_native_account_foundation"])


if __name__ == "__main__":
    unittest.main()
