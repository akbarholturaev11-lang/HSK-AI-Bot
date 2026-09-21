"""Bearer-authenticated Course v3 transport for the native iOS client.

This module owns transport only. Foundation, lesson access, XP, streak,
mistakes and completion idempotency remain in the shared native course service.
"""

from __future__ import annotations

import logging
from typing import Callable, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.desktop_course import (
    DesktopCourseCompleteRequest,
    bearer_access_token,
    course_error_response,
    validated_course_payload,
)
from app.services.android_course_service import AndroidCourseService
from app.services.desktop_auth_service import DesktopAuthError
from app.services.desktop_course_service import DesktopCourseError
from app.repositories.user_repo import UserRepository
from app.services.course_v3_dictionary import dictionary_for_language, dictionary_version
from app.services.desktop_auth_service import DesktopAuthService


logger = logging.getLogger(__name__)
MIN_TZ_OFFSET_MINUTES = -720
MAX_TZ_OFFSET_MINUTES = 840
MIN_LESSON_ORDER = 1
MAX_LESSON_ORDER = 500


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


class IOSStudyPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: Literal["hsk_exam", "study_china", "work_china", "daily_communication", "travel"] | None = None
    daily_minutes: Literal[5, 10, 15, 20, 30] | None = None
    daily_goal_xp: int | None = Field(default=None, ge=10, le=500)
    preferred_focus: Literal["speaking", "listening", "vocabulary", "grammar", "none"] | None = None


class IOSFoundationCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    foundation_id: Literal["starter0_hsk1"]
    foundation_version: Literal[1]
    speaking_bonus: bool = False
    event_id: str = Field(min_length=1, max_length=120)


class IOSCourseCompleteRequest(DesktopCourseCompleteRequest):
    access_ref: str = Field(default="", max_length=160)


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

    @router.get("/api/v3/ios/course/map")
    async def ios_course_map(request: Request):
        try:
            raw_offset = request.query_params.get("tz")
            offset: int | None = None
            if raw_offset is not None:
                try:
                    offset = int(raw_offset)
                except (TypeError, ValueError) as exc:
                    raise DesktopCourseError("ios_request_invalid", status_code=422) from exc
                if not MIN_TZ_OFFSET_MINUTES <= offset <= MAX_TZ_OFFSET_MINUTES:
                    raise DesktopCourseError("ios_request_invalid", status_code=422)

            async with session_factory() as session:
                result = await service_factory(session, settings_obj).course_map(
                    bearer_access_token(request),
                    timezone_offset_minutes=offset,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS course map failed")
            return _unavailable()

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

    @router.post("/api/v3/ios/preferences/study")
    async def ios_study_preferences(request: Request):
        try:
            payload = await validated_course_payload(request, IOSStudyPreferencesRequest)
            if all(value is None for value in (
                payload.goal, payload.daily_minutes, payload.daily_goal_xp, payload.preferred_focus
            )):
                raise DesktopCourseError("ios_request_invalid", status_code=422)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).set_study_preferences(
                    bearer_access_token(request),
                    goal=payload.goal,
                    daily_minutes=payload.daily_minutes,
                    preferred_focus=payload.preferred_focus,
                    daily_goal_xp=payload.daily_goal_xp,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS study preferences update failed")
            return _unavailable()

    @router.get("/api/v3/ios/course/foundation")
    async def ios_foundation(request: Request):
        try:
            if request.query_params:
                raise DesktopCourseError("ios_request_invalid", status_code=422)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).foundation(
                    bearer_access_token(request)
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS foundation load failed")
            return _unavailable()

    @router.post("/api/v3/ios/course/foundation/complete")
    async def ios_foundation_complete(request: Request):
        try:
            payload = await validated_course_payload(
                request,
                IOSFoundationCompleteRequest,
            )
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).complete_foundation(
                    bearer_access_token(request),
                    foundation_id=payload.foundation_id,
                    foundation_version=payload.foundation_version,
                    speaking_bonus=payload.speaking_bonus,
                    event_id=payload.event_id,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS foundation completion failed")
            return _unavailable()

    @router.get("/api/v3/ios/course/lesson/{lesson_order}")
    async def ios_course_lesson(request: Request, lesson_order: int):
        try:
            if not MIN_LESSON_ORDER <= lesson_order <= MAX_LESSON_ORDER:
                raise DesktopCourseError("invalid_lesson_order", status_code=422)
            access_ref = str(request.query_params.get("access_ref") or "").strip()[:160]
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).lesson(
                    bearer_access_token(request),
                    lesson_order=lesson_order,
                    access_ref=access_ref,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS course lesson failed")
            return _unavailable()

    @router.post("/api/v3/ios/course/complete")
    async def ios_course_complete(request: Request):
        try:
            payload = await validated_course_payload(
                request,
                IOSCourseCompleteRequest,
            )
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).complete(
                    bearer_access_token(request),
                    lesson_order=payload.lesson_order,
                    event_id=payload.event_id,
                    mistakes=[
                        mistake.model_dump(exclude_none=True)
                        for mistake in payload.mistakes
                    ],
                    access_ref=payload.access_ref,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS course completion failed")
            return _unavailable()


    @router.get("/api/v3/ios/dictionary")
    async def ios_dictionary(request: Request):
        try:
            if request.query_params:
                raise DesktopCourseError("ios_request_invalid", status_code=422)
            token = bearer_access_token(request)
            async with session_factory() as session:
                context = await DesktopAuthService(session, settings_obj).authenticate(token)
                user = await UserRepository(session).get_by_telegram_id(
                    int(context.user.telegram_id)
                )
                language = getattr(user, "language", None)

            version = dictionary_version()
            etag = f'W/"dictionary-{version}"'
            if version and request.headers.get("If-None-Match") == etag:
                return Response(
                    status_code=304,
                    headers={"ETag": etag, "Cache-Control": "private, max-age=0"},
                )
            return JSONResponse(
                content={
                    "ok": True,
                    "version": version,
                    "language": str(language or "ru"),
                    "words": dictionary_for_language(language),
                },
                headers={"ETag": etag, "Cache-Control": "private, max-age=0"},
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("iOS dictionary failed")
            return _unavailable()

    return router
