"""HTTP contract for the browser-only Telegram approval -> passkey-grant hop.

Mock completion service only; no real Google/Telegram/WebAuthn/auth session.
"""
import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_enrollment import GrantedPwaEnrollment
from app.admin_api.pwa_enrollment_grants import IssuedPwaEnrollmentGrant
from app.admin_api.pwa_approval import ApprovedPwaEnrollment
from app.admin_api.pwa_enrollment_transport import create_admin_pwa_completion_router

ORIGIN = "https://hskai.app"
PROOF = "A" * 64
ENROLL_TOKEN = "B" * 64
REQUEST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@asynccontextmanager
async def _db_factory():
    yield object()


class AdminPwaGrantHttpTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN,
        )
        self.calls = []

        async def complete(db, *, request_id, browser_proof,
                           settings_obj, issue_passkey_grant):
            self.calls.append((request_id, browser_proof, issue_passkey_grant))
            if request_id != REQUEST_ID or browser_proof != PROOF:
                return None
            return GrantedPwaEnrollment(
                linked=ApprovedPwaEnrollment(
                    user_id=1001, telegram_id=9001,
                    google_subject_hash="c" * 64,
                    google_audience="test-web-client",
                ),
                grant=IssuedPwaEnrollmentGrant(
                    token=ENROLL_TOKEN,
                    expires_at=datetime(2026, 10, 24, 17, 3, tzinfo=timezone.utc),
                ),
            )

        app = FastAPI()
        app.include_router(create_admin_pwa_completion_router(
            settings_obj=self.settings, session_factory=_db_factory,
            completion_service=complete,
        ))
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def post(self, payload=None, *, headers=None, raw=None, cookie=True):
        data = {"origin": ORIGIN, "content-type": "application/json",
                "sec-fetch-site": "same-origin"}
        if cookie:
            data["cookie"] = "__Host-hskai_admin_approval=" + PROOF
        if headers:
            data.update(headers)
        return self.client.post(
            "/api/admin/v1/auth/telegram/complete",
            headers=data, content=raw if raw is not None else json.dumps(
                {"request_id": REQUEST_ID} if payload is None else payload,
            ),
        )

    def test_verified_completion_sets_only_short_lived_two_cookie_grant(self):
        r = self.post()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["next"], "passkey_enrollment")
        self.assertNotIn(ENROLL_TOKEN, r.text)
        self.assertNotIn("user_id", r.text)
        self.assertNotIn("telegram_id", r.text)
        self.assertEqual(self.calls, [(REQUEST_ID, PROOF, True)])
        cookies = r.headers.get_list("set-cookie")
        self.assertEqual(len(cookies), 2)
        grant = next(v for v in cookies if v.startswith("__Host-hskai_admin_enroll="))
        proof = next(v for v in cookies if v.startswith("__Host-hskai_admin_approval="))
        self.assertIn("__Host-hskai_admin_enroll=" + ENROLL_TOKEN, grant)
        self.assertIn("__Host-hskai_admin_approval=" + PROOF, proof)
        for value in (grant, proof):
            self.assertIn("httponly", value.lower())
            self.assertIn("secure", value.lower())
            self.assertIn("samesite=lax", value.lower())
            self.assertIn("path=/", value.lower())
            self.assertIn("max-age=180", value.lower())
            self.assertNotIn("domain=", value.lower())
            self.assertNotIn("__Host-hskai_admin=", value)
        self.assertEqual(r.headers["cache-control"], "no-store")

    def test_feature_off_returns_404_with_no_cookie_or_calls(self):
        self.settings.ADMIN_PWA_ENABLED = False
        r = self.post()
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers.get_list("set-cookie"), [])
        self.assertEqual(self.calls, [])

    def test_missing_or_cross_origin_fails_before_service(self):
        for headers in (
            {"origin": "https://evil.example"},
            {"origin": ""},
            {"sec-fetch-site": "cross-site"},
            {"sec-fetch-site": "none"},
        ):
            with self.subTest(headers=headers):
                self.assertEqual(self.post(headers=headers).status_code, 403)
        self.assertEqual(self.calls, [])

    def test_wrong_content_type_and_missing_proof(self):
        self.assertEqual(self.post(headers={"content-type": "text/plain"}).status_code, 415)
        self.assertEqual(self.post(cookie=False).status_code, 401)
        self.assertEqual(self.calls, [])

    def test_malformed_extra_duplicate_or_oversized_body(self):
        cases = (
            b"not-json",
            b'{"request_id":1}',
            b'{"request_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","user_id":123}',
            b'{"request_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","request_id":"x"}',
            b"x" * 257,
        )
        for data in cases:
            with self.subTest(body=data[:60]):
                response = self.post(raw=data)
                self.assertIn(response.status_code, (400, 413))
                self.assertEqual(response.headers.get_list("set-cookie"), [])
        self.assertEqual(self.calls, [])

    def test_denied_or_wrong_request_never_mints_grant(self):
        r = self.post({"request_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.headers.get_list("set-cookie"), [])

    def test_mismatched_http_host_is_rejected(self):
        with TestClient(self.client.app, base_url="https://untrusted.example") as other:
            response = other.post(
                "/api/admin/v1/auth/telegram/complete",
                headers={"origin": ORIGIN, "content-type": "application/json",
                         "cookie": "__Host-hskai_admin_approval=" + PROOF},
                json={"request_id": REQUEST_ID},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
