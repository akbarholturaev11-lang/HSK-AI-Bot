"""HTTP regression contract for Admin PWA Google OAuth (no real provider/DB)."""

import unittest
from unittest.mock import patch
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_google_transport import (
    _OIDC_COOKIE, _APPROVAL_COOKIE, create_admin_pwa_google_router,
)
from app.admin_api.pwa_oidc import AdminPwaOidcError

ORIGIN = "https://hskai.app"
PROOF = "A" * 64
APPROVAL_PROOF = "B" * 64


@asynccontextmanager
async def _db_factory():
    yield object()


class AdminPwaGoogleTransportTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN,
        )
        self.started = []
        self.finished = []

        async def start_service(db, *, settings_obj):
            self.started.append(True)
            return SimpleNamespace(
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth?state=test",
                browser_proof=PROOF,
            )

        async def finish_service(db, *, settings_obj, state, code, browser_proof):
            self.finished.append((state, code, browser_proof))
            if state != "good" or code != "good-code":
                return None
            return SimpleNamespace(
                request_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                browser_proof=APPROVAL_PROOF,
            )

        self.app = FastAPI()
        self.app.include_router(create_admin_pwa_google_router(
            settings_obj=self.settings, session_factory=_db_factory,
            start_service=start_service, finish_service=finish_service,
        ))
        self.client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def start(self, headers=None):
        data = {
            "origin": ORIGIN,
            "content-type": "application/json",
            "sec-fetch-site": "same-origin",
        }
        if headers:
            data.update(headers)
        return self.client.post(
            "/api/admin/v1/auth/google/start", headers=data, json={},
        )

    def callback(self, query="?state=good&code=good-code", headers=None):
        return self.client.get(
            "/api/admin/v1/auth/google/callback" + query, headers=headers,
        )

    def test_disabled_flag_hides_both_routes(self):
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertEqual(self.start().status_code, 404)
        self.assertEqual(self.callback().status_code, 404)
        self.assertEqual(self.started, [])
        self.assertEqual(self.finished, [])

    def test_canonical_https_host_and_scheme_enforced(self):
        with TestClient(self.app, base_url="http://hskai.app") as http:
            self.assertEqual(http.post(
                "/api/admin/v1/auth/google/start",
                headers={"origin": ORIGIN, "content-type": "application/json"},
                json={},
            ).status_code, 403)
            self.assertEqual(http.get(
                "/api/admin/v1/auth/google/callback?state=good&code=good-code",
                headers={"x-forwarded-proto": "https"},
            ).status_code, 403)
        with TestClient(self.app, base_url="https://untrusted.example") as other:
            self.assertEqual(other.post(
                "/api/admin/v1/auth/google/start",
                headers={"origin": ORIGIN, "content-type": "application/json"},
                json={},
            ).status_code, 403)

    def test_csrf_origin_fetch_metadata_and_media_type(self):
        cases = (
            {"origin": "https://attacker.example"},
            {"origin": ""},
            {"sec-fetch-site": "cross-site"},
            {"sec-fetch-site": "none"},
            {"content-type": "text/plain"},
        )
        for headers in cases:
            with self.subTest(headers=headers):
                self.assertIn(self.start(headers).status_code, (403, 415))
        # A real browser fetch must have Origin; don't silently accept its absence.
        self.assertEqual(self.client.post(
            "/api/admin/v1/auth/google/start",
            headers={"content-type": "application/json"}, json={},
        ).status_code, 403)
        self.assertEqual(self.started, [])

    def test_invalid_origin_configuration_fails_closed(self):
        self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://[broken"
        self.assertEqual(self.start().status_code, 503)

    def test_proof_only_in_secure_httponly_host_only_cookie(self):
        response = self.start()
        self.assertEqual(response.status_code, 200)
        self.assertIn("accounts.google.com", response.json()["authorize_url"])
        self.assertNotIn(PROOF, response.text)
        headers = response.headers.get_list("set-cookie")
        self.assertTrue(any(
            line.startswith(_OIDC_COOKIE + "=")
            and "httponly" in line.lower()
            and "secure" in line.lower()
            and "samesite=lax" in line.lower()
            and "path=/" in line.lower()
            and "domain=" not in line.lower()
            for line in headers
        ))
        self.assertEqual(self.client.cookies.get(_OIDC_COOKIE), PROOF)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual(len(self.started), 1)

    def test_callback_only_creates_pending_telegram_proof(self):
        self.start()
        response = self.callback(headers={
            "sec-fetch-mode": "navigate", "sec-fetch-dest": "document",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "telegram_approval_pending")
        self.assertEqual(self.finished, [("good", "good-code", PROOF)])
        self.assertNotIn(APPROVAL_PROOF, response.text)
        self.assertNotIn(_OIDC_COOKIE, self.client.cookies)
        self.assertEqual(self.client.cookies.get(_APPROVAL_COOKIE), APPROVAL_PROOF)
        self.assertNotIn("__Host-hskai_admin", self.client.cookies)
        self.assertTrue(any(
            line.startswith(_APPROVAL_COOKIE + "=")
            and "httponly" in line.lower()
            and "secure" in line.lower()
            and "domain=" not in line.lower()
            for line in response.headers.get_list("set-cookie")
        ))

    def test_callback_missing_cookie_fails(self):
        self.assertEqual(self.callback().status_code, 400)
        self.assertEqual(self.finished, [])

    def test_callback_rejects_provider_error_or_duplicate_parameters(self):
        self.start()
        for query in (
            "?state=good&code=good-code&error=access_denied",
            "?state=good&state=good&code=good-code",
            "?state=good&code=a&code=b",
        ):
            with self.subTest(query=query):
                self.assertEqual(self.callback(query).status_code, 400)
                self.assertEqual(self.finished, [])
                self.start()  # malformed callback clears old proof

    def test_callback_rejects_subresource_navigation(self):
        self.start()
        self.assertEqual(self.callback(headers={
            "sec-fetch-mode": "cors",
        }).status_code, 403)
        self.assertEqual(self.finished, [])

    def test_failed_callback_clears_browser_proof(self):
        self.start()
        self.assertEqual(
            self.callback("?state=bad&code=good-code").status_code, 400,
        )
        self.assertIsNone(self.client.cookies.get(_OIDC_COOKIE))
        self.assertIsNone(self.client.cookies.get(_APPROVAL_COOKIE))

    def test_status_requires_proof_cookie_and_blocks_cross_site(self):
        request_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        path = "/api/admin/v1/auth/telegram/status?request_id=" + request_id
        self.assertEqual(self.client.get(path).status_code, 401)
        self.start()
        self.callback()
        self.assertEqual(self.client.get(path, headers={
            "sec-fetch-site": "cross-site",
        }).status_code, 403)
        self.assertEqual(self.client.get(path + "&request_id=" + request_id).status_code, 400)

    def test_status_returns_only_scoped_state_and_pairing_code(self):
        request_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        self.start()
        self.callback()
        async def read_status(db, *, request_id, browser_proof, settings_obj):
            self.assertEqual(browser_proof, APPROVAL_PROOF)
            return SimpleNamespace(
                status="pending", pairing_code="A1B2C3D4",
                expires_at=__import__("datetime").datetime(
                    2026, 10, 24, 0, 5, tzinfo=__import__("datetime").timezone.utc,
                ),
            )
        with patch("app.admin_api.pwa_google_transport.read_browser_pwa_approval",
                   new=read_status):
            response = self.client.get(
                "/api/admin/v1/auth/telegram/status?request_id=" + request_id,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(response.json()["pairing_code"], "A1B2C3D4")
        self.assertNotIn(APPROVAL_PROOF, response.text)
        self.assertNotIn(PROOF, response.text)
        self.assertNotIn("google_subject_hash", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_status_wrong_browser_proof_is_not_available(self):
        self.start()
        self.callback()
        async def no_status(**kwargs):
            return None
        async def no_status_db(db, **kwargs):
            return None
        with patch("app.admin_api.pwa_google_transport.read_browser_pwa_approval",
                   new=no_status_db):
            response = self.client.get(
                "/api/admin/v1/auth/telegram/status?request_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
        self.assertEqual(response.status_code, 404)

    def test_service_rate_limit_returns_429_no_cookies(self):
        async def rate_limited(db, *, settings_obj):
            raise AdminPwaOidcError("rate_limited")

        app = FastAPI()
        app.include_router(create_admin_pwa_google_router(
            settings_obj=self.settings, session_factory=_db_factory,
            start_service=rate_limited,
        ))
        with TestClient(app, base_url=ORIGIN) as client:
            response = client.post(
                "/api/admin/v1/auth/google/start",
                headers={"origin": ORIGIN, "content-type": "application/json"},
                json={},
            )
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.headers.get_list("set-cookie"))


if __name__ == "__main__":
    unittest.main()
