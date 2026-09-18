"""One answer covering every client a learner can install.

The desktop installers and the Android APK are published by different
pipelines and answered by different services. The download page needs them in
one shape — and so does anything reading the site without running its
JavaScript, which now includes search and AI crawlers.

The rule worth pinning is the conservative one: a platform whose state cannot
be read is reported as unavailable. Half a page that works beats a page that
fails because one pipeline is down.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.app_downloads import create_app_downloads_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.services.android_release_service import AndroidReleaseService
from app.services.app_downloads_service import app_download_status


def _desktop_settings(**overrides):
    values = {
        "DESKTOP_DOWNLOADS_ENABLED": True,
        "DESKTOP_DOWNLOAD_BASE_URL": "https://hsk.example",
        "DESKTOP_MAC_DOWNLOAD_URL": "https://cdn.example/HSK-AI_1.4.2.dmg",
        "DESKTOP_MAC_VERSION": "1.4.2",
        "DESKTOP_WINDOWS_DOWNLOAD_URL": "https://cdn.example/HSK-AI_1.4.2-setup.exe",
        "DESKTOP_WINDOWS_VERSION": "1.4.2",
        "DESKTOP_RELEASE_MANIFEST_URL": "",
        "ANDROID_RELEASE_MANIFEST_URL": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class StatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _publish_android(self):
        async with self.sessions() as session:
            service = AndroidReleaseService(session)
            await service.publish(
                file_id="F",
                file_unique_id="U",
                file_name="hsk-ai-1.1.1-3-direct-release.apk",
                file_size=3_850_356,
                version_name="1.1.1",
                version_code=3,
            )
            await service.set_update_url(
                "https://pub-example.r2.dev/android/v1.1.1/hsk-ai-1.1.1-3-direct-release.apk"
            )

    async def _status(self, settings_obj=None):
        return await app_download_status(
            session_factory=self.sessions,
            settings_obj=settings_obj or _desktop_settings(),
        )

    async def test_all_three_platforms_are_reported(self):
        await self._publish_android()
        status = await self._status()

        self.assertTrue(status["ok"])
        self.assertEqual(
            sorted(status["platforms"]), ["android", "macos", "windows"]
        )
        self.assertTrue(status["any"])

    async def test_a_published_platform_carries_its_version_and_a_stable_link(self):
        await self._publish_android()
        status = await self._status()

        android = status["platforms"]["android"]
        self.assertTrue(android["available"])
        self.assertEqual(android["version"], "1.1.1 (3)")
        self.assertEqual(android["size"], 3_850_356)
        # Our own origin, not the bucket: the bucket changes, this does not.
        self.assertEqual(android["download"], "/downloads/android")
        self.assertTrue(android["file"].endswith(".apk"))

        mac = status["platforms"]["macos"]
        self.assertTrue(mac["available"])
        self.assertEqual(mac["version"], "1.4.2")
        self.assertEqual(mac["download"], "/downloads/macos")

    async def test_an_apk_with_no_public_url_is_still_offered(self):
        """The bot is the channel; a link of ours is not required.

        The admin publishes the file to the bot first and sets the storage URL
        afterwards, if at all. In between, the APK can be handed over inside
        the chat — so the download page must offer it, while the crawler list
        and the JSON-LD, which need a real file to point at, must not claim a
        link that does not exist.
        """

        async with self.sessions() as session:
            await AndroidReleaseService(session).publish(
                file_id="F",
                file_unique_id="U",
                file_name="hsk-ai-1.1.1-3-direct-release.apk",
                file_size=3_850_356,
                version_name="1.1.1",
                version_code=3,
            )

        android = (await self._status())["platforms"]["android"]

        self.assertTrue(android["available"])
        self.assertEqual(android["version"], "1.1.1 (3)")
        self.assertIsNone(android["download"])

    async def test_an_unpublished_platform_is_plainly_unavailable(self):
        # Nothing published for Android at all.
        status = await self._status()

        android = status["platforms"]["android"]
        self.assertFalse(android["available"])
        self.assertIsNone(android["version"])
        self.assertIsNone(android["download"])

    async def test_desktop_downloads_switched_off_are_not_offered(self):
        await self._publish_android()
        status = await self._status(_desktop_settings(DESKTOP_DOWNLOADS_ENABLED=False))

        self.assertFalse(status["platforms"]["macos"]["available"])
        self.assertFalse(status["platforms"]["windows"]["available"])
        # Android is published by a different pipeline and is unaffected.
        self.assertTrue(status["platforms"]["android"]["available"])

    async def test_one_pipeline_failing_does_not_take_the_others_with_it(self):
        await self._publish_android()

        with patch(
            "app.services.app_downloads_service.DesktopReleaseConfig.resolve",
            side_effect=RuntimeError("manifest host is down"),
        ):
            status = await self._status()

        self.assertTrue(status["ok"])
        self.assertFalse(status["platforms"]["macos"]["available"])
        self.assertTrue(status["platforms"]["android"]["available"])

    async def test_a_broken_database_leaves_the_desktop_offer_standing(self):
        def exploding():
            raise RuntimeError("database is down")

        status = await app_download_status(
            session_factory=exploding,
            settings_obj=_desktop_settings(),
        )

        self.assertTrue(status["ok"])
        self.assertFalse(status["platforms"]["android"]["available"])
        self.assertTrue(status["platforms"]["macos"]["available"])


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

        app = FastAPI()
        app.include_router(
            create_app_downloads_router(
                session_factory=self.sessions,
                settings_obj=_desktop_settings(),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="https://testserver"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.dispose()

    async def test_it_answers_and_may_be_cached_briefly(self):
        response = await self.client.get("/api/v3/apps/public-status")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("android", body["platforms"])
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=60")


if __name__ == "__main__":
    unittest.main()
