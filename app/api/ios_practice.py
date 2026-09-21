"""Bearer-authenticated practice transport for the native iOS client.

The question bank, free-use gate, grading, mistake persistence and rewards stay
in CourseMiniAppPracticeService. This module only binds the verified native
session to that shared service.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.desktop_practice import (
    DesktopPracticeCompleteRequest,
    DesktopPracticeError,
    DesktopPracticeStartRequest,
    MAX_ANSWERS,
    MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
    _access_token,
    _validate_selection,
    _validated_payload,
)
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_hsk_exam_service import CourseHskExamService
from app.services.assistant_assessment_service import (
    assessment_abandoned,
    assessment_finished,
    assessment_started,
)
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


logger = logging.getLogger(__name__)


class IOSExamStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = Field(min_length=1, max_length=16)
    language: str = Field(default="", max_length=8)
    access_ref: str = Field(default="", max_length=160)
    ad_supported: bool = False


class IOSExamAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=160)
    selected_index: int = Field(ge=0, le=32)


class IOSExamCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=120)
    level: str = Field(default="", max_length=16)
    language: str = Field(default="", max_length=8)
    answers: list[IOSExamAnswer] = Field(default_factory=list, max_length=100)


class IOSMistakeReviewStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ad_supported: bool = False
    access_ref: str = Field(default="", max_length=160)


class IOSMistakeReviewAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=120)
    question_id: str = Field(min_length=1, max_length=160)
    selected_index: int = Field(ge=0, le=32)


class IOSMistakeReviewCompleteAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=160)
    selected_index: int = Field(ge=0, le=32)


class IOSMistakeReviewCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=120)
    answers: list[IOSMistakeReviewCompleteAnswer] = Field(default_factory=list, max_length=100)


def _error_response(
    error: DesktopAuthError | DesktopPracticeError,
) -> JSONResponse:
    return JSONResponse(
        status_code=getattr(error, "status_code", 400),
        content={"ok": False, "error": getattr(error, "code", "ios_practice_unavailable")},
        headers={"Cache-Control": "no-store"},
    )


def _service_response(result: dict) -> JSONResponse:
    if result.get("ok") is True:
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})

    code = str(result.get("error") or "ios_practice_unavailable")
    status = (
        403
        if code
        in {
            "free_feature_limit_reached",
            "access_start_first",
            "ad_authorization_required",
            "invalid_ad_authorization",
            "course_access_blocked",
        }
        else 404
        if code == "mistake_review_empty"
        else 409
    )
    return JSONResponse(
        status_code=status,
        content={**result, "ok": False, "error": code},
        headers={"Cache-Control": "no-store"},
    )


def create_ios_practice_router(
    *,
    session_factory,
    settings_obj,
    bot=None,
    service_factory: Callable[..., CourseMiniAppPracticeService] = CourseMiniAppPracticeService,
    mistake_service_factory: Callable[..., CourseMistakeService] = CourseMistakeService,
    exam_service_factory: Callable[..., CourseHskExamService] = CourseHskExamService,
) -> APIRouter:
    router = APIRouter(tags=["ios-practice"])

    async def _context(session, request: Request):
        return await DesktopAuthService(session, settings_obj).authenticate(
            _access_token(request)
        )

    async def _telegram_id(session, request: Request) -> int:
        context = await _context(session, request)
        return int(context.user.telegram_id)

    def _service(session):
        return (
            service_factory(session, bot=bot)
            if bot is not None
            else service_factory(session)
        )

    def _mistake_service(session):
        return mistake_service_factory(session)

    @router.post("/api/v3/ios/practice/start")
    async def ios_practice_start(request: Request):
        try:
            payload = await _validated_payload(request, DesktopPracticeStartRequest)
            _validate_selection(payload)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await _service(session).start(
                    telegram_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                    access_ref=payload.access_ref,
                    ad_supported=payload.ad_supported,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                DesktopPracticeError("ios_practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("iOS practice start failed")
            return _error_response(
                DesktopPracticeError("ios_practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/ios/practice/complete")
    async def ios_practice_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopPracticeCompleteRequest,
                max_body_bytes=MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
            )
            _validate_selection(payload)
            if len(payload.answers) > MAX_ANSWERS:
                raise DesktopPracticeError(
                    "ios_practice_request_too_large",
                    status_code=413,
                )

            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await _service(session).complete(
                    telegram_id,
                    session_id=payload.session_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                    answers=[
                        {
                            "question_id": item.question_id,
                            "selected_index": int(item.selected),
                        }
                        for item in payload.answers
                    ],
                    access_ref=payload.access_ref,
                    ad_supported=payload.ad_supported,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                DesktopPracticeError("ios_practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("iOS practice complete failed")
            return _error_response(
                DesktopPracticeError("ios_practice_unavailable", status_code=503)
            )



    @router.post("/api/v3/ios/exams/start")
    async def ios_exam_start(request: Request):
        try:
            payload = await _validated_payload(request, IOSExamStartRequest)
            async with session_factory() as session:
                context = await _context(session, request)
                result = await exam_service_factory(session).start(
                    int(context.user.telegram_id),
                    level=payload.level,
                    lang=payload.language,
                    access_ref=payload.access_ref,
                    ad_supported=payload.ad_supported,
                )
                session_id = str((result.get("session") or {}).get("id", ""))
                if session_id and await assessment_abandoned(
                    session,
                    int(context.user.id),
                    session_id,
                ):
                    raise DesktopPracticeError(
                        "assistant_assessment_abandoned",
                        status_code=409,
                    )
                await assessment_started(
                    session,
                    int(context.user.id),
                    "exam",
                    result,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                DesktopPracticeError("ios_exam_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("iOS exam start failed")
            return _error_response(
                DesktopPracticeError("ios_exam_unavailable", status_code=503)
            )

    @router.post("/api/v3/ios/exams/complete")
    async def ios_exam_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                IOSExamCompleteRequest,
                max_body_bytes=MAX_DESKTOP_PRACTICE_COMPLETE_BODY_BYTES,
            )
            async with session_factory() as session:
                context = await _context(session, request)
                if await assessment_abandoned(
                    session,
                    int(context.user.id),
                    payload.session_id,
                ):
                    raise DesktopPracticeError(
                        "assistant_assessment_abandoned",
                        status_code=409,
                    )

                result = await exam_service_factory(session).complete(
                    int(context.user.telegram_id),
                    session_id=payload.session_id,
                    answers=[
                        {
                            "question_id": item.question_id,
                            "selected_index": int(item.selected_index),
                        }
                        for item in payload.answers
                    ],
                    level=payload.level or None,
                    lang=payload.language or None,
                )
                if result.get("ok"):
                    await assessment_finished(
                        session,
                        int(context.user.id),
                        payload.session_id,
                    )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                DesktopPracticeError("ios_exam_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("iOS exam complete failed")
            return _error_response(
                DesktopPracticeError("ios_exam_unavailable", status_code=503)
            )

    @router.get("/api/v3/ios/mistakes")
    async def ios_mistakes(request: Request):
        try:
            unexpected = set(request.query_params) - {"category", "limit", "offset"}
            if unexpected:
                raise DesktopPracticeError("ios_practice_request_invalid", status_code=422)
            category = str(request.query_params.get("category") or "").strip().lower()
            if category == "all":
                category = ""
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await _mistake_service(session).overview(
                    telegram_id,
                    category=category or None,
                    limit=request.query_params.get("limit", "30"),
                    offset=request.query_params.get("offset", "0"),
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("iOS mistakes overview failed")
            return _error_response(
                DesktopPracticeError("ios_mistakes_unavailable", status_code=503)
            )

    @router.post("/api/v3/ios/mistakes/review/start")
    async def ios_mistake_review_start(request: Request):
        try:
            payload = await _validated_payload(request, IOSMistakeReviewStartRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await _mistake_service(session).start_review(
                    telegram_id,
                    ad_supported=payload.ad_supported,
                    access_ref=payload.access_ref,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("iOS mistake review start failed")
            return _error_response(
                DesktopPracticeError("ios_mistakes_unavailable", status_code=503)
            )

    @router.post("/api/v3/ios/mistakes/review/answer")
    async def ios_mistake_review_answer(request: Request):
        try:
            payload = await _validated_payload(request, IOSMistakeReviewAnswerRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await _mistake_service(session).answer_review_question(
                    telegram_id,
                    session_id=payload.session_id,
                    question_id=payload.question_id,
                    selected_index=payload.selected_index,
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("iOS mistake review answer failed")
            return _error_response(
                DesktopPracticeError("ios_mistakes_unavailable", status_code=503)
            )

    @router.post("/api/v3/ios/mistakes/review/complete")
    async def ios_mistake_review_complete(request: Request):
        try:
            payload = await _validated_payload(request, IOSMistakeReviewCompleteRequest)
            async with session_factory() as session:
                telegram_id = await _telegram_id(session, request)
                result = await _mistake_service(session).complete_review(
                    telegram_id,
                    session_id=payload.session_id,
                    answers=[
                        {
                            "question_id": item.question_id,
                            "selected_index": int(item.selected_index),
                        }
                        for item in payload.answers
                    ],
                )
            return _service_response(result)
        except (DesktopAuthError, DesktopPracticeError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("iOS mistake review complete failed")
            return _error_response(
                DesktopPracticeError("ios_mistakes_unavailable", status_code=503)
            )

    return router
