"""Isolated Admin PWA routes. Feature flag remains off by default.

Existing Telegram admin endpoints continue to authenticate via initData. These
routes ONLY trust a future browser session issued after verified onboarding.
"""

import logging
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session


logger = logging.getLogger(__name__)
_PRIVATE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


def _valid_pwa_origin(value: str) -> bool:
    try:
        parsed = urlsplit(str(value or ""))
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.netloc == parsed.hostname
            and parsed.path == ""
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def create_admin_pwa_bootstrap_router(*, settings_obj: Any, session_factory: Callable | None = None) -> APIRouter:
    """Register browser-only routes without granting Telegram/bearer privileges.

    No route here can issue a login session. Google/TG binding and WebAuthn
    must be verified before login credentials can ever be minted.
    """
    router = APIRouter(tags=["admin-pwa-bootstrap"])

    def response(code: int, error: str) -> JSONResponse:
        return JSONResponse(status_code=code, content={"ok": False, "error": error}, headers=_PRIVATE_HEADERS)

    def gate(request: Request) -> JSONResponse | None:
        if not bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False)):
            return response(404, "not_found")
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
        if not _valid_pwa_origin(origin):
            return response(503, "admin_pwa_origin_unconfigured")
        # A browser may not authenticate from the non-canonical Railway host or
        # plain HTTP. The deployment's trusted proxy must expose HTTPS scope.
        request_origin = f"{request.url.scheme}://{request.url.netloc}"
        if request_origin != origin:
            return response(403, "admin_pwa_wrong_origin")
        return None

    @router.get("/admin", include_in_schema=False)
    async def admin_pwa_entry(request: Request):
        error = gate(request)
        return error if error is not None else response(503, "admin_pwa_auth_not_ready")

    @router.get("/api/admin/v1/me")
    async def admin_pwa_me(request: Request):
        error = gate(request)
        if error is not None:
            return error
        if session_factory is None:
            return response(503, "admin_pwa_auth_not_ready")
        # HttpOnly __Host- cookie is issued *only* by a separate approved login
        # completion flow. Never read a user_id or initData header as proof.
        token = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not token:
            return response(401, "admin_pwa_unauthorized")
        try:
            async with session_factory() as db:
                actor = await authenticate_admin_pwa_session(db, token, settings_obj)
        except Exception:
            logger.exception("Admin PWA cookie verification unavailable")
            return response(503, "admin_pwa_auth_unavailable")
        if actor is None:
            return response(401, "admin_pwa_unauthorized")
        return JSONResponse(
            content={"ok": True, "user_id": actor.user_id, "auth_method": actor.auth_method},
            headers=_PRIVATE_HEADERS,
        )

    return router
