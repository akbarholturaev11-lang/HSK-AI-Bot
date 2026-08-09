import logging
from typing import Annotated, Any, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from app.services.desktop_download_service import (
    DesktopDownloadError,
    DesktopDownloadService,
    DesktopReleaseConfig,
)
from app.services.desktop_release_manifest_service import (
    DesktopReleaseManifestService,
)
from app.services.telegram_webapp_auth import extract_fresh_verified_webapp_user_id


logger = logging.getLogger(__name__)
MAX_DESKTOP_DOWNLOAD_BODY_BYTES = 2048
PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

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
    transport: Literal["download_file", "open_link", "web_share", "copy_link"]


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
) -> PayloadModel:
    """Read desktop download JSON through a strict application body bound."""

    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise DesktopDownloadError(
            "desktop_download_request_invalid",
            status_code=415,
        )

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            if int(content_length) > MAX_DESKTOP_DOWNLOAD_BODY_BYTES:
                raise DesktopDownloadError(
                    "desktop_download_request_too_large",
                    status_code=413,
                )
        except ValueError as exc:
            raise DesktopDownloadError(
                "desktop_download_request_invalid",
                status_code=400,
            ) from exc

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_DESKTOP_DOWNLOAD_BODY_BYTES:
            raise DesktopDownloadError(
                "desktop_download_request_too_large",
                status_code=413,
            )
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise DesktopDownloadError(
            "desktop_download_request_invalid",
            status_code=422,
        ) from exc


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
    release_manifest_service: DesktopReleaseManifestService | None = None,
) -> APIRouter:
    router = APIRouter(tags=["desktop-download"])
    release_manifest_service = (
        release_manifest_service
        or DesktopReleaseManifestService(settings_obj)
    )

    def make_service(session) -> DesktopDownloadService:
        if service_factory is DesktopDownloadService:
            return service_factory(
                session,
                settings_obj,
                release_manifest_service=release_manifest_service,
            )
        return service_factory(session, settings_obj)

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
                payload = await make_service(session).status(telegram_id)
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
        releases = await DesktopReleaseConfig.resolve(
            settings_obj,
            release_manifest_service=release_manifest_service,
        )
        payload = releases.public_status_payload()
        return JSONResponse(
            content=payload,
            headers={"Cache-Control": "public, max-age=60"},
        )

    @router.post("/api/v3/desktop-download/request")
    async def desktop_download_request(request: Request):
        telegram_id = _auth_user_id(request, settings_obj)
        if not telegram_id:
            return unauthorized()
        try:
            payload = await _validated_payload(request, DesktopDownloadRequest)
            async with session_factory() as session:
                result = await make_service(session).request_download(
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
    async def desktop_download_started(request: Request):
        telegram_id = _auth_user_id(request, settings_obj)
        if not telegram_id:
            return unauthorized()
        try:
            payload = await _validated_payload(
                request,
                DesktopDownloadStartedRequest,
            )
            async with session_factory() as session:
                result = await make_service(session).mark_started(
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
                target, file_name = await make_service(session).resolve_redirect(
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
