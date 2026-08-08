import asyncio
import json
import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, MockTransport, Response

from app.api.desktop_download import create_desktop_download_router
from app.api.desktop_update import create_desktop_update_router
from app.services.desktop_download_service import DesktopReleaseConfig
from app.services.desktop_release_manifest_service import (
    DesktopReleaseManifestError,
    DesktopReleaseManifestService,
    parse_desktop_release_manifest,
    resolve_desktop_latest_versions,
)


def _settings(**overrides):
    values = {
        "DESKTOP_DOWNLOADS_ENABLED": True,
        "DESKTOP_DOWNLOAD_BASE_URL": "https://app.example.test",
        "MINI_APP_BASE_URL": "https://app.example.test/course-v3.html",
        "DESKTOP_UPDATES_ENABLED": True,
        "DESKTOP_RELEASE_MANIFEST_URL": (
            "https://releases.example.test/desktop/latest.json"
        ),
        "DESKTOP_RELEASE_MANIFEST_CACHE_TTL_SECONDS": 60,
        "DESKTOP_RELEASE_MANIFEST_TIMEOUT_SECONDS": 3,
        "DESKTOP_RELEASE_MANIFEST_MAX_BYTES": 65536,
        # Deliberately different legacy values prove that a configured
        # manifest is authoritative instead of silently mixing sources.
        "DESKTOP_MAC_DOWNLOAD_URL": "https://legacy.test/legacy.dmg",
        "DESKTOP_WINDOWS_DOWNLOAD_URL": "https://legacy.test/legacy.exe",
        "DESKTOP_MAC_VERSION": "9.9.9",
        "DESKTOP_WINDOWS_VERSION": "9.9.9",
        "DESKTOP_MAC_UPDATER_URL": "https://legacy.test/legacy.app.tar.gz",
        "DESKTOP_MAC_UPDATER_SIGNATURE": "L" * 96,
        "DESKTOP_MAC_UPDATER_NOTES": "legacy",
        "DESKTOP_WINDOWS_UPDATER_URL": "https://legacy.test/legacy.exe",
        "DESKTOP_WINDOWS_UPDATER_SIGNATURE": "W" * 96,
        "DESKTOP_WINDOWS_UPDATER_NOTES": "legacy",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _manifest(
    version="1.3.0",
    *,
    notes="Desktop release",
    mac_download=None,
    mac_update=None,
    win_download=None,
    win_update=None,
):
    base = f"https://releases.example.test/desktop/v{version}"
    document = {
        "schema_version": 1,
        "version": version,
        "notes": notes,
        "published_at": "2026-08-09T01:02:03Z",
        "macos": {
            "download_url": mac_download
            or f"{base}/Pomp-HSK-AI_{version}_universal.dmg",
            "update_url": mac_update
            or f"{base}/Pomp-HSK-AI_{version}_universal.app.tar.gz",
            "signature": "A" * 96,
            "download_sha256": "1" * 64,
            "update_sha256": "2" * 64,
        },
        "windows": {
            "download_url": win_download
            or f"{base}/Pomp-HSK-AI_{version}_x64-setup.exe",
            "update_url": win_update
            or f"{base}/Pomp-HSK-AI_{version}_x64-setup.exe",
            "signature": "B" * 96,
            "sha256": "3" * 64,
        },
    }
    return json.dumps(document, separators=(",", ":")).encode()


class _Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class _SequenceFetcher:
    def __init__(self, *items):
        self.items = list(items)
        self.calls = 0

    async def __call__(self, _url, _timeout, _max_bytes):
        self.calls += 1
        if not self.items:
            raise AssertionError("unexpected fetch")
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _NullSessionContext:
    async def __aenter__(self):
        return None

    async def __aexit__(self, _exc_type, _exc, _traceback):
        return False


def _session_factory():
    return _NullSessionContext()


class DesktopReleaseManifestServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        DesktopReleaseManifestService.clear_cache()
        self.clients = []

    async def asyncTearDown(self):
        for client in self.clients:
            await client.aclose()
        DesktopReleaseManifestService.clear_cache()

    async def test_one_manifest_drives_update_download_and_public_status(self):
        fetcher = _SequenceFetcher(_manifest("1.3.0", notes="Real release"))
        resolver = DesktopReleaseManifestService(
            _settings(),
            fetcher=fetcher,
        )

        update_app = FastAPI()
        update_app.include_router(
            create_desktop_update_router(
                settings_obj=_settings(),
                release_manifest_service=resolver,
            )
        )
        update_client = AsyncClient(
            transport=ASGITransport(app=update_app),
            base_url="https://app.example.test",
        )
        self.clients.append(update_client)
        update_response = await update_client.get(
            "/api/v3/desktop/update/darwin/aarch64/1.2.9"
        )

        releases = await DesktopReleaseConfig.resolve(
            _settings(),
            release_manifest_service=resolver,
        )
        download_app = FastAPI()
        download_app.include_router(
            create_desktop_download_router(
                session_factory=_session_factory,
                settings_obj=_settings(),
                release_manifest_service=resolver,
            )
        )
        download_client = AsyncClient(
            transport=ASGITransport(app=download_app),
            base_url="https://app.example.test",
        )
        self.clients.append(download_client)
        status_response = await download_client.get(
            "/api/v3/desktop-download/public-status"
        )
        redirect_response = await download_client.get(
            "/downloads/macos",
            follow_redirects=False,
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["version"], "1.3.0")
        self.assertEqual(update_response.json()["notes"], "Real release")
        self.assertIn("/desktop/v1.3.0/", update_response.json()["url"])
        self.assertEqual(releases.macos_version, "1.3.0")
        self.assertIn("/desktop/v1.3.0/", releases.macos_url)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(redirect_response.status_code, 307)
        self.assertIn(
            "/desktop/v1.3.0/",
            redirect_response.headers["location"],
        )
        self.assertEqual(
            status_response.json()["versions"],
            {"macos": "1.3.0", "windows": "1.3.0"},
        )
        self.assertEqual(
            await resolve_desktop_latest_versions(_settings()),
            {"macos": "1.3.0", "windows": "1.3.0"},
        )
        self.assertEqual(fetcher.calls, 1)

    async def test_cache_last_known_good_network_failure_and_no_downgrade(self):
        clock = _Clock()
        fetcher = _SequenceFetcher(
            _manifest("2.0.0"),
            RuntimeError("network unavailable"),
            _manifest("1.9.9"),
        )
        resolver = DesktopReleaseManifestService(
            _settings(),
            fetcher=fetcher,
            clock=clock,
        )

        first = await resolver.resolve()
        cached = await resolver.resolve()
        clock.advance(61)
        after_network_failure = await resolver.resolve()
        clock.advance(61)
        after_downgrade = await resolver.resolve()

        self.assertEqual(first.version, "2.0.0")
        self.assertIs(first, cached)
        self.assertEqual(after_network_failure.version, "2.0.0")
        self.assertEqual(after_downgrade.version, "2.0.0")
        self.assertEqual(fetcher.calls, 3)

    async def test_initial_network_or_oversize_failure_is_fail_closed(self):
        for payload in (
            RuntimeError("offline"),
            b"x" * 65_537,
        ):
            with self.subTest(payload=type(payload).__name__):
                DesktopReleaseManifestService.clear_cache()
                resolver = DesktopReleaseManifestService(
                    _settings(),
                    fetcher=_SequenceFetcher(payload),
                )
                self.assertIsNone(await resolver.resolve())

    async def test_default_http_fetch_is_bounded_and_strict(self):
        async def valid_handler(_request):
            return Response(
                200,
                headers={"Content-Type": "application/json; charset=utf-8"},
                content=_manifest(),
            )

        valid = DesktopReleaseManifestService(
            _settings(),
            http_transport=MockTransport(valid_handler),
        )
        self.assertEqual((await valid.resolve()).version, "1.3.0")

        async def wrong_type_handler(_request):
            return Response(
                200,
                headers={"Content-Type": "text/plain"},
                content=_manifest(),
            )

        DesktopReleaseManifestService.clear_cache()
        wrong_type = DesktopReleaseManifestService(
            _settings(),
            http_transport=MockTransport(wrong_type_handler),
        )
        self.assertIsNone(await wrong_type.resolve())

        async def oversized_header_handler(_request):
            return Response(
                200,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": "70000",
                },
                content=b"{}",
            )

        DesktopReleaseManifestService.clear_cache()
        oversized_header = DesktopReleaseManifestService(
            _settings(),
            http_transport=MockTransport(oversized_header_handler),
        )
        self.assertIsNone(await oversized_header.resolve())

        async def redirect_handler(_request):
            return Response(302, headers={"Location": "https://other.test/latest.json"})

        DesktopReleaseManifestService.clear_cache()
        redirect = DesktopReleaseManifestService(
            _settings(),
            http_transport=MockTransport(redirect_handler),
        )
        self.assertIsNone(await redirect.resolve())

        async def slow_handler(_request):
            await asyncio.sleep(0.05)
            return Response(
                200,
                headers={"Content-Type": "application/json"},
                content=_manifest(),
            )

        DesktopReleaseManifestService.clear_cache()
        timed = DesktopReleaseManifestService(
            _settings(),
            http_transport=MockTransport(slow_handler),
        )
        timed.timeout_seconds = 0.005
        self.assertIsNone(await timed.resolve())

    async def test_configured_invalid_url_does_not_fall_back_to_legacy_values(self):
        settings_obj = _settings(
            DESKTOP_RELEASE_MANIFEST_URL="http://releases.test/latest.json"
        )
        resolver = DesktopReleaseManifestService(settings_obj)
        releases = await DesktopReleaseConfig.resolve(
            settings_obj,
            release_manifest_service=resolver,
        )

        app = FastAPI()
        app.include_router(
            create_desktop_update_router(
                settings_obj=settings_obj,
                release_manifest_service=resolver,
            )
        )
        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://app.example.test",
        )
        self.clients.append(client)
        update_response = await client.get(
            "/api/v3/desktop/update/windows/x86_64/1.0.0"
        )

        self.assertTrue(resolver.configured)
        self.assertIsNone(resolver.url)
        self.assertFalse(releases.enabled)
        self.assertIsNone(releases.macos_url)
        self.assertEqual(update_response.status_code, 204)

    def test_schema_parser_rejects_malformed_or_unsafe_documents(self):
        valid = json.loads(_manifest())
        invalid_documents = []

        extra = json.loads(_manifest())
        extra["unexpected"] = True
        invalid_documents.append(extra)

        prerelease = json.loads(_manifest())
        prerelease["version"] = "1.3.0-rc.1"
        invalid_documents.append(prerelease)

        insecure = json.loads(_manifest())
        insecure["macos"]["download_url"] = "http://cdn.test/app.dmg"
        invalid_documents.append(insecure)

        internal = json.loads(_manifest())
        internal["windows"]["download_url"] = "https://127.0.0.1/app.exe"
        invalid_documents.append(internal)

        single_label = json.loads(_manifest())
        single_label["windows"]["download_url"] = "https://releases/app.exe"
        invalid_documents.append(single_label)

        control_character = json.loads(_manifest())
        control_character["macos"]["download_url"] = (
            "https://cdn.example.test/path\n/app.dmg"
        )
        invalid_documents.append(control_character)

        query = json.loads(_manifest())
        query["windows"]["update_url"] += "?token=secret"
        invalid_documents.append(query)

        bad_signature = json.loads(_manifest())
        bad_signature["windows"]["signature"] = "short"
        invalid_documents.append(bad_signature)

        bad_hash = json.loads(_manifest())
        bad_hash["macos"]["download_sha256"] = "not-a-sha"
        invalid_documents.append(bad_hash)

        bad_date = json.loads(_manifest())
        bad_date["published_at"] = "yesterday"
        invalid_documents.append(bad_date)

        self.assertEqual(parse_desktop_release_manifest(_manifest()).version, "1.3.0")
        for document in invalid_documents:
            with self.subTest(keys=set(document)):
                with self.assertRaises(DesktopReleaseManifestError):
                    parse_desktop_release_manifest(json.dumps(document).encode())

        duplicate = _manifest().decode().replace(
            '"schema_version":1,',
            '"schema_version":1,"schema_version":1,',
            1,
        )
        with self.assertRaises(DesktopReleaseManifestError):
            parse_desktop_release_manifest(duplicate.encode())

        self.assertEqual(valid["schema_version"], 1)


