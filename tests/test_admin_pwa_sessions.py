"""Isolated Admin PWA cookie verification; does not create privileged sessions."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router
from app.admin_api.pwa_sessions import (
    ADMIN_PWA_COOKIE_NAME,
    authenticate_admin_pwa_session,
)

TOKEN = "A" * 72
NOW = datetime(2026, 10, 23, 15, tzinfo=timezone.utc)


class _Db:
    def __init__(self, row, user):
        self.row, self.user = row, user

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def execute(self, query):
        return SimpleNamespace(scalar_one_or_none=lambda: self.row)

    async def get(self, cls, pk):
        return self.user if self.user and self.user.id == pk else None


class _Sessions:
    def __init__(self, row, user):
        self.row, self.user = row, user

    def __call__(self):
        return _Db(self.row, self.user)


def settings(enabled=True, origin="https://hskai.app"):
    return SimpleNamespace(ADMIN_PWA_ENABLED=enabled, ADMIN_PWA_PUBLIC_ORIGIN=origin, admin_id_list=[9001])


def row(*, token=TOKEN, revoked=False, expires_at=None, auth_method="webauthn"):
    return SimpleNamespace(
        user_id=14,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        revoked_at=NOW if revoked else None,
        expires_at=expires_at or (NOW + timedelta(hours=1)),
        auth_method=auth_method,
    )


def user(telegram_id=9001, status="active"):
    return SimpleNamespace(id=14, telegram_id=telegram_id, status=status)


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_good_session_resolves_only_allowlisted_admin(self):
        actor = await authenticate_admin_pwa_session(_Db(row(), user()), TOKEN, settings(), now=NOW)
        self.assertEqual((actor.user_id, actor.telegram_id, actor.auth_method), (14, 9001, "webauthn"))

    async def test_no_cookie_or_invalid_token_denied(self):
        for token in ("", "short", "x" * 300, "bad!" * 16, "B" * 72):
            with self.subTest(token=token[:8]):
                self.assertIsNone(await authenticate_admin_pwa_session(_Db(row(), user()), token, settings(), now=NOW))

    async def test_revoked_expired_or_unknown_method_denied(self):
        for invalid in (row(revoked=True), row(expires_at=NOW), row(auth_method="injected")):
            self.assertIsNone(await authenticate_admin_pwa_session(_Db(invalid, user()), TOKEN, settings(), now=NOW))

    async def test_non_admin_and_blocked_denied(self):
        for actor in (user(telegram_id=777), user(telegram_id=None), user(status="blocked"), user(status="BLOCKED"),
                      user(status=" Blocked "), None):
            self.assertIsNone(await authenticate_admin_pwa_session(_Db(row(), actor), TOKEN, settings(), now=NOW))

    async def test_missing_row_denied(self):
        self.assertIsNone(await authenticate_admin_pwa_session(_Db(None, user()), TOKEN, settings(), now=NOW))

    async def test_realistic_route_ignores_forged_identity_headers(self):
        app = FastAPI()
        app.include_router(create_admin_pwa_bootstrap_router(settings_obj=settings(), session_factory=_Sessions(None, None)))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app") as client:
            res = await client.get("/api/admin/v1/me", headers={"X-Telegram-Init-Data": "forged", "X-Admin-Id": "9001"})
            self.assertEqual(401, res.status_code)
            self.assertEqual("no-store", res.headers["cache-control"])
            self.assertNotIn("set-cookie", res.headers)

    async def test_verified_database_cookie_returns_minimal_identity(self):
        app = FastAPI()
        live_row = row(expires_at=datetime.now(timezone.utc) + timedelta(minutes=20))
        app.include_router(create_admin_pwa_bootstrap_router(
            settings_obj=settings(), session_factory=_Sessions(live_row, user())
        ))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app", cookies={ADMIN_PWA_COOKIE_NAME: TOKEN}) as client:
            result = await client.get("/api/admin/v1/me")
            self.assertEqual(200, result.status_code)
            self.assertEqual({"ok": True, "user_id": 14, "auth_method": "webauthn"}, result.json())
            self.assertEqual("no-store", result.headers["cache-control"])
            self.assertNotIn("set-cookie", result.headers)

    async def test_noncanonical_origins_are_rejected_even_if_enabled(self):
        app = FastAPI()
        app.include_router(create_admin_pwa_bootstrap_router(settings_obj=settings(), session_factory=_Sessions(row(), user())))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://railway.example", cookies={ADMIN_PWA_COOKIE_NAME: TOKEN}) as client:
            result = await client.get("/api/admin/v1/me")
            self.assertEqual(403, result.status_code)

    async def test_with_no_backend_even_enabled_is_not_a_login(self):
        app = FastAPI()
        app.include_router(create_admin_pwa_bootstrap_router(settings_obj=settings()))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app") as client:
            r = await client.get("/api/admin/v1/me")
            self.assertEqual(503, r.status_code)
            self.assertEqual("admin_pwa_auth_not_ready", r.json()["error"])
