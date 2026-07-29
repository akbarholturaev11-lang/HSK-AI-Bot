import logging
from typing import Annotated, Any, Callable, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.services.desktop_download_service import (
    DesktopDownloadError,
    DesktopDownloadService,
    DesktopReleaseConfig,
)
from app.services.telegram_webapp_auth import extract_fresh_verified_webapp_user_id


logger = logging.getLogger(__name__)

DesktopEventId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=16,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$",
    ),
]


class DesktopDownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["macos", "windows"]
    source: Literal["profile", "home_prompt", "lesson_end_promo", "ad_promo"]
    event_id: DesktopEventId
    language: Literal["uz", "ru", "tj"] | None = None


class DesktopDownloadStartedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["macos", "windows"]
    source: Literal["profile", "home_prompt", "lesson_end_promo", "ad_promo"]
    event_id: DesktopEventId
    transport: Literal["download_file", "open_link"]


def _auth_user_id(request: Request, settings_obj: Any) -> int | None:
    return extract_fresh_verified_webapp_user_id(
        request.headers.get("X-Telegram-Init-Data", ""),
        str(getattr(settings_obj, "BOT_TOKEN", "") or ""),
        max_age_seconds=int(
            getattr(settings_obj, "DESKTOP_DOWNLOAD_AUTH_MAX_AGE_SECONDS", 86400)
        ),
    )


def _error_response(error: DesktopDownloadError) -> JSONResponse:
    content: dict[str, Any] = {"ok": False, "error": error.code}
    if error.platform:
        content["platform"] = error.platform
    if error.retry_after_seconds is not None:
        content["retry_after_seconds"] = error.retry_after_seconds
    headers = {"Cache-Control": "no-store"}
    if error.retry_after_seconds is not None:
        headers["Retry-After"] = str(error.retry_after_seconds)
    return JSONResponse(status_code=error.status_code, content=content, headers=headers)


def create_desktop_download_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., DesktopDownloadService] = DesktopDownloadService,
) -> APIRouter:
    router = APIRouter(tags=["desktop-download"])

    def unauthorized() -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "invalid_telegram_init_data"},
            headers={"Cache-Control": "no-store"},
        )

    @router.get("/api/v3/desktop-download/status")
    async def desktop_download_status(request: Request):
        telegram_id = _auth_user_id(request, settings_obj)
        if not telegram_id:
            return unauthorized()
        try:
            async with session_factory() as session:
                payload = await service_factory(session, settings_obj).status(telegram_id)
            return JSONResponse(content=payload, headers={"Cache-Control": "no-store"})
        except DesktopDownloadError as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop download status failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "desktop_download_temporarily_unavailable"},
                headers={"Cache-Control": "no-store"},
            )

    @router.get("/api/v3/desktop-download/public-status")
    async def desktop_download_public_status():
        payload = DesktopReleaseConfig.from_settings(
            settings_obj
        ).public_status_payload()
        return JSONResponse(
            content=payload,
            headers={"Cache-Control": "public, max-age=60"},
        )

    @router.post("/api/v3/desktop-download/request")
    async def desktop_download_request(
        request: Request,
        payload: DesktopDownloadRequest,
    ):
        telegram_id = _auth_user_id(request, settings_obj)
        if not telegram_id:
            return unauthorized()
        try:
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).request_download(
                    telegram_id=telegram_id,
                    platform=payload.platform,
                    source=payload.source,
                    event_id=payload.event_id,
                    language=payload.language,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopDownloadError as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop download request failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "desktop_download_temporarily_unavailable"},
                headers={"Cache-Control": "no-store"},
            )

    @router.post("/api/v3/desktop-download/started")
    async def desktop_download_started(
        request: Request,
        payload: DesktopDownloadStartedRequest,
    ):
        telegram_id = _auth_user_id(request, settings_obj)
        if not telegram_id:
            return unauthorized()
        try:
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).mark_started(
                    telegram_id=telegram_id,
                    platform=payload.platform,
                    source=payload.source,
                    event_id=payload.event_id,
                    transport=payload.transport,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopDownloadError as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop download start tracking failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "desktop_download_temporarily_unavailable"},
                headers={"Cache-Control": "no-store"},
            )

    async def _redirect(platform: str, request_token: str | None):
        try:
            async with session_factory() as session:
                target, file_name = await service_factory(
                    session, settings_obj
                ).resolve_redirect(
                    platform=platform,
                    request_token=request_token,
                )
            return RedirectResponse(
                url=target,
                status_code=307,
                headers={
                    "Cache-Control": "no-store",
                    "Referrer-Policy": "no-referrer",
                    "Content-Disposition": f'attachment; filename="{file_name}"',
                    "Access-Control-Allow-Origin": "https://web.telegram.org",
                },
            )
        except DesktopDownloadError as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop download redirect failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "desktop_download_temporarily_unavailable"},
                headers={"Cache-Control": "no-store"},
            )

    @router.get("/downloads/macos", name="desktop_download_redirect_macos")
    async def desktop_download_redirect_macos(request: str | None = None):
        return await _redirect("macos", request)

    @router.get("/downloads/windows", name="desktop_download_redirect_windows")
    async def desktop_download_redirect_windows(request: str | None = None):
        return await _redirect("windows", request)

    return router
