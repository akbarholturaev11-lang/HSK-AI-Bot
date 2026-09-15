"""What an installed Android app is told about newer builds.

Android cannot update itself silently outside Play, so this answer is the only
thing standing between a learner and a stale app — and every way of getting it
wrong is worse than saying nothing:

* Offering the link from the previous release next to the new release's
  version. The app would download 1.1.0, be told it is 1.2.0, and never stop
  offering the update. Publishing therefore drops the old link.
* Handing out a link that is not a plain https `.apk`. The app downloads
  whatever is behind it and asks the system to install it.
* Answering at all when the caller is already current. A card that never goes
  away is a card people learn to ignore.
"""

import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_update import create_android_update_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.services.android_release_service import (
    AndroidRelease,
    AndroidReleaseError,
    AndroidReleaseService,
    _https_apk_url,
)


GOOD_URL = "https://pub-example.r2.dev/hsk-ai-1.2.0-3-direct-release.apk"


class UpdateUrlValidationTests(unittest.TestCase):
    def test_a_plain_https_apk_link_is_accepted(self):
        self.assertEqual(_https_apk_url(GOOD_URL), GOOD_URL)
        self.assertEqual(_https_apk_url(f"  {GOOD_URL}  "), GOOD_URL)

    def test_everything_else_is_treated_as_absent(self):
        for value in (
            "",
            None,
            "http://pub-example.r2.dev/app.apk",          # not https
            "https://pub-example.r2.dev/app.zip",         # not an apk
            "https://pub-example.r2.dev/",                # no file
            "ftp://pub-example.r2.dev/app.apk",           # not http at all
            "https://user:secret@pub-example.r2.dev/a.apk",  # carries a credential
            "https://" + "a" * 3000 + "/app.apk",         # absurd length
            "not a url at all",
        ):
            with self.subTest(value=value):
                self.assertIsNone(_https_apk_url(value))

    def test_a_stored_bad_url_reads_back_as_absent(self):
        # A row outlives the code that wrote it; validation runs on the way out
        # too, so a link written by an older build is not handed to a client.
        release = AndroidRelease.from_json(
            '{"file_id":"X","version_name":"1.1.0","version_code":2,'
            '"update_url":"http://insecure.example/app.apk"}'
        )
        self.assertIsNone(release.update_url)
        self.assertFalse(release.can_self_update)


class DatabaseBackedTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        self.clients = []

    async def asyncTearDown(self):
        for client in self.clients:
            await client.aclose()
        await self.db.dispose()

    async def _publish(self, session, **overrides):
        payload = {
            "file_id": "BQACAgIAAx",
            "file_unique_id": "AgAD1",
            "file_name": "hsk-ai-1.2.0-3-direct-release.apk",
            "file_size": 3_766_687,
            "version_name": "1.2.0",
            "version_code": 3,
            "published_by": 7965751363,
        }
        payload.update(overrides)
        return await AndroidReleaseService(session).publish(**payload)

    async def make_client(self):
        app = FastAPI()
        app.include_router(create_android_update_router(session_factory=self.sessions))
        client = AsyncClient(
            transport=ASGITransport(app=app), base_url="https://testserver"
        )
        self.clients.append(client)
        return client


