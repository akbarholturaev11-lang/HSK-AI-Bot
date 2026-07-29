from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from app.services.desktop_update_service import (
    DesktopUpdateError,
    DesktopUpdateService,
)


_NO_STORE_HEADERS = {"Cache-Control": "no-store"}


def _error_response(error: DesktopUpdateError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers=_NO_STORE_HEADERS,
    )


def create_desktop_update_router(*, settings_obj) -> APIRouter:
    router = APIRouter(tags=["desktop-update"])
    service = DesktopUpdateService(settings_obj)

    @router.get(
        "/api/v3/desktop/update/{target}/{arch}/{current_version}",
        response_model=None,
    )
    async def desktop_update_manifest(
        target: str,
        arch: str,
        current_version: str,
    ):
        try:
            manifest = service.manifest(
                target=target,
                arch=arch,
                current_version=current_version,
            )
        except DesktopUpdateError as exc:
            return _error_response(exc)
        except Exception:
            return _error_response(
                DesktopUpdateError(
                    "desktop_update_unavailable",
                    status_code=503,
                )
            )
        if manifest is None:
            return Response(status_code=204, headers=_NO_STORE_HEADERS)
        return JSONResponse(content=manifest, headers=_NO_STORE_HEADERS)

    return router
