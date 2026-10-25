"""Browser-only per-operation WebAuthn step-up ceremony.

This router NEVER executes an admin mutation and NEVER provides a generic
"authorize next write" HTTP endpoint. Future PWA payment/delete/broadcast
routes must consume the verified receipt in their own DB write transaction
using the EXACT same validated action, target and payload.
"""
import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_webauthn_transport import _guard_post, _body
from app.admin_api.pwa_step_up import begin_step_up, verify_step_up

logger = logging.getLogger(__name__)


def create_admin_pwa_step_up_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    begin_service: Callable = begin_step_up,
    verify_service: Callable = verify_step_up,
) -> APIRouter:
    router = APIRouter(tags=["admin-pwa-step-up"])

    @router.post("/api/admin/v1/auth/step-up/options")
    async def begin(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        body = await _body(request, 4096)
        if body is None or set(body) != {"action", "target", "payload"}:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await begin_service(
                    db, session_cookie=cookie, action=body["action"],
                    target=body["target"], payload=body["payload"],
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin PWA step-up options unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if result is None:
            return _reply(403, "admin_pwa_step_up_denied")
        return JSONResponse(
            content={"ok": True, "step_up_id": result.step_up_id,
                     "publicKey": result.options,
                     "expires_at": result.expires_at.isoformat()},
            headers=_PRIVATE_HEADERS,
        )

    @router.post("/api/admin/v1/auth/step-up/verify")
    async def verify(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        body = await _body(request, 16384)
        if (body is None or set(body) != {"step_up_id", "credential"}
                or not isinstance(body["step_up_id"], str)
                or not isinstance(body["credential"], dict)):
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                passed = await verify_service(
                    db, session_cookie=cookie, step_up_id=body["step_up_id"],
                    credential=body["credential"], settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin PWA step-up WebAuthn verification unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if not passed:
            return _reply(403, "admin_pwa_step_up_denied")
        # A successful result is STILL NOT an execution capability: the
        # exact sensitive mutation must consume the matching row atomically.
        return JSONResponse(
            content={"ok": True, "status": "step_up_verified",
                     "step_up_id": body["step_up_id"]}, headers=_PRIVATE_HEADERS,
        )

    return router
