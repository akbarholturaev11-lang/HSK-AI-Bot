"""Tests for the isolated, intentionally disabled Admin PWA route scaffold."""

import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_bootstrap import (
    _valid_pwa_origin,
    create_admin_pwa_bootstrap_router,
)


class AdminPwaBootstrapTests(unittest.IsolatedAsyncioTestCase):
    async def fetch(self, settings, url, headers=None):
        app = FastAPI()
        app.include_router(create_admin_pwa_bootstrap_router(settings_obj=settings))
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://hskai.app"
        ) as client:
            return await client.get(url, headers=headers or {})

    async def test_feature_flag_off_never_exposes_admin(self):
        settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=False, ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app"
        )
        for path in ("/admin", "/api/admin/v1/me"):
            with self.subTest(path=path):
                response = await self.fetch(settings, path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(response.headers["x-frame-options"], "DENY")
                self.assertNotIn("user_id", response.text)

    async def test_enabled_without_https_origin_fails_closed(self):
        for origin in ("", "http://hskai.app", "https://hskai.app/admin", "https://alice@hskai.app", "https://hskai.app:443"):
            with self.subTest(origin=origin):
                settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=origin)
                response = await self.fetch(settings, "/api/admin/v1/me")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error"], "admin_pwa_origin_unconfigured")

    async def test_enabled_cannot_authenticate_without_real_verifier(self):
        settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app")
        for headers in ({}, {"X-Telegram-Init-Data": "fake", "X-Admin-Id": "777"}, {"Cookie": "admin_pwa_session=forged"}):
            with self.subTest(headers=headers):
                response = await self.fetch(settings, "/api/admin/v1/me", headers=headers)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error"], "admin_pwa_auth_not_ready")
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertNotIn("set-cookie", response.headers)

    def test_origin_parser(self):
        self.assertTrue(_valid_pwa_origin("https://hskai.app"))
        self.assertTrue(_valid_pwa_origin("https://staging.hskai.app"))
        for origin in ("", "https://", "https://hskai.app/a", "http://hskai.app", "https://hskai.app?x=1", "https://hskai.app#x", "https://hskai.app:443"):
            with self.subTest(origin=origin):
                self.assertFalse(_valid_pwa_origin(origin))
