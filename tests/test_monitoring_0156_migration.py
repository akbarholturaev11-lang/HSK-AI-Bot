"""Exercise the actual 0156 DDL on a disposable PostgreSQL schema."""
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

PATH = Path(__file__).resolve().parents[1] / "alembic/versions/0156_diagnostic_monitoring.py"


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"), "requires disposable monitoring PostgreSQL")
class MonitoringMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_upgrade_downgrade_and_protection_of_diagnostic_audit(self):
        spec = importlib.util.spec_from_file_location("diagnostic_migration_0156", PATH)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.down_revision, "0155_subscription_entry_client")

        def exercise(connection):
            ops = Operations(MigrationContext.configure(connection, opts={"target_metadata": Base.metadata}))
            with patch.object(migration, "op", ops):
                migration.downgrade()  # convert the empty ORM fixture to its immediate predecessor
                before = inspect(connection)
                self.assertNotIn("diagnostic_incidents", before.get_table_names())
                self.assertNotIn("diagnostic_kind", {c["name"] for c in before.get_columns("admin_pwa_push_outbox")})
                connection.execute(text("""INSERT INTO admin_pwa_inbox_triage
                    (source, source_id, status, priority, revision, updated_at)
                    VALUES ('technical', 41, 'read', 'important', 1, CURRENT_TIMESTAMP)"""))
                migration.upgrade()
                after = inspect(connection)
                self.assertIn("diagnostic_receipts", after.get_table_names())
                self.assertIn("ix_admin_pwa_outbox_diag_cap", {i["name"] for i in after.get_indexes("admin_pwa_push_outbox")})
                self.assertTrue(any("ON DELETE CASCADE" in clause for clause in connection.execute(text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'diagnostic_receipts'::regclass"
                )).scalars()))
                with self.assertRaises(IntegrityError), connection.begin_nested():
                    connection.execute(text("""INSERT INTO admin_pwa_inbox_triage
                        (source, source_id, status, priority, revision, updated_at)
                        VALUES ('arbitrary', 1, 'read', 'normal', 1, CURRENT_TIMESTAMP)"""))
                with connection.begin_nested() as diagnostic:
                    connection.execute(text("""INSERT INTO admin_pwa_inbox_triage
                        (source, source_id, status, priority, revision, updated_at)
                        VALUES ('diagnostic', 1, 'read', 'normal', 1, CURRENT_TIMESTAMP)"""))
                    with self.assertRaisesRegex(RuntimeError, "Archive diagnostic rows"):
                        migration.downgrade()
                    diagnostic.rollback()
                migration.downgrade()
                self.assertEqual(connection.execute(text("SELECT source, source_id FROM admin_pwa_inbox_triage")).one(),
                                 ("technical", 41))

        async with pg_sessions(PG_URL) as sessions:
            async with sessions() as db, db.begin():
                await (await db.connection()).run_sync(exercise)
