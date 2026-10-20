"""Payment ownership backfill preserves money, anonymous facts and safe rollback."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


class NativePaymentMigrationTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0106_canonical_payment_ownership.py"
        spec = importlib.util.spec_from_file_location("native_payment_migration", path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self.connection.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT UNIQUE)")
        self.connection.exec_driver_sql("CREATE TABLE payments (id INTEGER PRIMARY KEY, user_telegram_id BIGINT NOT NULL, amount INTEGER NOT NULL, payment_status TEXT NOT NULL)")
        self.connection.exec_driver_sql("CREATE TABLE subscription_entry_events (id INTEGER PRIMARY KEY, user_id INTEGER, telegram_id BIGINT NOT NULL, source TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL)")
        self.connection.exec_driver_sql("INSERT INTO users VALUES (1,1001),(2,NULL),(3,-3)")
        self.connection.exec_driver_sql("INSERT INTO payments VALUES (10,1001,95,'approved'),(11,9999,250,'approved'),(12,-1,95,'approved'),(13,-3,10,'pending')")
        self.connection.exec_driver_sql("INSERT INTO subscription_entry_events VALUES (1,NULL,1001,'legacy'),(2,2,1001,'canonical'),(3,NULL,9999,'orphan'),(4,NULL,-3,'anonymous')")
        self.operations = Operations(MigrationContext.configure(self.connection))

    def tearDown(self):
        self.connection.close()
        self.engine.dispose()

    def _upgrade(self):
        with patch.object(self.migration, "op", self.operations):
            self.migration.upgrade()

    def _columns(self):
        return {column["name"]: column for column in sa.inspect(self.connection).get_columns("payments")}

    def test_upgrade_backfills_only_real_telegram_owners_without_altering_financial_facts(self):
        before = self.connection.execute(sa.text("SELECT * FROM payments ORDER BY id")).all()
        self._upgrade()
        self._upgrade()
        self.assertEqual(self.connection.execute(sa.text(
            "SELECT id,user_telegram_id,amount,payment_status FROM payments ORDER BY id"
        )).all(), before)
        self.assertEqual(self.connection.execute(sa.text("SELECT user_id FROM payments ORDER BY id")).all(),
                         [(1,), (None,), (None,), (None,)])
        self.assertTrue(self._columns()["user_telegram_id"]["nullable"])
        self.assertTrue(self._columns()["user_id"]["nullable"])
        self.assertIn("ix_payments_user_id", {index["name"] for index in sa.inspect(self.connection).get_indexes("payments")})
        self.assertEqual(sa.inspect(self.connection).get_foreign_keys("payments"), [])
        self.assertEqual(self.connection.execute(sa.text("SELECT id,user_id,telegram_id FROM subscription_entry_events ORDER BY id")).all(),
                         [(1, 1, 1001), (2, 2, 1001), (3, None, 9999), (4, None, -3)])
        self.assertTrue({c["name"]: c for c in sa.inspect(self.connection).get_columns("subscription_entry_events")}["telegram_id"]["nullable"])
        self.connection.execute(sa.text("UPDATE payments SET user_id=2 WHERE id=10"))
        self._upgrade()
        self.assertEqual(self.connection.execute(sa.text("SELECT user_id FROM payments WHERE id=10")).scalar_one(), 2)

    def test_upgrade_handles_bootstrap_column_without_index_and_never_cascades_money(self):
        self.connection.exec_driver_sql("ALTER TABLE payments ADD COLUMN user_id INTEGER")
        self._upgrade()
        self.connection.exec_driver_sql("INSERT INTO payments VALUES (20,NULL,95,'approved',2)")
        self.connection.exec_driver_sql("DELETE FROM users WHERE id=2")
        self.assertEqual(self.connection.execute(sa.text("SELECT amount FROM payments WHERE id=20")).scalar_one(), 95)
        self.assertIn("ix_payments_user_id", {index["name"] for index in sa.inspect(self.connection).get_indexes("payments")})

    def test_downgrade_preserves_legacy_and_anonymous_financial_rows(self):
        self._upgrade()
        self.connection.execute(sa.text("DELETE FROM subscription_entry_events WHERE id=2"))
        before = self.connection.execute(sa.text("SELECT id,user_telegram_id,amount,payment_status FROM payments ORDER BY id")).all()
        entry_before = self.connection.execute(sa.text("SELECT * FROM subscription_entry_events ORDER BY id")).all()
        with patch.object(self.migration, "op", self.operations):
            self.migration.downgrade()
        self.assertNotIn("user_id", self._columns())
        self.assertFalse(self._columns()["user_telegram_id"]["nullable"])
        self.assertEqual(self.connection.execute(sa.text("SELECT * FROM payments ORDER BY id")).all(), before)
        self.assertEqual(self.connection.execute(sa.text("SELECT * FROM subscription_entry_events ORDER BY id")).all(), entry_before)
        self.assertFalse({c["name"]: c for c in sa.inspect(self.connection).get_columns("subscription_entry_events")}["telegram_id"]["nullable"])

    def test_native_or_conflicting_entry_owner_refuses_downgrade_before_payment_ddl(self):
        self._upgrade()
        for telegram_id in (None, 1001):
            with self.subTest(telegram_id=telegram_id):
                self.connection.execute(sa.text("UPDATE subscription_entry_events SET telegram_id=:tid WHERE id=2"), {"tid": telegram_id})
                with patch.object(self.migration, "op", self.operations), self.assertRaisesRegex(RuntimeError, "subscription_entry_events"):
                    self.migration.downgrade()
                self.assertIn("user_id", self._columns())
                self.assertTrue(self._columns()["user_telegram_id"]["nullable"])

    def test_provider_only_or_unrecoverable_canonical_owner_blocks_downgrade_before_ddl(self):
        self._upgrade()
        for telegram_id, user_id in ((None, 2), (1001, 2), (-7, 999)):
            with self.subTest(telegram_id=telegram_id, user_id=user_id):
                self.connection.execute(sa.text(
                    "INSERT INTO payments (id,user_id,user_telegram_id,amount,payment_status) VALUES (20,:uid,:tid,95,'approved')"
                ), {"uid": user_id, "tid": telegram_id})
                before = self.connection.execute(sa.text("SELECT * FROM payments ORDER BY id")).all()
                with patch.object(self.migration, "op", self.operations), self.assertRaisesRegex(RuntimeError, "refusing destructive downgrade"):
                    self.migration.downgrade()
                self.assertIn("user_id", self._columns())
                self.assertTrue(self._columns()["user_telegram_id"]["nullable"])
                self.assertEqual(self.connection.execute(sa.text("SELECT * FROM payments ORDER BY id")).all(), before)
                self.connection.execute(sa.text("DELETE FROM payments WHERE id=20"))
