"""Dars ichidagi shaxsiy takror (UIUX-007) — Telegram, iPhone PWA va Android.

Egasi faqat tasdiqlangan transportdan olinadi (Telegram initData, PWA sessiya
cookie + CSRF, Android Bearer token); body hech qachon user_id bermaydi.
Reja so'rovidagi har qanday ichki nosozlik `enabled: false` qaytaradi — dars
shaxsiy takrorsiz odatdagidek davom etadi.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

from app.repositories.user_repo import UserRepository
from app.services.account_identity import actual_telegram_id
from app.services.course_adaptive_lesson_service import (
    AdaptiveRequestError,
    CourseAdaptiveLessonService,
)
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.pwa_auth_service import (
    PWA_SESSION_COOKIE,
    PwaAuthError,
    PwaAuthService,
    require_same_origin,
)
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


logger = logging.getLogger(__name__)

HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
MAX_BODY_BYTES = 4096
DISABLED = {"ok": True, "enabled": False, "plan": None}

Surface = Literal["telegram", "iphone_pwa", "android"]


class AdaptivePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = Field(min_length=1, max_length=16)
    lesson_order: int = Field(ge=1, le=10000)
    formats: list[Annotated[str, StringConstraints(max_length=40)]] | None = Field(
        default=None, max_length=40
    )
    language: Literal["uz", "ru", "tj"] | None = None


class AdaptiveAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: int = Field(ge=1)
    item_id: str = Field(min_length=1, max_length=120)
    selected_index: int | None = Field(default=None, ge=0, le=32)
    selected_tokens: list[Annotated[str, StringConstraints(max_length=200)]] | None = Field(
        default=None, max_length=30
    )

    @model_validator(mode="after")
    def _one_answer(self):
        if (self.selected_index is None) == (self.selected_tokens is None):
            raise ValueError("exactly one of selected_index / selected_tokens is required")
        return self


class _RequestError(Exception):
    def __init__(self, code: str, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


async def _payload(request: Request, model):
    if request.query_params:
        raise _RequestError("adaptive_request_invalid", 422)
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise _RequestError("adaptive_request_invalid", 415)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise _RequestError("adaptive_request_too_large", 413)
    try:
        return model.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError):
        raise _RequestError("adaptive_request_invalid", 422) from None


def _error(code: str, status_code: int) -> JSONResponse:
    return JSONResponse({"ok": False, "error": code}, status_code=status_code, headers=HEADERS)


def create_course_adaptive_router(*, session_factory, settings_obj, service_factory=None):
    router = APIRouter(tags=["course-adaptive"])
    make_service = service_factory or (lambda session: CourseAdaptiveLessonService(session, settings_obj))

    async def _user(session, request: Request, surface: Surface):
        if surface == "telegram":
            if request.headers.get("Authorization"):
                raise _RequestError("adaptive_auth_ambiguous", 401)
            telegram_id = extract_verified_webapp_user_id(
                request.headers.get("X-Telegram-Init-Data", ""), settings_obj.BOT_TOKEN
            )
            if not telegram_id:
                raise _RequestError("invalid_telegram_init_data", 401)
            user = await UserRepository(session).get_by_telegram_id(int(telegram_id))
        elif surface == "iphone_pwa":
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            user, _ = await PwaAuthService(session, settings_obj).mutation_actor(
                request.cookies.get(PWA_SESSION_COOKIE),
                request.headers.get("X-HSK-PWA-CSRF"),
            )
        else:
            if request.headers.get("X-Telegram-Init-Data"):
                raise _RequestError("adaptive_auth_ambiguous", 401)
            value = str(request.headers.get("Authorization", "") or "")
            scheme, separator, token = value.partition(" ")
            token = token.strip() if separator and scheme.lower() == "bearer" else ""
            context = await DesktopAuthService(session, settings_obj).authenticate(token)
            telegram_id = actual_telegram_id(context.user)
            user = (
                await UserRepository(session).get_by_telegram_id(telegram_id)
                if telegram_id is not None
                else context.user
            )
        if not user or not getattr(user, "id", None):
            raise _RequestError("access_start_first", 403)
        return user

    async def _plan(request: Request, surface: Surface) -> JSONResponse:
        try:
            # Autentifikatsiya body talqinidan oldin emas — body kichik va
            # sxemasi qat'iy; egalik baribir faqat transportdan olinadi.
            payload = await _payload(request, AdaptivePlanRequest)
            async with session_factory() as session:
                user = await _user(session, request, surface)
                try:
                    result = await make_service(session).plan(
                        user,
                        level=payload.level,
                        lesson_order=payload.lesson_order,
                        formats=payload.formats,
                        language=payload.language,
                        analytics_client=surface,
                    )
                except AdaptiveRequestError:
                    raise
                except Exception:  # noqa: BLE001 — shaxsiy takror darsni to'xtatmaydi
                    logger.exception("Course adaptive plan failed (%s)", surface)
                    await session.rollback()
                    result = dict(DISABLED)
            return JSONResponse(result, headers=HEADERS)
        except AdaptiveRequestError as exc:
            return _error(exc.code, exc.status_code)
        except _RequestError as exc:
            return _error(exc.code, exc.status_code)
        except PwaAuthError as exc:
            return _error(exc.code, exc.status_code)
        except DesktopAuthError as exc:
            return _error(getattr(exc, "code", "android_auth_required"), getattr(exc, "status_code", 401))

    async def _answer(request: Request, surface: Surface) -> JSONResponse:
        try:
            payload = await _payload(request, AdaptiveAnswerRequest)
            async with session_factory() as session:
                user = await _user(session, request, surface)
                result = await make_service(session).answer(
                    user,
                    plan_id=payload.plan_id,
                    item_id=payload.item_id,
                    answer=(
                        payload.selected_tokens
                        if payload.selected_tokens is not None
                        else payload.selected_index
                    ),
                    analytics_client=surface,
                )
            return JSONResponse(result, headers=HEADERS)
        except AdaptiveRequestError as exc:
            return _error(exc.code, exc.status_code)
        except _RequestError as exc:
            return _error(exc.code, exc.status_code)
        except PwaAuthError as exc:
            return _error(exc.code, exc.status_code)
        except DesktopAuthError as exc:
            return _error(getattr(exc, "code", "android_auth_required"), getattr(exc, "status_code", 401))
        except Exception:  # noqa: BLE001 — klient javobni navbatda saqlab qayta yuboradi
            logger.exception("Course adaptive answer failed (%s)", surface)
            return _error("adaptive_unavailable", 503)

    @router.post("/api/v3/adaptive/plan")
    async def telegram_adaptive_plan(request: Request):
        return await _plan(request, "telegram")

    @router.post("/api/v3/adaptive/answer")
    async def telegram_adaptive_answer(request: Request):
        return await _answer(request, "telegram")

    @router.post("/api/v3/pwa/adaptive/plan")
    async def pwa_adaptive_plan(request: Request):
        return await _plan(request, "iphone_pwa")

    @router.post("/api/v3/pwa/adaptive/answer")
    async def pwa_adaptive_answer(request: Request):
        return await _answer(request, "iphone_pwa")

    @router.post("/api/v3/android/adaptive/plan")
    async def android_adaptive_plan(request: Request):
        return await _plan(request, "android")

    @router.post("/api/v3/android/adaptive/answer")
    async def android_adaptive_answer(request: Request):
        return await _answer(request, "android")

    return router
