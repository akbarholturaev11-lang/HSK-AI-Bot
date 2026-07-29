import logging
from typing import Annotated, Any, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    ValidationError,
)

from app.services.desktop_auth_service import (
    DesktopAuthError,
    DesktopAuthService,
)


logger = logging.getLogger(__name__)
MAX_DESKTOP_AUTH_BODY_BYTES = 2048
PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

InstallationKey = Annotated[SecretStr, Field(min_length=32, max_length=200)]
AppVersion = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=40,
        pattern=r"^[A-Za-z0-9._+-]+$",
    ),
]
OpaqueSecret = Annotated[SecretStr, Field(min_length=32, max_length=512)]
LinkRequestId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=36,
        max_length=36,
        pattern=(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{12}$"
        ),
    ),
]


class DesktopLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["macos", "windows"]
    app_version: AppVersion
    installation_key: InstallationKey


class DesktopLinkStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_request_id: LinkRequestId
    polling_secret: OpaqueSecret


class DesktopRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: OpaqueSecret


class DesktopRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revoke_device: bool = False


def _access_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


def _error(error: DesktopAuthError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise DesktopAuthError("desktop_request_invalid", status_code=415)

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            if int(content_length) > MAX_DESKTOP_AUTH_BODY_BYTES:
                raise DesktopAuthError("desktop_request_too_large", status_code=413)
        except ValueError as exc:
            raise DesktopAuthError("desktop_request_invalid", status_code=400) from exc

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_DESKTOP_AUTH_BODY_BYTES:
            raise DesktopAuthError("desktop_request_too_large", status_code=413)
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise DesktopAuthError("desktop_request_invalid", status_code=422) from exc


def create_desktop_auth_router(
    *,
    session_factory,
    settings_obj: Any,
    service_factory: Callable[..., DesktopAuthService] = DesktopAuthService,
) -> APIRouter:
    router = APIRouter(tags=["desktop-auth"])

    @router.post("/api/v3/desktop-auth/link/start")
    async def desktop_link_start(request: Request):
        try:
            payload = await _validated_payload(request, DesktopLinkStartRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).start_link(
                    platform=payload.platform,
                    app_version=payload.app_version,
                    installation_key=payload.installation_key.get_secret_value(),
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except DesktopAuthError as exc:
            return _error(exc)
        except Exception:
            logger.exception("Desktop link start failed")
            return _error(
                DesktopAuthError("desktop_auth_unavailable", status_code=503)
            )

    @router.post("/api/v3/desktop-auth/link/status")
    async def desktop_link_status(request: Request):
        try:
            payload = await _validated_payload(request, DesktopLinkStatusRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).poll_link(
                    link_request_id=payload.link_request_id,
                    polling_secret=payload.polling_secret.get_secret_value(),
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except DesktopAuthError as exc:
            return _error(exc)
        except Exception:
            logger.exception("Desktop link status failed")
            return _error(
                DesktopAuthError("desktop_auth_unavailable", status_code=503)
            )

    @router.post("/api/v3/desktop-auth/refresh")
    async def desktop_refresh(request: Request):
        try:
            payload = await _validated_payload(request, DesktopRefreshRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).refresh(
                    payload.refresh_token.get_secret_value()
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except DesktopAuthError as exc:
            return _error(exc)
        except Exception:
            logger.exception("Desktop refresh failed")
            return _error(
                DesktopAuthError("desktop_auth_unavailable", status_code=503)
            )

    @router.post("/api/v3/desktop-auth/revoke")
    async def desktop_revoke(
        request: Request,
    ):
        try:
            payload = await _validated_payload(request, DesktopRevokeRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).revoke(
                    _access_token(request),
                    revoke_device=payload.revoke_device,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except DesktopAuthError as exc:
            return _error(exc)
        except Exception:
            logger.exception("Desktop revoke failed")
            return _error(
                DesktopAuthError("desktop_auth_unavailable", status_code=503)
            )

    @router.get("/api/v3/desktop/bootstrap")
    async def desktop_bootstrap(
        request: Request,
        app_version: AppVersion | None = None,
    ):
        try:
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).bootstrap(
                    _access_token(request),
                    app_version=app_version,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except DesktopAuthError as exc:
            return _error(exc)
        except Exception:
            logger.exception("Desktop bootstrap failed")
            return _error(
                DesktopAuthError("desktop_auth_unavailable", status_code=503)
            )

    return router