class DesktopReleaseManifestSettingsTests(unittest.TestCase):
    def test_settings_defaults_are_bounded_and_opt_in(self):
        from app.config import Settings

        settings = Settings(_env_file=None)

        self.assertEqual(settings.DESKTOP_RELEASE_MANIFEST_URL, "")
        self.assertEqual(settings.DESKTOP_RELEASE_MANIFEST_CACHE_TTL_SECONDS, 60)
        self.assertEqual(settings.DESKTOP_RELEASE_MANIFEST_TIMEOUT_SECONDS, 5.0)
        self.assertEqual(settings.DESKTOP_RELEASE_MANIFEST_MAX_BYTES, 65536)

    def test_non_finite_or_out_of_range_limits_use_safe_defaults(self):
        resolver = DesktopReleaseManifestService(
            _settings(
                DESKTOP_RELEASE_MANIFEST_CACHE_TTL_SECONDS=float("nan"),
                DESKTOP_RELEASE_MANIFEST_TIMEOUT_SECONDS=float("nan"),
                DESKTOP_RELEASE_MANIFEST_MAX_BYTES=float("inf"),
            )
        )

        self.assertEqual(resolver.cache_ttl_seconds, 60)
        self.assertEqual(resolver.timeout_seconds, 5.0)
        self.assertEqual(resolver.max_bytes, 65536)
