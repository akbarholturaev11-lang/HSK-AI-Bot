"""Isolated Admin PWA routes. Feature flag remains off by default.

Existing Telegram admin endpoints continue to authenticate via initData. These
routes only trust a server-backed browser session issued after verified onboarding.
"""

import logging
import hashlib
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response

from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session


logger = logging.getLogger(__name__)
_ASSETS = Path(__file__).resolve().parents[1] / "static" / "admin-pwa"
_PUBLIC_ASSETS = {"app.js": "text/javascript", "styles.css": "text/css",
                  "catalog.js": "text/javascript", "mcp-consent.js": "text/javascript",
                  "mcp-consent.css": "text/css", "icon.png": "image/png", "icon-large.png": "image/png"}
_PAGE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; "
             "img-src 'self' blob:; connect-src 'self'; manifest-src 'self'; "
             "worker-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
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
        return error if error is not None else RedirectResponse("/admin/", status_code=303,
                                                               headers=_PRIVATE_HEADERS)

    @router.get("/admin/", include_in_schema=False)
    async def shell(request: Request):
        error = gate(request)
        if error is not None:
            return error
        # Identical PUBLIC shell for every browser: no actor/account/secret is
        # ever embedded. Only authenticated no-store APIs supply private data.
        return FileResponse(_ASSETS / "index.html", media_type="text/html", headers={
            **_PRIVATE_HEADERS, "Content-Security-Policy": _PAGE_CSP,
            "Referrer-Policy": "no-referrer", "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        })

    @router.get("/admin/assets/{filename}", include_in_schema=False)
    async def asset(request: Request, filename: str):
        error = gate(request)
        if error is not None:
            return error
        if filename not in _PUBLIC_ASSETS:
            return response(404, "not_found")
        return FileResponse(_ASSETS / filename, media_type=_PUBLIC_ASSETS[filename], headers={
            "Cache-Control": "public, max-age=0, must-revalidate", "X-Content-Type-Options": "nosniff",
        })

    @router.get("/admin/manifest.webmanifest", include_in_schema=False)
    async def manifest(request: Request):
        error = gate(request)
        if error is not None:
            return error
        return JSONResponse({"id": "/admin/", "name": "HSK AI Admin", "short_name": "HSK AI",
                             "start_url": "/admin/", "scope": "/admin/", "display": "standalone",
                             "background_color": "#f5f7f7", "theme_color": "#172731",
                             "icons": [{"src": "/admin/assets/icon.png", "sizes": "256x256",
                                        "type": "image/png", "purpose": "any"},
                                       {"src": "/admin/assets/icon-large.png", "sizes": "1024x1024",
                                        "type": "image/png", "purpose": "any"}]},
                            media_type="application/manifest+json", headers={"Cache-Control": "no-cache"})

    @router.get("/admin/sw.js", include_in_schema=False)
    async def service_worker(request: Request):
        error = gate(request)
        if error is not None:
            return error
        version = hashlib.sha256(b"".join((_ASSETS / name).read_bytes()
            for name in ("index.html", *_PUBLIC_ASSETS))).hexdigest()[:16]
        body = (_ASSETS / "sw.js").read_text().replace("__SHELL_VERSION__", version)
        return Response(body, media_type="text/javascript", headers={
            "Cache-Control": "no-cache", "Service-Worker-Allowed": "/admin/",
            "X-Content-Type-Options": "nosniff",
        })

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
