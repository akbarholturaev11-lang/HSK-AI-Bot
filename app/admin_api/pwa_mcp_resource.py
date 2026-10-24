"""Unexposed MCP OAuth *resource-side* verifier, statistics-only.

No token issuer, OAuth authorization endpoint, or public MCP route exists.
Until a reviewed authorization-code+PKCE+consent flow is implemented, NO
real access grant can be minted. A future token issuer MUST generate a 48-byte
random opaque bearer token, save only its SHA-256 hash, and bind it to
verified OAuth client/resource/consent/current canonical admin. The browser's
PWA login cookie and Google ID token can NEVER substitute for that grant.

Every read rechecks revocation, expiry, exact resource and narrow scope,
and the CURRENT Telegram admin allowlist. Do not expose bearer tokens to logs.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_read import StatisticsRequest, statistics, read_transaction
from app.admin_api.pwa_sessions import _authorized_admin
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.user import User

_REQUIRED_RESOURCE = "https://hskai.app/mcp"
_ANALYTICS_SCOPE = "admin:analytics:read"
_TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_-]{40,192}$")
_CLIENT_SHAPE = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_ACCESS_MAX_TTL = timedelta(minutes=5)


class McpBearerDenied(PermissionError):
    """No server-verified, eligible scoped OAuth access grant."""


class McpBearerBadArguments(ValueError):
    """Unsupported tool name or malformed tool arguments."""


@dataclass(frozen=True)
class McpBearerActor:
    """Validated OAuth grant; never constructed from client-supplied JSON."""

    admin_user_id: int
    grant_id: str
    client_id: str
    scope: str


def _ready(settings_obj: Any) -> bool:
    return (
        bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False))
        and bool(getattr(settings_obj, "ADMIN_PWA_MCP_ENABLED", False))
        and getattr(settings_obj, "ADMIN_PWA_MCP_RESOURCE", "") == _REQUIRED_RESOURCE
    )


async def verify_readonly_mcp_bearer(
    db: Any, *,
    authorization: str,
    settings_obj: Any,
    now: datetime | None = None,
) -> McpBearerActor | None:
    """Validate OAuth *access token* stored as keyed resource-bound grant.

    This does not accept a browser session, query-token, arbitrary OAuth
    scopes, id_token or a future unverified JWT. It requires a genuine DB row
    created by a separately authenticated/consented OAuth issuer.
    """
    if not _ready(settings_obj) or not isinstance(authorization, str):
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix):]
    if not _TOKEN_SHAPE.fullmatch(token):
        return None

    stamp = _utc(now or datetime.now(timezone.utc))
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    grant = (await db.execute(select(AdminPwaMcpAccessGrant).where(
        AdminPwaMcpAccessGrant.token_hash == digest,
    ))).scalar_one_or_none()
    if (
        grant is None
        or not hmac.compare_digest(str(grant.token_hash), digest)
        or grant.revoked_at is not None
        or grant.scope != _ANALYTICS_SCOPE
        or grant.audience != _REQUIRED_RESOURCE
        or not isinstance(grant.client_id, str)
        or not _CLIENT_SHAPE.fullmatch(grant.client_id)
        or not isinstance(grant.consent_event_id, str)
        or not _UUID.fullmatch(grant.consent_event_id)
        or _utc(grant.created_at) > stamp
        or _utc(grant.expires_at) <= stamp
        or _utc(grant.expires_at) - _utc(grant.created_at) > _ACCESS_MAX_TTL
    ):
        return None

    user = await db.get(User, grant.user_id)
    if not _authorized_admin(user, settings_obj):
        return None

    return McpBearerActor(
        admin_user_id=int(user.id), grant_id=str(grant.id),
        client_id=str(grant.client_id), scope=grant.scope,
    )


async def read_mcp_statistics_with_verified_token(
    db: Any, *, authorization: str, args: dict[str, Any],
    settings_obj: Any,
) -> dict[str, Any]:
    """Process one statistics-only read in the existing READ ONLY snapshot.

    No standalone HTTP handler exists. A future MCP HTTP ingress MUST enforce
    OAuth authorization-server metadata, audience/resource scope, TLS, rate
    limit, audit and trust boundaries BEFORE calling this adapter. Current
    code intentionally DOES NOT support users/feedback/payments through OAuth.
    """
    if not isinstance(args, dict):
        raise McpBearerBadArguments("invalid MCP arguments")
    try:
        query = StatisticsRequest.model_validate(args)
    except ValidationError as exc:
        raise McpBearerBadArguments("invalid statistics request") from exc

    async with read_transaction(db):
        actor = await verify_readonly_mcp_bearer(
            db, authorization=authorization, settings_obj=settings_obj,
        )
        if actor is None:
            raise McpBearerDenied("resource authorization denied")
        data = await statistics(db, query)
    return {"tool": "hskai_statistics", "source": "admin_pwa_read", "data": data}
