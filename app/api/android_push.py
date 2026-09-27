"""Authenticated FCM token lifecycle and Android payment status fallback."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.desktop_auth import (
    auth_error_response,
    bearer_access_token,
    validated_auth_payload,
)
from app.repositories.payment_repo import PaymentRepository
from app.services.android_payment_push_service import AndroidPaymentPushService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


logger = logging.getLogger(__name__)


class AndroidPushRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=4096, pattern=r"^[^\s]+$")


def create_android_push_router(*, session_factory, settings_obj: Any) -> APIRouter:
    router = APIRouter(tags=["android-push"])

    async def context(session, request: Request):
        authenticated = await DesktopAuthService(session, settings_obj).authenticate(
            bearer_access_token(request)
        )
        if authenticated.device.platform != "android":
            raise DesktopAuthError("android_device_required", status_code=403)
        return authenticated

    @router.post("/api/v3/android/push/register")
    async def register(request: Request):
        try:
            payload = await validated_auth_payload(request, AndroidPushRegisterRequest)
            async with session_factory() as session:
                current = await context(session, request)
                await AndroidPaymentPushService(session, settings_obj).register(
                    device=current.device, token=payload.token
                )
            return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android push registration failed")
            return JSONResponse({"ok": False, "error": "android_push_unavailable"}, status_code=503)

    @router.post("/api/v3/android/push/unregister")
    async def unregister(request: Request):
        try:
            if request.query_params or await request.body():
                raise DesktopAuthError("android_request_invalid", status_code=422)
            async with session_factory() as session:
                current = await context(session, request)
                await AndroidPaymentPushService(session, settings_obj).unregister(
                    device=current.device
                )
            return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android push unregistration failed")
            return JSONResponse({"ok": False, "error": "android_push_unavailable"}, status_code=503)

    @router.get("/api/v3/android/subscription/payments/{payment_id}/status")
    async def payment_status(payment_id: int, request: Request):
        try:
            if payment_id <= 0 or request.query_params:
                raise DesktopAuthError("android_request_invalid", status_code=422)
            async with session_factory() as session:
                current = await context(session, request)
                payment = await PaymentRepository(session).get_by_id(payment_id)
                if (
                    payment is None
                    or payment.user_telegram_id != current.user.telegram_id
                ):
                    raise DesktopAuthError("payment_not_found", status_code=404)
                result = {
                    "ok": True,
                    "payment_id": payment.id,
                    "status": payment.payment_status,
                }
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android payment status failed")
            return JSONResponse({"ok": False, "error": "android_payment_unavailable"}, status_code=503)

    return router
