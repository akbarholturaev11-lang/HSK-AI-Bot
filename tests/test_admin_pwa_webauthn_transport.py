"""Same-origin HTTP boundaries for passkey registration (mock verifier).

No new admin-session cookie or legacy Telegram admin-path bypass.
"""
import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_webauthn_transport import create_admin_pwa_webauthn_router

ORIGIN = "https://hskai.app"
PROOF = "A" * 64
GRANT = "B" * 64
EXPIRES = datetime(2026, 10, 24, 17, tzinfo=timezone.utc)


@asynccontextmanager
async def _db():
    yield object()


class WebAuthnTransportTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN)
        self.called = []

        async def begin(db, *, token, browser_proof, settings_obj):
            self.called.append(("begin", token, browser_proof))
            if token != GRANT or browser_proof != PROOF:
                return None
            return SimpleNamespace(options={
                "rp": {"id": "hskai.app"},
                "challenge": "publicChallenge", "user": {"id": "opaque"},
            }, expires_at=EXPIRES)

        async def finish(db, *, token, browser_proof, credential, settings_obj):
            self.called.append(("finish", token, browser_proof))
            return token == GRANT and browser_proof == PROOF and credential.get("type") == "public-key"

        app = FastAPI()
        app.include_router(create_admin_pwa_webauthn_router(
            settings_obj=self.settings, session_factory=_db,
            begin_service=begin, complete_service=finish,
        ))
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def post(self, action, *, content=None, headers=None, cookie=True):
        h = {"origin": ORIGIN, "content-type": "application/json",
             "sec-fetch-site": "same-origin"}
        if cookie:
            h["cookie"] = "__Host-hskai_admin_enroll=" + GRANT + "; __Host-hskai_admin_approval=" + PROOF
        if headers:
            h.update(headers)
        return self.client.post(
            "/api/admin/v1/auth/passkey/register/" + action,
            headers=h, content=content if content is not None else (
                b"{}" if action == "options" else json.dumps(
                    {"credential": {"id": "x", "type": "public-key"}},
                ).encode()
            ),
        )

    def test_begin_returns_public_challenge_never_proof(self):
        response = self.post("options")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["publicKey"]["rp"]["id"], "hskai.app")
        self.assertNotIn(PROOF, response.text)
        self.assertNotIn(GRANT, response.text)
        self.assertFalse(response.headers.get_list("set-cookie"))
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(len(self.called), 1)

    def test_complete_clears_only_grant_and_proof_cookie_not_admin_session(self):
        response = self.post("verify")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "passkey_registered")
        cookies = response.headers.get_list("set-cookie")
        self.assertEqual(len(cookies), 2)
        self.assertTrue(any(x.startswith("__Host-hskai_admin_enroll=") for x in cookies))
        self.assertTrue(any(x.startswith("__Host-hskai_admin_approval=") for x in cookies))
        self.assertFalse(any(x.startswith("__Host-hskai_admin=") for x in cookies))
        self.assertNotIn("user_id", response.text)
        self.assertEqual(self.called[0][0], "finish")

    def test_csrf_and_feature_flag_stop_calls(self):
        for headers in ({"origin": "https://evil.example"},
                        {"origin": ""}, {"sec-fetch-site": "cross-site"},
                        {"content-type": "text/plain"}):
            with self.subTest(headers=headers):
                self.assertIn(self.post("options", headers=headers).status_code, (403, 415))
        self.assertEqual(self.called, [])
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertEqual(self.post("options").status_code, 404)
        self.assertEqual(self.post("verify").status_code, 404)
        self.assertEqual(self.called, [])

    def test_missing_one_cookie_rejects(self):
        self.assertEqual(self.post("options", cookie=False).status_code, 401)
        self.assertEqual(self.post("verify", cookie=False).status_code, 401)
        self.assertEqual(self.called, [])

    def test_duplicate_and_malformed_json_rejected(self):
        for content in (
            b'{"credential":{},"credential":{}}',
            b'{"credential":{"type":"public-key"},"user_id":999}',
            b"x" * 16385,
            b"null", b"[]",
        ):
            with self.subTest(content=content[:50]):
                self.assertEqual(self.post("verify", content=content).status_code, 400)
        self.assertEqual(self.post("options", content=b'{"extra":1}').status_code, 400)
        self.assertEqual(self.called, [])

    def test_error_does_not_issue_cookie(self):
        response = self.post(
            "verify", content=b'{"credential":{"type":"not-a-public-key"}}',
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.headers.get_list("set-cookie"))

    def test_wrong_host_rejects_before_service(self):
        with TestClient(self.client.app, base_url="https://evil.example") as other:
            response = other.post(
                "/api/admin/v1/auth/passkey/register/options",
                headers={"origin": ORIGIN, "content-type": "application/json",
                         "cookie": "__Host-hskai_admin_enroll=" + GRANT + "; __Host-hskai_admin_approval=" + PROOF},
                json={},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.called, [])


if __name__ == "__main__":
    unittest.main()
