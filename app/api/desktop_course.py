from __future__ import annotations

import logging
from typing import Annotated, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)

from app.services.desktop_auth_service import DesktopAuthError
from app.services.desktop_course_service import (
    DesktopCourseError,
    DesktopCourseService,
)


logger = logging.getLogger(__name__)
MAX_DESKTOP_COURSE_BODY_BYTES = 64 * 1024
PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

DesktopCourseEventId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=16,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$",
    ),
]
DesktopCourseMaterialRef = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=20,
        max_length=160,
        pattern=(
            r"^lesson:(?:hsk1|hsk2|hsk3|hsk4):[1-9][0-9]*:"
            r"section:[1-9][0-9]*:card:[1-9][0-9]*$"
        ),
    ),
]
DesktopCourseSelectedAnswer = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000),
]
DesktopCourseSelectedToken = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class DesktopCourseMistakeRequest(BaseModel):
    """Only client selections are accepted; answer keys stay server-owned."""

    model_config = ConfigDict(extra="forbid")

    material_ref: DesktopCourseMaterialRef
    selected_index: int | None = Field(default=None, ge=0, le=100)
    selected_answer: DesktopCourseSelectedAnswer | None = None
    selected_tokens: list[DesktopCourseSelectedToken] | None = Field(
        default=None,
        max_length=100,
    )
    selected_left_index: int | None = Field(default=None, ge=0, le=100)
    selected_right_index: int | None = Field(default=None, ge=0, le=100)


class DesktopCourseCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_order: int = Field(ge=1, le=500)
    event_id: DesktopCourseEventId
    mistakes: list[DesktopCourseMistakeRequest] = Field(
        default_factory=list,
        max_length=50,
    )


class DesktopCourseLanguageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = Field(pattern=r"^(uz|ru|tj)$")


class DesktopNativeEventRequest(BaseModel):
    """Small, allowlisted native telemetry payload; prompts never belong here."""

    model_config = ConfigDict(extra="forbid")

    event_name: Literal[
        "desktop_ai_pack_started",
        "desktop_ai_pack_completed",
        "desktop_offline_ai_used",
    ]
    event_id: DesktopCourseEventId
    model_id: str = Field(
        default="qwen3-4b-q4-k-m",
        min_length=3,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$",
    )
    size_bytes: int | None = Field(default=None, ge=0, le=20_000_000_000)
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)


def _access_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise DesktopCourseError("desktop_course_request_invalid", status_code=415)

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            if int(content_length) > MAX_DESKTOP_COURSE_BODY_BYTES:
                raise DesktopCourseError(
                    "desktop_course_request_too_large",
                    status_code=413,
                )
        except ValueError as exc:
            raise DesktopCourseError(
                "desktop_course_request_invalid",
                status_code=400,
            ) from exc

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_DESKTOP_COURSE_BODY_BYTES:
            raise DesktopCourseError(
                "desktop_course_request_too_large",
                status_code=413,
            )
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise DesktopCourseError(
            "desktop_course_request_invalid",
            status_code=422,
        ) from exc


def _error_response(error: DesktopAuthError | DesktopCourseError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


def create_desktop_course_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., DesktopCourseService] = DesktopCourseService,
) -> APIRouter:
    router = APIRouter(tags=["desktop-course"])

    @router.get("/api/v3/desktop/course/map")
    async def desktop_course_map(request: Request):
        try:
            timezone_offset: int | None = None
            timezone_raw = request.query_params.get("tz")
            if timezone_raw is not None:
                try:
                    timezone_offset = int(timezone_raw)
                except (TypeError, ValueError) as exc:
                    raise DesktopCourseError(
                        "desktop_course_request_invalid",
                        status_code=422,
                    ) from exc
                if not -720 <= timezone_offset <= 840:
                    raise DesktopCourseError(
                        "desktop_course_request_invalid",
                        status_code=422,
                    )

            async with session_factory() as session:
                result = await service_factory(
                    session,
                    settings_obj,
                ).course_map(
                    _access_token(request),
                    timezone_offset_minutes=timezone_offset,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop course map failed")
            return _error_response(
                DesktopCourseError(
                    "desktop_course_unavailable",
                    status_code=503,
                )
            )

    @router.get("/api/v3/desktop/course/lesson/{lesson_order}")
    async def desktop_course_lesson(request: Request, lesson_order: int):
        try:
            if not 1 <= lesson_order <= 500:
                raise DesktopCourseError(
                    "invalid_lesson_order",
                    status_code=422,
                )
            async with session_factory() as session:
                result = await service_factory(
                    session,
                    settings_obj,
                ).lesson(
                    _access_token(request),
                    lesson_order=lesson_order,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop course lesson failed")
            return _error_response(
                DesktopCourseError(
                    "desktop_course_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/course/complete")
    async def desktop_course_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopCourseCompleteRequest,
            )
            async with session_factory() as session:
                result = await service_factory(
                    session,
                    settings_obj,
                ).complete(
                    _access_token(request),
                    lesson_order=payload.lesson_order,
                    event_id=payload.event_id,
                    mistakes=[
                        mistake.model_dump(exclude_none=True)
                        for mistake in payload.mistakes
                    ],
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop course completion failed")
            return _error_response(
                DesktopCourseError(
                    "desktop_course_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/preferences/language")
    async def desktop_course_language(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopCourseLanguageRequest,
            )
            async with session_factory() as session:
                result = await service_factory(
                    session,
                    settings_obj,
                ).set_language(
                    _access_token(request),
                    language=payload.language,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop course language update failed")
            return _error_response(
                DesktopCourseError(
                    "desktop_course_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/events")
    async def desktop_native_event(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopNativeEventRequest,
            )
            async with session_factory() as session:
                result = await service_factory(
                    session,
                    settings_obj,
                ).record_native_event(
                    _access_token(request),
                    event_name=payload.event_name,
                    event_id=payload.event_id,
                    payload={
                        "model_id": payload.model_id,
                        **(
                            {"size_bytes": payload.size_bytes}
                            if payload.size_bytes is not None
                            else {}
                        ),
                        **(
                            {"duration_ms": payload.duration_ms}
                            if payload.duration_ms is not None
                            else {}
                        ),
                    },
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopCourseError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop native event failed")
            return _error_response(
                DesktopCourseError(
                    "desktop_course_unavailable",
                    status_code=503,
                )
            )

    return router
