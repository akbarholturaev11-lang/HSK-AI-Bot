"""HTTP contracts for the isolated first-party MCP revocation API."""
import json
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_mcp_management import create_admin_pwa_mcp_management_router

ORIGIN = "https://hskai.app"
COOKIE = "C" * 64
CONSENT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@asynccontextmanager
async def session_factory():
    yield object()


class McpManagementTransportTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_TRANSPORT_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE=ORIGIN + "/mcp",
            ADMIN_PWA_MCP_CLIENT_ID="registered",
            ADMIN_PWA_MCP_REDIRECT_URI="https://client.example/callback",
            ADMIN_PWA_PUBLIC_ORIGIN=ORIGIN,
        )
        self.calls = []

        async def history(db, *, session_cookie, settings_obj):
            self.calls.append(("history", session_cookie))
            return [{"id": CONSENT, "status": "redeemed",
                     "scope": "admin:analytics:read",
                     "active_access": True} ] if session_cookie == COOKIE else None

        async def revoke(db, *, authorization_id, session_cookie, settings_obj):
            self.calls.append(("revoke", authorization_id, session_cookie))
            return authorization_id == CONSENT and session_cookie == COOKIE

        app = FastAPI()
        app.include_router(create_admin_pwa_mcp_management_router(
            settings_obj=self.settings, session_factory=session_factory,
            history_service=history, revoke_service=revoke,
        ))
        self.client = TestClient(app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def read(self, *, cookie=COOKIE):
        headers = {"cookie": "__Host-hskai_admin=" + cookie} if cookie else {}
        return self.client.get("/api/admin/v1/mcp/authorizations",
                               headers=headers)

    def revoke(self, *, cookie=COOKIE, headers=None, payload=None):
        h = {"cookie": "__Host-hskai_admin=" + cookie,
             "origin": ORIGIN, "sec-fetch-site": "same-origin",
             "content-type": "application/json"}
        if not cookie:
            h.pop("cookie")
        if headers:
            h.update(headers)
        body = payload if payload is not None else {"authorization_id": CONSENT}
        return self.client.post(
            "/api/admin/v1/mcp/authorizations/revoke",
            content=json.dumps(body), headers=h)

    def test_history_requires_browser_session_and_never_exposes_tokens(self):
        response = self.read()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["authorizations"][0]["id"], CONSENT)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn(COOKIE, response.text)
        self.assertFalse(response.headers.get_list("set-cookie"))
        self.assertEqual(self.read(cookie="").status_code, 401)
        self.assertEqual(self.read(cookie="X" * 64).status_code, 401)

    def test_revoke_requires_exact_origin_json_and_session(self):
        response = self.revoke()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"revoked": True})
        self.assertEqual(response.headers["cache-control"], "no-store")
        count = len(self.calls)
        for headers in (
            {"origin": "https://evil.example"},
            {"origin": ""},
            {"sec-fetch-site": "cross-site"},
            {"content-type": "text/plain"},
        ):
            self.assertIn(self.revoke(headers=headers).status_code, (403, 415))
        for payload in (
            {}, {"authorization_id": "x"},
            {"authorization_id": CONSENT, "users.delete": True},
        ):
            self.assertEqual(self.revoke(payload=payload).status_code, 400)
        self.assertEqual(self.revoke(cookie="").status_code, 401)
        self.assertEqual(len(self.calls), count)

    def test_wrong_session_or_foreign_consent_fails_closed(self):
        self.assertEqual(self.revoke(cookie="X" * 64).status_code, 403)
        self.assertEqual(self.revoke(payload={
            "authorization_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        }).status_code, 403)

    def test_three_gates_keep_both_management_routes_invisible(self):
        for flag in ("ADMIN_PWA_ENABLED", "ADMIN_PWA_MCP_ENABLED",
                     "ADMIN_PWA_MCP_TRANSPORT_ENABLED"):
            with self.subTest(flag=flag):
                setattr(self.settings, flag, False)
                self.assertEqual(self.read().status_code, 404)
                self.assertEqual(self.revoke().status_code, 404)
                setattr(self.settings, flag, True)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
