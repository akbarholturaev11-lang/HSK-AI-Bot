"""Additive learner Web Push migration is reversible only when empty."""
import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic/versions/0147_learner_pwa_push.py"
SPEC = importlib.util.spec_from_file_location("learner_pwa_push_0147", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class LearnerPwaPushMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.connection.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        self.connection.exec_driver_sql(
            "CREATE TABLE desktop_devices (id VARCHAR(36) PRIMARY KEY, user_id INTEGER NOT NULL)"
        )
        self.context = MigrationContext.configure(self.connection)

    def tearDown(self):
        self.connection.close()
        self.engine.dispose()

    def upgrade(self):
        with Operations.context(self.context):
            MIGRATION.upgrade()

    def downgrade(self):
        with Operations.context(self.context):
            MIGRATION.downgrade()

    def tables(self):
        return {
            row[0] for row in self.connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    def test_empty_upgrade_and_downgrade_round_trip(self):
        self.upgrade()
        self.assertTrue({
            "learner_pwa_push_subscriptions", "learner_pwa_push_outbox",
        } <= self.tables())
        self.downgrade()
        self.assertFalse({
            "learner_pwa_push_subscriptions", "learner_pwa_push_outbox",
        } & self.tables())

    def test_populated_downgrade_refuses_before_dropping_either_table(self):
        self.connection.exec_driver_sql("INSERT INTO users(id) VALUES (1)")
        self.connection.exec_driver_sql(
            "INSERT INTO desktop_devices(id, user_id) VALUES ('device-1', 1)"
        )
        self.upgrade()
        self.connection.exec_driver_sql(
            "INSERT INTO learner_pwa_push_subscriptions "
            "(id, device_id, endpoint_hash, encrypted_payload, created_at, updated_at) "
            "VALUES ('sub-1', 'device-1', ?, 'ciphertext', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("a" * 64,),
        )
        with self.assertRaisesRegex(RuntimeError, "Refusing downgrade"):
            self.downgrade()
        self.assertTrue({
            "learner_pwa_push_subscriptions", "learner_pwa_push_outbox",
        } <= self.tables())
        self.assertEqual(self.connection.exec_driver_sql(
            "SELECT COUNT(*) FROM learner_pwa_push_subscriptions"
        ).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
