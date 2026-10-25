"""Fail-closed Google OIDC HTTP transport for HSK AI Admin PWA.

This only moves verified Google identity into a pending Telegram approval.
It never links a user, issues an admin cookie or opens admin data endpoints.
"""

import logging
import re
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.admin_api.pwa_oidc import (
    AdminPwaOidcError,
    finish_admin_pwa_google,
    start_admin_pwa_google,
)
from app.admin_api.pwa_bootstrap import _valid_pwa_origin
from app.admin_api.pwa_bot_approval import read_browser_pwa_approval
from app.services.oidc_verifier import OidcVerificationError

logger = logging.getLogger(__name__)

# __Host- cookies MUST remain Secure, host-only and Path=/.
_OIDC_COOKIE = "__Host-hskai_admin_oidc"
_APPROVAL_COOKIE = "__Host-hskai_admin_approval"
_REQUEST_COOKIE = "__Host-hskai_admin_request"
_BOT_USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
_PRIVATE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Vary": "Cookie, Origin",
}


def _reply(code: int, error: str) -> JSONResponse:
    return JSONResponse(
        status_code=code, content={"ok": False, "error": error}, headers=_PRIVATE_HEADERS,
    )


def _set_secret_cookie(response: JSONResponse, name: str, value: str, ttl: int) -> None:
    response.set_cookie(
        key=name, value=value, max_age=ttl,
        httponly=True, secure=True, samesite="lax", path="/",
    )


def _drop_cookie(response: JSONResponse, name: str) -> None:
    response.delete_cookie(
        key=name, path="/", secure=True, httponly=True, samesite="lax",
    )


def _gate(request: Request, settings_obj: Any) -> JSONResponse | None:
    if not bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False)):
        return _reply(404, "not_found")
    origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
    if not _valid_pwa_origin(origin):
        return _reply(503, "admin_pwa_origin_unconfigured")
    # Trusted reverse proxy must expose the actual HTTPS scope. Untrusted
    # X-Forwarded-* supplied by a browser must never override this decision.
    request_origin = f"{request.url.scheme}://{request.url.netloc}"
    if request_origin != origin:
        return _reply(403, "admin_pwa_wrong_origin")
    return None


def _approval_bot_url(settings_obj: Any, request_id: str) -> str | None:
    """Use only the configured Bot identity and the existing non-secret request UUID."""
    username = str(getattr(settings_obj, "BOT_USERNAME", "") or "").strip().lstrip("@")
    if not _BOT_USERNAME.fullmatch(username):
        return None
    return f"https://t.me/{username}?start=admin_pwa_{request_id}"