class SettingTheUpdateUrlTests(DatabaseBackedTest):
    async def test_it_is_stored_beside_the_file_it_belongs_to(self):
        async with self.sessions() as session:
            await self._publish(session)
            release = await AndroidReleaseService(session).set_update_url(GOOD_URL)
            self.assertEqual(release.update_url, GOOD_URL)
            self.assertTrue(release.can_self_update)

            reread = await AndroidReleaseService(session).current()
            self.assertEqual(reread.update_url, GOOD_URL)
            # The Telegram file is untouched by any of this.
            self.assertEqual(reread.file_id, "BQACAgIAAx")

    async def test_it_is_refused_when_nothing_is_published(self):
        async with self.sessions() as session:
            with self.assertRaises(AndroidReleaseError):
                await AndroidReleaseService(session).set_update_url(GOOD_URL)

    async def test_it_is_refused_without_a_version_code_to_compare(self):
        async with self.sessions() as session:
            await self._publish(session, version_code=None, file_name="app.apk")
            with self.assertRaises(AndroidReleaseError):
                await AndroidReleaseService(session).set_update_url(GOOD_URL)

    async def test_a_bad_link_is_refused_rather_than_stored(self):
        async with self.sessions() as session:
            await self._publish(session)
            with self.assertRaises(AndroidReleaseError):
                await AndroidReleaseService(session).set_update_url(
                    "http://insecure.example/app.apk"
                )
            self.assertIsNone((await AndroidReleaseService(session).current()).update_url)

    async def test_clearing_stops_updates_but_keeps_the_file(self):
        async with self.sessions() as session:
            await self._publish(session)
            await AndroidReleaseService(session).set_update_url(GOOD_URL)
            release = await AndroidReleaseService(session).clear_update_url()

            self.assertIsNone(release.update_url)
            self.assertFalse(release.can_self_update)
            self.assertEqual(release.file_id, "BQACAgIAAx")

    async def test_publishing_again_drops_the_previous_link(self):
        """The one that would be silently wrong."""

        async with self.sessions() as session:
            await self._publish(session, version_name="1.2.0", version_code=3)
            await AndroidReleaseService(session).set_update_url(GOOD_URL)

            await self._publish(
                session,
                version_name="1.3.0",
                version_code=4,
                file_name="hsk-ai-1.3.0-4-direct-release.apk",
            )
            current = await AndroidReleaseService(session).current()

            self.assertEqual(current.version_code, 4)
            # 1.3.0 must not be advertised with 1.2.0's file behind it.
            self.assertIsNone(current.update_url)
            self.assertFalse(current.can_self_update)


class UpdateCheckTests(DatabaseBackedTest):
    async def test_an_older_app_is_told_what_exists(self):
        async with self.sessions() as session:
            await self._publish(session)
            await AndroidReleaseService(session).set_update_url(GOOD_URL)

        client = await self.make_client()
        response = await client.get("/api/v3/android-update/check", params={"version_code": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "version_name": "1.2.0",
                "version_code": 3,
                "url": GOOD_URL,
                "size": 3_766_687,
            },
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    async def test_an_app_already_on_it_is_told_nothing(self):
        async with self.sessions() as session:
            await self._publish(session)
            await AndroidReleaseService(session).set_update_url(GOOD_URL)

        client = await self.make_client()
        for installed in (3, 4, 99):
            with self.subTest(installed=installed):
                response = await client.get(
                    "/api/v3/android-update/check", params={"version_code": installed}
                )
                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.content, b"")

    async def test_every_reason_to_say_nothing_looks_the_same(self):
        client = await self.make_client()

        # Nothing published at all.
        response = await client.get("/api/v3/android-update/check", params={"version_code": 1})
        self.assertEqual(response.status_code, 204)

        # Published, but no link behind it.
        async with self.sessions() as session:
            await self._publish(session)
        response = await client.get("/api/v3/android-update/check", params={"version_code": 1})
        self.assertEqual(response.status_code, 204)

        # Published with a link but no version code to compare against.
        async with self.sessions() as session:
            await self._publish(session, version_code=None, file_name="app.apk")
        response = await client.get("/api/v3/android-update/check", params={"version_code": 1})
        self.assertEqual(response.status_code, 204)

    async def test_a_nonsense_version_code_is_refused_not_guessed(self):
        client = await self.make_client()
        for value in ("-1", "abc", ""):
            with self.subTest(value=value):
                response = await client.get(
                    "/api/v3/android-update/check", params={"version_code": value}
                )
                self.assertEqual(response.status_code, 422)

    async def test_a_broken_database_says_nothing_rather_than_failing(self):
        """An app that cannot reach us must keep working."""

        def exploding_session():
            raise RuntimeError("database is down")

        app = FastAPI()
        app.include_router(create_android_update_router(session_factory=exploding_session))
        client = AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")
        self.clients.append(client)

        response = await client.get("/api/v3/android-update/check", params={"version_code": 1})
        self.assertEqual(response.status_code, 204)


class DownloadRedirectTests(DatabaseBackedTest):
    async def test_it_points_at_the_published_artifact(self):
        async with self.sessions() as session:
            await self._publish(session)
            await AndroidReleaseService(session).set_update_url(GOOD_URL)

        client = await self.make_client()
        response = await client.get("/downloads/android", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], GOOD_URL)
        self.assertIn("hsk-ai-1.2.0-3-direct-release.apk", response.headers["Content-Disposition"])

    async def test_it_is_a_plain_404_when_there_is_nothing_to_point_at(self):
        client = await self.make_client()
        response = await client.get("/downloads/android", follow_redirects=False)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
