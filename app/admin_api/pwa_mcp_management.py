"""First-party, session-bound MCP consent history and grant revocation.

This browser management API is deliberately separate from /mcp: it never
accepts an OAuth bearer token, and it cannot read user profiles, payments,
feedback, or execute MCP tools. All three MCP gates remain OFF by default.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, update

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_mcp_http import _HEADERS, _inactive_response
from app.admin_api.pwa_mcp_oauth import _UUID
from app.admin_api.pwa_mcp_resource import _ready
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_step_up import _locked_session
from app.admin_api.pwa_webauthn_transport import _guard_post, _body
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.admin_pwa_mcp_authorization import AdminPwaMcpAuthorization

logger = logging.getLogger(__name__)
_MAX_HISTORY = 30


async def list_mcp_consent_history(
    db: Any, *, session_cookie: str, settings_obj: Any,
    now: datetime | None = None,
) -> list[dict[str, Any]] | None:
    """Return only this verified WebAuthn admin's bounded consent metadata."""
    if not _ready(settings_obj):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None:
            return None
        _, user = pair
        rows = (await db.execute(
            select(AdminPwaMcpAuthorization).where(
                AdminPwaMcpAuthorization.user_id == int(user.id),
            ).order_by(
                AdminPwaMcpAuthorization.created_at.desc(),
                AdminPwaMcpAuthorization.id.desc(),
            ).limit(_MAX_HISTORY)
        )).scalars().all()
        if not rows:
            return []
        identifiers = [row.id for row in rows]
        grants = (await db.execute(select(
            AdminPwaMcpAccessGrant.consent_event_id,
            AdminPwaMcpAccessGrant.expires_at,
        ).where(
            AdminPwaMcpAccessGrant.user_id == int(user.id),
            AdminPwaMcpAccessGrant.consent_event_id.in_(identifiers),
            AdminPwaMcpAccessGrant.revoked_at.is_(None),
            AdminPwaMcpAccessGrant.expires_at > stamp,
        ))).all()
        active = {consent_id for consent_id, _ in grants}
        return [{
            "id": row.id,
            "client_id": row.client_id,
            "scope": row.scope,
            "created_at": _utc(row.created_at).isoformat(),
            "status": row.status if row.status != "approved" or
                      _utc(row.expires_at) > stamp else "expired",
            "active_access": row.id in active,
        } for row in rows]


async def revoke_mcp_consent(
    db: Any, *, authorization_id: str, session_cookie: str,
    settings_obj: Any, now: datetime | None = None,
) -> bool:
    """Atomically invalidate unredeemed codes AND every issued access grant.

    Only the same currently-authorized canonical admin with a valid WebAuthn
    browser session can revoke. The OAuth client cannot call this method.
    """
    if (not _ready(settings_obj) or not isinstance(authorization_id, str)
            or not _UUID.fullmatch(authorization_id)):
        return False
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        row = (await db.execute(select(AdminPwaMcpAuthorization).where(
            AdminPwaMcpAuthorization.id == authorization_id,
        ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if row is None:
            return False
        # Lock order matches OAuth code redemption: authorization -> session -> user.
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None or int(pair[1].id) != int(row.user_id):
            return False
        if row.status not in ("pending", "approved", "redeemed", "revoked"):
            return False
        if row.status == "revoked":
            return True
        await db.execute(update(AdminPwaMcpAccessGrant).where(
            AdminPwaMcpAccessGrant.user_id == int(row.user_id),
            AdminPwaMcpAccessGrant.consent_event_id == row.id,
            AdminPwaMcpAccessGrant.revoked_at.is_(None),
        ).values(revoked_at=stamp).execution_options(synchronize_session=False))
        row.status = "revoked"
        row.code_hash = None
        row.consent_csrf_hash = None
        await db.flush()
    return True


def create_admin_pwa_mcp_management_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    history_service: Callable = list_mcp_consent_history,
    revoke_service: Callable = revoke_mcp_consent,
) -> APIRouter:
    """Owner-only, cookie+same-origin browser routes; NEVER mounted on /mcp."""
    router = APIRouter(tags=["admin-pwa-mcp-management"])

    @router.get("/api/admin/v1/mcp/authorizations", include_in_schema=False)
    async def history(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return JSONResponse({"error": "temporarily_unavailable"},
                                status_code=503, headers=_HEADERS)
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return JSONResponse({"error": "admin_login_required"},
                                status_code=401, headers=_HEADERS)
        try:
            async with session_factory() as db:
                history_rows = await history_service(
                    db, session_cookie=cookie, settings_obj=settings_obj)
        except Exception:
            logger.exception("Admin MCP consent history unavailable")
            return JSONResponse({"error": "temporarily_unavailable"},
                                status_code=503, headers=_HEADERS)
        if history_rows is None:
            return JSONResponse({"error": "admin_login_required"},
                                status_code=401, headers=_HEADERS)
        return JSONResponse({"authorizations": history_rows}, headers=_HEADERS)

    @router.post("/api/admin/v1/mcp/authorizations/revoke", include_in_schema=False)
    async def revoke(request: Request):
        failure = _inactive_response(request, settings_obj)
        if failure is not None:
            return failure
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return JSONResponse({"error": "temporarily_unavailable"},
                                status_code=503, headers=_HEADERS)
        body = await _body(request, 512)
        if (body is None or set(body) != {"authorization_id"}
                or not isinstance(body["authorization_id"], str)
                or not _UUID.fullmatch(body["authorization_id"])):
            return JSONResponse({"error": "invalid_request"},
                                status_code=400, headers=_HEADERS)
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return JSONResponse({"error": "admin_login_required"},
                                status_code=401, headers=_HEADERS)
        try:
            async with session_factory() as db:
                revoked = await revoke_service(
                    db, authorization_id=body["authorization_id"],
                    session_cookie=cookie, settings_obj=settings_obj)
        except Exception:
            logger.exception("Admin MCP consent revocation unavailable")
            return JSONResponse({"error": "temporarily_unavailable"},
                                status_code=503, headers=_HEADERS)
        if not revoked:
            # Same response for nonexistent and foreign consent: no enumeration.
            return JSONResponse({"error": "access_denied"},
                                status_code=403, headers=_HEADERS)
        return JSONResponse({"revoked": True}, headers=_HEADERS)

    return router
