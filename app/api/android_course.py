"""Bearer-authenticated Course v3 transport for the native Android client.

Like the auth adapter, this is transport only. Access rules, XP, streak,
mistakes and completion idempotency all live in the shared course service; the
Android client cannot reach a different code path or a different decision.

The request models are reused from the desktop adapter so both clients are
validated by exactly the same constraints. The completion event id is expected
to look like ``android:<uuid>``, which already fits the shared pattern.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.desktop_course import (
    DesktopCourseCompleteRequest,
    DesktopCourseLanguageRequest,
    bearer_access_token,
    course_error_response,
    validated_course_payload,
)
from app.services.android_course_service import AndroidCourseService
from app.services.desktop_auth_service import DesktopAuthError
from app.services.desktop_course_service import DesktopCourseError


logger = logging.getLogger(__name__)

MIN_LESSON_ORDER = 1
MAX_LESSON_ORDER = 500
MIN_TZ_OFFSET_MINUTES = -720
MAX_TZ_OFFSET_MINUTES = 840


def _unavailable() -> JSONResponse:
    return course_error_response(
        DesktopCourseError("android_course_unavailable", status_code=503)
    )


def _timezone_offset(request: Request) -> int | None:
    """Device timezone offset in minutes, bounded. Absent means 'unchanged'."""

    raw = request.query_params.get("tz")
    if raw is None:
        return None
    try:
        offset = int(raw)
    except (TypeError, ValueError) as exc:
        raise DesktopCourseError(
            "desktop_course_request_invalid",
            status_code=422,
        ) from exc
    # Note the explicit None check above: UTC+0 is a real offset and must not
    # be swallowed by a falsy test.
    if not MIN_TZ_OFFSET_MINUTES <= offset <= MAX_TZ_OFFSET_MINUTES:
        raise DesktopCourseError(
            "desktop_course_request_invalid",
            status_code=422,
        )
    return offset


def create_android_course_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., AndroidCourseService] = AndroidCourseService,
) -> APIRouter:
    router = APIRouter(tags=["android-course"])

    @router.get("/api/v3/android/course/map")
    async def android_course_map(request: Request):
        try:
            offset = _timezone_offset(request)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).course_map(
                    bearer_access_token(request),
                    timezone_offset_minutes=offset,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course map failed")
            return _unavailable()

    @router.get("/api/v3/android/course/lesson/{lesson_order}")
    async def android_course_lesson(request: Request, lesson_order: int):
        try:
            if not MIN_LESSON_ORDER <= lesson_order <= MAX_LESSON_ORDER:
                raise DesktopCourseError("invalid_lesson_order", status_code=422)
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).lesson(
                    bearer_access_token(request),
                    lesson_order=lesson_order,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course lesson failed")
            return _unavailable()

    @router.post("/api/v3/android/course/complete")
    async def android_course_complete(request: Request):
        try:
            payload = await validated_course_payload(
                request,
                DesktopCourseCompleteRequest,
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
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course completion failed")
            return _unavailable()

    @router.post("/api/v3/android/preferences/language")
    async def android_course_language(request: Request):
        try:
            payload = await validated_course_payload(
                request,
                DesktopCourseLanguageRequest,
            )
            async with session_factory() as session:
                result = await service_factory(session, settings_obj).set_language(
                    bearer_access_token(request),
                    language=payload.language,
                )
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, DesktopCourseError) as exc:
            return course_error_response(exc)
        except Exception:
            logger.exception("Android course language update failed")
            return _unavailable()

    return router
