"""Regression coverage for the Android Course v3 adapter.

The point of these tests is that Android reuses the desktop course rules
exactly, with one deliberate difference: its own analytics and dedupe
namespace. So they check both that Android behaves like desktop where it must,
and that the two namespaces cannot contaminate each other.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_course import create_android_course_router
from app.db.base import Base
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.android_course_service import AndroidCourseService
from app.services.course_miniapp_access_service import (
    FREE_COURSE_LESSONS_PER_LEVEL,
    free_course_parts_for_level,
)
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.desktop_course_service import (
    DesktopCourseError,
    DesktopCourseService,
)


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="android-course-test-secret-" + "x" * 40,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
    )


def _user(user_id: int, telegram_id: int, name: str, *, level: str = "hsk1") -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=name,
        language="uz",
        level=level,
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


class AndroidCourseNamespaceTests(unittest.TestCase):
    def test_android_reuses_the_desktop_rules_with_its_own_namespace(self):
        # Subclassing, not copying: every course rule stays in one place.
        self.assertTrue(issubclass(AndroidCourseService, DesktopCourseService))
        self.assertEqual("android", AndroidCourseService.CLIENT_NAMESPACE)
        self.assertEqual("desktop", DesktopCourseService.CLIENT_NAMESPACE)


class AndroidCourseServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Account A"))
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _token(self, session, *, platform="android", installation="i" * 48):
        auth = DesktopAuthService(session, _settings())
        started = await auth.start_link(
            platform=platform,
            app_version="1.0.0",
            installation_key=installation,
        )
        await auth.approve_link(
            display_code=started["display_code"],
            telegram_id=1001,
        )
        linked = await auth.poll_link(
            link_request_id=started["link_request_id"],
            polling_secret=started["polling_secret"],
        )
        return linked["access_token"]

    async def _completed_count(self, session):
        progress = await CourseProgressRepository(session).get_by_user_id(1)
        return int(progress.completed_lessons_count or 0)

    @staticmethod
    def _flatten(data):
        return [lesson for unit in data["units"] for lesson in unit["lessons"]]

    async def test_map_returns_canonical_progress_and_server_access_state(self):
        async with self.sessions() as session:
            token = await self._token(session)
            data = await AndroidCourseService(session, _settings()).course_map(token)

        self.assertTrue(data["ok"])
        self.assertEqual("hsk1", data["level"])
        self.assertEqual(0, data["progress"]["completed"])
        self.assertFalse(data["user"]["is_paid"])

        lessons = self._flatten(data)
        # Course v3 is split into mini-parts; the client must never hardcode
        # this count, so the map is the only source of truth.
        self.assertEqual(63, len(lessons))
        # Legacy constant stays two for compatibility; HSK1 uses the canonical
        # level-aware allowance.
        self.assertEqual(2, FREE_COURSE_LESSONS_PER_LEVEL)
        hsk1_free_parts = free_course_parts_for_level("hsk1")
        self.assertEqual(3, hsk1_free_parts)

        # Lesson 1 is the current one and is fully free.
        self.assertEqual("current", lessons[0]["status"])
        self.assertTrue(lessons[0]["completion_allowed"])

        # Lesson 2 is inside the free allowance but has not been reached yet,
        # so it is locked by progress, not by payment.
        self.assertEqual("locked", lessons[1]["status"])
        self.assertFalse(lessons[1]["completion_allowed"])
        self.assertEqual(
            "course_lesson_not_unlocked",
            lessons[1]["completion_error"],
        )
        self.assertNotIn("locked_premium", lessons[1])

        # Part 3 is the free HSK1 checkpoint, still locked only by progress.
        checkpoint = lessons[hsk1_free_parts - 1]
        self.assertNotIn("locked_premium", checkpoint)
        self.assertEqual("course_lesson_not_unlocked", checkpoint["completion_error"])

        # The first premium lesson is a hard lock while it is still out of
        # reach. The half preview is NOT shown here.
        first_premium = lessons[hsk1_free_parts]
        self.assertTrue(first_premium["locked_premium"])
        self.assertIsNone(first_premium.get("preview_half"))
        self.assertFalse(first_premium["completion_allowed"])
        self.assertEqual("free_feature_limit_reached", first_premium["completion_error"])

    async def test_half_preview_appears_only_once_the_learner_reaches_it(self):
        """`preview_half` is bound to the learner's position, not to the level.

        The server only offers it when the premium lesson is the learner's
        *current* one, i.e. exactly after the free allowance is used up.
        """

        async with self.sessions() as session:
            token = await self._token(session)
            service = AndroidCourseService(session, _settings())
            hsk1_free_parts = free_course_parts_for_level("hsk1")
            for order in range(1, hsk1_free_parts + 1):
                await service.complete(
                    token,
                    lesson_order=order,
                    event_id=f"android:reach{order:031d}",
                )
            lessons = self._flatten(await service.course_map(token))

        for index in range(hsk1_free_parts):
            self.assertEqual("done", lessons[index]["status"])

        first_premium = lessons[hsk1_free_parts]
        self.assertEqual("current", first_premium["status"])
        self.assertTrue(first_premium["preview_half"])
        self.assertNotIn("locked_premium", first_premium)
        # Visible, but the preview still cannot finish the lesson.
        self.assertFalse(first_premium["completion_allowed"])
        self.assertEqual("free_feature_limit_reached", first_premium["completion_error"])

        # Everything past the preview stays hard-locked.
        next_premium = lessons[hsk1_free_parts + 1]
        self.assertTrue(next_premium["locked_premium"])
        self.assertIsNone(next_premium.get("preview_half"))
        self.assertFalse(next_premium["completion_allowed"])

    async def test_utc_plus_zero_timezone_is_stored_not_swallowed(self):
        async with self.sessions() as session:
            token = await self._token(session)
            await AndroidCourseService(session, _settings()).course_map(
                token,
                timezone_offset_minutes=0,
            )
            profile = await CourseMiniAppProfileService(session).get_or_create(1)
            self.assertEqual(0, int(profile.timezone_offset_minutes or 0))

    async def test_completion_is_idempotent_and_awards_progress_once(self):
        async with self.sessions() as session:
            token = await self._token(session)
            service = AndroidCourseService(session, _settings())
            event_id = "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6"

            first = await service.complete(token, lesson_order=1, event_id=event_id)
            self.assertTrue(first["ok"])
            self.assertEqual(1, first["completed_lesson"])
            self.assertNotIn("duplicate", first)
            self.assertEqual(1, await self._completed_count(session))

            # A retried request (flaky network, process death) must return the
            # stored result rather than advancing progress a second time.
            retry = await service.complete(token, lesson_order=1, event_id=event_id)
            self.assertTrue(retry["duplicate"])
            self.assertEqual(
                first["completed_lessons_count"],
                retry["completed_lessons_count"],
            )
            self.assertEqual(1, await self._completed_count(session))

    async def test_completion_uses_an_android_dedupe_namespace(self):
        async with self.sessions() as session:
            token = await self._token(session)
            event_id = "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6"
            await AndroidCourseService(session, _settings()).complete(
                token,
                lesson_order=1,
                event_id=event_id,
            )
            recorded = (
                await session.execute(
                    select(CourseMiniAppEvent).where(
                        CourseMiniAppEvent.event_name == "lesson_completed",
                    )
                )
            ).scalars().all()

        self.assertEqual(1, len(recorded))
        event = recorded[0]
        self.assertEqual(f"android-course-complete:{event_id}", event.dedupe_key)
        self.assertEqual("android_course", event.source)
        # Never counted as a desktop completion.
        self.assertNotIn("desktop", str(event.dedupe_key))
        self.assertNotIn("desktop", str(event.source))

    async def test_android_and_desktop_completions_do_not_collide(self):
        """The same event id from two clients must stay two separate records."""

        async with self.sessions() as session:
            android_token = await self._token(session, platform="android")
            desktop_token = await self._token(
                session,
                platform="macos",
                installation="d" * 48,
            )
            shared_event_id = "shared:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6"

            await AndroidCourseService(session, _settings()).complete(
                android_token,
                lesson_order=1,
                event_id=shared_event_id,
            )
            # Desktop reuses the same id; it must not be treated as a duplicate
            # of the Android one, and it must not be rejected as a conflict.
            desktop_result = await DesktopCourseService(session, _settings()).complete(
                desktop_token,
                lesson_order=2,
                event_id=shared_event_id,
            )
            self.assertTrue(desktop_result["ok"])
            self.assertNotIn("duplicate", desktop_result)

            keys = sorted(
                (
                    await session.execute(
                        select(CourseMiniAppEvent.dedupe_key).where(
                            CourseMiniAppEvent.event_name == "lesson_completed",
                        )
                    )
                ).scalars().all()
            )

        self.assertEqual(
            [
                f"android-course-complete:{shared_event_id}",
                f"desktop-course-complete:{shared_event_id}",
            ],
            keys,
        )

    async def test_free_user_cannot_complete_a_premium_lesson(self):
        async with self.sessions() as session:
            token = await self._token(session)
            service = AndroidCourseService(session, _settings())
            hsk1_free_parts = free_course_parts_for_level("hsk1")
            for order in range(1, hsk1_free_parts + 1):
                await service.complete(
                    token,
                    lesson_order=order,
                    event_id=f"android:free{order:032d}",
                )

            # The next lesson is the half preview: visible, not completable.
            with self.assertRaises(DesktopCourseError) as blocked:
                await service.complete(
                    token,
                    lesson_order=hsk1_free_parts + 1,
                    event_id="android:preview" + "0" * 25,
                )
            self.assertEqual(403, blocked.exception.status_code)
            self.assertEqual(
                hsk1_free_parts,
                await self._completed_count(session),
            )

    async def test_lesson_payload_matches_the_checked_in_material(self):
        async with self.sessions() as session:
            token = await self._token(session)
            lesson = await AndroidCourseService(session, _settings()).lesson(
                token,
                lesson_order=1,
            )

        self.assertTrue(lesson["ok"])
        sections = lesson["lesson"]["sections"]
        self.assertTrue(sections)
        # Section metadata has no `type`; the renderer keys off section_purpose.
        for section in sections:
            self.assertIn("section_no", section)
            self.assertIn("section_purpose", section)
            self.assertNotIn("type", section)


class AndroidCourseApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Account A"))
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
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _bearer(self):
        async with self.sessions() as session:
            auth = DesktopAuthService(session, _settings())
            started = await auth.start_link(
                platform="android",
                app_version="1.0.0",
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
        return {"Authorization": f"Bearer {linked['access_token']}"}

    async def test_every_route_requires_a_bearer_token(self):
        cases = [
            ("get", "/api/v3/android/course/map", None),
            ("get", "/api/v3/android/course/lesson/1", None),
            ("get", "/api/v3/android/tts?text=你好", None),
            (
                "post",
                "/api/v3/android/course/complete",
                {"lesson_order": 1, "event_id": "android:" + "a" * 32},
            ),
            ("post", "/api/v3/android/preferences/language", {"language": "uz"}),
        ]
        for method, path, body in cases:
            with self.subTest(path=path):
                response = await getattr(self.client, method)(
                    path,
                    **({"json": body} if body is not None else {}),
                )
                self.assertEqual(401, response.status_code)
                self.assertEqual("no-store", response.headers.get("Cache-Control"))

    async def test_tts_requires_bearer_before_validating_text(self):
        response = await self.client.get("/api/v3/android/tts")

        self.assertEqual(401, response.status_code)
        self.assertEqual("no-store", response.headers.get("Cache-Control"))

    async def test_tts_rejects_non_chinese_or_oversized_text(self):
        headers = await self._bearer()
        for text in ("hello", "你" * 241):
            with self.subTest(length=len(text)):
                response = await self.client.get(
                    "/api/v3/android/tts",
                    params={"text": text},
                    headers=headers,
                )
                self.assertEqual(400, response.status_code)
                self.assertEqual("android_tts_bad_text", response.json()["error"])
                self.assertEqual("no-store", response.headers.get("Cache-Control"))

    async def test_tts_serves_a_private_bearer_authenticated_audio_file(self):
        headers = await self._bearer()
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "lesson.mp3"
            audio.write_bytes(b"ID3-test-audio")
            with patch(
                "app.api.android_course._android_tts_file",
                new=AsyncMock(return_value=audio),
            ) as generator:
                response = await self.client.get(
                    "/api/v3/android/tts",
                    params={"text": "你好"},
                    headers=headers,
                )

        self.assertEqual(200, response.status_code)
        self.assertEqual("audio/mpeg", response.headers["content-type"])
        self.assertEqual(
            "private, max-age=31536000, immutable",
            response.headers["cache-control"],
        )
        self.assertEqual(b"ID3-test-audio", response.content)
        generator.assert_awaited_once_with("你好")

    async def test_map_is_served_with_no_store(self):
        response = await self.client.get(
            "/api/v3/android/course/map",
            headers=await self._bearer(),
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers.get("Cache-Control"))
        self.assertEqual("hsk1", response.json()["level"])

    async def test_lesson_order_is_bounded(self):
        headers = await self._bearer()
        for order in (0, 501, 9999):
            with self.subTest(order=order):
                response = await self.client.get(
                    f"/api/v3/android/course/lesson/{order}",
                    headers=headers,
                )
                self.assertEqual(422, response.status_code)
                self.assertEqual(
                    "invalid_lesson_order",
                    response.json()["error"],
                )

    async def test_timezone_query_is_validated_and_accepts_utc(self):
        headers = await self._bearer()
        ok = await self.client.get(
            "/api/v3/android/course/map?tz=0",
            headers=headers,
        )
        self.assertEqual(200, ok.status_code)

        for value in ("-721", "841", "abc"):
            with self.subTest(tz=value):
                bad = await self.client.get(
                    f"/api/v3/android/course/map?tz={value}",
                    headers=headers,
                )
                self.assertEqual(422, bad.status_code)

    async def test_completion_rejects_a_client_supplied_user(self):
        headers = await self._bearer()
        response = await self.client.post(
            "/api/v3/android/course/complete",
            headers=headers,
            json={
                "lesson_order": 1,
                "event_id": "android:" + "a" * 32,
                "telegram_id": 1002,
            },
        )
        # extra="forbid": identity comes from the bearer token, never the body.
        self.assertEqual(422, response.status_code)

    async def test_language_preference_round_trips(self):
        headers = await self._bearer()
        response = await self.client.post(
            "/api/v3/android/preferences/language",
            headers=headers,
            json={"language": "tj"},
        )
        self.assertEqual(200, response.status_code)

        async with self.sessions() as session:
            user = (
                await session.execute(select(User).where(User.id == 1))
            ).scalar_one()
            self.assertEqual("tj", user.language)

        bad = await self.client.post(
            "/api/v3/android/preferences/language",
            headers=headers,
            # "tg" is the Android resource qualifier, never a backend value.
            json={"language": "tg"},
        )
        self.assertEqual(422, bad.status_code)

    async def test_duplicate_completion_over_http_returns_the_stored_result(self):
        headers = await self._bearer()
        body = {"lesson_order": 1, "event_id": "android:" + "b" * 32}
        first = await self.client.post(
            "/api/v3/android/course/complete",
            headers=headers,
            json=body,
        )
        self.assertEqual(200, first.status_code)
        retry = await self.client.post(
            "/api/v3/android/course/complete",
            headers=headers,
            json=body,
        )
        self.assertEqual(200, retry.status_code)
        self.assertTrue(retry.json()["duplicate"])
        self.assertEqual(
            first.json()["completed_lessons_count"],
            retry.json()["completed_lessons_count"],
        )

    async def test_notifications_toggle_persists_and_shows_in_the_map(self):
        headers = await self._bearer()
        # The course map is the single source of truth the clients read back.
        before = await self.client.get("/api/v3/android/course/map", headers=headers)
        self.assertTrue(before.json()["notify"]["enabled"])

        off = await self.client.post(
            "/api/v3/android/preferences/notifications",
            headers=headers,
            json={"enabled": False},
        )
        self.assertEqual(200, off.status_code)
        self.assertTrue(off.json()["ok"])

        after = await self.client.get("/api/v3/android/course/map", headers=headers)
        self.assertFalse(after.json()["notify"]["enabled"])

        on = await self.client.post(
            "/api/v3/android/preferences/notifications",
            headers=headers,
            json={"enabled": True},
        )
        self.assertEqual(200, on.status_code)
        again = await self.client.get("/api/v3/android/course/map", headers=headers)
        self.assertTrue(again.json()["notify"]["enabled"])

    async def test_notifications_toggle_requires_a_bearer_token(self):
        anonymous = await self.client.post(
            "/api/v3/android/preferences/notifications",
            json={"enabled": False},
        )
        self.assertEqual(401, anonymous.status_code)
        self.assertFalse(anonymous.json()["ok"])

    async def test_notifications_toggle_rejects_a_value_that_is_not_a_flag(self):
        headers = await self._bearer()
        for value in ("maybe", 7, [], None):
            with self.subTest(enabled=value):
                bad = await self.client.post(
                    "/api/v3/android/preferences/notifications",
                    headers=headers,
                    json={"enabled": value},
                )
                self.assertEqual(422, bad.status_code)

    async def test_notifications_toggle_shares_the_desktop_request_model(self):
        # The model is reused from desktop, so boolean-like strings coerce the
        # same way on both clients. Pinned here so a future strictness change
        # is a deliberate, cross-client decision rather than a surprise.
        headers = await self._bearer()
        coerced = await self.client.post(
            "/api/v3/android/preferences/notifications",
            headers=headers,
            json={"enabled": "false"},
        )
        self.assertEqual(200, coerced.status_code)
        after = await self.client.get("/api/v3/android/course/map", headers=headers)
        self.assertFalse(after.json()["notify"]["enabled"])


if __name__ == "__main__":
    unittest.main()
