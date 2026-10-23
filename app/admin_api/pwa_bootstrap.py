"""Fail-closed Admin PWA route reservation, not an authentication implementation.

Only a deliberately enabled, explicitly HTTPS-configured installation may return
an 'auth not ready' response. This module deliberately never accepts Telegram
initData, browser headers, or user-supplied IDs as an admin proof. Existing
Telegram Admin Mini App endpoints are not touched.
"""

from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter
from fastapi.responses import JSONResponse


_PRIVATE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


def _valid_pwa_origin(value: str) -> bool:
    """Only a bare, explicit HTTPS origin can enable privileged routes."""
    try:
        parsed = urlsplit(str(value or ""))
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.netloc == parsed.hostname  # no auth, port or mixed case
            and parsed.path == ""
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:  # invalid port/URL authority
        return False


def create_admin_pwa_bootstrap_router(*, settings_obj: Any) -> APIRouter:
    """Reserve new routes while leaving Google/TG and passkey auth CLOSED.

    Do not replace the 503 responses until the server has implemented and
    tested real Google+Telegram enrollment, WebAuthn verification, and session
    authentication. Returning a 200 here would imply an unsafe login exists.
    """

    router = APIRouter(tags=["admin-pwa-bootstrap"])

    def blocked_response() -> JSONResponse:
        enabled = bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False))
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
        if not enabled:
            return JSONResponse(
                status_code=404,
                content={"ok": False, "error": "not_found"},
                headers=_PRIVATE_HEADERS,
            )
        if not _valid_pwa_origin(origin):
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "admin_pwa_origin_unconfigured"},
                headers=_PRIVATE_HEADERS,
            )
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "admin_pwa_auth_not_ready"},
            headers=_PRIVATE_HEADERS,
        )

    @router.get("/admin", include_in_schema=False)
    async def admin_pwa_entry():
        return blocked_response()

    @router.get("/api/admin/v1/me")
    async def admin_pwa_me():
        # Fail-closed; neither a forged cookie nor Telegram initData may pass.
        return blocked_response()

    return router
