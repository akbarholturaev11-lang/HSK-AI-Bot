"""0107 preserves legacy reward facts and rejects lossy provider downgrade."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


class UniversalReferralMigrationTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0107_canonical_referral_ownership.py"
        spec = importlib.util.spec_from_file_location("universal_referral_migration", path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self.connection.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT UNIQUE)")
        self.connection.exec_driver_sql("CREATE TABLE referrals (id INTEGER PRIMARY KEY, referrer_telegram_id BIGINT NOT NULL, invited_user_telegram_id BIGINT NOT NULL UNIQUE, status TEXT, bonus_granted BOOLEAN)")
        self.connection.exec_driver_sql("CREATE TABLE desktop_link_requests (id TEXT PRIMARY KEY, status TEXT)")
        self.connection.exec_driver_sql("INSERT INTO users VALUES (1,1001),(2,1002),(3,NULL),(4,NULL)")
        self.connection.exec_driver_sql("INSERT INTO referrals VALUES (1,1001,1002,'active',1),(2,9999,8888,'pending',0)")
        self.operations = Operations(MigrationContext.configure(self.connection))

    def tearDown(self):
        self.connection.close()
        self.engine.dispose()

    def upgrade(self):
        with patch.object(self.migration, "op", self.operations):
            self.migration.upgrade()

    def test_backfill_keeps_legacy_rows_owners_and_uniqueness(self):
        self.upgrade()
        self.upgrade()
        self.assertEqual(self.connection.execute(sa.text("SELECT id,referrer_user_id,invited_user_id,status,bonus_granted FROM referrals ORDER BY id")).all(),
                         [(1,1,2,'active',1),(2,None,None,'pending',0)])
        self.connection.execute(sa.text("INSERT INTO referrals VALUES (3,NULL,NULL,'pending',0,3,4)"))
        # Native accounts coexist without NULL Telegram IDs matching anyone.
        self.assertEqual(self.connection.execute(sa.text("SELECT COUNT(*) FROM referrals")).scalar_one(), 3)
        self.assertTrue(all(c["nullable"] for c in sa.inspect(self.connection).get_columns("referrals") if c["name"].endswith("telegram_id")))
        with self.assertRaises(sa.exc.IntegrityError):
            self.connection.execute(sa.text("INSERT INTO referrals VALUES (4,NULL,NULL,'pending',0,1,4)"))

    def test_bootstrap_columns_still_receive_owner_constraints_and_index(self):
        self.connection.exec_driver_sql("ALTER TABLE referrals ADD COLUMN referrer_user_id INTEGER")
        self.connection.exec_driver_sql("ALTER TABLE referrals ADD COLUMN invited_user_id INTEGER")
        self.upgrade()
        fks = sa.inspect(self.connection).get_foreign_keys("referrals")
        self.assertEqual({tuple(fk["constrained_columns"]) for fk in fks}, {("referrer_user_id",), ("invited_user_id",)})
        self.assertTrue(all(fk["options"].get("ondelete") == "CASCADE" for fk in fks))
        self.assertIn("ix_referrals_referrer_user_id", {index["name"] for index in sa.inspect(self.connection).get_indexes("referrals")})
        self.connection.execute(sa.text("INSERT INTO referrals VALUES (3,NULL,NULL,'pending',0,3,4)"))
        with self.assertRaises(sa.exc.IntegrityError):
            self.connection.execute(sa.text("INSERT INTO referrals VALUES (4,NULL,NULL,'pending',0,1,4)"))

    def test_safe_legacy_downgrade_roundtrip(self):
        self.upgrade()
        with patch.object(self.migration, "op", self.operations):
            self.migration.downgrade()
        self.assertEqual(self.connection.execute(sa.text("SELECT * FROM referrals ORDER BY id")).all(),
                         [(1,1001,1002,'active',1),(2,9999,8888,'pending',0)])
        self.assertNotIn("referral_code", {c["name"] for c in sa.inspect(self.connection).get_columns("desktop_link_requests")})

    def test_provider_or_pending_attribution_refuses_downgrade_before_ddl(self):
        self.upgrade()
        self.connection.execute(sa.text("INSERT INTO desktop_link_requests VALUES ('start','pending','a1b2c3d4')"))
        with patch.object(self.migration, "op", self.operations), self.assertRaisesRegex(RuntimeError, "Pending signup"):
            self.migration.downgrade()
        self.connection.execute(sa.text("DELETE FROM desktop_link_requests"))
        self.connection.execute(sa.text("INSERT INTO referrals VALUES (3,NULL,NULL,'pending',0,3,4)"))
        with patch.object(self.migration, "op", self.operations), self.assertRaisesRegex(RuntimeError, "Provider-only"):
            self.migration.downgrade()
        self.assertIn("referrer_user_id", {c["name"] for c in sa.inspect(self.connection).get_columns("referrals")})
