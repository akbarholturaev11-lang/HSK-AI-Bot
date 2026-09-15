"""One status for every installable client.

Read by the download page's JavaScript, and by the page's own server-side
render so that the version and the links are in the HTML before any script
runs — which is what a search or AI crawler sees.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.app_downloads_service import app_download_status


logger = logging.getLogger(__name__)


def create_app_downloads_router(*, session_factory, settings_obj) -> APIRouter:
    router = APIRouter(tags=["app-downloads"])

    @router.get("/api/v3/apps/public-status")
    async def apps_public_status():
        try:
            payload = await app_download_status(
                session_factory=session_factory,
                settings_obj=settings_obj,
            )
        except Exception:
            logger.exception("App download status failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "app_downloads_unavailable"},
                headers={"Cache-Control": "no-store"},
            )
        # Short and public: the page is static for everyone, and a release is
        # not so urgent that a minute of cache costs anything.
        return JSONResponse(content=payload, headers={"Cache-Control": "public, max-age=60"})

    return router
