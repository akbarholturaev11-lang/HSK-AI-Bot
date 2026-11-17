"""Rehearse additive migration 0155 (next-stage R3) on a legacy schema.

The column is nullable with no default, so existing entries keep NULL and stay
Overall-only. The upgrade is reentrant for metadata-first QA databases.
PostgreSQL upgrade/downgrade was rehearsed separately on local PostgreSQL.
"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

REVISION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic/versions/0155_subscription_entry_client.py"
)
INDEX = "ix_subscription_entry_events_client_created_at"


class SubscriptionEntryClientMigration0155Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.conn = self.engine.connect()
        self.conn.execute(text("""
            CREATE TABLE subscription_entry_events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                telegram_id BIGINT,
                source VARCHAR(80) NOT NULL,
                mode VARCHAR(40) NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """))
        self.conn.execute(text("""
            INSERT INTO subscription_entry_events (id, user_id, source, mode, created_at)
            VALUES (1, 42, 'android_subscription', 'subscription', '2026-11-01 10:00:00')
        """))
        self.conn.commit()
        spec = importlib.util.spec_from_file_location("entry_client_0155_qa", REVISION_PATH)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.ops = Operations(MigrationContext.configure(self.conn))

    def tearDown(self):
        self.conn.close()
        self.engine.dispose()

    def _run(self, step):
        with patch.object(self.migration, "op", self.ops):
            getattr(self.migration, step)()

    def _schema(self):
        inspector = inspect(self.conn)
        columns = {column["name"]: column for column in inspector.get_columns("subscription_entry_events")}
        indexes = {index["name"]: index["column_names"] for index in inspector.get_indexes("subscription_entry_events")}
        return columns, indexes

    def test_revision_is_linear_extension_of_li_onboarding_head(self):
        self.assertEqual(self.migration.revision, "0155_subscription_entry_client")
        self.assertEqual(self.migration.down_revision, "0154_li_onboarding_choices")

    def test_additive_upgrade_keeps_old_entries_unattributed(self):
        self._run("upgrade")
        self._run("upgrade")  # metadata-first QA also starts with the column present
        columns, indexes = self._schema()
        self.assertTrue(columns["client"]["nullable"])
        self.assertIsNone(columns["client"]["default"])
        self.assertEqual(indexes[INDEX], ["client", "created_at"])
        row = self.conn.execute(text("SELECT user_id, source, client FROM subscription_entry_events")).one()
        self.assertEqual(tuple(row), (42, "android_subscription", None))

    def test_downgrade_removes_only_the_new_column_and_index(self):
        self._run("upgrade")
        self._run("downgrade")
        columns, indexes = self._schema()
        self.assertNotIn("client", columns)
        self.assertNotIn(INDEX, indexes)
        row = self.conn.execute(text("SELECT user_id, source FROM subscription_entry_events")).one()
        self.assertEqual(tuple(row), (42, "android_subscription"))


if __name__ == "__main__":
    unittest.main()
