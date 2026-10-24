"""OAuth/MCP HTTP boundary: feature-off, client/resource, token and JSON-RPC.

The app stays feature-off in real settings, so these requests are never
production or real ChatGPT traffic. Services injected as explicit mocks.
"""
from tests.mcp_transport_fakes import admit, finish, statistics_admit

import json
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from urllib.parse import urlencode
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_mcp_http import create_admin_pwa_mcp_http_router

RESOURCE = "https://hskai.app/mcp"
ISSUER = "https://hskai.app"
CLIENT = "test-oauth-client"
REDIRECT = "https://chatgpt.example.com/callback"
TOKEN = "B" * 64
CODE = "C" * 64
VERIFIER = "V" * 64


@asynccontextmanager
async def session_factory():
    yield object()


class McpHttpTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_TRANSPORT_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE=RESOURCE,
            ADMIN_PWA_MCP_CLIENT_ID=CLIENT,
            ADMIN_PWA_MCP_REDIRECT_URI=REDIRECT,
        )
        self.calls = []

        async def exchange(db, *, code, code_verifier, client_id, redirect_uri,
                           resource, settings_obj):
            self.calls.append(("exchange", code, client_id))
            if (code, code_verifier, client_id, redirect_uri, resource) != (
                CODE, VERIFIER, CLIENT, REDIRECT, RESOURCE,
            ):
                return None
            return SimpleNamespace(token=TOKEN, token_type="Bearer",
                                   expires_in=300, scope="admin:analytics:read")

        async def verify(db, *, authorization, settings_obj):
            self.calls.append(("verify", authorization))
            if authorization != "Bearer " + TOKEN:
                return None
            return SimpleNamespace(admin_user_id=1)

        async def read(db, *, authorization, args, settings_obj):
            self.calls.append(("read", authorization, args))
            return {"data": {"available": True, "users_total": 7}}

        self.app = FastAPI()
        self.app.include_router(create_admin_pwa_mcp_http_router(
            settings_obj=self.settings, session_factory=session_factory,
            exchange_service=exchange, verify_service=verify,
            read_service=read, admission_service=admit, completion_service=finish,
            statistics_admission=statistics_admit,
        ))
        self.client = TestClient(self.app, base_url=ISSUER)
        self.addCleanup(self.client.close)

    def token(self, *, data=None, headers=None, raw=None):
        val = {
            "grant_type": "authorization_code",
            "code": CODE, "code_verifier": VERIFIER, "client_id": CLIENT,
            "redirect_uri": REDIRECT, "resource": RESOURCE,
        } if data is None else data
        return self.client.post("/oauth/token",
            content=urlencode(val).encode() if raw is None else raw,
            headers={"content-type": "application/x-www-form-urlencoded", **(headers or {})})

    def rpc(self, method="tools/list", *, params=None, token=TOKEN, headers=None,
            data=None, raw=None):
        payload = ({"jsonrpc": "2.0", "id": 7, "method": method}
                   if data is None else data)
        if params is not None:
            payload["params"] = params
        h = {
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
            "authorization": "Bearer " + token,
            "mcp-protocol-version": "2025-11-25",
            **(headers or {}),
        }
        return self.client.post("/mcp",
            content=json.dumps(payload).encode() if raw is None else raw, headers=h)

    def test_disabled_by_any_feature_flag_is_always_404(self):
        for flag in ("ADMIN_PWA_ENABLED", "ADMIN_PWA_MCP_ENABLED",
                     "ADMIN_PWA_MCP_TRANSPORT_ENABLED"):
            with self.subTest(flag=flag):
                setattr(self.settings, flag, False)
                for method, url in (
                    ("get", "/.well-known/oauth-protected-resource"),
                    ("get", "/.well-known/oauth-authorization-server"),
                    ("post", "/oauth/token"),
                    ("post", "/mcp"),
                ):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 404)
                setattr(self.settings, flag, True)
        self.assertEqual(self.calls, [])

    def test_metadata_only_exact_https_resource(self):
        r = self.client.get("/.well-known/oauth-protected-resource")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["resource"], RESOURCE)
        self.assertEqual(r.json()["authorization_servers"], [ISSUER])
        self.assertNotIn("admin:payments:write", str(r.json()))
        metadata = self.client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(metadata.json()["code_challenge_methods_supported"], ["S256"])
        self.assertEqual(metadata.json()["token_endpoint_auth_methods_supported"], ["none"])
        self.assertIs(metadata.json()["authorization_response_iss_parameter_supported"], True)
        self.assertNotIn("access_token", metadata.text)
        self.assertEqual(metadata.headers["cache-control"], "no-store")

    def test_token_exchange_oauth_form_never_sets_cookie(self):
        r = self.token()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["access_token"], TOKEN)
        self.assertEqual(r.json()["token_type"], "Bearer")
        self.assertEqual(r.json()["expires_in"], 300)
        self.assertFalse(r.headers.get_list("set-cookie"))
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertEqual(self.calls, [("exchange", CODE, CLIENT)])

    def test_token_unknown_client_redirect_resource_and_grant_deny_before_service(self):
        for key, value in (
            ("client_id", "other-client"),
            ("redirect_uri", "https://attacker.example/cb"),
            ("resource", "https://evil.example/mcp"),
            ("grant_type", "password"),
        ):
            with self.subTest(key=key):
                values = {
                    "grant_type": "authorization_code", "code": CODE,
                    "code_verifier": VERIFIER, "client_id": CLIENT,
                    "redirect_uri": REDIRECT, "resource": RESOURCE,
                }
                values[key] = value
                self.assertEqual(self.token(data=values).status_code, 400)
        self.assertEqual(self.calls, [])

    def test_duplicate_form_sql_and_json_content_denied(self):
        cases = (
            b"code=AAA&code=BBB",
            b"grant_type=authorization_code&grant_type=authorization_code",
            b"a=" + b"x" * 6000,
            b"not-form-encoded",
        )
        for raw in cases:
            with self.subTest(raw=raw[:30]):
                self.assertEqual(self.token(raw=raw).status_code, 400)
        self.assertEqual(
            self.token(headers={"content-type": "application/json"}).status_code, 400,
        )
        self.assertEqual(self.calls, [])

    def test_missing_bearer_rejected_with_oauth_metadata_header(self):
        r = self.rpc(headers={"authorization": ""})
        self.assertEqual(r.status_code, 401)
        self.assertIn("resource_metadata=", r.headers["www-authenticate"])
        self.assertEqual(self.calls, [])
        wrong = self.rpc(token="X" * 64)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(self.calls[-1][0], "verify")

    def test_stateless_mcp_initialize_tools_and_one_stats_call(self):
        r = self.rpc("initialize", params={"protocolVersion": "2025-11-25", "capabilities": {},
                                           "clientInfo": {"name": "synthetic", "version": "1"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(r.json()["result"]["serverInfo"]["name"], "hskai-admin-readonly")
        r = self.rpc()
        self.assertEqual(r.status_code, 200)
        self.assertEqual([t["name"] for t in r.json()["result"]["tools"]],
                         ["hskai_statistics"])
        r = self.rpc("tools/call", params={"name": "hskai_statistics",
                                           "arguments": {"platform": "overall"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["result"]["structuredContent"]["users_total"], 7)
        self.assertEqual(self.calls[-1][0], "read")
        self.assertNotIn(TOKEN, r.text)
        self.assertFalse(r.headers.get_list("set-cookie"))

    def test_forbidden_tools_and_invalid_json_rpc_are_not_executed(self):
        for name in ("payments.review", "users.delete", "broadcast.send",
                     "hskai_users_search", "hskai_feedback_list"):
            response = self.rpc("tools/call", params={"name": name, "arguments": {}})
            self.assertEqual(response.json()["error"]["code"], -32602)
        for raw in (
            b'{"jsonrpc":"2.0","id":1,"method":"tools/list","method":"tools/call"}',
            b'[{"jsonrpc":"2.0","id":1,"method":"tools/list"}]',
            b"{" + b"a" * 12001 + b"}",
        ):
            with self.subTest(raw=raw[:70]):
                self.assertEqual(self.rpc(raw=raw).json()["error"]["code"], -32700)
        self.assertFalse(any(c[0] == "read" for c in self.calls))

    def test_origin_cookie_and_accept_fail_closed(self):
        cases = [
            ({"origin": "https://evil.example"}, 403),
            ({"sec-fetch-site": "cross-site"}, 403),
            ({"accept": "application/json"}, 406),
            ({"cookie": "__Host-hskai_admin=" + "S" * 64}, 401),
            ({"x-telegram-init-data": "forged"}, 401),
            ({"mcp-protocol-version": "1900-01-01"}, 400),
        ]
        for headers, expected in cases:
            with self.subTest(headers=headers):
                self.assertEqual(self.rpc(headers=headers).status_code, expected)
        self.assertFalse(any(c[0] == "read" for c in self.calls))

    def test_unimplemented_sse_and_stateful_delete_refused(self):
        self.assertEqual(self.client.get("/mcp").status_code, 405)
        self.assertEqual(self.client.delete("/mcp").status_code, 405)

    def test_protocol_negotiation_and_strict_initialize(self):
        for requested, expected in (("2025-06-18", "2025-06-18"), ("2030-01-01", "2025-11-25")):
            response = self.rpc("initialize", params={
                "protocolVersion": requested, "capabilities": {},
                "clientInfo": {"name": "synthetic", "version": "1"}})
            self.assertEqual(response.json()["result"]["protocolVersion"], expected)
        self.assertEqual(self.rpc(headers={"mcp-protocol-version":""}).status_code, 400)
        self.assertEqual(self.rpc("initialize", params={}).json()["error"]["code"], -32602)
        self.assertEqual(self.rpc(data={"jsonrpc":"2.0", "method":"notifications/initialized"}).status_code, 202)
        self.assertEqual(self.rpc(data={"jsonrpc":"2.0", "method":"tools/call", "params":{
            "name":"hskai_statistics", "arguments":{}}}).status_code, 400)
        self.assertFalse(any(c[0] == "read" for c in self.calls))

    def test_accept_quality_origin_and_non_utf8_fail_shut(self):
        for accept in ("application/json;q=0, text/event-stream", "application/json-bogus, text/event-stream", "application/json, text/event-stream;q=oops"):
            self.assertEqual(self.rpc(headers={"accept":accept}).status_code, 406)
        for method in (self.client.get, self.client.delete):
            self.assertEqual(method("/mcp", headers={"origin":"https://evil.example"}).status_code, 403)
        self.assertEqual(self.rpc(raw='{"jsonrpc":"2.0","id":1,"method":"ping"}'.encode('utf-16')).status_code, 400)
        self.assertEqual(self.rpc(raw=b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":NaN}}').status_code, 400)
        response = self.client.post('/mcp', content=b'{}', headers=[
            ('authorization','Bearer '+TOKEN), ('origin', ISSUER), ('origin','https://evil.example')])
        self.assertEqual(response.status_code, 403)

    def test_public_client_does_not_accept_secret_or_cookie_credentials(self):
        for headers in ({"authorization":"Basic synthetic"},{"cookie":"__Host-hskai_admin=synthetic"}):
            self.assertEqual(self.token(headers=headers).json()["error"], "invalid_client")
        self.assertEqual(self.calls, [])

    def test_wrong_request_host_denied(self):
        with TestClient(self.app, base_url="https://other.example") as client:
            self.assertEqual(client.get("/.well-known/oauth-protected-resource").status_code, 403)


if __name__ == "__main__":
    unittest.main()
