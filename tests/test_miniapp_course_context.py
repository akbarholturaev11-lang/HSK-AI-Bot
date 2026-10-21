"""Signed lesson writes must retain their opened course across device switches.

Exercise the actual handlers and SQLite persistence without application startup,
real Telegram credentials, or external database/analytics connections.
"""
import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main as main
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_feature_usage import CourseFeatureUsage
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from tests.test_i18n_miniapp_reservation_asgi import TEST_ID, TEST_TOKEN, synthetic_init_data


class MiniAppCourseContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(User(id=1, telegram_id=TEST_ID, full_name="Synthetic QA",
                             language="uz", level="hsk2", status="free", payment_status="none"))
            session.add(CourseProgress(user_id=1, level="hsk2", completed_lessons_count=0,
                                       current_step="intro", waiting_for="none", homework_status="none"))
            await session.commit()
        for target in ("app.main.async_session_maker",
                       "app.services.conversion_funnel_service.async_session_maker",
                       "app.services.entitlements.shadow.async_session_maker"):
            mocked = patch(target, self.sessions)
            mocked.start()
            self.addCleanup(mocked.stop)
        token = patch.object(main.settings, "BOT_TOKEN", TEST_TOKEN)
        token.start()
        self.addCleanup(token.stop)
        app = FastAPI()
        app.add_api_route("/api/v3/lesson/complete", main.v3_course_lesson_complete, methods=["POST"])
        app.add_api_route("/api/v3/lesson/unlock", main.v3_course_lesson_unlock, methods=["POST"])
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://synthetic.test")
        self.headers = {"X-Telegram-Init-Data": synthetic_init_data()}

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _snapshot(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            progress = (await session.execute(select(CourseProgress))).scalar_one()
            return (user.level, progress.level, progress.completed_lessons_count,
                    progress.current_step, progress.current_lesson_id,
                    await session.scalar(select(func.count()).select_from(CourseXpEvent)),
                    await session.scalar(select(func.count()).select_from(CourseMiniAppEvent)),
                    await session.scalar(select(func.count()).select_from(CourseFeatureUsage)))

    async def _post(self, action, payload):
        return await self.client.post("/api/v3/lesson/" + action, headers=self.headers, json=payload)

    async def test_stale_completion_cannot_complete_the_new_course_or_award_xp(self):
        before = await self._snapshot()
        for level in ("hsk1", "nhsk1"):
            with self.subTest(level=level):
                response = await self._post("complete", {"lesson_id": 1, "level": level,
                                                         "session_id": "old-course-finish"})
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json()["error"], "course_context_changed")
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(await self._snapshot(), before)

    async def test_stale_skip_cannot_unlock_the_new_course_or_consume_a_slot(self):
        before = await self._snapshot()
        response = await self._post("unlock", {"lesson_id": 4, "level": "hsk1", "score": 100})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["error"], "course_context_changed")
        self.assertEqual(await self._snapshot(), before)

    async def test_old_progress_is_never_relabelled_as_a_different_course(self):
        async with self.sessions() as session:
            progress = (await session.execute(select(CourseProgress))).scalar_one()
            progress.level, progress.completed_lessons_count = "hsk1", 8
            await session.commit()
        before = await self._snapshot()
        for action in ("complete", "unlock"):
            with self.subTest(action=action):
                response = await self._post(action, {"lesson_id": 1, "score": 100})
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(await self._snapshot(), before)

    async def test_current_course_completion_is_idempotent_and_legacy_compatible(self):
        response = await self._post("complete", {"lesson_id": 1, "level": "hsk2",
                                                 "session_id": "current-course-finish"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["completed_lessons_count"], 1)
        before = await self._snapshot()
        response = await self._post("complete", {"lesson_id": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["duplicate"])
        self.assertEqual(await self._snapshot(), before)

    async def test_current_course_skip_and_retry_preserve_existing_behavior(self):
        response = await self._post("unlock", {"lesson_id": 4, "level": "hsk2", "score": 40})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["completed_lessons_count"], 3)
        before = await self._snapshot()
        response = await self._post("unlock", {"lesson_id": 4, "score": 40})
        self.assertEqual(response.status_code, 200, response.text)
        after = await self._snapshot()
        self.assertEqual(after[:6], before[:6])
        self.assertEqual(after[-1], before[-1])

    async def _beginner(self, *, completed=False):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.level = "beginner"
            progress = await session.scalar(select(CourseProgress))
            progress.level = "hsk1"
            if completed:
                session.add(CourseMiniAppEvent(
                    user_id=1, telegram_id=TEST_ID, event_name="foundation_completed",
                    payload_json=json.dumps({"foundation_version": "starter-0-v1"}),
                ))
            await session.commit()

    async def test_required_foundation_blocks_signed_completion_and_unlock_before_writes(self):
        await self._beginner()
        before = await self._snapshot()
        for action in ("complete", "unlock"):
            with self.subTest(action=action):
                response = await self._post(action, {
                    "lesson_id": 1 if action == "complete" else 4,
                    "level": "hsk1", "score": 100,
                })
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["error"], "android_foundation_required")
                self.assertEqual(response.headers.get("cache-control"), "no-store")
                self.assertEqual(await self._snapshot(), before)

    async def test_completed_foundation_allows_normal_completion_and_unlock(self):
        await self._beginner(completed=True)
        completed = await self._post("complete", {"lesson_id": 1, "level": "hsk1"})
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(completed.json()["completed_lessons_count"], 1)
        unlocked = await self._post("unlock", {"lesson_id": 4, "level": "hsk1", "score": 40})
        self.assertEqual(unlocked.status_code, 200, unlocked.text)
        self.assertEqual(unlocked.json()["completed_lessons_count"], 3)

    async def test_non_object_lesson_payloads_return_400_without_side_effects(self):
        before = await self._snapshot()
        for action in ("complete", "unlock"):
            for payload in ([], [{"lesson_id": 1}], "lesson", 1, None, True):
                with self.subTest(action=action, payload=payload):
                    response = await self.client.post(
                        "/api/v3/lesson/" + action,
                        headers={**self.headers, "Content-Type": "application/json"},
                        content=json.dumps(payload),
                    )
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(response.json()["error"], "invalid_lesson_payload")
                    self.assertEqual(await self._snapshot(), before)
