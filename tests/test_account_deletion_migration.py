"""Formal migration and bootstrap-created table must expose the same contract."""
import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.db.models.account_deletion import AccountDeletionRequest


class AccountDeletionMigrationTests(unittest.TestCase):
    def test_upgrade_matches_model_and_is_safe_after_bootstrap(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0101_account_deletion_requests.py"
        spec = importlib.util.spec_from_file_location("deletion_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration.upgrade()
                migration.upgrade()
            schema = inspect(connection)
            actual = {c["name"]: c for c in schema.get_columns("account_deletion_requests")}
            expected = AccountDeletionRequest.__table__.columns
            self.assertEqual(set(actual), set(expected.keys()))
            for column in expected:
                self.assertEqual(actual[column.name]["nullable"], column.nullable)
            self.assertEqual({tuple(u["column_names"]) for u in schema.get_unique_constraints("account_deletion_requests")},
                             {("active_user_id",)})
            fks = schema.get_foreign_keys("account_deletion_requests")
            self.assertEqual({fk["options"]["ondelete"] for fk in fks}, {"SET NULL"})
            with Operations.context(context):
                migration.downgrade()
            self.assertFalse(inspect(connection).has_table("account_deletion_requests"))
        engine.dispose()
