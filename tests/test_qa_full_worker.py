"""Safety contracts for full staging Telegram worker (no live Bot API calls)."""
import unittest
from dataclasses import dataclass

from app.bot.qa_full_worker import validate_qa_settings

BASE = {
    "RAILWAY_ENVIRONMENT_NAME": "staging",
    "HSK_QA_FULL_FEATURES_ENABLED": "true",
}

@dataclass
class StubSettings:
    BOT_USERNAME: str = "hsk_qa_test_bot"
    BOT_TOKEN: str = "999999999:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    DATABASE_URL: str = (
        "postgresql+asyncpg://qa:masked@"
        "hsk-universal-qa-db.railway.internal:5432/hsk_universal_qa_schema"
    )
    PUBLIC_SITE_URL: str = "https://hsk-universal-qa-api-staging.up.railway.app"
    MINI_APP_BASE_URL: str = (
        "https://hsk-universal-qa-api-staging.up.railway.app/course-v3.html"
    )
    OAUTH_NATIVE_RETURN_SCHEME: str = "pomp-hsk-ai-qa"


class FullQaWorkerGuardTests(unittest.TestCase):
    def test_accepts_only_real_qa_config(self):
        self.assertEqual(validate_qa_settings(BASE, StubSettings()), "hsk_qa_test_bot")

    def test_rejects_wrong_environment_database_and_bot(self):
        variants = [
            ({"RAILWAY_ENVIRONMENT_NAME": "production"}, {}),
            ({"HSK_QA_FULL_FEATURES_ENABLED": "false"}, {}),
            ({}, {"DATABASE_URL": StubSettings.DATABASE_URL.replace("hsk_universal_qa_schema", "railway")}),
            ({}, {"DATABASE_URL": StubSettings.DATABASE_URL.replace("hsk-universal-qa-db", "Postgres-Iy93")}),
            ({}, {"BOT_USERNAME": "darsi_chini_bot"}),
            ({}, {"BOT_USERNAME": ""}),
            ({}, {"BOT_TOKEN": ""}),
            ({}, {"PUBLIC_SITE_URL": "https://telegram-chinese-bot-production.up.railway.app"}),
            ({}, {"MINI_APP_BASE_URL": "https://telegram-chinese-bot-production.up.railway.app/course-v3.html"}),
            ({}, {"OAUTH_NATIVE_RETURN_SCHEME": "pomp-hsk-ai"}),
        ]
        for env_delta, setting_delta in variants:
            with self.subTest(env=env_delta,setting=setting_delta):
                env = BASE | env_delta
                conf = StubSettings(**setting_delta)
                with self.assertRaises(RuntimeError):
                    validate_qa_settings(env, conf)

    def test_full_bot_handlers_imported_without_registering_extra_polling(self):
        from app.bot.create_bot import create_bot
        source = __import__("inspect").getsource(create_bot)
        self.assertIn("dp.include_router(start_router)", source)
        self.assertIn("dp.include_router(desktop_auth_router)", source)
        self.assertIn("dp.include_router(payments_router)", source)
        self.assertIn("dp.include_router(admin_payments_router)", source)
        self.assertIn("dp.include_router(referral_router)", source)
        self.assertIn("dp.include_router(course_router)", source)
        self.assertIn("dp.include_router(admin_router)", source)
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "app/bot/qa_full_worker.py").read_text()
        self.assertNotIn("delete_webhook(", src)
        self.assertIn("get_webhook_info()", src)
        self.assertIn("_background_scheduler(bot)", src)
        self.assertIn("_desktop_auth_retention_scheduler()", src)
        self.assertIn("bot, dp = hsk_server.bot, hsk_server.dp", src)
        self.assertNotIn("bot, dp = create_bot(settings)", src)



if __name__ == "__main__":
    unittest.main()
