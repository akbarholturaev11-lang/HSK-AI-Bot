"""Small, bearer-bound Android widget telemetry surface; no client user IDs."""

import logging
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.desktop_auth import (
    LinkRequestId,
    auth_error_response,
    bearer_access_token,
    validated_auth_payload,
)
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService

logger = logging.getLogger(__name__)


class AndroidEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_name: Literal[
        "android_widget_onboarding_viewed",
        "android_widget_pin_requested",
        "android_widget_pinned",
        "android_widget_opened",
        "android_notification_opened",
    ]
    event_id: LinkRequestId


def create_android_events_router(*, session_factory, settings_obj) -> APIRouter:
    router = APIRouter(tags=["android-events"])

    @router.post("/api/v3/android/events")
    async def android_event(request: Request):
        try:
            payload = await validated_auth_payload(request, AndroidEventRequest)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(
                    access_token=bearer_access_token(request),
                )
                if context.device.platform != "android":
                    raise DesktopAuthError("android_device_required", status_code=403)
                result = await CourseMiniAppAnalyticsService(session).record_server_event(
                    event_name=payload.event_name,
                    telegram_id=context.user.telegram_id,
                    user_id=context.user.id,
                    source="android_native",
                    level=context.user.level,
                    dedupe_key=f"android:{context.device.id}:{payload.event_id}",
                )
                if result.get("ok"):
                    await session.commit()
            return JSONResponse(
                content=result,
                status_code=200 if result.get("ok") else 503,
                headers={"Cache-Control": "no-store"},
            )
        except DesktopAuthError as exc:
            return auth_error_response(exc)
        except Exception:
            logger.exception("Android event write failed")
            return auth_error_response(DesktopAuthError("android_events_unavailable", status_code=503))

    return router