def create_admin_pwa_google_router(
    *,
    settings_obj: Any,
    session_factory: Callable | None = None,
    start_service: Callable = start_admin_pwa_google,
    finish_service: Callable = finish_admin_pwa_google,
) -> APIRouter:
    """Separate browser-only routes; no session issuer or Telegram bypass."""
    router = APIRouter(tags=["admin-pwa-google"])

    @router.post("/api/admin/v1/auth/google/start")
    async def google_start(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN"))
        # Explicit Origin + JSON and Fetch Metadata refuse cross-site forms,
        # missing Origin and credentialed cross-site browser requests.
        origins = request.headers.getlist("origin")
        if len(origins) != 1 or origins[0] != origin:
            return _reply(403, "admin_pwa_csrf")
        if request.headers.get("sec-fetch-site", "same-origin") != "same-origin":
            return _reply(403, "admin_pwa_csrf")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return _reply(415, "unsupported_media_type")
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        try:
            async with session_factory() as db:
                started = await start_service(db, settings_obj=settings_obj)
        except AdminPwaOidcError as exc:
            if str(exc) == "rate_limited":
                return _reply(429, "admin_pwa_rate_limited")
            logger.warning("Admin PWA Google auth unavailable: %s", exc)
            return _reply(503, "admin_pwa_auth_unavailable")
        except Exception:
            logger.exception("Admin PWA Google OAuth start failed")
            return _reply(503, "admin_pwa_auth_unavailable")
        # Only the authorization URL is browser-JS-visible. The proof stays
        # exclusively in a Secure HttpOnly host-only cookie.
        response = JSONResponse(
            content={"ok": True, "authorize_url": started.authorize_url},
            headers=_PRIVATE_HEADERS,
        )
        _set_secret_cookie(response, _OIDC_COOKIE, started.browser_proof, 600)
        _drop_cookie(response, _APPROVAL_COOKIE)
        _drop_cookie(response, _REQUEST_COOKIE)
        return response

    @router.get(
        "/api/admin/v1/auth/google/callback", include_in_schema=False,
    )
    async def google_callback(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        # Google's top-level cross-site navigation preserves SameSite=Lax.
        # Subresource fetches are not a valid OAuth callback transport.
        fetch_mode = request.headers.get("sec-fetch-mode")
        if fetch_mode and fetch_mode != "navigate":
            return _reply(403, "admin_pwa_invalid_navigation")
        fetch_dest = request.headers.get("sec-fetch-dest")
        if fetch_dest and fetch_dest != "document":
            return _reply(403, "admin_pwa_invalid_navigation")
        state = request.query_params.getlist("state")
        code = request.query_params.getlist("code")
        error = request.query_params.getlist("error")
        proof = request.cookies.get(_OIDC_COOKIE, "")
        if session_factory is None:
            return _reply(503, "admin_pwa_auth_not_ready")
        if len(state) != 1 or len(code) != 1 or error or not proof:
            response = _reply(400, "admin_pwa_oauth_invalid")
            _drop_cookie(response, _OIDC_COOKIE)
            return response
        try:
            async with session_factory() as db:
                pending = await finish_service(
                    db, settings_obj=settings_obj,
                    state=state[0], code=code[0], browser_proof=proof,
                )
        except (AdminPwaOidcError, OidcVerificationError):
            pending = None
        except Exception:
            # Provider messages must never leak into client-visible errors.
            logger.exception("Admin PWA Google OAuth callback failed")
            return _reply(503, "admin_pwa_auth_unavailable")
        if pending is None:
            response = _reply(400, "admin_pwa_oauth_invalid")
            _drop_cookie(response, _OIDC_COOKIE)
            return response
        response = JSONResponse(
            content={
                "ok": True,
                "status": "telegram_approval_pending",
                "request_id": pending.request_id,
            },
            headers=_PRIVATE_HEADERS,
        )
        if "text/html" in request.headers.get("accept", ""):
            # Fixed local destination, no OAuth code/state/proof in the URL.
            # This is only a browser transport after the SAME verified flow.
            response = RedirectResponse("/admin/", status_code=303, headers=_PRIVATE_HEADERS)
        _drop_cookie(response, _OIDC_COOKIE)
        _set_secret_cookie(response, _APPROVAL_COOKIE, pending.browser_proof, 300)
        _set_secret_cookie(response, _REQUEST_COOKIE, pending.request_id, 300)
        return response

    @router.get("/api/admin/v1/auth/telegram/status")
    async def telegram_approval_status(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        if request.headers.get("sec-fetch-site", "same-origin") != "same-origin":
            return _reply(403, "admin_pwa_csrf")
        identifiers = request.query_params.getlist("request_id")
        if not identifiers and request.cookies.get(_REQUEST_COOKIE):
            identifiers = [request.cookies[_REQUEST_COOKIE]]
        if len(identifiers) != 1 or session_factory is None:
            return _reply(400, "admin_pwa_approval_invalid")
        browser_proof = request.cookies.get(_APPROVAL_COOKIE, "")
        if not browser_proof:
            return _reply(401, "admin_pwa_approval_invalid")
        try:
            async with session_factory() as db:
                result = await read_browser_pwa_approval(
                    db,
                    request_id=identifiers[0],
                    browser_proof=browser_proof,
                    settings_obj=settings_obj,
                )
        except Exception:
            logger.exception("Admin PWA Telegram approval status unavailable")
            return _reply(503, "admin_pwa_auth_unavailable")
        if result is None:
            return _reply(404, "admin_pwa_approval_invalid")
        return JSONResponse(content={
            "ok": True,
            "request_id": identifiers[0],
            "status": result.status,
            "pairing_code": result.pairing_code,
            "telegram_url": _approval_bot_url(settings_obj, identifiers[0]) if result.status == "pending" else None,
            "expires_at": result.expires_at.isoformat(),
        }, headers=_PRIVATE_HEADERS)

    return router
