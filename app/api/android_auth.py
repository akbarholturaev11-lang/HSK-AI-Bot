"""Bearer-authenticated device-link adapter for the native Android client.

This module is a thin transport layer only. Every cryptographic, session,
device-binding and rate-limiting decision stays inside the shared
``DesktopAuthService``; nothing security-relevant is duplicated here.

The Android link flow keeps the exact security properties of the desktop flow:
the 8-character display code is never placed in the Telegram deep link, the
user types it manually in the private bot chat, approval is explicit, the code
is single-use, and refresh tokens rotate with reuse detection.
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

ANDROID_PLATFORM = "android"


class AndroidLinkStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["android"] = ANDROID_PLATFORM
    app_version: AppVersion
    installation_key: InstallationKey


class AndroidLinkStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_request_id: LinkRequestId
    polling_secret: OpaqueSecret


class AndroidRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: OpaqueSecret


class AndroidRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revoke_device: bool = False


def _unavailable() -> JSONResponse:
    return auth_error_response(
        DesktopAuthError("android_auth_unavailable", status_code=503)
    )


def create_android_auth_router(
    *,
    session_factory,
    settings_obj: Any,
    service_factory: Callable[..., DesktopAuthService] = DesktopAuthService,
) -> APIRouter:
    router = APIRouter(tags=["android-auth"])

    @router.post("/api/v3/android-auth/link/start")
    async def android_link_start(request: Request):
        try:
            payload = await validated_auth_payload(request, AndroidLinkStartRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).start_link(
                    platform=ANDROID_PLATFORM,
                    app_version=payload.app_version,
                    installation_key=payload.installation_key.get_secret_value(),
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android link start failed")
            return _unavailable()

    @router.post("/api/v3/android-auth/link/status")
    async def android_link_status(request: Request):
        try:
            payload = await validated_auth_payload(request, AndroidLinkStatusRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).poll_link(
                    link_request_id=payload.link_request_id,
                    polling_secret=payload.polling_secret.get_secret_value(),
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android link status failed")
            return _unavailable()

    @router.post("/api/v3/android-auth/refresh")
    async def android_refresh(request: Request):
        try:
            payload = await validated_auth_payload(request, AndroidRefreshRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).refresh(
                    payload.refresh_token.get_secret_value()
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android refresh failed")
            return _unavailable()

    @router.post("/api/v3/android-auth/revoke")
    async def android_revoke(request: Request):
        try:
            payload = await validated_auth_payload(request, AndroidRevokeRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).revoke(
                    bearer_access_token(request),
                    revoke_device=payload.revoke_device,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android revoke failed")
            return _unavailable()

    @router.get("/api/v3/android/bootstrap")
    async def android_bootstrap(
        request: Request,
        app_version: AppVersion | None = None,
    ):
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
            logger.exception("Android bootstrap failed")
            return _unavailable()

    return router
