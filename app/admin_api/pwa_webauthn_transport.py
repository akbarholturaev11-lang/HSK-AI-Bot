"""Fail-closed HTTP WebAuthn registration; no login cookie or Admin data API.

Both endpoints require a same-origin JSON POST and the independently issued
Secure HttpOnly enrollment + original browser-proof cookies. The auth model is
revalidated server-side on every call. This router does not expose sign-in.
"""
import json
import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_google_transport import (
    _APPROVAL_COOKIE, _PRIVATE_HEADERS, _drop_cookie, _gate, _reply,
)
from app.admin_api.pwa_enrollment_transport import _ENROLL_COOKIE, _no_duplicate_json_keys
from app.admin_api.pwa_webauthn_registration import (
    begin_passkey_registration, complete_passkey_registration,
)

logger = logging.getLogger(__name__)
_MAX_ATTESTATION_BODY = 16384


def _guard_post(request: Request, settings_obj: Any):
    gate = _gate(request, settings_obj)
    if gate is not None:
        return gate
    origins = request.headers.getlist("origin")
    if len(origins) != 1 or origins[0] != settings_obj.ADMIN_PWA_PUBLIC_ORIGIN:
        return _reply(403, "admin_pwa_csrf")
    if request.headers.get("sec-fetch-site", "same-origin") != "same-origin":
        return _reply(403, "admin_pwa_csrf")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return _reply(415, "unsupported_media_type")
    return None


async def _body(request: Request, limit: int) -> dict | None:
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > limit:
            return None
        content.extend(chunk)
    try:
        parsed = json.loads(content, object_pairs_hook=_no_duplicate_json_keys)
    except (UnicodeDecodeError, ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def create_admin_pwa_webauthn_router(
    *, settings_obj: Any, session_factory: Callable | None = None,
    begin_service: Callable = begin_passkey_registration,
    complete_service: Callable = complete_passkey_registration,
) -> APIRouter:
    router = APIRouter(tags=["admin-pwa-webauthn"])

    @router.post("/api/admin/v1/auth/passkey/register/options")
    async def registration_options(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        token = request.cookies.get(_ENROLL_COOKIE, "")
        proof = request.cookies.get(_APPROVAL_COOKIE, "")
        if not token or not proof:
            return _reply(401, "admin_pwa_enrollment_invalid")
        body = await _body(request, 32)
        if body is None or body:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await begin_service(
                    db, token=token, browser_proof=proof,
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin PWA WebAuthn options unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if result is None:
            return _reply(409, "admin_pwa_enrollment_invalid")
        return JSONResponse(
            content={"ok": True, "publicKey": result.options,
                     "expires_at": result.expires_at.isoformat()},
            headers=_PRIVATE_HEADERS,
        )

    @router.post("/api/admin/v1/auth/passkey/register/verify")
    async def registration_verify(request: Request):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        token = request.cookies.get(_ENROLL_COOKIE, "")
        proof = request.cookies.get(_APPROVAL_COOKIE, "")
        if not token or not proof:
            return _reply(401, "admin_pwa_enrollment_invalid")
        body = await _body(request, _MAX_ATTESTATION_BODY)
        if body is None or set(body) != {"credential"} or not isinstance(body["credential"], dict):
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                verified = await complete_service(
                    db, token=token, browser_proof=proof,
                    credential=body["credential"], settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin PWA WebAuthn verification unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if not verified:
            return _reply(409, "admin_pwa_enrollment_invalid")
        # Grant is consumed by the service. Clear both temporary cookies.
        # No normal admin login cookie is issued until a separately verified
        # passkey authentication ceremony is implemented.
        response = JSONResponse(
            content={"ok": True, "status": "passkey_registered",
                     "next": "passkey_sign_in"},
            headers=_PRIVATE_HEADERS,
        )
        _drop_cookie(response, _ENROLL_COOKIE)
        _drop_cookie(response, _APPROVAL_COOKIE)
        return response

    return router
