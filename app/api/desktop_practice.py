"""Bearer-authenticated desktop adapter for the shared practice engine.

``CourseMiniAppPracticeService`` already builds and grades placement, mock and
training sets for the Telegram Mini App, including the free daily-use gate. This
router binds it to the user resolved from a verified desktop session, so the
question bank, the daily limit and the mistake bookkeeping stay in one place.
"""

from __future__ import annotations

import logging
from typing import Annotated, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from app.services.course_miniapp_practice_service import (
    PRACTICE_MODES,
    TRAINING_SKILLS,
    CourseMiniAppPracticeService,
)
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


logger = logging.getLogger(__name__)

MAX_DESKTOP_PRACTICE_BODY_BYTES = 16 * 1024
MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES = 64 * 1024
MAX_ANSWERS = 100

PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

DesktopPracticeMode = Literal["placement", "mock", "training"]
DesktopPracticeLanguage = Literal["uz", "ru", "tj"]
DesktopPracticeSkill = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=32, pattern=r"^[a-z]*$"),
]
DesktopPracticeLevel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=16, pattern=r"^[a-z0-9_]+$"),
]
DesktopPracticeSessionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=160),
]
DesktopQuestionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


class DesktopPracticeError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class DesktopPracticeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: DesktopQuestionId
    selected: int


class DesktopPracticeStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: DesktopPracticeMode
    level: DesktopPracticeLevel
    language: DesktopPracticeLanguage
    skill: DesktopPracticeSkill = ""


class DesktopPracticeCompleteRequest(DesktopPracticeStartRequest):
    session_id: DesktopPracticeSessionId
    answers: list[DesktopPracticeAnswer]


def _access_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
    *,
    max_body_bytes: int = MAX_DESKTOP_PRACTICE_BODY_BYTES,
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise DesktopPracticeError("desktop_practice_request_invalid", status_code=415)

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError as exc:
            raise DesktopPracticeError(
                "desktop_practice_request_invalid",
                status_code=400,
            ) from exc
        if parsed_length < 0 or parsed_length > max_body_bytes:
            raise DesktopPracticeError(
                "desktop_practice_request_too_large",
                status_code=413,
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_body_bytes:
            raise DesktopPracticeError(
                "desktop_practice_request_too_large",
                status_code=413,
            )
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise DesktopPracticeError(
            "desktop_practice_request_invalid",
            status_code=422,
        ) from exc


def _validate_selection(payload: DesktopPracticeStartRequest) -> None:
    if payload.mode not in PRACTICE_MODES:
        raise DesktopPracticeError("desktop_practice_request_invalid", status_code=422)
    if payload.mode == "training":
        if payload.skill not in TRAINING_SKILLS:
            raise DesktopPracticeError("unknown_training_skill", status_code=422)
    elif payload.skill:
        raise DesktopPracticeError("desktop_practice_request_invalid", status_code=422)


def _error_response(
    error: DesktopAuthError | DesktopPracticeError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


def _service_response(result: dict) -> JSONResponse:
    """Free-plan gating and 'no questions' come back as ok=false, not as 500."""

    if result.get("ok") is not True:
        code = str(result.get("error") or "desktop_practice_unavailable")
        status = 403 if code in {"free_feature_limit_reached", "access_start_first"} else 409
        return JSONResponse(
            status_code=status,
            content={"ok": False, "error": code},
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


def create_desktop_practice_router(
    *,
    session_factory,
    settings_obj,
    service_factory: Callable[..., CourseMiniAppPracticeService] = (
        CourseMiniAppPracticeService
    ),
) -> APIRouter:
    router = APIRouter(tags=["desktop-practice"])

    async def _telegram_id(session, request: Request) -> int:
        context = await DesktopAuthService(session, settings_obj).authenticate(
            _access_token(request)
        )
        return int(context.user.telegram_id)

    @router.post("/api/v3/desktop/practice/start")
    async def desktop_practice_start(request: Request):
        try:
            payload = await _validated_payload(request, DesktopPracticeStartRequest)
            _validate_selection(payload)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).start(
                    telegram_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                DesktopPracticeError(
                    "desktop_practice_request_invalid",
                    status_code=422,
                )
            )
        except Exception:
            logger.exception("Desktop practice start failed")
            return _error_response(
                DesktopPracticeError("desktop_practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/desktop/practice/complete")
    async def desktop_practice_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopPracticeCompleteRequest,
                max_body_bytes=MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
            )
            _validate_selection(payload)
            if len(payload.answers) > MAX_ANSWERS:
                raise DesktopPracticeError(
                    "desktop_practice_request_too_large",
                    status_code=413,
                )
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await service_factory(session).complete(
                    telegram_id,
                    session_id=payload.session_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                    answers=[
                        {"question_id": item.question_id, "selected": int(item.selected)}
                        for item in payload.answers
                    ],
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                DesktopPracticeError(
                    "desktop_practice_request_invalid",
                    status_code=422,
                )
            )
        except Exception:
            logger.exception("Desktop practice complete failed")
            return _error_response(
                DesktopPracticeError("desktop_practice_unavailable", status_code=503)
            )

    return router
