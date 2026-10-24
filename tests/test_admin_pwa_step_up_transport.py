"""Browser security contracts for isolated WebAuthn step-up, no admin writes."""
import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_step_up_transport import create_admin_pwa_step_up_router

ORIGIN = "https://hskai.app"
SESSION = "S" * 64
STEP_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PAYLOAD = {"action": "payments.review", "target": "123",
           "payload": {"decision": "approve", "payment_id": 123}}


@asynccontextmanager
async def database():
    yield object()


class StepUpHttpTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN,
        )
        self.calls = []

        async def start(db, *, session_cookie, action, target, payload, settings_obj):
            self.calls.append(("start", session_cookie, action, target, payload))
            if session_cookie != SESSION or action != "payments.review":
                return None
            return SimpleNamespace(
                step_up_id=STEP_ID,
                options={"rpId": "hskai.app", "challenge": "public-challenge"},
                expires_at=datetime(2026, 10, 24, 18, 2, tzinfo=timezone.utc),
            )

        async def verify(db, *, session_cookie, step_up_id, credential, settings_obj):
            self.calls.append(("verify", session_cookie, step_up_id))
            return session_cookie == SESSION and step_up_id == STEP_ID and credential.get("id") == "signed"

        app = FastAPI()
        app.include_router(create_admin_pwa_step_up_router(
            settings_obj=self.settings, session_factory=database,
            begin_service=start, verify_service=verify,
        ))
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def post(self, suffix="options", *, payload=None, headers=None,
             cookie=True, raw=None):
        h = {"origin": ORIGIN, "sec-fetch-site": "same-origin",
             "content-type": "application/json"}
        if cookie:
            h["cookie"] = "__Host-hskai_admin=" + SESSION
        if headers:
            h.update(headers)
        if raw is None:
            data = PAYLOAD if suffix == "options" else {
                "step_up_id": STEP_ID,
                "credential": {"id": "signed", "type": "public-key"},
            }
            raw = json.dumps(data if payload is None else payload).encode("utf-8")
        return self.client.post(
            "/api/admin/v1/auth/step-up/" + suffix,
            headers=h, content=raw,
        )

    def test_challenge_only_no_cookie_or_mutation(self):
        r = self.post()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["step_up_id"], STEP_ID)
        self.assertEqual(r.json()["publicKey"]["rpId"], "hskai.app")
        self.assertNotIn(SESSION, r.text)
        self.assertNotIn("admin_token", r.text)
        self.assertFalse(r.headers.get_list("set-cookie"))
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertEqual(len(self.calls), 1)

    def test_verified_receipt_not_a_session_or_mutation(self):
        r = self.post("verify")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "step_up_verified")
        self.assertEqual(r.json()["step_up_id"], STEP_ID)
        self.assertFalse(r.headers.get_list("set-cookie"))
        self.assertNotIn("payment", r.json())
        self.assertEqual(self.calls[0][0], "verify")

    def test_origin_csrf_fetch_site_media_type(self):
        for h in ({"origin": ""},
                  {"origin": "https://attacker.example"},
                  {"sec-fetch-site": "cross-site"},
                  {"sec-fetch-site": "none"},
                  {"content-type": "text/plain"}):
            with self.subTest(headers=h):
                self.assertIn(self.post(headers=h).status_code, (403, 415))
        self.assertEqual(self.calls, [])

    def test_missing_session_or_feature_off_blocks(self):
        self.assertEqual(self.post(cookie=False).status_code, 401)
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(self.post("verify").status_code, 404)
        self.assertEqual(self.calls, [])

    def test_duplicate_keys_extra_body_and_oversize_rejected(self):
        for raw in (
            b'{"action":"payments.review","target":"123","payload":{"x":1},"action":"users.delete"}',
            b'{"action":"payments.review","target":"123","payload":{},"user_id":999}',
            b'{"action":"payments.review","target":"123","payload":{"x":1,"x":2}}',
            b"x" * 16385,
        ):
            with self.subTest(raw=raw[:75]):
                self.assertEqual(self.post(raw=raw).status_code, 400)
        self.assertEqual(self.post("verify", raw=b'{"step_up_id":"a"}').status_code, 400)
        self.assertEqual(self.calls, [])

    def test_bad_or_denied_service_returns_fail_closed(self):
        r = self.post(payload={"action": "users.delete", "target": "123", "payload": {"reason": "x"}})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(r.headers.get_list("set-cookie"))
        r = self.post("verify", payload={"step_up_id": STEP_ID, "credential": {"id": "bad"}})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(r.headers.get_list("set-cookie"))


if __name__ == "__main__":
    unittest.main()
