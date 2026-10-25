"""Origin-checked discoverable passkey login and revocable cookie logout.

No client account identifiers accepted. An authenticated session cookie is
created ONLY by the server-side, cryptographically verified WebAuthn assertion.
"""
import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_google_transport import (
    _PRIVATE_HEADERS, _drop_cookie, _reply, _set_secret_cookie,
)
from app.admin_api.pwa_sessions import (
    ADMIN_PWA_COOKIE_NAME, revoke_admin_pwa_session,
)
from app.admin_api.pwa_webauthn_registration import _ORIGIN
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.admin_api.pwa_webauthn_login import (
    PasskeyLoginRateLimited, begin_passkey_login, complete_passkey_login,
)

logger = logging.getLogger(__name__)
_ASSERT_COOKIE = "__Host-hskai_admin_assert"
_SESSION_MAX_AGE = 8 * 60 * 60


def create_admin_pwa_passkey_login_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    begin_service: Callable = begin_passkey_login,
    finish_service: Callable = complete_passkey_login,
    revoke_service: Callable = revoke_admin_pwa_session,
) -> APIRouter:
    router = APIRouter(tags=["admin-pwa-passkey-login"])

    @router.post("/api/admin/v1/auth/passkey/login/options")
    async def login_options(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        body = await _body(request, 32)
        if body is None or body:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                started = await begin_service(db, settings_obj=settings_obj)
        except PasskeyLoginRateLimited:
            return _reply(429, "admin_pwa_rate_limited")
        except Exception:
            logger.exception("Admin PWA passkey login options unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if started is None:
            return _reply(409, "admin_pwa_auth_unavailable")
        response = JSONResponse(content={
            "ok": True, "publicKey": started.options,
            "expires_at": started.expires_at.isoformat(),
        }, headers=_PRIVATE_HEADERS)
        _set_secret_cookie(response, _ASSERT_COOKIE, started.browser_proof, 120)
        return response

    @router.post("/api/admin/v1/auth/passkey/login/verify")
    async def login_verify(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        proof = request.cookies.get(_ASSERT_COOKIE, "")
        if not proof:
            return _reply(401, "admin_pwa_auth_invalid")
        body = await _body(request, 16384)
        if body is None or set(body) != {"credential"} or not isinstance(body["credential"], dict):
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                verified = await finish_service(
                    db, browser_proof=proof, credential=body["credential"],
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin PWA passkey verification unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if verified is None:
            response = _reply(401, "admin_pwa_auth_invalid")
            # Do not leave a failed assertion cookie available for replay.
            _drop_cookie(response, _ASSERT_COOKIE)
            return response
        response = JSONResponse(
            content={"ok": True, "status": "authenticated",
                     "expires_at": verified.expires_at.isoformat()},
            headers=_PRIVATE_HEADERS,
        )
        _drop_cookie(response, _ASSERT_COOKIE)
        _set_secret_cookie(response, ADMIN_PWA_COOKIE_NAME, verified.token, _SESSION_MAX_AGE)
        return response

    @router.post("/api/admin/v1/auth/logout")
    async def logout(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        body = await _body(request, 32)
        if body is None or body:
            return _reply(400, "admin_pwa_invalid_payload")
        token = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        try:
            async with session_factory() as db:
                if token:
                    await revoke_service(db, token)
        except Exception:
            logger.exception("Admin PWA logout revocation unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        response = JSONResponse(content={"ok": True, "status": "logged_out"},
                                headers=_PRIVATE_HEADERS)
        _drop_cookie(response, ADMIN_PWA_COOKIE_NAME)
        _drop_cookie(response, _ASSERT_COOKIE)
        return response

    return router
