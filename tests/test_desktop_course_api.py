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

from app.api.desktop_course import (
    DesktopCourseCompleteRequest,
    DesktopNativeEventRequest,
    create_desktop_course_router,
)
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_mistake import CourseMistake
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="desktop-course-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
    )


def _user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=1001,
        full_name="Desktop Student",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class DesktopCourseApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = _settings()
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()
            auth = DesktopAuthService(session, self.settings)
            started = await auth.start_link(
                platform="macos",
                app_version="0.1.0",
                installation_key="i" * 48,
            )
            await auth.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await auth.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            self.access_token = linked["access_token"]

        self.app = FastAPI()
        self.app.include_router(
            create_desktop_course_router(
                session_factory=self.sessions,
                settings_obj=self.settings,
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="https://desktop.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _complete(self, lesson_order: int, event_id: str):
        return await self.client.post(
            "/api/v3/desktop/course/complete",
            headers=self.auth_headers,
            json={
                "lesson_order": lesson_order,
                "event_id": event_id,
                "mistakes": [],
            },
        )

    async def test_map_uses_server_level_and_auth_has_no_bootstrap_side_effect(self):
        response = await self.client.get(
            "/api/v3/desktop/course/map?level=hsk4&tz=300",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["level"], "hsk1")
        self.assertEqual(payload["user"]["language"], "uz")
        self.assertEqual(payload["progress"]["completed"], 0)
        self.assertEqual(payload["units"][0]["lessons"][0]["status"], "current")
        self.assertTrue(
            payload["units"][0]["lessons"][0]["completion_allowed"]
        )
        self.assertTrue(
            payload["units"][0]["lessons"][2]["locked_premium"]
        )
        self.assertFalse(
            payload["units"][0]["lessons"][2]["completion_allowed"]
        )
        self.assertEqual(
            payload["units"][0]["lessons"][2]["completion_error"],
            "free_feature_limit_reached",
        )
        self.assertEqual(response.headers.get("cache-control"), "no-store")

        async with self.sessions() as session:
            device = (
                await session.execute(select(DesktopDevice))
            ).scalar_one()
            first_open_events = (
                await session.execute(
                    select(func.count())
                    .select_from(CourseMiniAppEvent)
                    .where(
                        CourseMiniAppEvent.event_name == "desktop_first_open"
                    )
                )
            ).scalar_one()
            progress = (
                await session.execute(select(CourseProgress))
            ).scalar_one()
            self.assertIsNone(device.first_open_at)
            self.assertEqual(int(first_open_events or 0), 0)
            self.assertEqual(progress.reminder_tz_offset, 5)

    async def test_lesson_returns_canonical_json_and_enforces_unlock_and_premium(self):
        first = await self.client.get(
            "/api/v3/desktop/course/lesson/1",
            headers=self.auth_headers,
        )
        locked = await self.client.get(
            "/api/v3/desktop/course/lesson/2",
            headers=self.auth_headers,
        )

        self.assertEqual(first.status_code, 200)
        lesson_payload = first.json()
        self.assertEqual(lesson_payload["level"], "hsk1")
        self.assertEqual(lesson_payload["lesson_order"], 1)
        self.assertEqual(lesson_payload["lesson"]["lesson_id"], 1)
        meaning_guess = next(
            card
            for section in lesson_payload["lesson"]["sections"]
            for card in section["cards"]
            if card["type"] == "meaning_guess"
        )
        self.assertEqual(meaning_guess["correct_index"], 2)
        self.assertEqual(locked.status_code, 403)
        self.assertEqual(
            locked.json()["error"],
            "course_lesson_not_unlocked",
        )

        self.assertEqual(
            (await self._complete(1, "desktop-course-event-0001")).status_code,
            200,
        )
        self.assertEqual(
            (await self._complete(2, "desktop-course-event-0002")).status_code,
            200,
        )
        preview_map = await self.client.get(
            "/api/v3/desktop/course/map",
            headers=self.auth_headers,
        )
        preview_map_lesson = preview_map.json()["units"][0]["lessons"][2]
        self.assertEqual(preview_map_lesson["status"], "current")
        self.assertTrue(preview_map_lesson["preview_half"])
        self.assertFalse(preview_map_lesson["completion_allowed"])
        self.assertEqual(
            preview_map_lesson["completion_error"],
            "free_feature_limit_reached",
        )
        premium = await self.client.get(
            "/api/v3/desktop/course/lesson/3",
            headers=self.auth_headers,
        )
        self.assertEqual(premium.status_code, 200)
        preview_payload = premium.json()
        self.assertTrue(preview_payload["preview_half"])
        self.assertFalse(preview_payload["completion_allowed"])
        self.assertEqual(
            preview_payload["completion_error"],
            "free_feature_limit_reached",
        )
        self.assertEqual(
            preview_payload["preview_card_limit"],
            max(1, preview_payload["total_cards"] // 2),
        )
        premium_completion = await self._complete(
            3,
            "desktop-course-event-preview",
        )
        self.assertEqual(premium_completion.status_code, 403)
        self.assertEqual(
            premium_completion.json()["error"],
            "free_feature_limit_reached",
        )

        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=7)
            await session.commit()
        paid_lesson = await self.client.get(
            "/api/v3/desktop/course/lesson/3",
            headers=self.auth_headers,
        )
        self.assertEqual(paid_lesson.status_code, 200)
        self.assertFalse(paid_lesson.json()["preview_half"])
        self.assertTrue(paid_lesson.json()["completion_allowed"])
        self.assertEqual(
            paid_lesson.json()["preview_card_limit"],
            paid_lesson.json()["total_cards"],
        )
        self.assertEqual(paid_lesson.json()["lesson"]["lesson_id"], 3)

    async def test_completed_premium_review_stays_available_after_expiry(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=7)
            await session.commit()

        event_ids = {}
        for lesson_order in (1, 2, 3):
            event_ids[lesson_order] = f"desktop-course-paid-review-{lesson_order}"
            response = await self._complete(
                lesson_order,
                event_ids[lesson_order],
            )
            self.assertEqual(response.status_code, 200)

        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "free"
            user.payment_status = "none"
            user.end_date = datetime.now(timezone.utc) - timedelta(days=1)
            await session.commit()

        lesson_response = await self.client.get(
            "/api/v3/desktop/course/lesson/3",
            headers=self.auth_headers,
        )
        replay = await self._complete(
            3,
            "desktop-course-expired-review",
        )
        original_event_replay = await self._complete(3, event_ids[3])
        next_premium = await self.client.get(
            "/api/v3/desktop/course/lesson/4",
            headers=self.auth_headers,
        )
        next_premium_completion = await self._complete(
            4,
            "desktop-course-expired-new-progress",
        )

        self.assertEqual(lesson_response.status_code, 200)
        self.assertFalse(lesson_response.json()["preview_half"])
        self.assertTrue(lesson_response.json()["completion_allowed"])
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["duplicate"])
        self.assertEqual(original_event_replay.status_code, 200)
        self.assertTrue(original_event_replay.json()["duplicate"])
        self.assertEqual(next_premium.status_code, 403)
        self.assertEqual(
            next_premium.json()["error"],
            "free_feature_limit_reached",
        )
        self.assertEqual(next_premium_completion.status_code, 403)
        self.assertEqual(
            next_premium_completion.json()["error"],
            "free_feature_limit_reached",
        )

    async def test_builder_and_pair_mistakes_use_canonical_lesson_material(self):
        response = await self.client.post(
            "/api/v3/desktop/course/complete",
            headers=self.auth_headers,
            json={
                "lesson_order": 1,
                "event_id": "desktop-course-canonical-mistakes",
                "mistakes": [
                    {
                        "material_ref": "lesson:hsk1:1:section:3:card:1",
                        "selected_tokens": ["好", "你"],
                    },
                    {
                        "material_ref": "lesson:hsk1:1:section:1:card:9",
                        "selected_left_index": 0,
                        "selected_right_index": 1,
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        async with self.sessions() as session:
            mistakes = list(
                (
                    await session.execute(
                        select(CourseMistake).order_by(CourseMistake.id)
                    )
                )
                .scalars()
                .all()
            )
        self.assertEqual(len(mistakes), 2)
        materials = [json.loads(item.material_json or "{}") for item in mistakes]
        self.assertEqual(
            {material["format"] for material in materials},
            {"sentence_builder", "match_pairs"},
        )
        self.assertTrue(
            all(
                material["source"]["kind"] == "lesson"
                and material["source"]["trusted"] is False
                for material in materials
            )
        )

    async def test_completion_is_idempotent_and_event_cannot_cross_lessons(self):
        first = await self._complete(1, "desktop-course-event-1001")
        replay = await self._complete(1, "desktop-course-event-1001")
        conflict = await self._complete(2, "desktop-course-event-1001")
        same_lesson_new_event = await self._complete(
            1,
            "desktop-course-event-1002",
        )

        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json().get("duplicate", False))
        self.assertEqual(first.json()["completed_lessons_count"], 1)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["duplicate"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(
            conflict.json()["error"],
            "desktop_course_event_conflict",
        )
        self.assertEqual(same_lesson_new_event.status_code, 200)
        self.assertTrue(same_lesson_new_event.json()["duplicate"])

        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.level = "hsk2"
            await session.commit()
        cross_level = await self._complete(
            1,
            "desktop-course-event-1001",
        )
        self.assertEqual(cross_level.status_code, 409)
        self.assertEqual(
            cross_level.json()["error"],
            "desktop_course_event_conflict",
        )

        async with self.sessions() as session:
            progress = (
                await session.execute(select(CourseProgress))
            ).scalar_one()
            xp_count = (
                await session.execute(
                    select(func.count()).select_from(CourseXpEvent)
                )
            ).scalar_one()
            completion_count = (
                await session.execute(
                    select(func.count())
                    .select_from(CourseMiniAppEvent)
                    .where(
                        CourseMiniAppEvent.event_name == "lesson_completed",
                        CourseMiniAppEvent.source == "desktop_course",
                    )
                )
            ).scalar_one()
            self.assertEqual(progress.completed_lessons_count, 1)
            self.assertEqual(int(xp_count or 0), 1)
            self.assertEqual(int(completion_count or 0), 1)

    async def test_existing_event_without_replay_result_fails_closed(self):
        event_id = "desktop-course-event-corrupt-replay"
        async with self.sessions() as session:
            session.add(
                CourseMiniAppEvent(
                    user_id=1,
                    telegram_id=1001,
                    event_name="lesson_completed",
                    source="desktop_course",
                    level="hsk1",
                    lesson_order=1,
                    session_id=event_id,
                    dedupe_key=f"desktop-course-complete:{event_id}",
                    payload_json="{}",
                )
            )
            await session.commit()

        response = await self._complete(1, event_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error"],
            "desktop_course_event_conflict",
        )
        async with self.sessions() as session:
            progress = (
                await session.execute(select(CourseProgress))
            ).scalar_one_or_none()
            xp_count = (
                await session.execute(
                    select(func.count()).select_from(CourseXpEvent)
                )
            ).scalar_one()
        self.assertIsNone(progress)
        self.assertEqual(int(xp_count or 0), 0)

    async def test_completion_does_not_report_success_after_transaction_rollback(self):
        async def fail_only_completion(analytics_self, **kwargs):
            if kwargs.get("event_name") == "lesson_completed":
                await analytics_self.session.rollback()
                return {
                    "ok": False,
                    "recorded": False,
                    "error": "forced_test_failure",
                }
            return {"ok": True, "recorded": True, "duplicate": False}

        with patch(
            "app.services.desktop_course_service."
            "CourseMiniAppAnalyticsService.record_server_event",
            new=fail_only_completion,
        ):
            response = await self._complete(
                1,
                "desktop-course-event-rollback",
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["error"],
            "desktop_course_save_failed",
        )
        async with self.sessions() as session:
            progress = (
                await session.execute(select(CourseProgress))
            ).scalar_one_or_none()
            xp_count = (
                await session.execute(
                    select(func.count()).select_from(CourseXpEvent)
                )
            ).scalar_one()
            self.assertIsNone(progress)
            self.assertEqual(int(xp_count or 0), 0)

    async def test_language_is_server_persisted_and_invalid_body_is_bounded(self):
        response = await self.client.post(
            "/api/v3/desktop/preferences/language",
            headers=self.auth_headers,
            json={"language": "tj"},
        )
        invalid = await self.client.post(
            "/api/v3/desktop/preferences/language",
            headers=self.auth_headers,
            json={"language": "en"},
        )
        too_many_mistakes = await self.client.post(
            "/api/v3/desktop/course/complete",
            headers=self.auth_headers,
            json={
                "lesson_order": 1,
                "event_id": "desktop-course-event-bounded",
                "mistakes": [{} for _ in range(51)],
            },
        )
        oversized = await self.client.post(
            "/api/v3/desktop/course/complete",
            headers={
                **self.auth_headers,
                "Content-Type": "application/json",
            },
            content=b'{"event_id":"' + b"x" * (65 * 1024) + b'"}',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "language": "tj"})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(too_many_mistakes.status_code, 422)
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(
            oversized.json()["error"],
            "desktop_course_request_too_large",
        )
        async with self.sessions() as session:
            user = await session.get(User, 1)
            self.assertEqual(user.language, "tj")

    async def test_missing_bearer_token_is_rejected(self):
        response = await self.client.get("/api/v3/desktop/course/map")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {"ok": False, "error": "desktop_access_invalid"},
        )

    async def test_native_ai_event_is_authenticated_bounded_and_idempotent(self):
        payload = {
            "event_name": "desktop_offline_ai_used",
            "event_id": "desktop-ai-chat-event-1001",
            "model_id": "qwen3-4b-q4-k-m",
            "duration_ms": 1234,
        }
        first = await self.client.post(
            "/api/v3/desktop/events",
            headers=self.auth_headers,
            json=payload,
        )
        replay = await self.client.post(
            "/api/v3/desktop/events",
            headers=self.auth_headers,
            json=payload,
        )
        invalid = await self.client.post(
            "/api/v3/desktop/events",
            headers=self.auth_headers,
            json={**payload, "event_name": "desktop_prompt_body"},
        )
        unauthenticated = await self.client.post(
            "/api/v3/desktop/events",
            json=payload,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), {"ok": True, "recorded": True, "duplicate": False})
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json(), {"ok": True, "recorded": False, "duplicate": True})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(unauthenticated.status_code, 401)
        async with self.sessions() as session:
            events = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.event_name == "desktop_offline_ai_used"
                    )
                )
            ).scalars().all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source, "desktop_native")
        stored = json.loads(events[0].payload_json or "{}")
        self.assertNotIn("prompt", stored)
        self.assertEqual(stored["model_id"], "qwen3-4b-q4-k-m")

    def test_model_and_router_contract(self):
        with self.assertRaises(ValueError):
            DesktopCourseCompleteRequest(
                lesson_order=1,
                event_id="desktop-course-event-model",
                mistakes=[{} for _ in range(51)],
            )
        with self.assertRaises(ValueError):
            DesktopCourseCompleteRequest(
                lesson_order=1,
                event_id="desktop-course-event-forged",
                mistakes=[
                    {
                        "material_ref": "lesson:hsk1:1:section:1:card:3",
                        "correct_answer": "FORGED",
                    }
                ],
            )
        with self.assertRaises(ValueError):
            DesktopNativeEventRequest(
                event_name="desktop_prompt_body",
                event_id="desktop-ai-chat-event-model",
            )
        paths = {
            route.path
            for route in create_desktop_course_router(
                session_factory=self.sessions,
                settings_obj=self.settings,
            ).routes
        }
        self.assertEqual(
            paths,
            {
                "/api/v3/desktop/course/map",
                "/api/v3/desktop/course/lesson/{lesson_order}",
                "/api/v3/desktop/course/complete",
                "/api/v3/desktop/preferences/language",
                "/api/v3/desktop/events",
            },
        )
