"""Never permit the standalone QA initializer to contact arbitrary DBs."""
import importlib.util
from contextlib import asynccontextmanager
import os
from pathlib import Path
import subprocess
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
                         ["0121_admin_pwa_mcp_security"])
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

    def test_all_new_tables_are_deferred_to_their_real_migrations_only(self):
        metadata = mod._registered_model_metadata()
        initial = {table.name for table in mod._initial_schema_tables(metadata)}
        expected = {
            "public_site_traffic_daily", "admin_pwa_sessions", "admin_pwa_approvals",
            "admin_pwa_oauth_attempts", "admin_pwa_enrollment_grants",
            "admin_pwa_credentials", "admin_pwa_registration_challenges",
            "admin_pwa_authentication_challenges", "admin_pwa_step_ups",
            "admin_pwa_payment_reviews", "admin_pwa_payment_outbox",
            "admin_pwa_mcp_access_grants",
            "admin_pwa_mcp_authorizations",
            "admin_pwa_mcp_audit", "admin_pwa_mcp_quotas",
        }
        self.assertEqual(set(metadata.tables) - initial, expected)
        self.assertIn("user_identities", initial)
        self.assertIn("users", initial)
        self.assertIn("notification_templates", initial)

    def test_fresh_cli_process_registers_every_orm_model_without_importing_app(self):
        # Shared test-process imports can hide a missing registration: the HTTP
        # app imports NotificationTemplate, but the empty bootstrap must not.
        code = """
import importlib
import pkgutil
import sys
from scripts.qa_standalone_bootstrap import _registered_model_metadata
from app.db import models
metadata = _registered_model_metadata()
registered = set(metadata.tables)
for module in pkgutil.iter_modules(models.__path__):
    importlib.import_module(models.__name__ + '.' + module.name)
assert set(metadata.tables) == registered, sorted(set(metadata.tables) - registered)
assert 'notification_templates' in registered
assert 'app.main' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=SCRIPT.parent.parent,
            capture_output=True, text=True, timeout=30,
            env={"PATH": os.defpath, "DATABASE_URL": SAFE["DATABASE_URL"]},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

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
        required = set(mod._registered_model_metadata().tables) | {"alembic_version"}
        columns = [{"name": name, "nullable": False} for name in ("visit_day", "source", "visits")]
        primary = {"constrained_columns": ["visit_day", "source"]}
        for case in ("valid", "missing_table", "missing_notification_table",
                     "bad_columns", "bad_primary_key", "identity_rows", "pwa_rows"):
            with self.subTest(case=case):
                missing = ("public_site_traffic_daily" if case == "missing_table" else
                           "notification_templates" if case == "missing_notification_table" else None)
                tables = required - {missing}
                shape = columns[:-1] if case == "bad_columns" else columns
                key = {"constrained_columns": ["source"]} if case == "bad_primary_key" else primary
                def execute(statement):
                    query = str(statement)
                    value = (mod.EXPECTED_HEAD if "version_num" in query else
                             1 if ((case == "identity_rows" and "FROM user_identities" in query)
                                   or (case == "pwa_rows" and "FROM admin_pwa_credentials" in query)) else 0)
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
                        expected = ("missing_schema_tables" if missing else
                                    "unexpected_user_rows" if case in {"identity_rows", "pwa_rows"} else
                                    "bad_public_traffic_schema")
                        with self.assertRaisesRegex(RuntimeError, expected):
                            await mod.verify_qa_tables()
                engine.dispose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
