"""0108 keeps legacy facts while adding provider-independent audit ownership."""
import importlib.util
import os
from datetime import datetime
from pathlib import Path
import unittest
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401; register bootstrap tables
from app.db.base import Base


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0108_native_audit_ownership.py"
    spec = importlib.util.spec_from_file_location("native_audit_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _NativeAuditMigrationChecks:
    async def asyncSetUp(self):
        self.migration = migration()
        self.admin = None
        if self.postgres:
            url = os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL")
            if not url:
                self.skipTest("NATIVE_ACCOUNT_TEST_DATABASE_URL must name an isolated PostgreSQL test database")
            self.schema = "native_audit_migration_" + uuid4().hex
            self.admin = create_async_engine(url)
            async with self.admin.begin() as connection:
                await connection.execute(sa.text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(url, connect_args={
                "server_settings": {"search_path": self.schema + ",public"},
            })
        else:
            self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.connection = await self.engine.connect()
        if not self.postgres:
            await self.connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        await self.connection.run_sync(self._legacy_schema)

    async def asyncTearDown(self):
        if hasattr(self, "connection"):
            await self.connection.close()
            await self.engine.dispose()
        if self.admin is not None:
            async with self.admin.begin() as connection:
                await connection.execute(sa.text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin.dispose()

    @staticmethod
    def _legacy_schema(connection):
        for statement in (
            "CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT UNIQUE, status TEXT, payment_status TEXT, end_date TEXT, xp INTEGER)",
            "CREATE TABLE course_pilot_events (id INTEGER PRIMARY KEY, user_id INTEGER, telegram_id BIGINT NOT NULL, payload_json TEXT, CONSTRAINT fk_course_pilot_events_user_id_users FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL)",
            "CREATE INDEX ix_course_pilot_events_user_id ON course_pilot_events(user_id)",
            "CREATE TABLE entitlement_shadow_events (id INTEGER PRIMARY KEY, telegram_id BIGINT NOT NULL, action TEXT NOT NULL, client TEXT NOT NULL, day_key TEXT NOT NULL, agree BOOLEAN NOT NULL, detail_json TEXT, CONSTRAINT uq_entitlement_shadow_events_daily UNIQUE(telegram_id,action,client,day_key,agree))",
            "CREATE TABLE discount_campaigns (id INTEGER PRIMARY KEY, target_telegram_id BIGINT, title TEXT NOT NULL, percent INTEGER NOT NULL, quota_total INTEGER, is_active BOOLEAN NOT NULL)",
            "INSERT INTO users VALUES (1,1001,'active','approved','2026-12-01',555),(2,1002,'free','none',NULL,17),(3,NULL,'free','none',NULL,10),(4,NULL,'free','none',NULL,2),(5,-5,'free','none',NULL,0)",
            "INSERT INTO course_pilot_events VALUES (1,NULL,1001,'legacy'),(2,2,1001,'canonical wins'),(3,NULL,9999,'orphan'),(4,NULL,-5,'negative'),(5,NULL,0,'zero')",
            "INSERT INTO entitlement_shadow_events VALUES (1,1001,'lesson','android','2026-10-18',TRUE,'match'),(2,9999,'lesson','android','2026-10-18',FALSE,'orphan'),(3,-5,'lesson','android','2026-10-18',TRUE,'negative')",
            "INSERT INTO discount_campaigns VALUES (1,1001,'personal',20,2,TRUE),(2,NULL,'global',10,10,TRUE),(3,9999,'unknown Telegram',15,NULL,FALSE),(4,-5,'negative',5,NULL,FALSE)",
        ):
            connection.exec_driver_sql(statement)

    def _upgrade(self, connection):
        with Operations.context(MigrationContext.configure(connection)):
            self.migration.upgrade()

    def _downgrade(self, connection):
        with Operations.context(MigrationContext.configure(connection)):
            self.migration.downgrade()

    @staticmethod
    def _schema(connection):
        inspector = sa.inspect(connection)
        return {
            table: {
                "columns": [column | {"type": str(column["type"])} for column in inspector.get_columns(table)],
                "foreign_keys": inspector.get_foreign_keys(table),
                "indexes": inspector.get_indexes(table),
                "unique": inspector.get_unique_constraints(table),
            }
            for table in ("course_pilot_events", "entitlement_shadow_events", "discount_campaigns")
        }

    def _assert_integrity_error(self, connection, statement):
        with self.assertRaises(sa.exc.IntegrityError):
            with connection.begin_nested():
                connection.execute(sa.text(statement))

    async def test_upgrade_preserves_all_legacy_facts_and_existing_canonical_precedence(self):
        def check(connection):
            users = connection.execute(sa.text("SELECT * FROM users ORDER BY id")).all()
            before = {table: connection.execute(sa.text(f"SELECT * FROM {table} ORDER BY id")).all()
                      for table in self.migration.OWNERS}
            self._upgrade(connection)
            first_schema = self._schema(connection)
            self._upgrade(connection)
            self.assertEqual(self._schema(connection), first_schema)
            self.assertEqual(connection.execute(sa.text("SELECT * FROM users ORDER BY id")).all(), users)
            for table, rows in before.items():
                legacy_columns = {"course_pilot_events": "id,user_id,telegram_id,payload_json",
                                  "entitlement_shadow_events": "id,telegram_id,action,client,day_key,agree,detail_json",
                                  "discount_campaigns": "id,target_telegram_id,title,percent,quota_total,is_active"}[table]
                after = connection.execute(sa.text(f"SELECT {legacy_columns} FROM {table} ORDER BY id")).all()
                if table == "course_pilot_events":
                    rows = [(row.id, 1 if row.id == 1 else row.user_id, row.telegram_id, row.payload_json) for row in rows]
                self.assertEqual(after, rows, table)
            self.assertEqual(connection.execute(sa.text("SELECT user_id FROM course_pilot_events ORDER BY id")).all(),
                             [(1,), (2,), (None,), (None,), (None,)])
            self.assertEqual(connection.execute(sa.text("SELECT user_id FROM entitlement_shadow_events ORDER BY id")).all(),
                             [(1,), (None,), (None,)])
            self.assertEqual(connection.execute(sa.text("SELECT target_user_id FROM discount_campaigns ORDER BY id")).all(),
                             [(1,), (None,), (None,), (None,)])
        await self.connection.run_sync(check)

    async def test_native_diagnostics_keep_separate_owners_and_both_shadow_outcomes(self):
        def check(connection):
            self._upgrade(connection)
            connection.execute(sa.text("INSERT INTO course_pilot_events VALUES (20,3,NULL,'native Google'),(21,4,NULL,'native Apple')"))
            connection.execute(sa.text("INSERT INTO entitlement_shadow_events (id,user_id,telegram_id,action,client,day_key,agree,detail_json) VALUES (20,3,NULL,'lesson','android','2026-10-18',TRUE,'native match'),(21,4,NULL,'lesson','android','2026-10-18',TRUE,'other native match'),(22,3,NULL,'lesson','android','2026-10-18',FALSE,'native mismatch')"))
            self._assert_integrity_error(connection, "INSERT INTO entitlement_shadow_events (id,user_id,telegram_id,action,client,day_key,agree) VALUES (23,3,NULL,'lesson','android','2026-10-18',TRUE)")
            # Attaching Telegram must not open a second sample for the same user.
            connection.execute(sa.text("UPDATE users SET telegram_id=3003 WHERE id=3"))
            self._assert_integrity_error(connection, "INSERT INTO entitlement_shadow_events (id,user_id,telegram_id,action,client,day_key,agree) VALUES (24,3,3003,'lesson','android','2026-10-18',TRUE)")
            self.assertEqual(connection.execute(sa.text("SELECT user_id,telegram_id FROM entitlement_shadow_events WHERE id>=20 ORDER BY id")).all(),
                             [(3, None), (4, None), (3, None)])
            for table in ("course_pilot_events", "entitlement_shadow_events"):
                self.assertTrue({column["name"]: column for column in sa.inspect(connection).get_columns(table)}["telegram_id"]["nullable"])
        await self.connection.run_sync(check)

    async def test_fk_actions_delete_personal_offer_without_making_it_global(self):
        def check(connection):
            self._upgrade(connection)
            connection.execute(sa.text("INSERT INTO course_pilot_events VALUES (20,3,NULL,'native')"))
            connection.execute(sa.text("INSERT INTO entitlement_shadow_events (id,user_id,telegram_id,action,client,day_key,agree) VALUES (20,3,NULL,'lesson','android','2026-10-18',TRUE)"))
            connection.execute(sa.text("INSERT INTO discount_campaigns (id,target_user_id,target_telegram_id,title,percent,is_active) VALUES (20,3,NULL,'native personal',25,TRUE)"))
            connection.execute(sa.text("DELETE FROM users WHERE id=3"))
            self.assertEqual(connection.execute(sa.text("SELECT user_id,telegram_id FROM course_pilot_events WHERE id=20")).one(), (None, None))
            self.assertEqual(connection.execute(sa.text("SELECT user_id,telegram_id FROM entitlement_shadow_events WHERE id=20")).one(), (None, None))
            self.assertIsNone(connection.execute(sa.text("SELECT id FROM discount_campaigns WHERE id=20")).first())
            self.assertEqual(connection.execute(sa.text("SELECT target_user_id,target_telegram_id,title,percent FROM discount_campaigns WHERE id=2")).one(), (None, None, "global", 10))
            for table, (owner, _telegram, action) in self.migration.OWNERS.items():
                fk = next(fk for fk in sa.inspect(connection).get_foreign_keys(table) if fk["constrained_columns"] == [owner])
                self.assertEqual(fk["options"].get("ondelete"), action)
                self.assertIn(f"ix_{table}_{owner}", {index["name"] for index in sa.inspect(connection).get_indexes(table)})
        await self.connection.run_sync(check)

    async def test_existing_bootstrap_owner_columns_never_get_reassigned(self):
        def check(connection):
            connection.execute(sa.text("ALTER TABLE entitlement_shadow_events ADD COLUMN user_id INTEGER"))
            connection.execute(sa.text("ALTER TABLE discount_campaigns ADD COLUMN target_user_id INTEGER"))
            connection.execute(sa.text("UPDATE entitlement_shadow_events SET user_id=2 WHERE id=1"))
            connection.execute(sa.text("UPDATE discount_campaigns SET target_user_id=2 WHERE id=1"))
            self._upgrade(connection)
            self._upgrade(connection)
            self.assertEqual(connection.execute(sa.text("SELECT user_id FROM entitlement_shadow_events WHERE id=1")).scalar_one(), 2)
            self.assertEqual(connection.execute(sa.text("SELECT target_user_id FROM discount_campaigns WHERE id=1")).scalar_one(), 2)
            for table in self.migration.OWNERS:
                self.assertEqual(len(sa.inspect(connection).get_foreign_keys(table)), 1)
        await self.connection.run_sync(check)

    async def test_safe_downgrade_keeps_global_and_unknown_telegram_personal_offers(self):
        def check(connection):
            # Remove the deliberately conflicting pilot owner for a lossless rollback.
            connection.execute(sa.text("UPDATE course_pilot_events SET user_id=1 WHERE id=2"))
            self._upgrade(connection)
            before = {table: connection.execute(sa.text(f"SELECT * FROM {table} ORDER BY id")).all()
                      for table in self.migration.OWNERS}
            self._downgrade(connection)
            for table, rows in before.items():
                if table != "course_pilot_events":
                    rows = [tuple(row[:-1]) for row in rows]
                self.assertEqual(connection.execute(sa.text(f"SELECT * FROM {table} ORDER BY id")).all(), rows)
            columns = {column["name"] for column in sa.inspect(connection).get_columns("discount_campaigns")}
            self.assertNotIn("target_user_id", columns)
            self.assertNotIn("user_id", {column["name"] for column in sa.inspect(connection).get_columns("entitlement_shadow_events")})
            self.assertIn("user_id", {column["name"] for column in sa.inspect(connection).get_columns("course_pilot_events")})
            for table in ("course_pilot_events", "entitlement_shadow_events"):
                self.assertFalse({column["name"]: column for column in sa.inspect(connection).get_columns(table)}["telegram_id"]["nullable"])
        await self.connection.run_sync(check)

    async def test_native_or_conflicting_downgrade_refuses_before_any_schema_change(self):
        def check(connection):
            connection.execute(sa.text("UPDATE course_pilot_events SET user_id=1 WHERE id=2"))
            self._upgrade(connection)
            for table, (owner, telegram, _action) in self.migration.OWNERS.items():
                for tid in (None, 1001):
                    with self.subTest(table=table, telegram_id=tid):
                        row = connection.execute(sa.text(f"SELECT {owner},{telegram} FROM {table} WHERE id=1")).one()
                        connection.execute(sa.text(f"UPDATE {table} SET {owner}=3,{telegram}=:tid WHERE id=1"), {"tid": tid})
                        schema = self._schema(connection)
                        facts = {name: connection.execute(sa.text(f"SELECT * FROM {name} ORDER BY id")).all() for name in self.migration.OWNERS}
                        with self.assertRaisesRegex(RuntimeError, "Native ownership|Canonical ownership"):
                            self._downgrade(connection)
                        self.assertEqual(self._schema(connection), schema)
                        self.assertEqual({name: connection.execute(sa.text(f"SELECT * FROM {name} ORDER BY id")).all() for name in self.migration.OWNERS}, facts)
                        connection.execute(sa.text(f"UPDATE {table} SET {owner}=:uid,{telegram}=:tid WHERE id=1"), {"uid": row[0], "tid": row[1]})
        await self.connection.run_sync(check)

    async def test_duplicate_shadow_samples_refuse_upgrade_without_discarding_rows(self):
        def check(connection):
            connection.execute(sa.text("ALTER TABLE entitlement_shadow_events ADD COLUMN user_id INTEGER"))
            connection.execute(sa.text("INSERT INTO entitlement_shadow_events (id,user_id,telegram_id,action,client,day_key,agree,detail_json) VALUES (20,1,1002,'lesson','android','2026-10-18',TRUE,'must not discard')"))
            before = connection.execute(sa.text("SELECT * FROM entitlement_shadow_events ORDER BY id")).all()
            schema = self._schema(connection)
            with self.assertRaisesRegex(RuntimeError, "Duplicate canonical shadow samples"):
                self._upgrade(connection)
            self.assertEqual(connection.execute(sa.text("SELECT * FROM entitlement_shadow_events ORDER BY id")).all(), before)
            self.assertEqual(self._schema(connection), schema)
        await self.connection.run_sync(check)

    async def test_unexpected_existing_foreign_key_refuses_upgrade_before_ddl(self):
        def check(connection):
            connection.execute(sa.text("DROP TABLE discount_campaigns"))
            connection.execute(sa.text("CREATE TABLE discount_campaigns (id INTEGER PRIMARY KEY, target_user_id INTEGER, target_telegram_id BIGINT, CONSTRAINT wrong_personal_offer_fk FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE SET NULL)"))
            connection.execute(sa.text("INSERT INTO discount_campaigns VALUES (1,3,NULL)"))
            schema = self._schema(connection)
            with self.assertRaisesRegex(RuntimeError, "Unexpected canonical ownership foreign key"):
                self._upgrade(connection)
            self.assertEqual(self._schema(connection), schema)
            self.assertEqual(connection.execute(sa.text("SELECT * FROM discount_campaigns")).one(), (1, 3, None))
        await self.connection.run_sync(check)

    async def test_create_all_schema_upgrade_is_idempotent_and_keeps_native_rows(self):
        def check(connection):
            for table in reversed(list(self.migration.OWNERS)):
                connection.execute(sa.text(f"DROP TABLE {table}"))
            connection.execute(sa.text("DROP TABLE users"))
            Base.metadata.create_all(connection)
            connection.execute(Base.metadata.tables["users"].insert().values(id=1, telegram_id=None))
            connection.execute(Base.metadata.tables["course_pilot_events"].insert().values(id=1, user_id=1, telegram_id=None, level="hsk1", lesson_order=1, event_type="started", step_name="lesson"))
            connection.execute(Base.metadata.tables["entitlement_shadow_events"].insert().values(id=1, user_id=1, telegram_id=None, action="lesson", client="android", day_key="2026-10-18", agree=True))
            connection.execute(Base.metadata.tables["discount_campaigns"].insert().values(id=1, target_user_id=1, target_telegram_id=None, title="Personal", percent=20, starts_at=sa.func.now(), ends_at=sa.func.now()))
            before = self._schema(connection)
            self._upgrade(connection)
            self._upgrade(connection)
            self.assertEqual(self._schema(connection), before)
            for table, (owner, telegram, _action) in self.migration.OWNERS.items():
                self.assertEqual(connection.execute(sa.text(f"SELECT {owner},{telegram} FROM {table} WHERE id=1")).one(), (1, None))
        await self.connection.run_sync(check)

    async def test_bootstrap_legacy_downgrade_preserves_data_with_existing_model_foreign_keys(self):
        def check(connection):
            for table in reversed(list(self.migration.OWNERS)):
                connection.execute(sa.text(f"DROP TABLE {table}"))
            connection.execute(sa.text("DROP TABLE users"))
            Base.metadata.create_all(connection)
            connection.execute(Base.metadata.tables["users"].insert().values(id=1, telegram_id=1001))
            connection.execute(Base.metadata.tables["course_pilot_events"].insert().values(id=1, user_id=1, telegram_id=1001, level="hsk1", lesson_order=1, event_type="started", step_name="lesson"))
            connection.execute(Base.metadata.tables["entitlement_shadow_events"].insert().values(id=1, user_id=1, telegram_id=1001, action="lesson", client="android", day_key="2026-10-18", agree=True))
            connection.execute(Base.metadata.tables["discount_campaigns"].insert(), [
                {"id": 1, "target_user_id": 1, "target_telegram_id": 1001, "title": "Personal", "percent": 20, "starts_at": datetime(2026, 10, 18), "ends_at": datetime(2026, 11, 18)},
                {"id": 2, "target_user_id": None, "target_telegram_id": None, "title": "Global", "percent": 10, "starts_at": datetime(2026, 10, 18), "ends_at": datetime(2026, 11, 18)},
            ])
            self._upgrade(connection)
            self._downgrade(connection)
            self.assertEqual(connection.execute(sa.text("SELECT user_id,telegram_id FROM course_pilot_events")).one(), (1, 1001))
            self.assertEqual(connection.execute(sa.text("SELECT telegram_id,action,agree FROM entitlement_shadow_events")).one(), (1001, "lesson", True))
            self.assertEqual(connection.execute(sa.text("SELECT target_telegram_id,title,percent FROM discount_campaigns ORDER BY id")).all(), [(1001, "Personal", 20), (None, "Global", 10)])
            for table, owner in (("entitlement_shadow_events", "user_id"), ("discount_campaigns", "target_user_id")):
                self.assertNotIn(owner, {column["name"] for column in sa.inspect(connection).get_columns(table)})
        await self.connection.run_sync(check)


class NativeAuditMigrationSQLiteTests(_NativeAuditMigrationChecks, unittest.IsolatedAsyncioTestCase):
    postgres = False


class NativeAuditMigrationPostgreSQLTests(_NativeAuditMigrationChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
