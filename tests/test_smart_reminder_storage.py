"""Real additive migration and storage invariants, SQLite and isolated PostgreSQL."""
import asyncio
import importlib.util
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.autogenerate import compare_metadata
from sqlalchemy import delete, event, func, inspect, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.db.models.smart_reminder import (
    SmartReminderAttempt, SmartReminderCapability, SmartReminderConsent,
    SmartReminderJob, SmartReminderPreference,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "smart_storage_migration", ROOT / "alembic/versions/0133_smart_reminder_storage.py")
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)
TABLES = {name: Base.metadata.tables[name] for name in MIGRATION.TABLES}
PREF = SmartReminderPreference.__table__
CONSENT = SmartReminderConsent.__table__
CAPABILITY = SmartReminderCapability.__table__
JOB = SmartReminderJob.__table__
ATTEMPT = SmartReminderAttempt.__table__
PG_URL = os.environ.get("SMART_REMINDER_TEST_DATABASE_URL")


class StorageChecks:
    postgres = False

    async def asyncSetUp(self):
        self.admin = None
        if self.postgres:
            url = make_url(PG_URL)
            if (url.drivername != "postgresql+asyncpg" or
                    url.host not in {"127.0.0.1", "localhost", "::1"} or
                    not (url.database or "").startswith("smart_reminder_qa") or url.query):
                raise RuntimeError("Use a loopback disposable smart_reminder_qa database")
            self.schema = "smart_test_" + uuid4().hex
            self.admin = create_async_engine(url)
            async with self.admin.begin() as c:
                await c.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.engine = create_async_engine(url, connect_args={
                "server_settings": {"search_path": self.schema}})
        else:
            self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            @event.listens_for(self.engine.sync_engine, "connect")
            def foreign_keys(dbapi, _):
                dbapi.execute("PRAGMA foreign_keys=ON")
        self.now = datetime.now(timezone.utc)
        async with self.engine.begin() as c:
            await c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT, marker VARCHAR(32) NOT NULL)"))
            await c.execute(text("CREATE TABLE desktop_devices (id VARCHAR(36) PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE)"))
            await c.execute(text("CREATE TABLE legacy_study_flags (user_id INTEGER PRIMARY KEY REFERENCES users(id), enabled BOOLEAN NOT NULL)"))
            await c.execute(text("INSERT INTO users VALUES (1, 3001, 'retained'), (2, NULL, 'native')"))
            await c.execute(text("INSERT INTO desktop_devices VALUES ('qa-device-1', 1), ('qa-device-2', 2)"))
            await c.execute(text("INSERT INTO legacy_study_flags VALUES (1, false)"))
            await c.run_sync(self.migrate, "upgrade")

    @staticmethod
    def migrate(connection, operation):
        with Operations.context(MigrationContext.configure(connection)):
            getattr(MIGRATION, operation)()

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.admin is not None:
            async with self.admin.begin() as c:
                await c.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            await self.admin.dispose()

    def job(self, **values):
        start = datetime(2026, 10, 28, tzinfo=timezone.utc)
        return dict(id=str(uuid4()), user_id=1, local_day=date(2026, 10, 28),
                    timezone_name="Etc/UTC", day_start_utc=start,
                    day_end_utc=start + timedelta(days=1),
                    scheduled_at=start + timedelta(hours=12),
                    expires_at=start + timedelta(hours=14), policy_version="qa-v1") | values

    def attempt(self, job_id, **values):
        return dict(id=str(uuid4()), job_id=job_id, attempt_key=str(uuid4()),
                    channel="android", prepared_at=self.now,
                    expires_at=self.now + timedelta(minutes=10)) | values

    async def reject(self, c, table, values):
        with self.assertRaises(IntegrityError):
            async with c.begin_nested():
                await c.execute(insert(table).values(**values))

    async def test_actual_migration_is_additive_and_empty_roundtrip_preserves_legacy(self):
        async with self.engine.begin() as c:
            names = await c.run_sync(lambda s: set(inspect(s).get_table_names()))
            self.assertTrue(set(TABLES) <= names)
            for name, table in TABLES.items():
                self.assertEqual(await c.scalar(select(func.count()).select_from(table)), 0)
                columns = await c.run_sync(lambda s, n=name: inspect(s).get_columns(n))
                self.assertEqual({x["name"]: x["nullable"] for x in columns},
                                 {x.name: x.nullable for x in table.columns})
            def schema_diff(sync):
                context = MigrationContext.configure(sync, opts={
                    "compare_server_default": True,
                    "include_object": lambda obj, name, kind, reflected, other:
                        kind != "table" or name in TABLES,
                })
                return compare_metadata(context, Base.metadata)
            self.assertEqual(await c.run_sync(schema_diff), [])
            indexes = await c.run_sync(lambda s: inspect(s).get_indexes(JOB.name))
            self.assertIn("ix_smart_job_due", {x["name"] for x in indexes})
            await c.run_sync(self.migrate, "downgrade")
            names = await c.run_sync(lambda s: set(inspect(s).get_table_names()))
            self.assertFalse(set(TABLES) & names)
            self.assertFalse(await c.scalar(text("SELECT enabled FROM legacy_study_flags WHERE user_id=1")))
            self.assertEqual(await c.scalar(text("SELECT marker FROM users WHERE id=1")), "retained")
            await c.run_sync(self.migrate, "upgrade")

    async def test_new_rows_have_unknown_consent_capability_and_shadow_defaults(self):
        async with self.engine.begin() as c:
            await c.execute(insert(PREF).values(user_id=2))
            await c.execute(insert(CONSENT).values(user_id=2, channel="android",
                source_key="qa-device-2", device_id="qa-device-2", source="legacy_mirror"))
            await c.execute(insert(CAPABILITY).values(user_id=2, device_id="qa-device-2"))
            await c.execute(insert(JOB).values(**self.job(user_id=2)))
            pref = (await c.execute(select(PREF))).mappings().one()
            self.assertIsNone(pref["master_enabled"])
            self.assertIsNone(pref["action_at"])
            self.assertIsNone(pref["manual_time_local"])
            self.assertEqual((pref["revision"], pref["grant_epoch"], pref["time_mode"]), (0, 0, "auto"))
            consent = (await c.execute(select(CONSENT))).mappings().one()
            self.assertEqual(consent["state"], "unknown")
            self.assertIsNone(consent["action_at"])
            cap = (await c.execute(select(CAPABILITY))).mappings().one()
            self.assertEqual(cap["protocol_version"], 0)
            self.assertIsNone(cap["autonomous_study_disabled"])
            self.assertIsNone(cap["study_notifications_allowed"])
            self.assertIsNone(cap["observed_at"])
            self.assertEqual(await c.scalar(select(JOB.c.state)), "shadow")

    async def test_account_day_ownership_survives_cancel_and_attempt_key_is_unique(self):
        async with self.engine.begin() as c:
            job = self.job()
            await c.execute(insert(JOB).values(**job))
            await self.reject(c, JOB, self.job(selected_channel="telegram"))
            await c.execute(update(JOB).where(JOB.c.id == job["id"]).values(state="cancelled"))
            await self.reject(c, JOB, self.job())
            other = self.job(user_id=2)
            await c.execute(insert(JOB).values(**other))
            attempt = self.attempt(job["id"], state="unknown")
            await c.execute(insert(ATTEMPT).values(**attempt))
            await self.reject(c, ATTEMPT, self.attempt(other["id"], attempt_key=attempt["attempt_key"]))
            self.assertEqual(await c.scalar(select(ATTEMPT.c.state)), "unknown")

    async def test_source_key_dedupes_without_fabricating_off_action_time(self):
        async with self.engine.begin() as c:
            values = dict(user_id=1, channel="telegram", source_key="legacy_course_v1",
                          source="legacy_course", state="off")
            await c.execute(insert(CONSENT).values(**values))
            await self.reject(c, CONSENT, values | {"state": "on"})
            self.assertIsNone(await c.scalar(select(CONSENT.c.action_at)))
            await c.execute(insert(PREF).values(user_id=1, master_enabled=False, revision=4, grant_epoch=2))
            self.assertFalse(await c.scalar(select(PREF.c.master_enabled)))

    async def test_postgres_two_transactions_cannot_reserve_two_same_day_jobs(self):
        if not self.postgres:
            self.skipTest("SQLite in-memory is not a multi-connection PostgreSQL race")
        ready = asyncio.Event()
        arrivals = 0

        async def reserve():
            nonlocal arrivals
            async with self.engine.connect() as c:
                arrivals += 1
                if arrivals == 2:
                    ready.set()
                await asyncio.wait_for(ready.wait(), timeout=10)
                try:
                    async with c.begin():
                        await c.execute(insert(JOB).values(**self.job()))
                    return True
                except IntegrityError:
                    return False

        winners = await asyncio.wait_for(asyncio.gather(reserve(), reserve()), timeout=15)
        self.assertEqual(sorted(winners), [False, True])
        async with self.engine.connect() as c:
            self.assertEqual(await c.scalar(select(func.count()).select_from(JOB)), 1)

    async def test_invalid_state_time_window_epoch_and_endpoint_combinations_are_rejected(self):
        async with self.engine.begin() as c:
            for change in ({"state": "sent"}, {"grant_epoch": -1}, {"category": "weekly"},
                           {"expires_at": datetime(2026, 10, 30, tzinfo=timezone.utc)},
                           {"selected_device_id": "qa-device-1"},
                           {"selected_device_id": "qa-device-1", "selected_channel": "telegram"},
                           {"lease_token": "incomplete"}):
                with self.subTest(change=change):
                    await self.reject(c, JOB, self.job(**change))
            for change in ({"revision": -1}, {"time_mode": "manual_locked"},
                           {"channel_mode": "manual_locked"}, {"quiet_start": time(23)},
                           {"legacy_offset_minutes": 900}):
                await self.reject(c, PREF, dict(user_id=1) | change)
            await self.reject(c, CONSENT, dict(user_id=1, channel="android", source_key="x", source="qa", state="assumed"))
            await self.reject(c, CAPABILITY, dict(user_id=1, device_id="qa-device-1", observed_at=self.now))
            job = self.job()
            await c.execute(insert(JOB).values(**job))
            await self.reject(c, ATTEMPT, self.attempt(job["id"], expires_at=self.now))
            await self.reject(c, ATTEMPT, self.attempt(job["id"], channel="telegram", device_id="qa-device-1"))

    async def test_device_removal_preserves_off_provenance_and_unknown_attempt(self):
        async with self.engine.begin() as c:
            await c.execute(insert(PREF).values(user_id=1, master_enabled=False, revision=3, grant_epoch=3))
            await c.execute(insert(CONSENT).values(user_id=1, channel="android", source_key="qa-device-1",
                source="user_action", device_id="qa-device-1", state="off", action_at=self.now))
            await c.execute(insert(CAPABILITY).values(user_id=1, device_id="qa-device-1"))
            job = self.job(selected_channel="android", selected_device_id="qa-device-1")
            await c.execute(insert(JOB).values(**job))
            await c.execute(insert(ATTEMPT).values(**self.attempt(job["id"], device_id="qa-device-1", state="unknown")))
            await c.execute(text("DELETE FROM desktop_devices WHERE id='qa-device-1'"))
            self.assertEqual(await c.scalar(select(func.count()).select_from(CAPABILITY)), 0)
            self.assertIsNone(await c.scalar(select(CONSENT.c.device_id)))
            self.assertEqual(await c.scalar(select(CONSENT.c.state)), "off")
            self.assertIsNone(await c.scalar(select(JOB.c.selected_device_id)))
            self.assertIsNone(await c.scalar(select(ATTEMPT.c.device_id)))
            self.assertEqual(await c.scalar(select(ATTEMPT.c.state)), "unknown")
            self.assertFalse(await c.scalar(select(PREF.c.master_enabled)))

    async def test_user_and_job_foreign_key_cleanup_does_not_touch_other_owner(self):
        async with self.engine.begin() as c:
            for uid in (1, 2):
                device = f"qa-device-{uid}"
                await c.execute(insert(PREF).values(user_id=uid, master_enabled=False))
                await c.execute(insert(CONSENT).values(user_id=uid, channel="android", source_key=device, source="qa", device_id=device))
                await c.execute(insert(CAPABILITY).values(user_id=uid, device_id=device))
                job = self.job(user_id=uid)
                await c.execute(insert(JOB).values(**job))
                await c.execute(insert(ATTEMPT).values(**self.attempt(job["id"])))
            # Only test-owned fixtures. Financial/user purge policy is unchanged.
            await c.execute(text("DELETE FROM legacy_study_flags WHERE user_id=1"))
            await c.execute(text("DELETE FROM users WHERE id=1"))
            for table in TABLES.values():
                self.assertEqual(await c.scalar(select(func.count()).select_from(table)), 1)
            await c.execute(delete(JOB).where(JOB.c.user_id == 2))
            self.assertEqual(await c.scalar(select(func.count()).select_from(ATTEMPT)), 0)

    async def test_downgrade_refuses_every_populated_table_before_dropping_anything(self):
        async with self.engine.begin() as c:
            for target in MIGRATION.TABLES:
                for table in MIGRATION.TABLES:
                    await c.execute(delete(TABLES[table]))
                if target in {JOB.name, ATTEMPT.name}:
                    job = self.job(state="unknown")
                    await c.execute(insert(JOB).values(**job))
                    if target == ATTEMPT.name:
                        await c.execute(insert(ATTEMPT).values(**self.attempt(job["id"], state="unknown")))
                elif target == PREF.name:
                    await c.execute(insert(PREF).values(user_id=1, master_enabled=False))
                elif target == CONSENT.name:
                    await c.execute(insert(CONSENT).values(user_id=1, channel="telegram", source_key="qa", source="qa", state="off"))
                else:
                    await c.execute(insert(CAPABILITY).values(user_id=1, device_id="qa-device-1"))
                with self.subTest(target=target), self.assertRaisesRegex(RuntimeError, "Archive Smart Reminder"):
                    await c.run_sync(self.migrate, "downgrade")
                names = await c.run_sync(lambda s: set(inspect(s).get_table_names()))
                self.assertTrue(set(TABLES) <= names)
                self.assertGreater(await c.scalar(select(func.count()).select_from(TABLES[target])), 0)


class SmartReminderSQLiteStorageTests(StorageChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL, "requires an isolated loopback PostgreSQL test database")
class SmartReminderPostgresStorageTests(StorageChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class SmartReminderBootstrapContractTests(unittest.TestCase):
    def test_empty_initializer_leaves_smart_tables_to_the_reviewed_migration(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from scripts import qa_standalone_bootstrap as qa
        self.assertEqual(ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_heads(),
                         [qa.EXPECTED_HEAD])
        self.assertTrue(set(TABLES) <= qa.MIGRATION_CREATED_TABLES)
        initial = {table.name for table in qa._initial_schema_tables(qa._registered_model_metadata())}
        self.assertFalse(set(TABLES) & initial)
        self.assertIn("smart_reminder_mutations", qa.MIGRATION_CREATED_TABLES)
        self.assertNotIn("smart_reminder_mutations", initial)
