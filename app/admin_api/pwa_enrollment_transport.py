"""Browser-only Admin PWA Telegram approval completion.

An approved one-time challenge is atomically linked to canonical Google identity
and exchanged for a SHORT-LIVED PASSKEY ENROLLMENT GRANT, never an admin
session. The grant token is only set as a Secure HttpOnly __Host- cookie.
Nothing in this module performs or bypasses WebAuthn attestation verification.
"""
import json
import logging
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_enrollment import (
    GrantedPwaEnrollment, finalize_google_admin_enrollment,
)
from app.admin_api.pwa_google_transport import (
    _APPROVAL_COOKIE, _PRIVATE_HEADERS, _gate, _reply, _set_secret_cookie,
)

logger = logging.getLogger(__name__)

_ENROLL_COOKIE = "__Host-hskai_admin_enroll"


def _no_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def create_admin_pwa_completion_router(
    *,
    settings_obj: Any,
    session_factory: Callable | None = None,
    completion_service: Callable = finalize_google_admin_enrollment,
) -> APIRouter:
    router = APIRouter(tags=["admin-pwa-enrollment"])

    @router.post("/api/admin/v1/auth/telegram/complete")
    async def complete_telegram_approval(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", ""))
        # Only a same-origin browser POST can exchange the HttpOnly approval
        # proof for another cookie. A bot callback, GET or HTML form cannot.
        origins = request.headers.getlist("origin")
        if len(origins) != 1 or origins[0] != origin:
            return _reply(403, "admin_pwa_csrf")
        if request.headers.get("sec-fetch-site", "same-origin") != "same-origin":
            return _reply(403, "admin_pwa_csrf")
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return _reply(415, "unsupported_media_type")
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        proof = request.cookies.get(_APPROVAL_COOKIE, "")
        if not proof:
            return _reply(401, "admin_pwa_approval_invalid")
        # Bound unauthenticated request-body memory before JSON decoding.
        body = bytearray()
        async for part in request.stream():
            if len(body) + len(part) > 256:
                return _reply(413, "admin_pwa_invalid_payload")
            body.extend(part)
        try:
            payload = json.loads(body, object_pairs_hook=_no_duplicate_json_keys)
        except (UnicodeDecodeError, ValueError, TypeError):
            return _reply(400, "admin_pwa_invalid_payload")
        if (not isinstance(payload, dict) or set(payload) != {"request_id"}
                or not isinstance(payload["request_id"], str)):
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                completed = await completion_service(
                    db, request_id=payload["request_id"],
                    browser_proof=proof, settings_obj=settings_obj,
                    issue_passkey_grant=True,
                )
        except Exception:
            logger.exception("Admin PWA passkey enrollment grant issuance unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if not isinstance(completed, GrantedPwaEnrollment):
            return _reply(409, "admin_pwa_approval_invalid")

        # The approval proof is intentionally retained: passkey registration
        # MUST verify both cookies against the linked canonical User.
        response = JSONResponse(content={
            "ok": True,
            "next": "passkey_enrollment",
            "expires_at": completed.grant.expires_at.isoformat(),
        }, headers=_PRIVATE_HEADERS)
        _set_secret_cookie(response, _ENROLL_COOKIE, completed.grant.token, 180)
        # Refresh the *same* browser-bound approval proof for the enrollment
        # window. Otherwise a Bot approval at T+4:59 leaves the fresh grant
        # unable to satisfy its mandatory second-cookie proof at T+5:00.
        # No additional proof is generated or made JS-readable.
        _set_secret_cookie(response, _APPROVAL_COOKIE, proof, 180)
        return response

    return router
