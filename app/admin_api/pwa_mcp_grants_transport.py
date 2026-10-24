"""First-party browser management for existing MCP OAuth consents.

These routes are NOT MCP tools. Both operations require a current WebAuthn
Admin PWA cookie and a canonical same-origin JSON POST. No tokens or OAuth
secrets are serialized; never add grants to the public PWA service worker.
"""
import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_mcp_grants import (
    list_mcp_authorizations, revoke_mcp_authorization,
)
from app.admin_api.pwa_mcp_http import _inactive_response
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_webauthn_transport import _body, _guard_post

logger = logging.getLogger(__name__)


def create_admin_pwa_mcp_grants_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    list_service: Callable = list_mcp_authorizations,
    revoke_service: Callable = revoke_mcp_authorization,
) -> APIRouter:
    router = APIRouter(tags=["admin-pwa-mcp-grants"])

    def gate(request: Request):
        inactive = _inactive_response(request, settings_obj)
        if inactive is not None:
            return inactive
        return _guard_post(request, settings_obj)

    @router.post("/api/admin/v1/mcp/grants/list", include_in_schema=False)
    async def list_grants(request: Request):
        failure = gate(request)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        if await _body(request, 64) != {}:
            return _reply(400, "admin_pwa_invalid_payload")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            async with session_factory() as db:
                items = await list_service(
                    db, session_cookie=cookie, settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("MCP consent history unavailable")
            return _reply(503, "admin_pwa_read_unavailable")
        if items is None:
            return _reply(401, "admin_pwa_unauthorized")
        return JSONResponse({"ok": True, "items": items}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/mcp/grants/revoke", include_in_schema=False)
    async def revoke_grant(request: Request):
        failure = gate(request)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        payload = await _body(request, 128)
        if (not isinstance(payload, dict) or set(payload) != {"request_id"}
                or not isinstance(payload["request_id"], str)):
            return _reply(400, "admin_pwa_invalid_payload")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            async with session_factory() as db:
                revoked = await revoke_service(
                    db, session_cookie=cookie, request_id=payload["request_id"],
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("MCP consent revocation unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if not revoked:
            # Don't leak existence of another administrator's grant.
            return _reply(404, "admin_pwa_not_found")
        return JSONResponse({"ok": True, "revoked": True}, headers=_PRIVATE_HEADERS)

    return router
