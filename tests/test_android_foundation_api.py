"""Regression coverage for the native Android Starter 0/Foundation contract."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_course import create_android_course_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="android-foundation-test-secret-" + "x" * 40,
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
        full_name="Foundation Learner",
        language="uz",
        level="beginner",
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


class AndroidFoundationApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

        app = FastAPI()
        app.include_router(
            create_android_course_router(
                session_factory=self.sessions,
                settings_obj=_settings(),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _bearer(self) -> dict[str, str]:
        async with self.sessions() as session:
            auth = DesktopAuthService(session, _settings())
            started = await auth.start_link(
                platform="android",
                app_version="1.0.0",
                installation_key="f" * 48,
            )
            await auth.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await auth.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
        return {"Authorization": f"Bearer {linked['access_token']}"}

    async def _complete_foundation(self, headers, *, suffix="z"):
        return await self.client.post(
            "/api/v3/android/course/foundation/complete",
            headers=headers,
            json={
                "foundation_id": "starter0_hsk1",
                "foundation_version": 1,
                "speaking_bonus": False,
                "event_id": "android:foundation:" + suffix * 32,
            },
        )

    async def test_foundation_requires_bearer_auth(self):
        response = await self.client.get("/api/v3/android/course/foundation")
        self.assertEqual(401, response.status_code)
        self.assertFalse(response.json()["ok"])

    async def test_foundation_returns_the_checked_in_starter_zero_contract(self):
        headers = await self._bearer()
        response = await self.client.get(
            "/api/v3/android/course/foundation",
            headers=headers,
        )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual("starter0_hsk1", body["foundation"]["id"])
        self.assertEqual(1, body["foundation"]["version"])
        self.assertEqual(
            ["meaning", "build", "listen"],
            body["foundation"]["required_objectives"],
        )
        self.assertGreaterEqual(len(body["foundation"]["cards"]), 10)
        self.assertTrue(body["status"]["required"])
        self.assertFalse(body["status"]["completed"])

    async def test_required_foundation_locks_every_unfinished_map_node(self):
        headers = await self._bearer()
        response = await self.client.get("/api/v3/android/course/map", headers=headers)
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["foundation"]["required"])
        self.assertFalse(body["foundation"]["completed"])
        unfinished = [
            lesson
            for unit in body["units"]
            for lesson in unit["lessons"]
            if lesson.get("status") != "done"
        ]
        self.assertTrue(unfinished)
        for lesson in unfinished:
            self.assertEqual("locked", lesson["status"])
            self.assertFalse(lesson["completion_allowed"])
            self.assertEqual("android_foundation_required", lesson["completion_error"])
            self.assertNotIn("preview_half", lesson)
            self.assertNotIn("locked_premium", lesson)

    async def test_required_foundation_blocks_lesson_fetch(self):
        headers = await self._bearer()
        response = await self.client.get(
            "/api/v3/android/course/lesson/1",
            headers=headers,
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("android_foundation_required", response.json()["error"])

    async def test_required_foundation_blocks_lesson_completion(self):
        headers = await self._bearer()
        response = await self.client.post(
            "/api/v3/android/course/complete",
            headers=headers,
            json={
                "lesson_order": 1,
                "event_id": "android:" + "d" * 32,
            },
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("android_foundation_required", response.json()["error"])

    async def test_foundation_completion_unlocks_the_first_lesson(self):
        headers = await self._bearer()
        completed = await self._complete_foundation(headers, suffix="u")
        self.assertEqual(200, completed.status_code)
        self.assertTrue(completed.json()["foundation"]["completed"])

        map_response = await self.client.get(
            "/api/v3/android/course/map",
            headers=headers,
        )
        self.assertEqual(200, map_response.status_code)
        first = map_response.json()["units"][0]["lessons"][0]
        self.assertEqual("current", first["status"])
        self.assertTrue(first["completion_allowed"])
        self.assertNotEqual("android_foundation_required", first.get("completion_error"))

        lesson_response = await self.client.get(
            "/api/v3/android/course/lesson/1",
            headers=headers,
        )
        self.assertEqual(200, lesson_response.status_code)
        self.assertTrue(lesson_response.json()["ok"])

    async def test_foundation_rejects_query_identity_or_overrides(self):
        headers = await self._bearer()
        response = await self.client.get(
            "/api/v3/android/course/foundation?level=hsk4",
            headers=headers,
        )
        self.assertEqual(422, response.status_code)

    async def test_foundation_completion_is_server_backed_and_idempotent(self):
        headers = await self._bearer()
        payload = {
            "foundation_id": "starter0_hsk1",
            "foundation_version": 1,
            "speaking_bonus": True,
            "event_id": "android:foundation:" + "a" * 32,
        }
        first = await self.client.post(
            "/api/v3/android/course/foundation/complete",
            headers=headers,
            json=payload,
        )
        self.assertEqual(200, first.status_code)
        self.assertTrue(first.json()["ok"])
        self.assertFalse(first.json()["duplicate"])
        self.assertTrue(first.json()["foundation"]["completed"])

        retry = await self.client.post(
            "/api/v3/android/course/foundation/complete",
            headers=headers,
            json=payload,
        )
        self.assertEqual(200, retry.status_code)
        self.assertTrue(retry.json()["duplicate"])
        self.assertTrue(retry.json()["foundation"]["completed"])

        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.telegram_id == 1001,
                        CourseMiniAppEvent.event_name == "foundation_completed",
                    )
                )
            ).scalars().all()
        self.assertEqual(1, len(rows))
        self.assertEqual("android_course", rows[0].source)

        map_response = await self.client.get(
            "/api/v3/android/course/map",
            headers=headers,
        )
        self.assertEqual(200, map_response.status_code)
        self.assertTrue(map_response.json()["foundation"]["completed"])

    async def test_foundation_completion_rejects_version_tampering(self):
        headers = await self._bearer()
        bad = await self.client.post(
            "/api/v3/android/course/foundation/complete",
            headers=headers,
            json={
                "foundation_id": "starter0_hsk1",
                "foundation_version": 2,
                "speaking_bonus": False,
                "event_id": "android:foundation:" + "b" * 32,
            },
        )
        self.assertEqual(422, bad.status_code)

    async def test_foundation_completion_rejects_client_identity(self):
        headers = await self._bearer()
        bad = await self.client.post(
            "/api/v3/android/course/foundation/complete",
            headers=headers,
            json={
                "foundation_id": "starter0_hsk1",
                "foundation_version": 1,
                "speaking_bonus": False,
                "event_id": "android:foundation:" + "c" * 32,
                "telegram_id": 9999,
            },
        )
        self.assertEqual(422, bad.status_code)


if __name__ == "__main__":
    unittest.main()
