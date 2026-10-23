"""Signed lesson writes must retain their opened course across device switches.

Exercise the actual handlers and SQLite persistence without application startup,
real Telegram credentials, or external database/analytics connections.
"""
import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main as main
from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_feature_usage import CourseFeatureUsage
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.course_lesson_completion_proof import issue_lesson_completion_proof
from app.services.course_lesson_start_grant import AUTHORIZED_START_EVENT
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
        app.include_router(create_miniapp_entitlements_router(
            session_factory=self.sessions, settings_obj=SimpleNamespace(BOT_TOKEN=TEST_TOKEN),
        ))
        app.add_api_route("/api/v3/lesson/complete", main.v3_course_lesson_complete, methods=["POST"])
        app.add_api_route("/api/v3/lesson/unlock", main.v3_course_lesson_unlock, methods=["POST"])
        app.add_api_route("/api/v3/exams/complete", main.v3_hsk_exam_complete, methods=["POST"])
        app.add_api_route("/api/v3/exams/start", main.v3_hsk_exam_start, methods=["POST"])
        app.add_api_route("/api/v3/language", main.v3_set_language, methods=["POST"])
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
        if action == "complete" and "completion_proof" not in payload:
            # Simulate the proof supplied by the authorized /lesson/start
            # response, without paying for another quota in these context tests.
            async with self.sessions() as session:
                user = await session.get(User, 1)
                level = main._course_v3_user_level(user)
            payload = {
                **payload,
                "completion_proof": issue_lesson_completion_proof(
                    user_id=1, level=level,
                    lesson_order=int(payload.get("lesson_id") or payload.get("lesson_order") or 0),
                    secret=TEST_TOKEN,
                ),
            }
        return await self.client.post("/api/v3/lesson/" + action, headers=self.headers, json=payload)

    async def test_completion_requires_user_level_and_lesson_bound_server_proof(self):
        before = await self._snapshot()
        valid = issue_lesson_completion_proof(
            user_id=1, level="hsk2", lesson_order=1, secret=TEST_TOKEN,
        )
        wrong_account = issue_lesson_completion_proof(
            user_id=2, level="hsk2", lesson_order=1, secret=TEST_TOKEN,
        )
        wrong_level = issue_lesson_completion_proof(
            user_id=1, level="hsk1", lesson_order=1, secret=TEST_TOKEN,
        )
        wrong_lesson = issue_lesson_completion_proof(
            user_id=1, level="hsk2", lesson_order=2, secret=TEST_TOKEN,
        )
        for payload in (
            {"lesson_id": 1, "level": "hsk2"},
            {"lesson_id": 1, "level": "hsk2", "completion_proof": ""},
            {"lesson_id": 1, "level": "hsk2", "completion_proof": "forged"},
            {"lesson_id": 1, "level": "hsk2", "completion_proof": valid + "x"},
            {"lesson_id": 1, "level": "hsk2", "completion_proof": wrong_account},
            {"lesson_id": 1, "level": "hsk2", "completion_proof": wrong_level},
            {"lesson_id": 1, "level": "hsk2", "completion_proof": wrong_lesson},
        ):
            with self.subTest(payload=payload):
                response = await self.client.post(
                    "/api/v3/lesson/complete", headers=self.headers, json=payload,
                )
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["error"], "lesson_completion_proof_required")
                self.assertEqual(await self._snapshot(), before)

    async def _start_legacy_lesson(self):
        return await self.client.post(
            "/api/v3/lesson/start", headers=self.headers,
            json={"lesson_id": 1, "level": "hsk2"},
        )

    async def test_cached_legacy_client_can_finish_after_authorized_start(self):
        # Old HTML starts the lesson but never echoes the response proof.
        started = await self._start_legacy_lesson()
        self.assertEqual(started.status_code, 200, started.text)
        self.assertTrue(started.json()["completion_proof"])
        async with self.sessions() as session:
            records = (await session.execute(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name == AUTHORIZED_START_EVENT,
            ))).scalars().all()
            self.assertEqual(len(records), 1)
            self.assertEqual((records[0].user_id, records[0].level, records[0].lesson_order),
                             (1, "hsk2", 1))
        complete = await self.client.post(
            "/api/v3/lesson/complete", headers=self.headers,
            json={"lesson_id": 1, "level": "hsk2"},
        )
        self.assertEqual(complete.status_code, 200, complete.text)
        self.assertEqual(complete.json()["completed_lessons_count"], 1)
        snapshot = await self._snapshot()
        self.assertEqual(snapshot[5], 1)  # Exactly one XP event.
        again = await self.client.post(
            "/api/v3/lesson/complete", headers=self.headers,
            json={"lesson_id": 1},
        )
        self.assertEqual(again.status_code, 200, again.text)
        self.assertTrue(again.json()["duplicate"])
        self.assertEqual(await self._snapshot(), snapshot)

    async def test_bad_supplied_proof_cannot_downgrade_to_legacy_after_start(self):
        started = await self._start_legacy_lesson()
        self.assertEqual(started.status_code, 200, started.text)
        before = await self._snapshot()
        for proof in ("", "forged", None, started.json()["completion_proof"] + "x"):
            with self.subTest(proof=proof):
                response = await self.client.post(
                    "/api/v3/lesson/complete", headers=self.headers,
                    json={"lesson_id": 1, "level": "hsk2", "completion_proof": proof},
                )
                self.assertEqual(response.status_code, 403, response.text)
                self.assertEqual(response.json()["error"], "lesson_completion_proof_required")
                self.assertEqual(await self._snapshot(), before)

    async def test_expired_or_other_user_server_start_never_grants_xp(self):
        started = await self._start_legacy_lesson()
        self.assertEqual(started.status_code, 200, started.text)
        async with self.sessions() as session:
            grant = await session.scalar(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name == AUTHORIZED_START_EVENT,
            ))
            grant.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
            await session.commit()
        before = await self._snapshot()
        response = await self.client.post(
            "/api/v3/lesson/complete", headers=self.headers,
            json={"lesson_id": 1, "level": "hsk2"},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(await self._snapshot(), before)

        # A subsequent authorized re-open renews the 24h legacy window.
        started = await self._start_legacy_lesson()
        self.assertEqual(started.status_code, 200, started.text)
        async with self.sessions() as session:
            grants = (await session.execute(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.event_name == AUTHORIZED_START_EVENT,
            ))).scalars().all()
            self.assertEqual(len(grants), 1)

    async def test_hsk_exam_endpoints_reject_non_object_json_before_database(self):
        for route in ("/api/v3/exams/start", "/api/v3/exams/complete"):
            for body in ("[]", '[{"session_id":"a"}]', '"abc"', "1", "null", "true", "{", ""):
                with self.subTest(route=route, body=body):
                    with patch.object(main, "async_session_maker", wraps=self.sessions) as sessions:
                        response = await self.client.post(
                            route, headers=self.headers, content=body,
                        )
                        self.assertEqual(response.status_code, 400, response.text)
                        self.assertEqual(response.json()["error"], "invalid_hsk_exam_payload")
                        sessions.assert_not_called()

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

    async def test_language_change_persists_all_locales_without_learning_writes(self):
        before = await self._snapshot()
        for value, expected in (("ru", "ru"), ("tj", "tj"), ("uz", "uz"),
                                (" TG ", "tj"), ("tg-Cyrl", "tj"), (" RU ", "ru")):
            with self.subTest(value=value):
                response = await self.client.post("/api/v3/language", headers=self.headers,
                                                  json={"language": value})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), {"ok": True, "language": expected})
                async with self.sessions() as session:
                    self.assertEqual((await session.get(User, 1)).language, expected)
                self.assertEqual(await self._snapshot(), before)

    async def test_malformed_language_json_is_rejected_before_opening_database(self):
        for body in ("[]", '[{"language":"ru"}]', '"ru"', "1", "null", "true", "{", ""):
            with self.subTest(body=body):
                with patch.object(main, "async_session_maker", wraps=self.sessions) as sessions:
                    response = await self.client.post(
                        "/api/v3/language", headers=self.headers, content=body,
                    )
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(response.json()["error"], "invalid_language_payload")
                    sessions.assert_not_called()

    async def test_invalid_language_cannot_silently_replace_account_preference(self):
        before = await self._snapshot()
        async with self.sessions() as session:
            (await session.get(User, 1)).language = "tj"
            await session.commit()
        for value in (None, "", "  ", "en", "unsupported", 1, True, ["ru"], {"code": "ru"}):
            payloads = ({}, {"language": value}) if value is None else ({"language": value},)
            for payload in payloads:
                with self.subTest(payload=payload):
                    with patch.object(main, "async_session_maker", wraps=self.sessions) as sessions:
                        response = await self.client.post("/api/v3/language", headers=self.headers,
                                                          json=payload)
                        self.assertEqual(response.status_code, 422, response.text)
                        self.assertEqual(response.json()["error"], "invalid_language")
                        sessions.assert_not_called()
                    async with self.sessions() as session:
                        self.assertEqual((await session.get(User, 1)).language, "tj")
                    self.assertEqual(await self._snapshot(), before)

    async def test_language_change_requires_verified_telegram_before_reading_body(self):
        for headers in ({}, {"X-Telegram-Init-Data": "forged"}):
            with self.subTest(headers=headers), patch.object(main, "async_session_maker") as sessions:
                response = await self.client.post("/api/v3/language", headers=headers, content="{")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"], "invalid_telegram_init_data")
                sessions.assert_not_called()
