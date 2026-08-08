import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.desktop_update import create_desktop_update_router
from app.config import Settings
from app.services.desktop_update_service import parse_desktop_semver


def _settings(**overrides):
    values = {
        "DESKTOP_UPDATES_ENABLED": True,
        "DESKTOP_MAC_VERSION": "1.2.0",
        "DESKTOP_MAC_UPDATER_URL": (
            "https://cdn.example.com/pomp-hsk-ai_1.2.0.app.tar.gz"
        ),
        "DESKTOP_MAC_UPDATER_SIGNATURE": "A" * 96,
        "DESKTOP_MAC_UPDATER_NOTES": "Offline kurs tayyorlandi.",
        "DESKTOP_WINDOWS_VERSION": "2.0.0",
        "DESKTOP_WINDOWS_UPDATER_URL": (
            "https://cdn.example.com/pomp-hsk-ai_2.0.0-setup.exe"
        ),
        "DESKTOP_WINDOWS_UPDATER_SIGNATURE": "B" * 96,
        "DESKTOP_WINDOWS_UPDATER_NOTES": "Windows yangilanishi.",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class DesktopUpdateApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clients = []

    async def asyncTearDown(self):
        for client in self.clients:
            await client.aclose()

    async def make_client(self, settings_obj):
        app = FastAPI()
        app.include_router(
            create_desktop_update_router(settings_obj=settings_obj)
        )
        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://updates.test",
        )
        self.clients.append(client)
        return client

    async def test_public_manifest_returns_newer_signed_release(self):
        client = await self.make_client(_settings())

        mac = await client.get(
            "/api/v3/desktop/update/darwin/aarch64/1.1.9"
        )
        windows = await client.get(
            "/api/v3/desktop/update/windows/x86_64/1.9.0"
        )

        self.assertEqual(mac.status_code, 200)
        self.assertEqual(
            mac.json(),
            {
                "version": "1.2.0",
                "url": (
                    "https://cdn.example.com/"
                    "pomp-hsk-ai_1.2.0.app.tar.gz"
                ),
                "signature": "A" * 96,
                "notes": "Offline kurs tayyorlandi.",
            },
        )
        self.assertEqual(windows.status_code, 200)
        self.assertEqual(windows.json()["version"], "2.0.0")
        self.assertTrue(windows.json()["url"].endswith(".exe"))
        self.assertNotIn("authorization", mac.request.headers)
        self.assertEqual(mac.headers["cache-control"], "no-store")

    async def test_disabled_unconfigured_or_current_release_returns_204(self):
        cases = [
            (
                _settings(DESKTOP_UPDATES_ENABLED=False),
                "darwin/aarch64/1.0.0",
            ),
            (
                _settings(DESKTOP_MAC_UPDATER_SIGNATURE=""),
                "darwin/aarch64/1.0.0",
            ),
            (
                _settings(
                    DESKTOP_MAC_UPDATER_URL=(
                        "http://cdn.example.com/app.app.tar.gz"
                    )
                ),
                "darwin/aarch64/1.0.0",
            ),
            (
                _settings(
                    DESKTOP_MAC_UPDATER_URL=(
                        "https://cdn.example.com/"
                        "app.app.tar.gz?token=secret"
                    )
                ),
                "darwin/aarch64/1.0.0",
            ),
            (
                _settings(
                    DESKTOP_MAC_UPDATER_URL=(
                        "https://cdn.example.com/app.dmg"
                    )
                ),
                "darwin/aarch64/1.0.0",
            ),
            (
                _settings(DESKTOP_MAC_VERSION="v1.2.0"),
                "darwin/aarch64/1.0.0",
            ),
            (_settings(), "darwin/x86_64/1.2.0"),
            (_settings(), "darwin/x86_64/1.3.0"),
            (_settings(), "windows/x86_64/2.0.0+build.9"),
        ]

        for settings_obj, path in cases:
            with self.subTest(path=path):
                client = await self.make_client(settings_obj)
                response = await client.get(
                    f"/api/v3/desktop/update/{path}"
                )

                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.content, b"")
                self.assertEqual(
                    response.headers["cache-control"],
                    "no-store",
                )

    async def test_path_allowlists_and_version_errors_are_stable(self):
        cases = [
            (
                "linux/x86_64/1.0.0",
                404,
                "desktop_update_target_unsupported",
            ),
            (
                "darwin/i686/1.0.0",
                404,
                "desktop_update_arch_unsupported",
            ),
            (
                "windows/armv7/1.0.0",
                404,
                "desktop_update_arch_unsupported",
            ),
            (
                "windows/aarch64/1.0.0",
                404,
                "desktop_update_arch_unsupported",
            ),
            (
                "windows/i686/1.0.0",
                404,
                "desktop_update_arch_unsupported",
            ),
            (
                "windows/x86_64/01.0.0",
                422,
                "desktop_update_version_invalid",
            ),
            (
                "darwin/aarch64/1.0",
                422,
                "desktop_update_version_invalid",
            ),
            (
                "darwin/aarch64/v1.0.0",
                422,
                "desktop_update_version_invalid",
            ),
        ]

        for path, status_code, error in cases:
            with self.subTest(path=path):
                client = await self.make_client(_settings())
                response = await client.get(
                    f"/api/v3/desktop/update/{path}"
                )

                self.assertEqual(response.status_code, status_code)
                self.assertEqual(
                    response.json(),
                    {"ok": False, "error": error},
                )
                self.assertEqual(
                    response.headers["cache-control"],
                    "no-store",
                )

    def test_semver_precedence_is_strict_and_build_metadata_is_ignored(self):
        ordered = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        ]
        parsed = [parse_desktop_semver(version) for version in ordered]

        self.assertEqual(parsed, sorted(parsed))
        self.assertEqual(
            parse_desktop_semver("1.0.0+build.1"),
            parse_desktop_semver("1.0.0+build.99"),
        )
        invalid_versions = (
            "1",
            "1.0",
            "01.0.0",
            "1.0.0-alpha.01",
            "1.0.0+",
        )
        for invalid in invalid_versions:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    parse_desktop_semver(invalid)

    def test_settings_default_keeps_updates_disabled(self):
        settings = Settings(_env_file=None)

        self.assertFalse(settings.DESKTOP_UPDATES_ENABLED)
        self.assertEqual(settings.DESKTOP_MAC_UPDATER_URL, "")
        self.assertEqual(settings.DESKTOP_WINDOWS_UPDATER_SIGNATURE, "")
