"""Offline ASGI tests: authenticated Mini App lesson reservation, no real DB/bot.

Uses a synthetic HMAC-signed Telegram initData fixture and mocks every
entitlement/database dependency. This does NOT inspect real user data, make
external HTTP requests, or certify deployed Pro/Free policy.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.miniapp_entitlements import create_miniapp_entitlements_router


TEST_TOKEN = "9123456:synthetic-test-only-unusable-secret"
TEST_ID = 748200001


def synthetic_init_data():
    items = {
        "auth_date": str(int(datetime.now(timezone.utc).timestamp())),
        "user": json.dumps({"id": TEST_ID, "first_name": "Synthetic QA"},
                           separators=(",", ":")),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(items.items()))
    secret = hmac.new(b"WebAppData", TEST_TOKEN.encode(), hashlib.sha256).digest()
    items["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(items)


class MiniAppLessonStartASGITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(commit=AsyncMock())
        self.entered_session = 0
        @asynccontextmanager
        async def sessions():
            self.entered_session += 1
            yield self.session
        self.session_factory = sessions
        self.user = SimpleNamespace(
            id=700, telegram_id=TEST_ID, level="hsk1", language="uz",
            status="free", payment_status="none", end_date=None,
        )
        self.progress = SimpleNamespace(
            level="hsk1", completed_lessons_count=0,
        )
        self.user_repo = MagicMock()
        self.user_repo.get_by_telegram_id = AsyncMock(return_value=self.user)
        self.progress_repo = MagicMock()
        self.progress_repo.get_by_user_id = AsyncMock(return_value=self.progress)
        self.lesson_service = MagicMock()
        self.lesson_service.status = AsyncMock(return_value={
            "ok": True, "allowed": True, "remaining": 1, "limit": 2,
        })
        self.patches = [
            patch("app.api.miniapp_entitlements.UserRepository",
                  return_value=self.user_repo),
            patch("app.api.miniapp_entitlements.CourseProgressRepository",
                  return_value=self.progress_repo),
            patch("app.api.miniapp_entitlements.LessonAccessService",
                  return_value=self.lesson_service),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(self._stop_patches)
        app = FastAPI()
        app.include_router(create_miniapp_entitlements_router(
            session_factory=self.session_factory,
            settings_obj=SimpleNamespace(BOT_TOKEN=TEST_TOKEN),
        ))
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="https://synthetic.test"
        )

    def _stop_patches(self):
        for item in reversed(self.patches):
            item.stop()

    async def asyncTearDown(self):
        await self.client.aclose()

    async def _start(self, order, headers=None):
        return await self.client.post(
            "/api/v3/lesson/start",
            headers=headers or {},
            json={"lesson_id": order, "level": "hsk1", "lang": "uz"},
        )

    async def test_no_initdata_cannot_reserve_or_use_session(self):
        response = await self._start(1)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_telegram_init_data")
        self.assertEqual(self.entered_session, 0)
        self.lesson_service.status.assert_not_awaited()

    async def test_forged_initdata_cannot_consume_lesson(self):
        signed = synthetic_init_data()
        forged = signed.replace("Synthetic+QA", "Forged+QA")
        self.assertNotEqual(forged, signed)
        response = await self._start(1, {"X-Telegram-Init-Data": forged})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.entered_session, 0)
        self.lesson_service.status.assert_not_awaited()

    async def test_valid_test_initdata_calls_consume_once(self):
        response = await self._start(1, {
            "X-Telegram-Init-Data": synthetic_init_data()
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["remaining"], 1)
        self.user_repo.get_by_telegram_id.assert_awaited_once_with(TEST_ID)
        self.lesson_service.status.assert_awaited_once()
        kwargs = self.lesson_service.status.await_args.kwargs
        self.assertEqual(kwargs["level"], "hsk1")
        self.assertEqual(kwargs["lesson_order"], 1)
        self.assertEqual(kwargs["completed"], 0)
        self.assertIs(kwargs["consume"], True)
        self.session.commit.assert_awaited_once()

    async def test_p3_patch_returned_only_after_authenticated_unlocked_reservation(self):
        self.user.level = "nhsk2"
        self.progress.level = "nhsk2"
        self.progress.completed_lessons_count = 15
        patch_data = {
            "version": 1, "level": "nhsk2", "lesson_order": 16,
            "source_git_blob_sha1": "a" * 40,
            "display_translations": [{
                "pointer": "/grammar/0/examples/0/translation",
                "zh": "她去过中国。", "pinyin": "",
                "values": {"uz": "U Xitoyda bo‘lgan.",
                           "ru": "Она бывала в Китае.",
                           "tj": "Ӯ ба Чин рафтааст."},
            }],
        }
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch",
                   return_value=patch_data) as localized:
            response = await self._start(16, {
                "X-Telegram-Init-Data": synthetic_init_data()
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["p3_grammar"], patch_data)
            self.assertEqual(response.headers["cache-control"], "no-store")
            localized.assert_called_once_with(level="nhsk2", lesson_order=16)
            self.lesson_service.status.assert_awaited_once()
            kwargs = self.lesson_service.status.await_args.kwargs
            self.assertEqual(kwargs["level"], "nhsk2")
            self.assertEqual(kwargs["lesson_order"], 16)
            self.assertIs(kwargs["consume"], True)
            self.session.commit.assert_awaited_once()

    async def test_p3_quota_denied_never_fetches_or_leaks_translations(self):
        self.user.level = "nhsk2"
        self.progress.level = "nhsk2"
        self.progress.completed_lessons_count = 15
        self.lesson_service.status.return_value = {
            "ok": False, "allowed": False, "error": "free_feature_limit_reached"
        }
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch") as localized:
            response = await self._start(16, {
                "X-Telegram-Init-Data": synthetic_init_data()
            })
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"], "free_feature_limit_reached")
            self.assertNotIn("p3_grammar", response.json())
            localized.assert_not_called()
            self.session.commit.assert_awaited_once()

    async def test_p3_skip_ahead_denied_before_localization(self):
        self.user.level = "nhsk2"
        self.progress.level = "nhsk2"
        self.progress.completed_lessons_count = 14
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch") as localized:
            response = await self._start(16, {
                "X-Telegram-Init-Data": synthetic_init_data()
            })
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("p3_grammar", response.json())
            localized.assert_not_called()
            self.lesson_service.status.assert_not_awaited()

    async def test_skip_ahead_denied_without_consumption(self):
        response = await self._start(3, {
            "X-Telegram-Init-Data": synthetic_init_data()
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "course_lesson_not_unlocked")
        self.lesson_service.status.assert_not_awaited()
        self.session.commit.assert_not_awaited()

    async def test_quota_denied_by_service_returns_403_not_static_lesson(self):
        self.lesson_service.status.return_value = {
            "ok": False, "allowed": False,
            "error": "free_feature_limit_reached", "remaining": 0,
        }
        response = await self._start(1, {
            "X-Telegram-Init-Data": synthetic_init_data()
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "free_feature_limit_reached")
        self.lesson_service.status.assert_awaited_once()
        self.session.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
