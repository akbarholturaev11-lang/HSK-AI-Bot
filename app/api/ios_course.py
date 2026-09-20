"""Bearer-authenticated onboarding transport for the native iOS client.

This module owns no learning rules. It validates the iOS request shape and
delegates to AndroidCourseService, which is already the shared native adapter
over CourseMiniAppOnboardingService and the canonical course/profile state.
"""

from __future__ import annotations

import logging
from typing import Callable, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.desktop_course import (
    bearer_access_token,
    course_error_response,
    validated_course_payload,
)
from app.services.android_course_service import AndroidCourseService
from app.services.desktop_auth_service import DesktopAuthError
from app.services.desktop_course_service import DesktopCourseError


logger = logging.getLogger(__name__)
MIN_TZ_OFFSET_MINUTES = -720
MAX_TZ_OFFSET_MINUTES = 840


class IOSOnboardingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["beginner", "hsk1", "hsk2", "hsk3", "hsk4"]
    goal: Literal[
        "hsk_exam",
        "study_china",
        "work_china",
        "daily_communication",
        "travel",
    ]
    daily_minutes: Literal[5, 10, 15, 20, 30] = 10
    start_mode: Literal["lesson_1", "continue", "placement"] = "lesson_1"
    language: Literal["uz", "ru", "tj"] | None = None
    timezone_offset_minutes: int = Field(
        default=0,
        ge=MIN_TZ_OFFSET_MINUTES,
        le=MAX_TZ_OFFSET_MINUTES,
    )
    activation_variant: str | None = Field(default="direct_start_v1", max_length=32)


def _unavailable() -> JSONResponse:
    return course_error_response(
        DesktopCourseError("ios_course_unavailable", status_code=503)
    )


def create_ios_course_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., AndroidCourseService] = AndroidCourseService,
) -> APIRouter:
    router = APIRouter(tags=["ios-course"])

    @router.get("/api/v3/ios/course/onboarding")
    async def ios_onboarding_status(request: Request):
        try:
            if request.query_params:
                raise DesktopCourseError("ios_request_invalid", status_code=422)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).onboarding_status(
                    bearer_access_token(request)
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS onboarding status failed")
            return _unavailable()

    @router.post("/api/v3/ios/course/onboarding")
    async def ios_onboarding_complete(request: Request):
        try:
            payload = await validated_course_payload(request, IOSOnboardingRequest)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).complete_onboarding(
                    bearer_access_token(request),
                    level=payload.level,
                    goal=payload.goal,
                    daily_minutes=payload.daily_minutes,
                    start_mode=payload.start_mode,
                    language=payload.language,
                    timezone_offset_minutes=payload.timezone_offset_minutes,
                    activation_variant=payload.activation_variant,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS onboarding completion failed")
            return _unavailable()

    return router
