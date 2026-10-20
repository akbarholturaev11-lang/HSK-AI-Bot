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
        self.profile_service = MagicMock()
        self.profile_service.foundation_status = AsyncMock(return_value={
            "required": False, "completed": False,
        })
        self.patches = [
            patch("app.api.miniapp_entitlements.UserRepository",
                  return_value=self.user_repo),
            patch("app.api.miniapp_entitlements.CourseProgressRepository",
                  return_value=self.progress_repo),
            patch("app.api.miniapp_entitlements.LessonAccessService",
                  return_value=self.lesson_service),
            patch("app.api.miniapp_entitlements.CourseMiniAppProfileService",
                  return_value=self.profile_service),
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

    async def _start(self, order, headers=None, *, review_only=False):
        data = {"lesson_id": order, "level": "hsk1", "lang": "uz"}
        if review_only:
            data["review_only"] = True
        return await self.client.post(
            "/api/v3/lesson/start", headers=headers or {}, json=data,
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

    async def test_finished_lesson_p3_read_is_authenticated_and_non_consuming(self):
        self.user.level = "nhsk2"
        self.progress.level = "nhsk2"
        self.progress.completed_lessons_count = 16
        localized = {"version": 1, "level": "nhsk2", "lesson_order": 16,
                     "source_git_blob_sha1": "a" * 40,
                     "display_translations": []}
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch",
                   return_value=localized) as adapter:
            response = await self._start(
                16, {"X-Telegram-Init-Data": synthetic_init_data()},
                review_only=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["p3_grammar"], localized)
            self.assertEqual(response.headers["cache-control"], "no-store")
            adapter.assert_called_once_with(level="nhsk2", lesson_order=16)
            self.lesson_service.status.assert_awaited_once()
            kwargs = self.lesson_service.status.await_args.kwargs
            self.assertEqual(kwargs["level"], "nhsk2")
            self.assertEqual(kwargs["lesson_order"], 16)
            self.assertEqual(kwargs["completed"], 16)
            self.assertIs(kwargs["consume"], False)
            self.session.commit.assert_not_awaited()

    async def test_completed_review_denied_by_shared_access_has_no_p3(self):
        self.user.level = "nhsk2"
        self.progress.level = "nhsk2"
        self.progress.completed_lessons_count = 16
        # Covers blocked identity, revoked HSK 3.0 track or level-disabled
        # access returned by LessonAccessService without consuming quota.
        for reason in ("blocked", "hsk30_access_required", "hsk30_level_not_live"):
            with self.subTest(reason=reason):
                self.lesson_service.status.reset_mock()
                self.lesson_service.status.return_value = {
                    "ok": False, "allowed": False, "error": reason,
                }
                with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch") as adapter:
                    response = await self._start(
                        16, {"X-Telegram-Init-Data": synthetic_init_data()},
                        review_only=True,
                    )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.json()["error"], reason)
                    self.assertNotIn("p3_grammar", response.json())
                    self.assertEqual(response.headers["cache-control"], "no-store")
                    adapter.assert_not_called()
                self.assertIs(self.lesson_service.status.await_args.kwargs["consume"], False)
                self.session.commit.assert_not_awaited()

    async def test_non_object_lesson_start_body_returns_400_not_500(self):
        signed = {"X-Telegram-Init-Data": synthetic_init_data()}
        for payload in ([], [16], "16", None):
            with self.subTest(payload=payload):
                response = await self.client.post(
                    "/api/v3/lesson/start", headers=signed, json=payload,
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_lesson_payload")
        self.lesson_service.status.assert_not_awaited()

    async def test_lesson_content_requires_signed_identity_and_never_commits(self):
        self.lesson_service.status.return_value = {
            "ok": True, "allowed": True, "idempotent": True,
        }
        with patch("app.api.miniapp_entitlements._read_course_lesson",
                   return_value={"level": "hsk1", "lesson_id": 1, "sections": []}) as read_lesson:
            response = await self.client.get("/api/v3/lesson/content/hsk1/1")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(self.entered_session, 0)
            read_lesson.assert_not_called()

            response = await self.client.get(
                "/api/v3/lesson/content/hsk1/1",
                headers={"X-Telegram-Init-Data": synthetic_init_data()},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            read_lesson.assert_called_once_with("hsk1", 1)
        kwargs = self.lesson_service.status.await_args.kwargs
        self.assertEqual(kwargs["level"], "hsk1")
        self.assertEqual(kwargs["lesson_order"], 1)
        self.assertEqual(kwargs["completed"], 0)
        self.assertIs(kwargs["consume"], False)
        self.session.commit.assert_not_awaited()

    async def test_lesson_content_rejects_skip_ahead_and_unreserved_free_start(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
            response = await self.client.get(
                "/api/v3/lesson/content/hsk1/2", headers=headers,
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"], "course_lesson_not_unlocked")
            self.lesson_service.status.assert_not_awaited()
            read_lesson.assert_not_called()

            self.lesson_service.status.return_value = {
                "ok": True, "allowed": True, "remaining": 1, "limit": 2,
            }
            response = await self.client.get(
                "/api/v3/lesson/content/hsk1/1", headers=headers,
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"], "lesson_start_required")
            read_lesson.assert_not_called()
            self.assertIs(self.lesson_service.status.await_args.kwargs["consume"], False)
            self.session.commit.assert_not_awaited()

    async def test_lesson_content_accepts_reserved_or_completed_reads_and_denies_revoked_access(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson",
                   return_value={"level": "hsk1", "lesson_id": 1, "sections": []}) as read_lesson:
            self.lesson_service.status.return_value = {
                "ok": True, "allowed": True, "idempotent": True,
            }
            response = await self.client.get(
                "/api/v3/lesson/content/hsk1/1", headers=headers,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["lesson_id"], 1)
            self.assertEqual(self.lesson_service.status.await_args.kwargs["consume"], False)
            self.session.commit.assert_not_awaited()

            self.progress.completed_lessons_count = 1
            self.lesson_service.status.reset_mock()
            self.lesson_service.status.return_value = {
                "ok": False, "allowed": False, "error": "hsk30_access_required",
            }
            response = await self.client.get(
                "/api/v3/lesson/content/hsk1/1", headers=headers,
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"], "hsk30_access_required")
            self.assertEqual(read_lesson.call_count, 1)
            self.session.commit.assert_not_awaited()

    async def test_lesson_content_enforces_required_foundation(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        self.user.level = "beginner"
        self.profile_service.foundation_status.return_value = {
            "required": True, "completed": False,
        }
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
            response = await self.client.get(
                "/api/v3/lesson/content/hsk1/1", headers=headers,
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "android_foundation_required")
        self.lesson_service.status.assert_not_awaited()
        read_lesson.assert_not_called()

    async def test_foundation_endpoint_returns_only_foundation_to_signed_account(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        foundation = {"id": "starter0_hsk1", "cards": [{"type": "intro"}]}
        with patch("app.api.miniapp_entitlements._read_course_lesson",
                   return_value={"level": "hsk1", "lesson_id": 1,
                                 "foundation": foundation, "sections": [{"cards": ["private"]}]}) as read_lesson:
            response = await self.client.get(
                "/api/v3/lesson/foundation", headers=headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "foundation": foundation})
        self.assertEqual(response.headers["cache-control"], "no-store")
        read_lesson.assert_called_once_with("hsk1", 1)
        self.lesson_service.status.assert_not_awaited()

    async def test_skip_test_returns_at_most_six_authorized_questions_without_consuming(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        lesson = {
            "level": "hsk1", "lesson_id": 1,
            "sections": [{"cards": [
                {"type": "quick_quiz", "question_id": str(i), "correct_index": 0}
                for i in range(12)
            ]}],
            "active_words": [],
            "correct_index": "private-top-level",
        }
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson",
                   return_value=lesson) as read_lesson:
            response = await self.client.post(
                "/api/v3/lesson/skip-test", headers=headers,
                json={"level": "hsk1", "lesson_id": 1},
            )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertEqual(result["lesson_order"], 1)
        self.assertEqual(len(result["questions"]), 6)
        self.assertTrue(all("correct_index" in question for question in result["questions"]))
        self.assertNotIn("correct_index", result)
        self.assertEqual(response.headers["cache-control"], "no-store")
        read_lesson.assert_called_once_with("hsk1", 1)
        self.assertIs(self.lesson_service.status.await_args.kwargs["consume"], False)
        self.session.commit.assert_not_awaited()

    async def test_skip_test_rejects_future_lesson_without_reading_questions(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
            response = await self.client.post(
                "/api/v3/lesson/skip-test", headers=headers,
                json={"level": "hsk1", "lesson_id": 2},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "course_lesson_not_unlocked")
        self.lesson_service.status.assert_not_awaited()
        read_lesson.assert_not_called()
        self.session.commit.assert_not_awaited()

    async def test_skip_test_empty_question_set_is_not_an_automatic_unlock(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson",
                   return_value={"level": "hsk1", "lesson_id": 1, "sections": []}):
            response = await self.client.post(
                "/api/v3/lesson/skip-test", headers=headers,
                json={"level": "hsk1", "lesson_id": 1},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "skip_test_unavailable")
        self.session.commit.assert_not_awaited()

    async def test_skip_test_keeps_bounded_word_choice_question_shapes(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        lesson = {
            "level": "hsk1", "lesson_id": 1, "sections": [],
            "active_words": [{"id": str(i), "zh": "你好"} for i in range(12)],
        }
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson", return_value=lesson):
            response = await self.client.post(
                "/api/v3/lesson/skip-test", headers=headers,
                json={"level": "hsk1", "lesson_id": 1},
            )
        self.assertEqual(response.status_code, 200)
        questions = response.json()["questions"]
        self.assertEqual(len(questions), 6)
        self.assertTrue(all(question["type"] in {
            "_word_pick_hanzi", "_word_pick_meaning",
        } for question in questions))
        self.assertTrue(all(len(question["words"]) == 8 for question in questions))
        self.session.commit.assert_not_awaited()

    async def test_sales_preview_exposes_only_allowlisted_public_content(self):
        response = await self.client.get("/api/v3/lesson/sales-preview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data), {"ok", "outcome", "next_outcome_preview"})
        self.assertEqual(set(data["outcome"]), {"id", "title", "can_do"})
        self.assertEqual(set(data["next_outcome_preview"]), {"id", "title", "example"})
        self.assertEqual(len(data["outcome"]["can_do"]), 3)
        self.assertNotIn("sections", json.dumps(data))
        self.assertNotIn("correct_index", json.dumps(data))
        self.assertEqual(self.entered_session, 0)

    async def test_uncompleted_lesson_cannot_use_p3_review_only(self):
        self.user.level = "nhsk2"
        self.progress.level = "nhsk2"
        self.progress.completed_lessons_count = 15
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch") as adapter:
            response = await self._start(
                16, {"X-Telegram-Init-Data": synthetic_init_data()},
                review_only=True,
            )
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("p3_grammar", response.json())
            adapter.assert_not_called()
            self.lesson_service.status.assert_not_awaited()
            self.session.commit.assert_not_awaited()

    async def test_non_nhsk2_track_cannot_request_p3_review(self):
        self.user.level = "hsk1"
        self.progress.level = "hsk1"
        self.progress.completed_lessons_count = 1
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch") as adapter:
            result = await self._start(
                1, {"X-Telegram-Init-Data": synthetic_init_data()},
                review_only=True,
            )
            self.assertEqual(result.status_code, 403)
            self.assertNotIn("p3_grammar", result.json())
            adapter.assert_not_called()
            self.lesson_service.status.assert_not_awaited()

    async def test_unsigned_p3_review_request_cannot_get_translation_patch(self):
        with patch("app.api.miniapp_entitlements.miniapp_reserved_grammar_patch") as adapter:
            response = await self._start(16, review_only=True)
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("p3_grammar", response.json())
            adapter.assert_not_called()
            self.assertEqual(self.entered_session, 0)

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
