"""Never permit the standalone QA initializer to contact arbitrary DBs."""
import importlib.util
from contextlib import asynccontextmanager
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/qa_standalone_bootstrap.py"
spec = importlib.util.spec_from_file_location("qa_standalone_bootstrap", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

SAFE = {
    "RAILWAY_PROJECT_ID": mod.QA_PROJECT_ID,
    "RAILWAY_ENVIRONMENT_NAME": "qa",
    "HSK_QA_EMPTY_DB_BOOTSTRAP": "I_APPROVE_EMPTY_QA_DB",
    "DATABASE_URL": "postgresql+asyncpg://test:dummy@postgres.railway.internal:5432/railway",
}


class StandaloneQAInitializerTests(unittest.TestCase):
    def test_explicit_isolated_project_is_accepted(self):
        mod.validate_target(SAFE)

    def test_all_other_environments_are_rejected(self):
        deltas = [
            {"RAILWAY_PROJECT_ID": "82d12023-f6cd-46ce-ad43-b73fcc037027"},
            {"RAILWAY_ENVIRONMENT_NAME": "production"},
            {"RAILWAY_ENVIRONMENT_NAME": "staging"},
            {"HSK_QA_EMPTY_DB_BOOTSTRAP": "false"},
            {"DATABASE_URL": SAFE["DATABASE_URL"].replace("postgres.railway.internal", "production-postgres.railway.internal")},
            {"DATABASE_URL": SAFE["DATABASE_URL"].replace("/railway", "/production")},
            {"DATABASE_URL": "broken"},
        ]
        for delta in deltas:
            with self.subTest(delta=delta), self.assertRaises(RuntimeError):
                mod.validate_target(SAFE | delta)

    def test_only_empty_database_is_initialized(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("standalone_qa_database_not_empty", source)
        self.assertIn("ensure_database_empty()", source)
        self.assertIn("NO_IMPORTED_ROWS", source)
        self.assertNotIn("pg_dump", source)
        self.assertNotIn("DROP DATABASE", source)

    def test_reviewed_head_matches_the_current_single_migration_head(self):
        from alembic.script import ScriptDirectory

        config = mod._reviewed_alembic_config()
        self.assertEqual(ScriptDirectory.from_config(config).get_heads(),
                         ["0109_public_site_traffic_daily"])
        self.assertEqual(mod.EXPECTED_BASELINE, "0102_payment_review_preview")

    def test_new_or_multiple_heads_stop_before_any_schema_creation_or_stamp(self):
        for heads in ([], ["0110_unreviewed"], [mod.EXPECTED_HEAD, "other_head"]):
            with self.subTest(heads=heads), \
                 patch.dict(os.environ, SAFE, clear=True), \
                 patch("alembic.script.ScriptDirectory.from_config") as revisions, \
                 patch.object(mod, "_create_empty_orm_schema") as create, \
                 patch("alembic.command.stamp") as stamp, \
                 patch("alembic.command.upgrade") as upgrade:
                revisions.return_value.get_heads.return_value = heads
                with self.assertRaisesRegex(RuntimeError, "unreviewed_schema_head"):
                    mod.main()
                create.assert_not_called()
                stamp.assert_not_called()
                upgrade.assert_not_called()

    def test_0109_table_is_deferred_to_its_real_migration_only(self):
        from app.db import models  # noqa: F401
        from app.db.base import Base

        initial = {table.name for table in mod._initial_schema_tables(Base.metadata)}
        self.assertEqual(set(Base.metadata.tables) - initial, {"public_site_traffic_daily"})
        self.assertIn("user_identities", initial)
        self.assertIn("users", initial)

    def test_local_or_unapproved_targets_are_never_enabled_for_rehearsal(self):
        for database in ("postgresql+asyncpg://test:dummy@127.0.0.1:5432/hsk_critical_test",
                         "postgresql+asyncpg://test:dummy@localhost:5432/railway"):
            with self.subTest(database=database), self.assertRaisesRegex(RuntimeError, "not_isolated"):
                mod.validate_target(SAFE | {"DATABASE_URL": database})


class StandaloneQASchemaSafetyTests(unittest.IsolatedAsyncioTestCase):
    def engine(self, connection):
        @asynccontextmanager
        async def connect():
            yield connection
        return SimpleNamespace(connect=connect, begin=MagicMock(), dispose=AsyncMock())

    async def test_nonempty_database_aborts_before_any_schema_write(self):
        connection = SimpleNamespace(run_sync=AsyncMock(return_value=["existing_table"]))
        engine = self.engine(connection)
        with patch("app.db.session.engine", engine):
            with self.assertRaisesRegex(RuntimeError, "database_not_empty"):
                await mod._create_empty_orm_schema()
        engine.begin.assert_not_called()
        engine.dispose.assert_awaited_once()

    async def test_traffic_schema_and_empty_identity_rows_are_verified(self):
        required = {"users", "payments", "referrals", "course_progress",
                    "user_identities", "alembic_version", "public_site_traffic_daily"}
        columns = [{"name": name, "nullable": False} for name in ("visit_day", "source", "visits")]
        primary = {"constrained_columns": ["visit_day", "source"]}
        for case in ("valid", "missing_table", "bad_columns", "bad_primary_key", "identity_rows"):
            with self.subTest(case=case):
                tables = required - {"public_site_traffic_daily"} if case == "missing_table" else required
                shape = columns[:-1] if case == "bad_columns" else columns
                key = {"constrained_columns": ["source"]} if case == "bad_primary_key" else primary
                def execute(statement):
                    query = str(statement)
                    value = (mod.EXPECTED_HEAD if "version_num" in query else
                             1 if case == "identity_rows" and "FROM user_identities" in query else 0)
                    return SimpleNamespace(scalar=lambda: value)
                connection = SimpleNamespace(
                    run_sync=AsyncMock(side_effect=[tables, (shape, key)]),
                    execute=AsyncMock(side_effect=execute),
                )
                engine = self.engine(connection)
                with patch("app.db.session.engine", engine):
                    if case == "valid":
                        await mod.verify_qa_tables()
                    else:
                        expected = ("missing_schema_tables" if case == "missing_table" else
                                    "unexpected_user_rows" if case == "identity_rows" else
                                    "bad_public_traffic_schema")
                        with self.assertRaisesRegex(RuntimeError, expected):
                            await mod.verify_qa_tables()
                engine.dispose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
