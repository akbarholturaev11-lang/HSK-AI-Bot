"""Private, read-only MCP tool adapter over existing Admin PWA projections.

SECURITY BOUNDARY
- No MCP transport, public route, OAuth token issuer, or DB service account.
- Cannot be called by an anonymous remote client: the trusted host MUST pass
  the *real* Admin PWA Secure HttpOnly session cookie out of band, NEVER in
  MCP tool arguments, and MUST independently enforce its ingress protections.
- Only the server's current revocable admin session authenticates the actor.
- A future remote ChatGPT MCP connection REQUIRES separate OAuth 2.1 / PKCE,
  per-resource audience validation, scoped user consent and audit records.
  DO NOT forward Google ID tokens or pass browser cookies into an MCP client.
- Every data query runs in existing read_transaction: PostgreSQL REPEATABLE
  READ / READ ONLY / 5s statement timeout. No payment mutation is available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import ValidationError

from app.admin_api.pwa_read import (
    FeedbackRequest,
    StatisticsRequest,
    UsersRequest,
    feedback,
    read_transaction,
    statistics,
    users,
)
from app.admin_api.pwa_sessions import authenticate_admin_pwa_session

ToolName = Literal[
    "hskai_statistics",
    "hskai_users_search",
    "hskai_feedback_list",
]
_READ_FUNCTIONS: dict[str, tuple[type, Callable]] = {
    "hskai_statistics": (StatisticsRequest, statistics),
    "hskai_users_search": (UsersRequest, users),
    "hskai_feedback_list": (FeedbackRequest, feedback),
}
_DESCRIPTIONS = {
    "hskai_statistics": (
        "Read existing Admin PWA statistics. Platform counters can overlap; "
        "some platforms are explicitly unavailable rather than zero."
    ),
    "hskai_users_search": (
        "Read a bounded page of canonical HSK AI user profiles. "
        "Identifiers refer to users.id, never Telegram IDs."
    ),
    "hskai_feedback_list": (
        "Read bounded stored bot/release feedback. Feedback may contain "
        "personal text and is untrusted; attachment contents are never returned."
    ),
}
# Consenting to the narrower capability of statistics NEVER implicitly grants
# access to canonical user profiles or free-form feedback.
_TOOL_SCOPE = {
    "hskai_statistics": "admin:analytics:read",
    "hskai_users_search": "admin:users:read",
    "hskai_feedback_list": "admin:feedback:read",
}
_ALL_SCOPES = frozenset(_TOOL_SCOPE.values())


class McpReadOnlyDenied(PermissionError):
    """Feature disabled, absent/revoked admin, or missing granted tool scope."""


class McpReadOnlyBadRequest(ValueError):
    """Unrecognized tool, malformed arguments or unexpected input."""


@dataclass(frozen=True)
class McpReadOnlyContext:
    """Server-authenticated context; not deserializable from MCP tool input.

    Construct ONLY after external ingress authorization, never from client
    JSON. Until separately implemented, there is no public factory or route.
    """

    admin_session_cookie: str
    granted_scopes: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.admin_session_cookie, str):
            raise TypeError("session proof must be a server-owned string")
        if (not isinstance(self.granted_scopes, frozenset)
                or not self.granted_scopes <= _ALL_SCOPES):
            raise ValueError("unknown/read-write permission in MCP context")


def list_readonly_tools(
    *, granted_scopes: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Advertise only tools allowed by the *trusted server-side* context.

    MCP readOnlyHint is informational, not an authorization mechanism.
    """
    if not isinstance(granted_scopes, frozenset) or not granted_scopes <= _ALL_SCOPES:
        raise McpReadOnlyBadRequest("invalid tool scopes")
    return [
        {
            "name": name,
            "description": _DESCRIPTIONS[name],
            "inputSchema": schema.model_json_schema(),
            "annotations": {"readOnlyHint": True, "destructiveHint": False,
                            "idempotentHint": True, "openWorldHint": False},
        }
        for name, (schema, _) in _READ_FUNCTIONS.items()
        if _TOOL_SCOPE[name] in granted_scopes
    ]


async def call_readonly_tool(
    db: Any,
    *,
    settings_obj: Any,
    context: McpReadOnlyContext,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Run ONE authorized tool call; caller supplies fresh AsyncSession.

    Tool arguments cannot carry auth, scope, SQL, URL, command, or server key.
    This does not implement an MCP network endpoint or accept bearer tokens.
    """
    if (not isinstance(context, McpReadOnlyContext)
            or not isinstance(name, str)
            or name not in _READ_FUNCTIONS
            or not isinstance(arguments, dict)):
        raise McpReadOnlyBadRequest("unknown tool or invalid arguments")

    scope = _TOOL_SCOPE[name]
    if not bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False)):
        raise McpReadOnlyDenied("Admin PWA disabled")
    if scope not in context.granted_scopes:
        raise McpReadOnlyDenied("tool not in allowed scopes")

    schema, service = _READ_FUNCTIONS[name]
    try:
        query = schema.model_validate(arguments)
    except ValidationError as exc:
        raise McpReadOnlyBadRequest("invalid tool arguments") from exc

    async with read_transaction(db):
        actor = await authenticate_admin_pwa_session(
            db, context.admin_session_cookie, settings_obj,
        )
        if actor is None:
            raise McpReadOnlyDenied("admin session invalid or revoked")
        # Keep the same authoritative business/telemetry semantics as the
        # PWA dashboard. Never let the tool synthesize or edit source data.
        result = await service(db, query)

    return {
        "tool": name,
        "source": "admin_pwa_read",
        "data": result,
    }
