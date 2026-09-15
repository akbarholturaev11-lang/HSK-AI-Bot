"""The file that makes an Android release take effect without anyone pasting it.

This mirrors what `desktop/latest.json` does for macOS and Windows, and it
carries the same three dangers, because the server fetches whatever the setting
points at and every installed app acts on the answer:

* A manifest that cannot be read must never un-publish a release. After one
  good read, the last-known-good build survives every later failure.
* A manifest that goes backwards must be refused. A stale or restored copy
  would otherwise tell every app to "update" to the build it already replaced.
* The same version pointing at a different file must be refused. A published
  release is finished; changing what is behind it is how people end up running
  something nobody tested.

And one that is specific to this product: Telegram's copy of the APK is keyed
by version. A file_id from an older build attached to a newer version's
announcement is worse than sending nothing at all.
"""

import json
import unittest
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.services.android_release_manifest_service import (
    AndroidReleaseManifestError,
    AndroidReleaseManifestService,
    parse_android_release_manifest,
)
from app.services.android_release_service import (
    ANDROID_MANIFEST_FILE_KEY,
    AndroidReleaseService,
)


BASE = "https://pub-example.r2.dev/android"


def manifest_bytes(**overrides) -> bytes:
    payload = {
        "schema_version": 1,
        "version_name": "1.2.0",
        "version_code": 3,
        "download_url": f"{BASE}/v1.2.0/hsk-ai-1.2.0-3-direct-release.apk",
        "size": 3_784_820,
        "sha256": "a" * 64,
        "published_at": "2026-09-15T12:00:00Z",
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


class ParsingTests(unittest.TestCase):
    def test_a_manifest_the_workflow_writes_is_read_back_whole(self):
        manifest = parse_android_release_manifest(manifest_bytes())

        self.assertEqual(manifest.version_name, "1.2.0")
        self.assertEqual(manifest.version_code, 3)
        self.assertEqual(manifest.size, 3_784_820)
        self.assertTrue(manifest.download_url.endswith(".apk"))

    def test_a_download_url_that_is_not_a_plain_https_apk_is_refused(self):
        for url in (
            "http://pub-example.r2.dev/a.apk",
            f"{BASE}/v1.2.0/app.zip",
            "https://user:pw@pub-example.r2.dev/a.apk",
            "https://localhost/a.apk",
            "https://192.168.1.10/a.apk",
            f"{BASE}/v1.2.0/a.apk?token=secret",
        ):
            with self.subTest(url=url):
                with self.assertRaises(AndroidReleaseManifestError):
                    parse_android_release_manifest(manifest_bytes(download_url=url))

    def test_a_version_code_that_is_not_a_plain_integer_is_refused(self):
        for code in ("3", 3.5, True, 0, -1, None):
            with self.subTest(code=code):
                with self.assertRaises(AndroidReleaseManifestError):
                    parse_android_release_manifest(manifest_bytes(version_code=code))

    def test_an_unknown_key_means_something_else_wrote_this_file(self):
        with self.assertRaises(AndroidReleaseManifestError):
            parse_android_release_manifest(manifest_bytes(surprise="yes"))

    def test_a_different_schema_version_is_refused(self):
        with self.assertRaises(AndroidReleaseManifestError):
            parse_android_release_manifest(manifest_bytes(schema_version=2))

    def test_junk_is_refused(self):
        for payload in (b"", b"not json", b"[]", b"null"):
            with self.subTest(payload=payload):
                with self.assertRaises(AndroidReleaseManifestError):
                    parse_android_release_manifest(payload)


class ResolvingTests(unittest.IsolatedAsyncioTestCase):
    URL = f"{BASE}/latest.json"

    def setUp(self):
        AndroidReleaseManifestService.clear_cache()

    def tearDown(self):
        AndroidReleaseManifestService.clear_cache()

    def _service(self, responses, *, clock=None):
        """A service whose fetches come from `responses`, one per call."""

        self.calls = 0

        def fetcher(url, timeout, max_bytes):
            self.calls += 1
            value = responses[min(self.calls - 1, len(responses) - 1)]
            if isinstance(value, Exception):
                raise value
            return value

        ticks = iter(clock or [0.0, 1000.0, 2000.0, 3000.0, 4000.0])
        return AndroidReleaseManifestService(
            SimpleNamespace(ANDROID_RELEASE_MANIFEST_URL=self.URL),
            fetcher=fetcher,
            clock=lambda: next(ticks),
        )

    async def test_nothing_configured_means_nothing_resolved(self):
        service = AndroidReleaseManifestService(
            SimpleNamespace(ANDROID_RELEASE_MANIFEST_URL="")
        )
        self.assertIsNone(await service.resolve())

    async def test_a_good_manifest_resolves(self):
        service = self._service([manifest_bytes()])
        manifest = await service.resolve()
        self.assertEqual(manifest.version_code, 3)

    async def test_it_is_not_refetched_inside_the_cache_window(self):
        service = self._service([manifest_bytes()], clock=[0.0, 1.0, 2.0])
        await service.resolve()
        await service.resolve()
        self.assertEqual(self.calls, 1)

    async def test_a_later_failure_keeps_the_last_known_good_release(self):
        service = self._service([manifest_bytes(), RuntimeError("storage down")])

        first = await service.resolve()
        second = await service.resolve()

        self.assertEqual(first, second)
        self.assertEqual(second.version_code, 3)

    async def test_a_downgrade_is_refused(self):
        service = self._service(
            [manifest_bytes(), manifest_bytes(version_name="1.1.0", version_code=2)]
        )
        await service.resolve()
        current = await service.resolve()

        self.assertEqual(current.version_code, 3)

    async def test_the_same_version_pointing_somewhere_else_is_refused(self):
        moved = manifest_bytes(
            download_url=f"{BASE}/v1.2.0/hsk-ai-1.2.0-3-direct-release-2.apk"
        )
        service = self._service([manifest_bytes(), moved])
        await service.resolve()
        current = await service.resolve()

        self.assertTrue(current.download_url.endswith("-direct-release.apk"))

    async def test_a_manifest_that_never_parses_resolves_to_nothing(self):
        service = self._service([b"not json"])
        self.assertIsNone(await service.resolve())


class ServingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    class FakeManifest:
        def __init__(self, manifest):
            self.manifest = manifest

        async def resolve(self):
            if isinstance(self.manifest, Exception):
                raise self.manifest
            return self.manifest

    def _service(self, session, manifest=None):
        return AndroidReleaseService(
            session, manifest_service=self.FakeManifest(manifest)
        )

    async def _publish(self, session, **overrides):
        payload = {
            "file_id": "OLD_FILE_ID",
            "file_unique_id": "u1",
            "file_name": "hsk-ai-1.1.0-2-direct-release.apk",
            "file_size": 3_766_687,
            "version_name": "1.1.0",
            "version_code": 2,
        }
        payload.update(overrides)
        return await AndroidReleaseService(session).publish(**payload)

    async def test_without_a_manifest_the_bot_panel_release_is_served(self):
        async with self.sessions() as session:
            await self._publish(session)
            served = await self._service(session).serve()

            self.assertEqual(served.source, "bot")
            self.assertEqual(served.version_code, 2)
            self.assertEqual(served.file_id, "OLD_FILE_ID")

    async def test_a_manifest_wins_over_whatever_was_pasted_by_hand(self):
        async with self.sessions() as session:
            await self._publish(session)
            manifest = parse_android_release_manifest(manifest_bytes())
            served = await self._service(session, manifest).serve()

            self.assertEqual(served.source, "manifest")
            self.assertEqual(served.version_code, 3)
            self.assertEqual(served.size, 3_784_820)
            self.assertTrue(served.download_url.endswith(".apk"))

    async def test_an_older_file_id_is_not_attached_to_a_newer_version(self):
        """The failure that would look fine and ship the wrong APK."""

        async with self.sessions() as session:
            await self._publish(session)
            manifest = parse_android_release_manifest(manifest_bytes())
            served = await self._service(session, manifest).serve()

            self.assertIsNone(served.file_id)

    async def test_telegrams_copy_is_reused_once_it_exists(self):
        async with self.sessions() as session:
            manifest = parse_android_release_manifest(manifest_bytes())
            service = self._service(session, manifest)
            await service.remember_file_id(version_code=3, file_id="NEW_FILE_ID")

            served = await service.serve()
            self.assertEqual(served.file_id, "NEW_FILE_ID")

    async def test_a_cached_file_id_from_another_version_is_ignored(self):
        async with self.sessions() as session:
            manifest = parse_android_release_manifest(manifest_bytes())
            service = self._service(session, manifest)
            await service.remember_file_id(version_code=99, file_id="WRONG_VERSION")

            served = await service.serve()
            self.assertIsNone(served.file_id)

    async def test_a_corrupt_file_id_cache_is_ignored_not_fatal(self):
        async with self.sessions() as session:
            await AndroidReleaseService(session).settings_repo.set(
                ANDROID_MANIFEST_FILE_KEY, "not json"
            )
            await session.commit()
            manifest = parse_android_release_manifest(manifest_bytes())

            served = await self._service(session, manifest).serve()
            self.assertIsNone(served.file_id)

    async def test_a_broken_manifest_never_stops_the_bot_handing_out_the_apk(self):
        async with self.sessions() as session:
            await self._publish(session)
            served = await self._service(session, RuntimeError("boom")).serve()

            self.assertEqual(served.source, "bot")
            self.assertEqual(served.file_id, "OLD_FILE_ID")

    async def test_nothing_anywhere_means_nothing_to_serve(self):
        async with self.sessions() as session:
            self.assertIsNone(await self._service(session).serve())


if __name__ == "__main__":
    unittest.main()
