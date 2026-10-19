"""Install-only PWA resources; no browser authentication or learner data routes.

Keep this router deliberately independent of database, payment and Telegram
logic.  The shared course page is still served by app/main.py.
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}


def create_pwa_router() -> APIRouter:
    router = APIRouter(tags=["pwa-install"])

    @router.get("/pwa.webmanifest", include_in_schema=False)
    async def pwa_manifest():
        return FileResponse(
            STATIC_DIR / "pwa.webmanifest",
            media_type="application/manifest+json",
            headers=NO_CACHE,
        )

    @router.get("/pwa-bootstrap.js", include_in_schema=False)
    async def pwa_bootstrap():
        return FileResponse(
            STATIC_DIR / "pwa-bootstrap.js",
            media_type="application/javascript",
            headers=NO_CACHE,
        )

    @router.get("/pwa-sw.js", include_in_schema=False)
    async def pwa_service_worker():
        return FileResponse(
            STATIC_DIR / "pwa-sw.js",
            media_type="application/javascript",
            headers={**NO_CACHE, "Service-Worker-Allowed": "/"},
        )

    return router
