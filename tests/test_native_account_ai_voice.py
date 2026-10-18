"""AI budget charging and voice ownership for accounts without Telegram."""

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


class NativeAccountLiveTransportTests(unittest.TestCase):
    """Actual native bearer, real NULL-Telegram rows and WebSocket lease."""

    def setUp(self):
        self.temp = TemporaryDirectory(prefix="hsk-native-live-")
        self.engine = create_async_engine("sqlite+aiosqlite:///" + self.temp.name + "/native.db")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(
            DESKTOP_AUTH_SIGNING_SECRET="native-live-transport-" + "x" * 48,
            DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
            BOT_TOKEN="test-only", GEMINI_API_KEY="test-only", GEMINI_BILLING_TIER="paid",
            ANDROID_VOICE_LIVE_ENABLED=True, ANDROID_VOICE_LIVE_ALLOWED_USERS="*",
            ANDROID_VOICE_LIVE_MODEL="gemini-3.8-live", ANDROID_VOICE_LIVE_MAX_SECONDS=180,
            ANDROID_VOICE_LIVE_SESSION_BUDGET_USD=0.15,
        )
        self.connected = []

        @asynccontextmanager
        async def connector(settings, item):
            self.connected.append(item.id)

            async def receive():
                await asyncio.Event().wait()
                yield

            yield SimpleNamespace(receive=receive)

        app = FastAPI()
        app.include_router(create_android_live_voice_router(
            session_factory=self.sessions, settings_obj=self.settings, provider_connector=connector,
        ))
        self.client = TestClient(app)
        asyncio.run(self.seed())

    async def seed(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as session:
            session.add_all([User(id=uid, telegram_id=None, full_name="Native learner", status="free") for uid in (1, 2)])
            device = DesktopDevice(id="native-device", user_id=1, telegram_id=None,
                installation_key_hash="i" * 64, platform="android", app_version="1.0")
            native_session = DesktopSession(id="native-session", device_id=device.id,
                refresh_token_hash="r" * 64, expires_at=datetime.now(timezone.utc) + timedelta(days=1))
            session.add_all([device, native_session])
            for uid in (1, 2):
                session.add(VoicePracticeSession(id=f"native-live-{uid}", user_id=uid,
                    user_telegram_id=None, mode="live", role="friend", level="hsk1",
                    language="uz", voice="female", status="active", live_started_at=datetime.now(timezone.utc)))
            await session.commit()
            self.token, _ = DesktopAuthService(session, self.settings)._access_token(
                desktop_session=native_session, device=device,
            )

    def tearDown(self):
        asyncio.run(self.engine.dispose())
        self.temp.cleanup()

    def test_native_bearer_can_stream_own_session_and_releases_lease(self):
        with self.client, self.client.websocket_connect(
            "/api/v3/android/voice/live?session_id=native-live-1",
            headers={"Authorization": "Bearer " + self.token},
        ) as socket:
            self.assertEqual(socket.receive_json()["type"], "ready")
            socket.send_json({"type": "ping"})
            self.assertEqual(socket.receive_json()["type"], "pong")
            socket.send_json({"type": "stop"})
            self.assertEqual(socket.receive()["type"], "websocket.close")
        self.assertEqual(self.connected, ["native-live-1"])
        asyncio.run(self.assert_leases_released())

    async def assert_leases_released(self):
        async with self.sessions() as session:
            for uid in (1, 2):
                row = await session.get(VoicePracticeSession, f"native-live-{uid}")
                self.assertIsNone(row.live_connection_token)

    def test_other_null_telegram_accounts_session_never_opens_provider(self):
        with self.client, self.client.websocket_connect(
            "/api/v3/android/voice/live?session_id=native-live-2",
            headers={"Authorization": "Bearer " + self.token},
        ) as socket:
            self.assertEqual(socket.receive_json()["code"], "LIVE_SESSION_BUSY")
            self.assertEqual(socket.receive()["code"], 1008)
        self.assertFalse(self.connected)
        asyncio.run(self.assert_leases_released())


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
