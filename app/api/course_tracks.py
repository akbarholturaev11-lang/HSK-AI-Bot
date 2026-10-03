from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.repositories.user_repo import UserRepository
from app.services.course_track_service import CourseTrackError, CourseTrackService
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.hsk30_unlock_service import Hsk30UnlockService
from app.services.hsk30_promo_service import Hsk30PromoService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


logger = logging.getLogger(__name__)

MAX_TRACK_BODY_BYTES = 4 * 1024
MAX_INIT_DATA_CHARS = 4096
CourseTrackName = Literal["hsk20", "hsk30"]
CourseTrackLevel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=4,
        max_length=16,
        pattern=r"^(?:n?beginner|n?hsk[1-4])$",
    ),
]


class CourseTrackRequestError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class CourseTrackSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_track: CourseTrackName
    level: CourseTrackLevel | None = None
    initData: str = Field(default="", max_length=MAX_INIT_DATA_CHARS)


async def _payload(request: Request) -> CourseTrackSwitchRequest:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise CourseTrackRequestError("course_track_request_invalid", status_code=415)

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_TRACK_BODY_BYTES:
            raise CourseTrackRequestError("course_track_request_too_large", status_code=413)
    try:
        return CourseTrackSwitchRequest.model_validate_json(bytes(body))
    except (ValidationError, TypeError, ValueError) as exc:
        raise CourseTrackRequestError("course_track_request_invalid", status_code=422) from exc


def _bearer_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


def _error(error) -> JSONResponse:
    return JSONResponse(
        status_code=int(getattr(error, "status_code", 400) or 400),
        content={"ok": False, "error": str(getattr(error, "code", "course_track_failed"))},
        headers={"Cache-Control": "no-store"},
    )


async def _status_payload(session, user) -> dict:
    status = await CourseTrackService(session).status(user)
    eligibility = await Hsk30UnlockService(session).payment_eligibility(
        user,
        include_display_price=True,
    )
    return {
        "ok": True,
        **status,
        "hsk30_unlock": eligibility,
        "hsk30_promo": await Hsk30PromoService(session).state(user),
    }


def create_course_tracks_router(*, session_factory, settings_obj) -> APIRouter:
    router = APIRouter(tags=["course-tracks"])

    def miniapp_telegram_id(request: Request, init_data_fallback: str = "") -> int:
        init_data = (
            str(request.headers.get("X-Telegram-Init-Data", "") or "")
            or str(init_data_fallback or "")
        )[:MAX_INIT_DATA_CHARS]
        telegram_id = (
            extract_verified_webapp_user_id(init_data, settings_obj.BOT_TOKEN)
            if init_data
            else None
        )
        if not telegram_id:
            raise CourseTrackRequestError(
                "invalid_telegram_init_data",
                status_code=401,
            )
        return int(telegram_id)

    @router.get("/api/v3/course-tracks")
    async def miniapp_track_status(request: Request):
        try:
            telegram_id = miniapp_telegram_id(request)
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(telegram_id)
                if not user:
                    raise CourseTrackRequestError("access_start_first", status_code=403)
                result = await _status_payload(session, user)
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (CourseTrackRequestError, CourseTrackError) as exc:
            return _error(exc)
        except Exception:
            logger.exception("Mini App course track status failed")
            return _error(
                CourseTrackRequestError("course_track_unavailable", status_code=503)
            )

    @router.post("/api/v3/course-tracks/switch")
    async def miniapp_track_switch(request: Request):
        try:
            body = await _payload(request)
            telegram_id = miniapp_telegram_id(request, body.initData)
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(telegram_id)
                if not user:
                    raise CourseTrackRequestError("access_start_first", status_code=403)
                result = await CourseTrackService(session).switch(
                    user,
                    target_track=body.target_track,
                    requested_level=body.level,
                )
                await session.commit()
                result = {
                    "ok": True,
                    **result,
                    "hsk30_unlock": await Hsk30UnlockService(
                        session
                    ).payment_eligibility(user),
                }
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (CourseTrackRequestError, CourseTrackError) as exc:
            return _error(exc)
        except Exception:
            logger.exception("Mini App course track switch failed")
            return _error(
                CourseTrackRequestError("course_track_unavailable", status_code=503)
            )

    @router.post("/api/v3/course-tracks/promo-shown")
    async def miniapp_track_promo_shown(request: Request):
        try:
            telegram_id = miniapp_telegram_id(request)
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(telegram_id)
                if not user:
                    raise CourseTrackRequestError("access_start_first", status_code=403)
                promo = await Hsk30PromoService(session).mark_shown(user)
                await session.commit()
            return JSONResponse(
                content={"ok": True, "hsk30_promo": promo},
                headers={"Cache-Control": "no-store"},
            )
        except CourseTrackRequestError as exc:
            return _error(exc)
        except Exception:
            logger.exception("Mini App HSK 3.0 promo record failed")
            return _error(
                CourseTrackRequestError("course_track_unavailable", status_code=503)
            )

    @router.get("/api/v3/native/course-tracks")
    async def native_track_status(request: Request):
        try:
            async with session_factory() as session:
                context = await DesktopAuthService(
                    session,
                    settings_obj,
                ).authenticate(_bearer_token(request))
                result = await _status_payload(session, context.user)
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (DesktopAuthError, CourseTrackError) as exc:
            return _error(exc)
        except Exception:
            logger.exception("Native course track status failed")
            return _error(
                CourseTrackRequestError("course_track_unavailable", status_code=503)
            )

    @router.post("/api/v3/native/course-tracks/switch")
    async def native_track_switch(request: Request):
        try:
            body = await _payload(request)
            async with session_factory() as session:
                context = await DesktopAuthService(
                    session,
                    settings_obj,
                ).authenticate(_bearer_token(request))
                result = await CourseTrackService(session).switch(
                    context.user,
                    target_track=body.target_track,
                    requested_level=body.level,
                )
                await session.commit()
                result = {
                    "ok": True,
                    **result,
                    "hsk30_unlock": await Hsk30UnlockService(
                        session
                    ).payment_eligibility(context.user),
                }
            return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
        except (CourseTrackRequestError, DesktopAuthError, CourseTrackError) as exc:
            return _error(exc)
        except Exception:
            logger.exception("Native course track switch failed")
            return _error(
                CourseTrackRequestError("course_track_unavailable", status_code=503)
            )

    @router.post("/api/v3/native/course-tracks/promo-shown")
    async def native_track_promo_shown(request: Request):
        try:
            async with session_factory() as session:
                context = await DesktopAuthService(
                    session,
                    settings_obj,
                ).authenticate(_bearer_token(request))
                promo = await Hsk30PromoService(session).mark_shown(
                    context.user
                )
                await session.commit()
            return JSONResponse(
                content={"ok": True, "hsk30_promo": promo},
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, CourseTrackError) as exc:
            return _error(exc)
        except Exception:
            logger.exception("Native HSK 3.0 promo record failed")
            return _error(
                CourseTrackRequestError("course_track_unavailable", status_code=503)
            )

    return router
