"""First-party, WebAuthn-session-only MCP consent history and revocation.

Not callable via MCP. No bearer/code hashes, OAuth state, callback URLs or
browser session secrets appear in returned data. All reads are user-scoped,
bounded, and require CURRENT canonical admin rights.
"""
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_mcp_resource import _ready
from app.admin_api.pwa_sessions import authenticate_admin_pwa_session
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.admin_pwa_mcp_authorization import AdminPwaMcpAuthorization

_REQUEST_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HISTORY_LIMIT = 30


def _iso(value: datetime | None) -> str | None:
    return _utc(value).isoformat() if value is not None else None


async def list_mcp_authorizations(
    db: Any, *, session_cookie: str, settings_obj: Any,
    now: datetime | None = None,
) -> list[dict[str, Any]] | None:
    """Bounded per-admin history. None means authentication was denied."""
    if not _ready(settings_obj):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        actor = await authenticate_admin_pwa_session(
            db, session_cookie, settings_obj, now=stamp,
        )
        if actor is None or actor.auth_method != "webauthn":
            return None
        rows = (await db.execute(
            select(AdminPwaMcpAuthorization)
            .where(AdminPwaMcpAuthorization.user_id == actor.user_id)
            .order_by(AdminPwaMcpAuthorization.created_at.desc(),
                      AdminPwaMcpAuthorization.id.desc())
            .limit(_HISTORY_LIMIT)
        )).scalars().all()
        ids = [row.id for row in rows]
        grants = (await db.execute(select(AdminPwaMcpAccessGrant).where(
            AdminPwaMcpAccessGrant.user_id == actor.user_id,
            AdminPwaMcpAccessGrant.consent_event_id.in_(ids),
        ))).scalars().all() if ids else []
        by_consent: dict[str, list[AdminPwaMcpAccessGrant]] = {}
        for grant in grants:
            by_consent.setdefault(grant.consent_event_id, []).append(grant)
        return [{
            "request_id": row.id,
            "client_id": row.client_id,
            "scope": row.scope,
            "status": ("expired" if row.status in ("pending", "approved")
                       and _utc(row.expires_at) <= stamp else row.status),
            "created_at": _iso(row.created_at),
            "approved_at": _iso(row.approved_at),
            "active_access": any(
                grant.revoked_at is None
                and _utc(grant.created_at) <= stamp < _utc(grant.expires_at)
                for grant in by_consent.get(row.id, [])
            ),
            "last_access_expiry": max(
                (_iso(grant.expires_at) for grant in by_consent.get(row.id, [])),
                default=None,
            ),
        } for row in rows]


async def revoke_mcp_authorization(
    db: Any, *, session_cookie: str, request_id: str,
    settings_obj: Any, now: datetime | None = None,
) -> bool:
    """Atomically block pending codes and revoke EVERY token from this consent.

    Locking the consent row serializes against concurrent OAuth code redemption
    on PostgreSQL. Repeated revocation is idempotent; other users' IDs fail shut.
    """
    if (not _ready(settings_obj) or not isinstance(request_id, str)
            or not _REQUEST_ID.fullmatch(request_id)):
        return False
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        actor = await authenticate_admin_pwa_session(
            db, session_cookie, settings_obj, now=stamp,
        )
        if actor is None or actor.auth_method != "webauthn":
            return False
        row = (await db.execute(
            select(AdminPwaMcpAuthorization).where(
                AdminPwaMcpAuthorization.id == request_id,
                AdminPwaMcpAuthorization.user_id == actor.user_id,
            ).with_for_update()
        )).scalar_one_or_none()
        if row is None:
            return False
        # Do not overwrite a historical denial: denied requests never granted
        # access, but revoke any inconsistent legacy token defensively.
        if row.status != "denied":
            row.status = "revoked"
        await db.execute(update(AdminPwaMcpAccessGrant).where(
            AdminPwaMcpAccessGrant.user_id == actor.user_id,
            AdminPwaMcpAccessGrant.consent_event_id == request_id,
            AdminPwaMcpAccessGrant.revoked_at.is_(None),
        ).values(revoked_at=stamp).execution_options(synchronize_session=False))
        await db.flush()
        return True
