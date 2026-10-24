"""Fail-closed MCP read adapter tests.

No MCP network endpoint/OAuth provider is installed by this change.
Do not interpret these unit tests as a connected ChatGPT integration.
"""
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

from app.admin_api.pwa_mcp_readonly import (
    McpReadOnlyContext, McpReadOnlyBadRequest, McpReadOnlyDenied,
    list_readonly_tools, call_readonly_tool, _READ_FUNCTIONS,
)

ANALYTICS = "admin:analytics:read"
USERS = "admin:users:read"
FEEDBACK = "admin:feedback:read"


def ctx(*scopes, cookie="S" * 64):
    return McpReadOnlyContext(
        admin_session_cookie=cookie, granted_scopes=frozenset(scopes),
    )


class ToolCatalogTests(unittest.TestCase):
    def test_tools_are_explicit_and_scope_limited(self):
        self.assertEqual(list_readonly_tools(), [])
        listing = list_readonly_tools(granted_scopes=frozenset({ANALYTICS}))
        self.assertEqual([x["name"] for x in listing], ["hskai_statistics"])
        self.assertTrue(listing[0]["annotations"]["readOnlyHint"])
        self.assertFalse(listing[0]["annotations"]["destructiveHint"])
        self.assertFalse(listing[0]["inputSchema"]["additionalProperties"])
        all_tools = list_readonly_tools(
            granted_scopes=frozenset({ANALYTICS, USERS, FEEDBACK}),
        )
        self.assertEqual({x["name"] for x in all_tools},
                         {"hskai_statistics", "hskai_users_search", "hskai_feedback_list"})

    def test_unknown_or_write_permissions_fail_closed(self):
        with self.assertRaises(ValueError):
            ctx(ANALYTICS, "admin:payments:write")
        with self.assertRaises(McpReadOnlyBadRequest):
            list_readonly_tools(granted_scopes=frozenset({"admin:all"}))
        with self.assertRaises(TypeError):
            McpReadOnlyContext(admin_session_cookie=5, granted_scopes=frozenset({ANALYTICS}))


class ScopedReadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True)
        self.db = object()
        self.events = []

        @asynccontextmanager
        async def read_only(db):
            self.assertIs(db, self.db)
            self.events.append("begin")
            try:
                yield
            finally:
                self.events.append("end")

        async def auth(db, cookie, settings):
            self.events.append("auth")
            return SimpleNamespace(user_id=1) if cookie == "S" * 64 else None

        async def stats(db, request):
            self.events.append("statistics")
            return {"available": True, "metrics": {"users_total": 7}}

        async def users(db, request):
            self.events.append("users")
            return {"items": [{"user_id": 1}]}

        async def feedback(db, request):
            self.events.append("feedback")
            return {"items": [{"source": request.source}]}

        self.patches = [
            patch("app.admin_api.pwa_mcp_readonly.read_transaction", side_effect=read_only),
            patch("app.admin_api.pwa_mcp_readonly.authenticate_admin_pwa_session", side_effect=auth),
            patch.dict(_READ_FUNCTIONS, {
                "hskai_statistics": (_READ_FUNCTIONS["hskai_statistics"][0], stats),
                "hskai_users_search": (_READ_FUNCTIONS["hskai_users_search"][0], users),
                "hskai_feedback_list": (_READ_FUNCTIONS["hskai_feedback_list"][0], feedback),
            }),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def run_tool(self, name="hskai_statistics", args=None, scopes=(ANALYTICS,),
                       cookie="S" * 64):
        return await call_readonly_tool(
            self.db, settings_obj=self.settings,
            context=ctx(*scopes, cookie=cookie),
            name=name, arguments=args if args is not None else {},
        )

    async def test_scoped_statistics_runs_only_inside_read_only_transaction(self):
        result = await self.run_tool()
        self.assertEqual(result["data"]["metrics"]["users_total"], 7)
        self.assertEqual(self.events, ["begin", "auth", "statistics", "end"])

    async def test_pii_tools_require_independent_permissions(self):
        with self.assertRaises(McpReadOnlyDenied):
            await self.run_tool("hskai_users_search")
        with self.assertRaises(McpReadOnlyDenied):
            await self.run_tool("hskai_feedback_list", {"source": "bot"})
        self.assertEqual(self.events, [])
        self.assertEqual(
            (await self.run_tool("hskai_users_search", {"limit": 1}, (USERS,)))["data"]["items"][0]["user_id"],
            1,
        )
        self.assertEqual(
            (await self.run_tool("hskai_feedback_list", {"source": "bot"}, (FEEDBACK,)))["data"]["items"][0]["source"],
            "bot",
        )

    async def test_disabled_or_revoked_admin_cannot_query(self):
        self.settings.ADMIN_PWA_ENABLED = False
        with self.assertRaises(McpReadOnlyDenied):
            await self.run_tool()
        self.assertEqual(self.events, [])
        self.settings.ADMIN_PWA_ENABLED = True
        with self.assertRaises(McpReadOnlyDenied):
            await self.run_tool(cookie="X" * 64)
        self.assertEqual(self.events, ["begin", "auth", "end"])

    async def test_tool_args_reject_auth_override_sql_and_bad_schemas(self):
        cases = [
            ("hskai_statistics", {"sql": "DELETE FROM users"}),
            ("hskai_users_search", {"admin_user_id": 9001}),
            ("hskai_feedback_list", {}),
            ("hskai_feedback_list", {"source": "android"}),
            ("hskai_statistics", {"platform": "other"}),
            ("payments.approve", {}),
        ]
        for name, args in cases:
            with self.subTest(name=name, args=args):
                with self.assertRaises(McpReadOnlyBadRequest):
                    await self.run_tool(name, args)
        self.assertEqual(self.events, [])

    async def test_no_client_supplied_scopes_are_accepted(self):
        with self.assertRaises(McpReadOnlyBadRequest):
            await self.run_tool("hskai_statistics", {"granted_scopes": [ANALYTICS]})
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
