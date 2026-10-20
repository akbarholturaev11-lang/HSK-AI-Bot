"""P3 stage-2: isolated native AI/voice canonical ownership and migration tests."""

import asyncio
import importlib.util
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, Column, Integer, MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.ai_usage import AIUsageBudget, AIUsageEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.ai_service import AIUsageResult
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.api.android_live_voice import create_android_live_voice_router
from app.services.android_live_voice_service import live_voice_available
from app.services.desktop_auth_service import DesktopAuthService
from app.services.voice_practice_service import VoicePracticeError, VoicePracticeService


class NativeAccountAIVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            session.add_all([
                User(id=uid, telegram_id=tid, full_name="Learner", language="ru", level="hsk1",
                     status="free", payment_status="none", created_at=now, last_active_at=now)
                for uid, tid in ((1, None), (2, None), (3, 3003))
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_budget_expiry_and_usage_charge_only_the_internal_owner(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            service = AIUsageBudgetService(session)
            now = datetime.now(timezone.utc)
            args = dict(plan_type="pro_trial_7_days", amount=2, currency="usd", total_budget_usd=2,
                        starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(days=7))
            budget_a = await service.create_fixed_budget(telegram_id=alice, **args)
            budget_b = await service.create_fixed_budget(telegram_id=bob, **args)
            usage = AIUsageResult(content="你好", model="gpt-4o-mini", prompt_tokens=1000,
                                  completion_tokens=500, total_tokens=1500)
            await service.record_usage(alice, usage, "voice_practice_pronounce")
            self.assertGreater(budget_a.segment_1_spent_usd, 0)
            self.assertEqual(budget_b.segment_1_spent_usd, 0)
            self.assertIs(await service.get_active_budget(alice), budget_a)
            self.assertIs(await service.get_active_budget(bob), budget_b)
            event = (await session.execute(select(AIUsageEvent))).scalars().one()
            self.assertEqual((event.user_id, event.user_telegram_id, event.budget_id), (1, None, budget_a.id))
            self.assertEqual(await VoicePracticeService(session)._pronounce_count_today(alice), 1)
            self.assertEqual(await VoicePracticeService(session)._pronounce_count_today(bob), 0)
            await service.expire_active_budgets(alice)
            self.assertEqual(budget_a.status, "expired")
            self.assertEqual(budget_b.status, "active")
            self.assertIsNone(await service.get_active_budget(None))

    async def test_legacy_budget_lookup_remains_scoped_to_real_telegram_id(self):
        async with self.sessions() as session:
            legacy = await session.get(User, 3)
            service = AIUsageBudgetService(session)
            now = datetime.now(timezone.utc)
            budget = await service.create_fixed_budget(
                telegram_id=3003, plan_type="legacy", amount=1, currency="usd", total_budget_usd=1,
                starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(days=1),
            )
            self.assertIsNone(budget.user_id)
            self.assertIs(await service.get_active_budget(legacy), budget)
            self.assertIs(await service.get_active_budget(3003), budget)
            self.assertIsNone(await service.get_active_budget(await session.get(User, 1)))

    async def test_voice_reuse_ownership_and_daily_limits_are_per_native_account(self):
        async with self.sessions() as session:
            alice, bob = await session.get(User, 1), await session.get(User, 2)
            voice = VoicePracticeService(session)
            voice._course_context = AsyncMock(return_value={"lesson_id": None, "words": [], "review_words": []})
            voice._learner_plan = AsyncMock(return_value={})
            args = dict(role="friend", level="hsk1", language="ru", voice="female")
            a = await voice.start_session(alice, **args)
            b = await voice.start_session(bob, **args)
            again = await voice.start_session(alice, **args)
            self.assertNotEqual(a["session_id"], b["session_id"])
            self.assertEqual(a["session_id"], again["session_id"])
            owned = await voice._get_active_session(alice, a["session_id"])
            self.assertEqual((owned.user_id, owned.user_telegram_id), (1, None))
            for stranger in (bob, None, 1):
                with self.subTest(stranger=getattr(stranger, "id", stranger)):
                    with self.assertRaises(VoicePracticeError) as caught:
                        await voice._get_active_session(stranger, a["session_id"])
                    self.assertEqual(caught.exception.code, "SESSION_NOT_FOUND")
            owned.turn_count = 1
            await session.flush()
            self.assertEqual((await voice.user_status(alice))["remaining_voice_limit"], 0)
            self.assertGreater((await voice.user_status(bob))["remaining_voice_limit"], 0)
            self.assertEqual(await voice._pronounce_count_today(bob), 0)

    def test_live_voice_native_accounts_respect_rollout_and_budget_gates(self):
        settings = SimpleNamespace(ANDROID_VOICE_LIVE_ENABLED=True, GEMINI_API_KEY="test-key",
            GEMINI_BILLING_TIER="paid", ANDROID_VOICE_LIVE_MODEL="gemini-3.8-live",
            ANDROID_VOICE_LIVE_SESSION_BUDGET_USD=0.15, ANDROID_VOICE_LIVE_ALLOWED_USERS="3003")
        self.assertFalse(live_voice_available(settings, User(id=1, telegram_id=None)))
        self.assertTrue(live_voice_available(settings, User(id=3, telegram_id=3003)))
        settings.ANDROID_VOICE_LIVE_ALLOWED_USERS = "*"
        self.assertTrue(live_voice_available(settings, User(id=1, telegram_id=None)))
        # Gemini Live is now explicitly available with free-tier billing too.
        # Account-scoped rollout must remain enforced independently of tier.
        settings.GEMINI_BILLING_TIER = "free"
        self.assertTrue(live_voice_available(settings, User(id=1, telegram_id=None)))
        settings.ANDROID_VOICE_LIVE_ALLOWED_USERS = "3003"
        self.assertFalse(live_voice_available(settings, User(id=1, telegram_id=None)))
        settings.ANDROID_VOICE_LIVE_SESSION_BUDGET_USD = 0
        self.assertFalse(live_voice_available(settings, User(id=3, telegram_id=3003)))



# The live bearer/WebSocket transport E2E is tested with Universal OAuth after
# the remaining DesktopAuthService/NativeOAuth API components land.

class NativeAIVoiceMigrationTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0105_native_ai_voice_ownership.py"
        spec = importlib.util.spec_from_file_location("native_ai_voice_migration", path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        metadata = MetaData()
        users = Table("users", metadata, Column("id", Integer, primary_key=True),
                      Column("telegram_id", BigInteger, nullable=True, unique=True))
        for name in self.migration.TABLES:
            Table(name, metadata, Column("id", Integer, primary_key=True),
                  Column("user_telegram_id", BigInteger, nullable=False))
        metadata.create_all(self.connection)
        self.connection.execute(users.insert(), [{"id": 3, "telegram_id": 3003}, {"id": 1, "telegram_id": None}])
        for name in self.migration.TABLES:
            self.connection.execute(metadata.tables[name].insert(), {"id": 7, "user_telegram_id": 3003})
        self.operations = Operations(MigrationContext.configure(self.connection))

    def tearDown(self):
        self.connection.close()
        self.engine.dispose()

    def _upgrade(self):
        with patch.object(self.migration, "op", self.operations):
            self.migration.upgrade()

    def test_upgrade_backfills_legacy_ownership_and_supports_safe_native_cascade(self):
        self._upgrade()
        self._upgrade()  # The app's bootstrap may already have added columns.
        for name in self.migration.TABLES:
            with self.subTest(table=name):
                columns = {column["name"]: column for column in inspect(self.connection).get_columns(name)}
                self.assertTrue(columns["user_telegram_id"]["nullable"])
                self.assertEqual(self.connection.execute(text(f"SELECT user_id FROM {name} WHERE id=7")).scalar_one(), 3)
                self.connection.execute(text(f"INSERT INTO {name} (id,user_id,user_telegram_id) VALUES (8,1,NULL)"))
        self.connection.execute(text("DELETE FROM users WHERE id=1"))
        for name in self.migration.TABLES:
            self.assertEqual(self.connection.execute(text(f"SELECT count(*) FROM {name}")).scalar_one(), 1)

    def test_downgrade_refuses_native_data_before_changing_any_table(self):
        self._upgrade()
        self.connection.execute(text("INSERT INTO voice_practice_sessions (id,user_id,user_telegram_id) VALUES (8,1,NULL)"))
        with patch.object(self.migration, "op", self.operations), self.assertRaisesRegex(RuntimeError, "Provider-only"):
            self.migration.downgrade()
        for name in self.migration.TABLES:
            self.assertIn("user_id", {column["name"] for column in inspect(self.connection).get_columns(name)})

    def test_legacy_only_downgrade_preserves_original_records(self):
        self._upgrade()
        with patch.object(self.migration, "op", self.operations):
            self.migration.downgrade()
        for name in self.migration.TABLES:
            columns = {column["name"]: column for column in inspect(self.connection).get_columns(name)}
            self.assertNotIn("user_id", columns)
            self.assertFalse(columns["user_telegram_id"]["nullable"])
            self.assertEqual(self.connection.execute(text(f"SELECT user_telegram_id FROM {name} WHERE id=7")).scalar_one(), 3003)

    def test_bootstrap_foreign_key_names_also_support_legacy_only_downgrade(self):
        from sqlalchemy import ForeignKey
        engine = create_engine('sqlite:///:memory:')
        with engine.begin() as connection:
            metadata = MetaData()
            Table('users', metadata, Column('id', Integer, primary_key=True), Column('telegram_id', BigInteger))
            for name in self.migration.TABLES:
                Table(name, metadata, Column('id', Integer, primary_key=True),
                    Column('user_telegram_id', BigInteger, nullable=True),
                    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True))
            metadata.create_all(connection)
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(self.migration, 'op', operations):
                self.migration.upgrade()
                self.migration.downgrade()
            for name in self.migration.TABLES:
                self.assertNotIn('user_id', {column['name'] for column in inspect(connection).get_columns(name)})
        engine.dispose()
