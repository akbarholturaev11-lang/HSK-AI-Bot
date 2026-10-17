"""No real bot token or production database may pass QA startup."""
import unittest
from pathlib import Path
from scripts.i18n_staging_boot_guard import normalize_staging_db_url, validate_staging_environment

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    "HSK_STAGING_QA_MODE": "1",
    "RAILWAY_ENVIRONMENT_NAME": "staging",
    "HSK_STAGING_DB_HOST": "postgres.qa.internal",
    "DATABASE_URL": "postgresql+asyncpg://qa:somepassword@postgres.qa.internal:5432/qa",
}


class StagingBootGuardTests(unittest.TestCase):
    def test_isolated_staging_connection_passes(self):
        self.assertTrue(validate_staging_environment(BASE))

    def test_railway_url_conversion_is_driver_only(self):
        input_url = "postgresql://qa:p%40ss@postgres.qa.internal:5432/qa"
        normalized = normalize_staging_db_url(input_url)
        self.assertEqual(normalized, "postgresql+asyncpg://" + input_url[len("postgresql://"):])
        self.assertTrue(validate_staging_environment({**BASE, "DATABASE_URL": normalized}))
        self.assertEqual(normalize_staging_db_url(normalized), normalized)
        self.assertEqual(normalize_staging_db_url("https://not-a-db"), "https://not-a-db")

    def test_reject_prod_name_secret_and_database_host(self):
        for extra in (
            {"RAILWAY_ENVIRONMENT_NAME": "production"},
            {"HSK_STAGING_QA_MODE": ""},
            {"BOT_TOKEN": "123:prod_token"},
            {"GEMINI_API_KEY": "expensive"},
            {"OPENAI_API_KEY": "expensive"},
            {"ANDROID_FCM_SERVICE_ACCOUNT_JSON": "push-credentials"},
            {"GOOGLE_DESKTOP_CLIENT_SECRET": "prod"},
            {"HSK_STAGING_DB_HOST": "postgres.other.internal"},
            {"DATABASE_URL": "postgresql+asyncpg://qa:pw@prod.internal/qa"},
            {"DATABASE_URL": "postgresql://qa:pw@postgres.qa.internal/qa"},
            {"DATABASE_URL": "postgresql+asyncpg://qa@postgres.qa.internal/qa"},
        ):
            with self.subTest(extra=sorted(extra)):
                with self.assertRaises(RuntimeError):
                    validate_staging_environment({**BASE, **extra})

    def test_staging_entrypoint_does_not_start_background_bot_workers(self):
        source = (ROOT / "app/staging_qa.py").read_text(encoding="utf-8")
        self.assertIn("validate_staging_environment(os.environ)", source)
        self.assertIn('os.environ["BOT_TOKEN"] = "100000001:"', source)
        self.assertIn("app.router.lifespan_context = staging_qa_lifespan", source)
        self.assertNotIn("start_polling(", source)
        self.assertNotIn("create_task(", source)
        self.assertNotIn("_background_scheduler(", source)
        self.assertNotIn("_seed_lessons(", source)


if __name__ == "__main__":
    unittest.main()
