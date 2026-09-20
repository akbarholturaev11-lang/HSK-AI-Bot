"""Bearer-authenticated device-link adapter for the native iOS client.

This is transport only. Cryptography, device binding, refresh rotation,
rate-limiting and session rules stay in the shared DesktopAuthService.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.desktop_auth import (
    AppVersion,
    InstallationKey,
    LinkRequestId,
    OpaqueSecret,
    auth_error_response,
    bearer_access_token,
    validated_auth_payload,
)
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


logger = logging.getLogger(__name__)
IOS_PLATFORM = "ios"


class IOSLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["ios"] = IOS_PLATFORM
    app_version: AppVersion
    installation_key: InstallationKey


class IOSLinkStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_request_id: LinkRequestId
    polling_secret: OpaqueSecret


class IOSRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: OpaqueSecret


class IOSRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revoke_device: bool = False


def _unavailable() -> JSONResponse:
    return auth_error_response(DesktopAuthError("ios_auth_unavailable", status_code=503))


def create_ios_auth_router(
    *,
    session_factory,
    settings_obj: Any,
    service_factory: Callable[..., DesktopAuthService] = DesktopAuthService,
) -> APIRouter:
    router = APIRouter(tags=["ios-auth"])

    @router.post("/api/v3/ios-auth/link/start")
    async def ios_link_start(request: Request):
        try:
            payload = await validated_auth_payload(request, IOSLinkStartRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).start_link(
                    platform=IOS_PLATFORM,
                    app_version=payload.app_version,
                    installation_key=payload.installation_key.get_secret_value(),
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("iOS link start failed")
            return _unavailable()

    @router.post("/api/v3/ios-auth/link/status")
    async def ios_link_status(request: Request):
        try:
            payload = await validated_auth_payload(request, IOSLinkStatusRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).poll_link(
                    link_request_id=payload.link_request_id,
                    polling_secret=payload.polling_secret.get_secret_value(),
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("iOS link status failed")
            return _unavailable()

    @router.post("/api/v3/ios-auth/refresh")
    async def ios_refresh(request: Request):
        try:
            payload = await validated_auth_payload(request, IOSRefreshRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).refresh(
                    payload.refresh_token.get_secret_value()
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("iOS refresh failed")
            return _unavailable()

    @router.post("/api/v3/ios-auth/revoke")
    async def ios_revoke(request: Request):
        try:
            payload = await validated_auth_payload(request, IOSRevokeRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).revoke(
                    bearer_access_token(request),
                    revoke_device=payload.revoke_device,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("iOS revoke failed")
            return _unavailable()

    @router.get("/api/v3/ios/bootstrap")
    async def ios_bootstrap(request: Request, app_version: AppVersion | None = None):
        try:
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).bootstrap(
                    bearer_access_token(request),
                    app_version=app_version,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("iOS bootstrap failed")
            return _unavailable()

    return router
