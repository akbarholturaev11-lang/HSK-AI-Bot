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
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


logger = logging.getLogger(__name__)


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
) -> APIRouter:
    router = APIRouter(tags=["ios-practice"])

    async def _telegram_id(session, request: Request) -> int:
        context = await DesktopAuthService(session, settings_obj).authenticate(
            _access_token(request)
        )
        return int(context.user.telegram_id)

    def _service(session):
        return (
            service_factory(session, bot=bot)
            if bot is not None
            else service_factory(session)
        )

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

    return router
