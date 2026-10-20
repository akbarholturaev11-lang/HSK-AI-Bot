"""Offline safety tests; never call Telegram or Railway from CI."""
from unittest import TestCase
from app.bot.qa_native_worker import (
    QA_FLAG, assert_qa_runtime, create_qa_dispatcher,
)

QA_ENV = {
    "RAILWAY_ENVIRONMENT_NAME": "staging",
    QA_FLAG: "true",
}
QA_URL = (
    "postgresql+asyncpg://qa_user:not-a-real-secret@"
    "hsk-universal-qa-db.railway.internal:5432/hsk_universal_qa_schema"
)


class QANativeWorkerTests(TestCase):
    def test_runtime_accepts_only_staging_db_and_nonproduction_username(self):
        self.assertEqual(
            assert_qa_runtime(env=QA_ENV, database_url=QA_URL,
                              username="@my_hsk_qa_testbot"),
            "my_hsk_qa_testbot",
        )
        candidates = (
            ({"RAILWAY_ENVIRONMENT_NAME": "production", QA_FLAG: "true"}, QA_URL, "my_qa_bot"),
            ({"RAILWAY_ENVIRONMENT_NAME": "staging"}, QA_URL, "my_qa_bot"),
            (QA_ENV, QA_URL, "darsi_chini_bot"),
            (QA_ENV, QA_URL, ""),
            (QA_ENV, QA_URL.replace("hsk-universal-qa-db", "production-postgres"), "my_qa_bot"),
            (QA_ENV, QA_URL.replace("hsk_universal_qa_schema", "railway"), "my_qa_bot"),
            (QA_ENV, "broken-url", "my_qa_bot"),
        )
        for env, url, name in candidates:
            with self.subTest(env=env, name=name):
                with self.assertRaises(RuntimeError):
                    assert_qa_runtime(env=env, database_url=url, username=name)

    def test_no_normal_onboarding_or_schedulers_are_registered(self):
        dp = create_qa_dispatcher()
        self.assertEqual(len(dp.sub_routers), 2)
        self.assertEqual(dp.sub_routers[1].name, "qa_native_start")
        # The explicit Telegram link router is mounted; the broadcast,
        # payment, course, admin and ordinary /start routers are not.
        from app.bot.handlers.desktop_auth import router as native
        self.assertIs(dp.sub_routers[0], native)
        self.assertNotIn("start", [x.name for x in dp.sub_routers])

    def test_start_bot_does_not_delete_telegram_webhook(self):
        from pathlib import Path
        worker = Path(__file__).resolve().parents[1] / "app/bot/qa_native_worker.py"
        source = worker.read_text(encoding="utf-8")
        self.assertIn("get_webhook_info()", source)
        self.assertNotIn("delete_webhook(", source)
        self.assertIn("qa_worker_webhook_active", source)
        self.assertNotIn("create_bot(settings)", source)


if __name__ == "__main__":
    import unittest
    unittest.main()
