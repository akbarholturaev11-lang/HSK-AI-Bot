"""Passkey login/logout HTTP boundary. WebAuthn verifier is mocked in routes."""
import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_webauthn_login_transport import create_admin_pwa_passkey_login_router

ORIGIN = "https://hskai.app"
ASSERT_PROOF = "P" * 64
SESSION = "S" * 64
EXPIRES = datetime(2026, 10, 24, 20, tzinfo=timezone.utc)


@asynccontextmanager
async def _db():
    yield object()


class PasskeyLoginTransportTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN)
        self.calls = []

        async def start(db, *, settings_obj):
            self.calls.append("start")
            return SimpleNamespace(
                options={"rpId": "hskai.app", "challenge": "public"},
                browser_proof=ASSERT_PROOF, expires_at=EXPIRES,
            )

        async def finish(db, *, browser_proof, credential, settings_obj):
            self.calls.append("finish")
            if browser_proof != ASSERT_PROOF or credential.get("id") != "signed":
                return None
            return SimpleNamespace(token=SESSION, expires_at=EXPIRES)

        async def revoke(db, token):
            self.calls.append(("logout", token))
            return True

        app = FastAPI()
        app.include_router(create_admin_pwa_passkey_login_router(
            settings_obj=self.settings, session_factory=_db,
            begin_service=start, finish_service=finish, revoke_service=revoke,
        ))
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def post(self, endpoint, *, value=None, headers=None, cookies=None, raw=None):
        hs = {"origin": ORIGIN, "content-type": "application/json",
              "sec-fetch-site": "same-origin"}
        if cookies is not None:
            hs["cookie"] = cookies
        if headers:
            hs.update(headers)
        if raw is None:
            raw = json.dumps({} if value is None else value).encode()
        return self.client.post("/api/admin/v1/auth/" + endpoint,
                                headers=hs, content=raw)

    def test_public_start_only_sets_httponly_assertion_cookie(self):
        r = self.post("passkey/login/options")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["publicKey"]["rpId"], "hskai.app")
        self.assertNotIn(ASSERT_PROOF, r.text)
        self.assertNotIn("user_id", r.text)
        cookies = r.headers.get_list("set-cookie")
        self.assertEqual(len(cookies), 1)
        c = cookies[0]
        self.assertTrue(c.startswith("__Host-hskai_admin_assert=" + ASSERT_PROOF))
        for val in ("secure", "httponly", "samesite=lax", "path=/", "max-age=120"):
            self.assertIn(val, c.lower())
        self.assertNotIn("domain=", c.lower())
        self.assertEqual(r.headers["cache-control"], "no-store")

    def test_only_verified_assertion_sets_admin_session(self):
        self.post("passkey/login/options")
        r = self.post("passkey/login/verify", value={"credential": {"id": "signed"}},
                      cookies="__Host-hskai_admin_assert=" + ASSERT_PROOF)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "authenticated")
        self.assertNotIn(SESSION, r.text)
        cookies = r.headers.get_list("set-cookie")
        self.assertEqual(len(cookies), 2)
        self.assertTrue(any(x.startswith("__Host-hskai_admin_assert=") for x in cookies))
        real = next(x for x in cookies if x.startswith("__Host-hskai_admin="))
        self.assertIn("httponly", real.lower())
        self.assertIn("secure", real.lower())
        self.assertIn("max-age=28800", real.lower())
        self.assertEqual(self.calls, ["start", "finish"])

    def test_no_assertion_cookie_or_rejected_assertion_is_no_login(self):
        self.assertEqual(self.post("passkey/login/verify",
                         value={"credential": {"id": "signed"}}).status_code, 401)
        r = self.post("passkey/login/verify",
                      value={"credential": {"id": "attacker"}},
                      cookies="__Host-hskai_admin_assert=" + ASSERT_PROOF)
        self.assertEqual(r.status_code, 401)
        self.assertFalse(any(x.startswith("__Host-hskai_admin=")
                             for x in r.headers.get_list("set-cookie")))

    def test_csrf_wrong_origin_and_feature_disabled(self):
        for hs in ({"origin": "https://evil.example"},
                   {"origin": ""},
                   {"sec-fetch-site": "cross-site"},
                   {"content-type": "text/plain"}):
            with self.subTest(headers=hs):
                self.assertIn(self.post("passkey/login/options", headers=hs).status_code,
                              (403, 415))
        self.assertEqual(self.calls, [])
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertEqual(self.post("passkey/login/options").status_code, 404)
        self.assertEqual(self.post("logout").status_code, 404)

    def test_malformed_json_fails_closed(self):
        for raw in (
            b"null", b"not-json",
            b'{"credential":{},"credential":{}}',
            b'{"credential":{},"user_id":9001}',
            b"x" * 16385,
        ):
            with self.subTest(raw=raw[:60]):
                self.assertEqual(self.post("passkey/login/verify", raw=raw,
                                 cookies="__Host-hskai_admin_assert=" + ASSERT_PROOF).status_code, 400)
        self.assertEqual(self.post("passkey/login/options", value={"user_id": 1}).status_code, 400)

    def test_logout_revokes_session_and_clears_cookie(self):
        r = self.post("logout", cookies="__Host-hskai_admin=" + SESSION)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "logged_out")
        self.assertEqual(self.calls, [("logout", SESSION)])
        self.assertTrue(any(x.startswith("__Host-hskai_admin=")
                            for x in r.headers.get_list("set-cookie")))
        self.assertFalse(any(x.lower().startswith("__host-hskai_admin=" + SESSION.lower())
                             for x in r.headers.get_list("set-cookie")))

    def test_unknown_browser_cannot_use_other_origin(self):
        with TestClient(self.client.app, base_url="https://evil.example") as other:
            r = other.post("/api/admin/v1/auth/passkey/login/options",
                           headers={"origin": ORIGIN, "content-type": "application/json"}, json={})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
