"""Actual additive 0161 DDL, existing PWA CHECK and lossless rollback guard."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from tests.monitoring_chain import PG_URL, pg_sessions

PATH = Path(__file__).resolve().parents[1] / "alembic/versions/0161_android_pro_funnel.py"


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"), "requires disposable PostgreSQL")
class AndroidProMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_upgrade_keeps_existing_events_and_downgrade_refuses_populated_attribution(self):
        spec = importlib.util.spec_from_file_location("native_pro_migration", PATH)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.down_revision, "0160_smart_routing_pwa_state")

        def exercise(connection):
            with patch.object(migration, "op", Operations(MigrationContext.configure(connection, opts={"target_metadata": Base.metadata}))):
                migration.downgrade()
                self.assertNotIn("android_inline_attempt_id", {c["name"] for c in inspect(connection).get_columns("lava_invoices")})
                connection.execute(text("INSERT INTO conversion_funnel_events (event_name,created_at) VALUES ('pwa_pro_opened',CURRENT_TIMESTAMP)"))
                with self.assertRaises(IntegrityError), connection.begin_nested():
                    connection.execute(text("INSERT INTO conversion_funnel_events (event_name,created_at) VALUES ('android_pro_opened',CURRENT_TIMESTAMP)"))
                migration.upgrade()
                self.assertIn("android_inline_attempt_id", {c["name"] for c in inspect(connection).get_columns("lava_invoices")})
                with connection.begin_nested() as savepoint:
                    connection.execute(text("INSERT INTO conversion_funnel_events (event_name,created_at) VALUES ('android_pro_opened',CURRENT_TIMESTAMP)"))
                    with self.assertRaisesRegex(RuntimeError, "would_lose_attribution"):
                        migration.downgrade()
                    savepoint.rollback()
                with connection.begin_nested() as savepoint:
                    connection.execute(text("""INSERT INTO lava_invoices
                        (contract_id,kind,user_id,plan_type,currency,source,status,android_inline_attempt_id,created_at,updated_at)
                        VALUES ('migration-fixture','first',1,'1_month','USD','android','created','native-fixture',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"""))
                    with self.assertRaisesRegex(RuntimeError, "would_lose_attribution"):
                        migration.downgrade()
                    savepoint.rollback()
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM conversion_funnel_events WHERE event_name='pwa_pro_opened'")), 1)
                migration.downgrade()
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM conversion_funnel_events")), 1)
                migration.upgrade()

        async with pg_sessions(PG_URL) as sessions:
            async with sessions.kw["bind"].begin() as connection:
                await connection.run_sync(exercise)
