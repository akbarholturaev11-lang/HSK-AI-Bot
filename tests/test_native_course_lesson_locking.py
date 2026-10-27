"""PostgreSQL regressions for concurrent native course maps and lesson starts."""
import asyncio
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_progress import CourseProgress
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.user import User
from app.services.android_course_service import AndroidCourseService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.desktop_course_service import DesktopCourseService
from tests.native_postgres_deadlines import postgres_timeout


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"),
                     "requires isolated PostgreSQL test database")
class NativeCourseLessonLockingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        database = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
        parsed = make_url(database)
        if parsed.host not in {"localhost", "127.0.0.1", "::1"} or not any(
            marker in (parsed.database or "") for marker in ("_test", "_qa_")
        ):
            raise RuntimeError("lesson locking regression requires a loopback QA/test database")
        self.schema = "lesson_lock_test_" + uuid4().hex
        self.admin = create_async_engine(database)
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(database, connect_args={"server_settings": {
            "search_path": self.schema,
            "lock_timeout": f"{postgres_timeout(5)}s",
            "statement_timeout": f"{postgres_timeout(15)}s",
        }})
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = SimpleNamespace(
            DESKTOP_AUTH_SIGNING_SECRET="native-course-lock-test-" + "x" * 48,
            BOT_USERNAME="fixture_bot",
        )
        self.tokens = {}
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            session.add(User(id=1, telegram_id=91001, full_name="Synthetic learner",
                             level="hsk2", language="uz", status="active",
                             payment_status="approved", start_date=now - timedelta(days=1),
                             end_date=now + timedelta(days=7)))
            await session.flush()
            session.add(CourseProgress(user_id=1, level="hsk2", completed_lessons_count=2))
            for platform in ("android", "macos", "windows"):
                device = DesktopDevice(id="lock-device-" + platform, user_id=1,
                                       telegram_id=91001, platform=platform,
                                       app_version="1.7.21", installation_key_hash=platform)
                session.add(device)
                await session.flush()
                auth_session = DesktopSession(id="lock-session-" + platform,
                    device_id=device.id, refresh_token_hash="lock-refresh-" + platform,
                    expires_at=now + timedelta(days=1))
                session.add(auth_session)
                await session.flush()
                self.tokens[platform], _ = DesktopAuthService(session, self.settings)._access_token(
                    desktop_session=auth_session, device=device)
            await session.commit()
        for target in ("app.services.conversion_funnel_service.async_session_maker",
                       "app.services.entitlements.shadow.async_session_maker"):
            isolated = patch(target, self.sessions)
            isolated.start()
            self.addCleanup(isolated.stop)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    def _service(self, platform, session):
        service = AndroidCourseService if platform == "android" else DesktopCourseService
        return service(session, self.settings)

    async def _assert_parallel_map_and_lesson(self, platform):
        map_has_user, lesson_requests_user = asyncio.Event(), asyncio.Event()

        async def read_map():
            async with self.sessions() as session:
                service = self._service(platform, session)
                original_progress = service._progress

                async def coordinated_progress(user, *, for_update):
                    # The map already owns User. Let the lesson reach its User
                    # lock before requesting progress: the old lesson held the
                    # progress row here, making this an actual database cycle.
                    map_has_user.set()
                    await asyncio.wait_for(lesson_requests_user.wait(), postgres_timeout(10))
                    return await original_progress(user, for_update=for_update)

                service._progress = coordinated_progress
                return await service.course_map(self.tokens[platform])

        async def read_lesson():
            await asyncio.wait_for(map_has_user.wait(), postgres_timeout(10))
            async with self.sessions() as session:
                original_execute = session.execute

                async def coordinated_execute(statement, *args, **kwargs):
                    if getattr(statement, "_for_update_arg", None) is not None and any(
                        column.get("entity") is User
                        for column in getattr(statement, "column_descriptions", ())
                    ):
                        lesson_requests_user.set()
                    return await original_execute(statement, *args, **kwargs)

                session.execute = coordinated_execute
                return await self._service(platform, session).lesson(
                    self.tokens[platform], lesson_order=3)

        results = await asyncio.wait_for(
            asyncio.gather(read_map(), read_lesson(), return_exceptions=True),
            postgres_timeout(20),
        )
        for result in results:
            if isinstance(result, BaseException):
                raise result
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["level"], "hsk2")
        self.assertEqual(results[1]["lesson_order"], 3)
        async with self.sessions() as session:
            progress = await session.scalar(select(CourseProgress).where(CourseProgress.user_id == 1))
            self.assertEqual((progress.level, progress.completed_lessons_count), ("hsk2", 2))

    async def _assert_stale_level_is_refreshed(self, platform):
        async with self.sessions() as reader:
            stale_user = await reader.get(User, 1)
            self.assertEqual(stale_user.level, "hsk2")
            async with self.sessions() as writer:
                user = await writer.get(User, 1)
                user.level = "hsk3"
                progress = await writer.scalar(select(CourseProgress).where(CourseProgress.user_id == 1))
                progress.level, progress.completed_lessons_count = "hsk3", 4
                await writer.commit()
            lesson = await self._service(platform, reader).lesson(
                self.tokens[platform], lesson_order=1)
            self.assertEqual(lesson["level"], "hsk3")
        async with self.sessions() as session:
            progress = await session.scalar(select(CourseProgress).where(CourseProgress.user_id == 1))
            self.assertEqual((progress.level, progress.completed_lessons_count), ("hsk3", 4))

    async def test_android_map_and_lesson_do_not_deadlock(self):
        await self._assert_parallel_map_and_lesson("android")

    async def test_macos_map_and_lesson_do_not_deadlock(self):
        await self._assert_parallel_map_and_lesson("macos")

    async def test_windows_map_and_lesson_do_not_deadlock(self):
        await self._assert_parallel_map_and_lesson("windows")

    async def test_android_lesson_refreshes_stale_level_before_progress(self):
        await self._assert_stale_level_is_refreshed("android")

    async def test_macos_lesson_refreshes_stale_level_before_progress(self):
        await self._assert_stale_level_is_refreshed("macos")

    async def test_windows_lesson_refreshes_stale_level_before_progress(self):
        await self._assert_stale_level_is_refreshed("windows")
