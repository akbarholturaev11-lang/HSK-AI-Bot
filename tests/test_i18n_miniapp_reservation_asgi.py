"""Offline ASGI tests: authenticated Mini App lesson reservation, no real DB/bot.

Uses a synthetic HMAC-signed Telegram initData fixture and mocks every
entitlement/database dependency; the final class uses isolated in-memory SQLite
with the real shared lesson service. This does NOT inspect real user data, make
external HTTP requests, or certify deployed Pro/Free policy.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.user import User
from app.services.course_levels import content_level
from app.services.course_lesson_completion_proof import verify_lesson_completion_proof
from app.services.course_miniapp_access_service import COURSE_DAILY_EVENT_NAME
from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import LimitConfigService


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
        self.user_repo.get_by_telegram_id_for_update = AsyncMock(return_value=self.user)
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
        data = {"lesson_id": order, "level": content_level(self.user.level), "lang": "uz"}
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
        self.assertTrue(verify_lesson_completion_proof(
            response.json()["completion_proof"],
            user_id=self.user.id, level="hsk1", lesson_order=1,
            secret=TEST_TOKEN,
        ))
        self.user_repo.get_by_telegram_id_for_update.assert_awaited_once_with(TEST_ID)
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

    async def test_skip_test_allows_entitled_locked_lessons_without_unlocking_full_content(self):
        """The map offers skip tests for n > completed + 1, including for Free.

        The shared allowance gate decides eligibility, matching lesson/unlock.
        Receiving questions must not itself advance progress or authorize a
        full lesson read/start.
        """
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        for status, payment_status in (("free", "none"), ("active", "approved")):
            for order in (2, 100):
                with self.subTest(status=status, order=order):
                    self.user.status = status
                    self.user.payment_status = payment_status
                    self.user.end_date = (
                        datetime.now(timezone.utc) + timedelta(days=1)
                        if payment_status == "approved" else None
                    )
                    self.lesson_service.status.reset_mock()
                    self.user_repo.get_by_telegram_id.reset_mock()
                    self.progress_repo.get_by_user_id.reset_mock()
                    lesson = {
                        "level": "hsk1", "lesson_id": order,
                        "sections": [{"cards": [
                            {"type": "quick_quiz", "question_id": str(i), "correct_index": 0}
                            for i in range(12)
                        ]}],
                        "active_words": [], "grammar": [{"private": True}],
                    }
                    with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
                         patch("app.api.miniapp_entitlements._read_course_lesson",
                               return_value=lesson) as read_lesson:
                        response = await self.client.post(
                            "/api/v3/lesson/skip-test", headers=headers,
                            json={"level": "hsk1", "lesson_id": order,
                                  "telegram_id": TEST_ID + 1},
                        )
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(set(response.json()), {
                            "ok", "level", "lesson_order", "questions",
                        })
                        self.assertEqual(len(response.json()["questions"]), 6)
                        read_lesson.assert_called_once_with("hsk1", order)
                        self.user_repo.get_by_telegram_id.assert_awaited_once_with(TEST_ID)
                        self.progress_repo.get_by_user_id.assert_awaited_once_with(self.user.id)
                        self.lesson_service.status.assert_awaited_once_with(
                            self.user, level="hsk1", lesson_order=order,
                            completed=0, consume=False,
                        )
                        self.assertEqual(response.headers["cache-control"], "no-store")
                        self.assertEqual(self.progress.completed_lessons_count, 0)
                        self.session.commit.assert_not_awaited()

                        self.lesson_service.status.reset_mock()
                        read_lesson.reset_mock()
                        content = await self.client.get(
                            f"/api/v3/lesson/content/hsk1/{order}", headers=headers,
                        )
                        start = await self._start(order, headers)
                        for denied in (content, start):
                            self.assertEqual(denied.status_code, 403)
                            self.assertEqual(denied.json()["error"], "course_lesson_not_unlocked")
                        read_lesson.assert_not_called()
                        self.lesson_service.status.assert_not_awaited()

    async def test_skip_test_denied_shared_access_never_reads_questions(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        for level, reason in (
            ("hsk1", "course_access_blocked"),
            ("hsk1", "free_feature_limit_reached"),
            ("nhsk2", "hsk30_access_required"),
            ("nhsk2", "hsk30_level_not_live"),
        ):
            with self.subTest(level=level, reason=reason):
                self.user.level = self.progress.level = level
                self.lesson_service.status.reset_mock()
                self.lesson_service.status.return_value = {
                    "ok": False, "allowed": False, "error": reason,
                }
                with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
                     patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
                    response = await self.client.post(
                        "/api/v3/lesson/skip-test", headers=headers,
                        json={"level": level, "lesson_id": 2},
                    )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), self.lesson_service.status.return_value)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.lesson_service.status.assert_awaited_once_with(
                    self.user, level=level, lesson_order=2, completed=0, consume=False,
                )
                read_lesson.assert_not_called()
                self.session.commit.assert_not_awaited()

    async def test_skip_test_rejects_missing_or_forged_identity_before_session(self):
        signed = synthetic_init_data()
        for headers in ({}, {"X-Telegram-Init-Data": signed.replace("Synthetic+QA", "Forged+QA")}):
            with self.subTest(headers_present=bool(headers)):
                response = await self.client.post(
                    "/api/v3/lesson/skip-test", headers=headers,
                    json={"level": "hsk1", "lesson_id": 2},
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"], "invalid_telegram_init_data")
        self.assertEqual(self.entered_session, 0)
        self.lesson_service.status.assert_not_awaited()

    async def test_skip_test_rejects_invalid_level_and_lesson_bounds_before_content(self):
        headers = {"X-Telegram-Init-Data": synthetic_init_data()}
        for level, order, status, error in (
            ("hsk2", 2, 403, "course_level_not_allowed"),
            ("hsk1", 101, 404, "course_lesson_not_found"),
            ("hsk1", 0, 400, "invalid_lesson_payload"),
            ("hsk1", -1, 400, "invalid_lesson_payload"),
            ("hsk1", "invalid", 400, "invalid_lesson_payload"),
            ("../../private", 2, 400, "invalid_lesson_payload"),
        ):
            with self.subTest(level=level, order=order):
                with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
                     patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
                    response = await self.client.post(
                        "/api/v3/lesson/skip-test", headers=headers,
                        json={"level": level, "lesson_id": order},
                    )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"], error)
                read_lesson.assert_not_called()
        self.lesson_service.status.assert_not_awaited()
        self.session.commit.assert_not_awaited()

    async def test_skip_test_requires_existing_canonical_account(self):
        self.user_repo.get_by_telegram_id.return_value = None
        with patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
            response = await self.client.post(
                "/api/v3/lesson/skip-test",
                headers={"X-Telegram-Init-Data": synthetic_init_data()},
                json={"level": "hsk1", "lesson_id": 2},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "access_start_first")
        self.lesson_service.status.assert_not_awaited()
        read_lesson.assert_not_called()

    async def test_skip_test_keeps_required_foundation_gate_for_locked_lesson(self):
        self.user.level = "beginner"
        self.profile_service.foundation_status.return_value = {
            "required": True, "completed": False,
        }
        with patch("app.api.miniapp_entitlements.total_parts", return_value=100), \
             patch("app.api.miniapp_entitlements._read_course_lesson") as read_lesson:
            response = await self.client.post(
                "/api/v3/lesson/skip-test",
                headers={"X-Telegram-Init-Data": synthetic_init_data()},
                json={"level": "hsk1", "lesson_id": 2},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "android_foundation_required")
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


class MiniAppLessonRealReservationASGITests(unittest.IsolatedAsyncioTestCase):
    """Private content reads must agree with the real reservation decision."""

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        for target in (
            "app.services.conversion_funnel_service.async_session_maker",
            "app.services.entitlements.shadow.async_session_maker",
        ):
            analytics = patch(target, self.sessions)
            analytics.start()
            self.addCleanup(analytics.stop)
        async with self.sessions() as session:
            session.add(User(
                id=700, telegram_id=TEST_ID, full_name="Synthetic QA",
                language="uz", level="hsk1", learning_mode="course",
                voice_mode="none", status="free", payment_status="none",
            ))
            session.add(CourseProgress(
                user_id=700, level="hsk1", completed_lessons_count=0,
            ))
            await session.commit()
        app = FastAPI()
        app.include_router(create_miniapp_entitlements_router(
            session_factory=self.sessions,
            settings_obj=SimpleNamespace(BOT_TOKEN=TEST_TOKEN),
        ))
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="https://synthetic.test",
            headers={"X-Telegram-Init-Data": synthetic_init_data()},
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _configure(self, *, trial=False, limit=2, level="hsk1"):
        async with self.sessions() as session:
            user = await session.get(User, 700)
            user.level = level
            if trial:
                user.pro_trial_ends_at = datetime.now(timezone.utc) + timedelta(days=1)
            config = LimitConfigService(session)
            payload = (await config.get_config()).public_payload()
            payload["plans"]["TRIAL_ACTIVE" if trial else "FREE"][A.LESSON_START] = {
                "limit": limit, "window": "none" if limit is None else "daily",
            }
            await config.save_config(payload)
            await session.commit()

    async def _reservation_count(self):
        async with self.sessions() as session:
            return await session.scalar(select(func.count(CourseMiniAppEvent.id)).where(
                CourseMiniAppEvent.user_id == 700,
                CourseMiniAppEvent.event_name == COURSE_DAILY_EVENT_NAME,
                CourseMiniAppEvent.session_id == "lesson",
            ))

    async def _start(self):
        return await self.client.post(
            "/api/v3/lesson/start", json={"lesson_id": 1, "level": "hsk1"},
        )

    async def _assert_unlimited_reads(self, *, trial):
        await self._configure(trial=trial, limit=None)
        started = await self._start()
        self.assertEqual(started.status_code, 200, started.text)
        self.assertTrue(started.json()["unlimited"])
        for _ in range(3):
            response = await self.client.get("/api/v3/lesson/content/hsk1/1")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn("sections", response.json())
            self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual((await self._start()).status_code, 200)
        # Unlimited starts intentionally do not create a reservation.
        self.assertEqual(await self._reservation_count(), 0)

    async def test_admin_unlimited_free_start_can_read_content_without_reservation(self):
        await self._assert_unlimited_reads(trial=False)

    async def test_admin_unlimited_trial_start_can_read_content_without_reservation(self):
        await self._assert_unlimited_reads(trial=True)

    async def _assert_one_limited_reservation(self, *, trial):
        await self._configure(trial=trial, limit=10 if trial else 2)
        before = await self.client.get("/api/v3/lesson/content/hsk1/1")
        self.assertEqual(before.status_code, 403, before.text)
        self.assertEqual(before.json()["error"], "lesson_start_required")
        started = await self._start()
        self.assertEqual(started.status_code, 200, started.text)
        for _ in range(3):
            response = await self.client.get("/api/v3/lesson/content/hsk1/1")
            self.assertEqual(response.status_code, 200, response.text)
        repeated = await self._start()
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertTrue(repeated.json()["idempotent"])
        self.assertEqual(await self._reservation_count(), 1)

    async def test_limited_free_reads_and_retry_spend_only_one_slot(self):
        await self._assert_one_limited_reservation(trial=False)

    async def test_limited_trial_reads_and_retry_spend_only_one_slot(self):
        await self._assert_one_limited_reservation(trial=True)

    async def test_required_foundation_denial_does_not_consume_lesson(self):
        await self._configure(level="beginner")
        for _ in range(2):
            start = await self._start()
            self.assertEqual(start.status_code, 403, start.text)
            self.assertEqual(start.json()["error"], "android_foundation_required")
            self.assertEqual(start.headers["cache-control"], "no-store")
        content = await self.client.get("/api/v3/lesson/content/hsk1/1")
        self.assertEqual(content.status_code, 403, content.text)
        self.assertEqual(content.json()["error"], "android_foundation_required")
        self.assertEqual(await self._reservation_count(), 0)
        async with self.sessions() as session:
            progress = await session.scalar(select(CourseProgress).where(
                CourseProgress.user_id == 700,
            ))
            self.assertEqual(progress.completed_lessons_count, 0)
            session.add(CourseMiniAppEvent(
                user_id=700, telegram_id=TEST_ID, event_name="foundation_completed",
                payload_json=json.dumps({"foundation_version": "starter-0-v1"}),
            ))
            await session.commit()
        started = await self._start()
        self.assertEqual(started.status_code, 200, started.text)
        self.assertEqual((await self.client.get("/api/v3/lesson/content/hsk1/1")).status_code, 200)
        self.assertEqual(await self._reservation_count(), 1)

    async def test_stale_course_start_does_not_consume_or_retag_progress(self):
        await self._configure(level="hsk2")
        response = await self._start()
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["error"], "course_context_changed")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(await self._reservation_count(), 0)
        async with self.sessions() as session:
            progress = await session.scalar(select(CourseProgress).where(
                CourseProgress.user_id == 700,
            ))
            self.assertEqual(progress.level, "hsk1")
            self.assertEqual(progress.completed_lessons_count, 0)
        current = await self.client.post(
            "/api/v3/lesson/start", json={"lesson_id": 1, "level": "HSK2"},
        )
        self.assertEqual(current.status_code, 200, current.text)
        self.assertEqual(await self._reservation_count(), 1)

    async def test_legacy_start_without_level_keeps_server_course_authority(self):
        await self._configure(level="hsk2")
        response = await self.client.post(
            "/api/v3/lesson/start", json={"lesson_id": 1},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await self._reservation_count(), 1)
        async with self.sessions() as session:
            event = await session.scalar(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.session_id == "lesson",
            ))
            self.assertTrue(event.dedupe_key.endswith(":ref:lesson:hsk2:1"))

    async def test_zero_limit_and_blocked_account_cannot_read_unreserved_content(self):
        await self._configure(limit=0)
        response = await self.client.get("/api/v3/lesson/content/hsk1/1")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertFalse(response.json()["allowed"])
        await self._configure(limit=None)
        async with self.sessions() as session:
            user = await session.get(User, 700)
            user.status = "blocked"
            await session.commit()
        for response in (
            await self._start(),
            await self.client.get("/api/v3/lesson/content/hsk1/1"),
        ):
            self.assertEqual(response.status_code, 403, response.text)
            self.assertFalse(response.json()["allowed"])
        self.assertEqual(await self._reservation_count(), 0)


if __name__ == "__main__":
    unittest.main()
