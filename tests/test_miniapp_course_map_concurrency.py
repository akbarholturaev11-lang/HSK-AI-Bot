"""Real PostgreSQL: a map read must not overwrite a concurrent track switch."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.main as main
from app.api.android_course import create_android_course_router
from app.api.desktop_course import create_desktop_course_router
from app.db.base import Base
from app.db.models.course_progress import CourseProgress
from app.db.models.course_feature_usage import CourseFeatureUsage
from app.db.models.course_track_state import CourseTrackState
from app.db.models.user import User
from app.services.course_track_service import CourseTrackService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.hsk30_feature_service import Hsk30FeatureService
from tests.test_i18n_miniapp_reservation_asgi import TEST_ID, TEST_TOKEN, synthetic_init_data
from tests.test_desktop_course_api import _settings


@unittest.skipUnless(os.environ.get("NATIVE_ACCOUNT_TEST_DATABASE_URL"),
                     "requires isolated PostgreSQL test database")
class MiniAppCourseMapConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        database = os.environ["NATIVE_ACCOUNT_TEST_DATABASE_URL"]
        parsed = make_url(database)
        if parsed.host != "127.0.0.1" or "_test" not in (parsed.database or ""):
            raise RuntimeError("course map regression requires a loopback-only test database")
        self.schema = "map_race_test_" + uuid4().hex
        self.reader_tag = "hsk_map_reader_" + uuid4().hex
        self.admin = create_async_engine(database)
        async with self.admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(database, connect_args={
            "server_settings": {"search_path": self.schema + ",public"},
        })
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            now = datetime.now(timezone.utc)
            session.add(User(id=1, telegram_id=TEST_ID, full_name="Synthetic QA",
                             language="uz", level="hsk1", status="active",
                             payment_status="approved", start_date=now - timedelta(days=1),
                             end_date=now + timedelta(days=7)))
            await session.flush()
            session.add(CourseProgress(user_id=1, level="hsk1", completed_lessons_count=5,
                                       current_step="intro", waiting_for="none", homework_status="none"))
            session.add(CourseTrackState(user_id=1, track="hsk30", level="nhsk2",
                                        completed_lessons_count=16))
            feature = Hsk30FeatureService(session)
            await feature.set_enabled(True)
            await feature.set_live_levels(["nhsk2"])
            await session.commit()
        self.settings = _settings()
        self.tokens = {}
        for platform in ("macos", "windows", "android"):
            async with self.sessions() as session:
                auth = DesktopAuthService(session, self.settings)
                started = await auth.start_link(platform=platform, app_version="0.1.0",
                                                installation_key=platform.ljust(48, "x"))
                await auth.approve_link(display_code=started["display_code"], telegram_id=TEST_ID)
                linked = await auth.poll_link(link_request_id=started["link_request_id"],
                                             polling_secret=started["polling_secret"])
                self.tokens[platform] = linked["access_token"]

        @asynccontextmanager
        async def map_sessions():
            async with self.sessions() as session:
                await session.execute(text("SELECT set_config('application_name', :name, true)"),
                                      {"name": self.reader_tag})
                yield session

        for target, replacement in (
            ("app.main.async_session_maker", map_sessions),
            ("app.services.conversion_funnel_service.async_session_maker", self.sessions),
            ("app.services.entitlements.shadow.async_session_maker", self.sessions),
        ):
            mocked = patch(target, replacement)
            mocked.start()
            self.addCleanup(mocked.stop)
        token = patch.object(main.settings, "BOT_TOKEN", TEST_TOKEN)
        token.start()
        self.addCleanup(token.stop)
        app = FastAPI()
        app.add_api_route("/api/v3/map", main.v3_course_map, methods=["GET"])
        app.include_router(create_desktop_course_router(session_factory=map_sessions,
                                                       settings_obj=self.settings))
        app.include_router(create_android_course_router(session_factory=map_sessions,
                                                       settings_obj=self.settings))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://synthetic.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()
        async with self.admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin.dispose()

    async def _wait_for_database_lock(self, task):
        async def observed():
            async with self.admin.connect() as connection:
                while True:
                    if task.done():
                        self.fail(f"map returned before the locked switch committed: {task.result()}")
                    waiting = await connection.scalar(text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE application_name = :name AND wait_event_type = 'Lock'"
                    ), {"name": self.reader_tag})
                    # PostgreSQL caches its statistics snapshot per transaction.
                    await connection.commit()
                    if waiting:
                        return
                    await asyncio.sleep(0.02)
        await asyncio.wait_for(observed(), timeout=10)

    async def _assert_switch_map(self, target_track, level, completed, platform="miniapp"):
        async with self.sessions() as switch_session:
            user = await switch_session.get(User, 1)
            switched = await CourseTrackService(switch_session).switch(user, target_track=target_track)
            self.assertEqual(switched["active_level"], level)
            path = "/api/v3/map" if platform == "miniapp" else (
                "/api/v3/android/course/map" if platform == "android" else "/api/v3/desktop/course/map"
            )
            headers = {"X-Telegram-Init-Data": synthetic_init_data()} if platform == "miniapp" else {
                "Authorization": "Bearer " + self.tokens[platform],
            }
            task = asyncio.create_task(self.client.get(path, headers=headers))
            try:
                await self._wait_for_database_lock(task)
            except BaseException:
                await switch_session.rollback()
                await asyncio.wait_for(task, timeout=15)
                raise
            await switch_session.commit()
            response = await asyncio.wait_for(task, timeout=15)
        self.assertEqual(response.status_code, 200, response.text[:500])
        async with self.sessions() as session:
            user = await session.get(User, 1)
            progress = await session.scalar(select(CourseProgress).where(CourseProgress.user_id == 1))
            self.assertEqual((user.level, progress.level, progress.completed_lessons_count),
                             (level, level, completed))
            states = {row.track: (row.level, row.completed_lessons_count) for row in
                      (await session.scalars(select(CourseTrackState))).all()}
            self.assertEqual(states, {"hsk20": ("hsk1", 5), "hsk30": ("nhsk2", 16)})
            self.assertEqual(await session.scalar(select(func.count()).select_from(CourseFeatureUsage)), 0)
        self.assertEqual(response.json()["level"], level)
        self.assertEqual(response.json()["progress"]["completed"], completed)

    async def test_map_waits_for_track_switch_and_keeps_restored_progress(self):
        await self._assert_switch_map("hsk30", "nhsk2", 16)

    async def test_map_keeps_restored_legacy_progress_when_switching_back(self):
        async with self.sessions() as session:
            await CourseTrackService(session).switch(await session.get(User, 1), target_track="hsk30")
            await session.commit()
        await self._assert_switch_map("hsk20", "hsk1", 5)

    async def test_android_map_keeps_concurrently_restored_progress(self):
        await self._assert_switch_map("hsk30", "nhsk2", 16, "android")

    async def test_macos_map_keeps_concurrently_restored_progress(self):
        await self._assert_switch_map("hsk30", "nhsk2", 16, "macos")

    async def test_windows_map_keeps_concurrently_restored_progress(self):
        await self._assert_switch_map("hsk30", "nhsk2", 16, "windows")
