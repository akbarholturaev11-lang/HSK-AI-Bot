"""Never permit the standalone QA initializer to contact arbitrary DBs."""
import importlib.util
from pathlib import Path
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
