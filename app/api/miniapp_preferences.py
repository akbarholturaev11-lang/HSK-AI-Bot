"""Mini App o'quv preferensiyalari: kunlik vaqt, fokus va XP maqsadi.

Onboarding faqat DARAJA va MAQSADni so'raydi — ular birinchi darsdan oldin
ham ma'noli javob beriladigan savollar. Kunlik vaqt va "nimaga urg'u
beraylik" esa birinchi darsdan KEYIN so'raladi: hali bir dars ham
ko'rmagan o'quvchidan buni so'rash past signal beradi.

`daily_goal_xp` ilgari Mini App ichidagi oddiy JS o'zgaruvchi edi
(`dailyGoal=50`) va hech qayerga saqlanmasdi: foydalanuvchi profilda
tanlagan maqsad ilova qayta ochilganda yo'qolardi. Endi server saqlaydi.

Bu router hech qanday kirish/limit qoidasiga tegmaydi — u faqat
o'quvchining o'z sozlamasini yozadi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Callable, Literal, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_profile_service import (
    COURSE_DAILY_MINUTES,
    CourseMiniAppProfileService,
)
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


logger = logging.getLogger(__name__)

MAX_PREFERENCES_BODY_BYTES = 4 * 1024
MAX_INIT_DATA_CHARS = 4096

PreferredFocus = Literal["speaking", "listening", "vocabulary", "grammar", "none"]
CourseGoal = Literal[
    "hsk_exam", "study_china", "work_china", "daily_communication", "travel"
]


class PreferencesError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class PreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Maqsad savoli onboardingga keyin qo'shilgani uchun eski o'quvchilardan
    # u birinchi darsdan keyin so'raladi.
    goal: Optional[CourseGoal] = None
    daily_minutes: Optional[int] = None
    preferred_focus: Optional[PreferredFocus] = None
    # `None` yuborish "avto rejimga qaytar" degani emas — maydonni umuman
    # yubormaslik "tegma" degani. Avtoga qaytarish uchun `auto` yuboriladi.
    daily_goal_xp: Optional[Annotated[int, Field(ge=10, le=500)]] = None
    daily_goal_auto: bool = False
    initData: str = Field(default="", max_length=MAX_INIT_DATA_CHARS)

    @model_validator(mode="after")
    def _at_least_one_change(self):
        if (
            self.goal is None
            and self.daily_minutes is None
            and self.preferred_focus is None
            and self.daily_goal_xp is None
            and not self.daily_goal_auto
        ):
            raise ValueError("no preference supplied")
        if self.daily_minutes is not None and self.daily_minutes not in COURSE_DAILY_MINUTES:
            raise ValueError("unknown daily_minutes")
        if self.daily_goal_xp is not None and self.daily_goal_auto:
            raise ValueError("daily_goal_xp and daily_goal_auto are exclusive")
        return self


async def _validated_payload(request: Request) -> PreferencesRequest:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise PreferencesError("preferences_request_invalid", status_code=415)

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_PREFERENCES_BODY_BYTES:
            raise PreferencesError("preferences_request_too_large", status_code=413)
    try:
        return PreferencesRequest.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise PreferencesError("preferences_request_invalid", status_code=422) from exc


def _profile_payload(profile) -> dict:
    return {
        "goal": profile.goal,
        "goal_chosen": getattr(profile, "goal_chosen_at", None) is not None,
        "daily_minutes": profile.daily_minutes,
        "preferred_focus": profile.preferred_focus,
        "daily_goal_xp": CourseMiniAppProfileService.resolve_daily_goal_xp(profile),
        "daily_goal_is_custom": profile.daily_goal_xp is not None,
        "plan_size": CourseMiniAppProfileService.daily_plan_size(profile.daily_minutes),
    }


def create_miniapp_preferences_router(
    *,
    session_factory,
    settings_obj,
    profile_service_factory: Callable[..., CourseMiniAppProfileService] = (
        CourseMiniAppProfileService
    ),
) -> APIRouter:
    router = APIRouter(tags=["miniapp-preferences"])

    def _telegram_id(request: Request, payload: PreferencesRequest) -> int:
        init_data = (
            str(request.headers.get("X-Telegram-Init-Data", "") or "")
            or str(payload.initData or "")
        )[:MAX_INIT_DATA_CHARS]
        telegram_id = (
            extract_verified_webapp_user_id(init_data, settings_obj.BOT_TOKEN)
            if init_data
            else None
        )
        if not telegram_id:
            raise PreferencesError("invalid_telegram_init_data", status_code=401)
        return int(telegram_id)

    @router.post("/api/v3/preferences")
    async def miniapp_preferences(request: Request):
        try:
            payload = await _validated_payload(request)
            telegram_id = _telegram_id(request, payload)
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(telegram_id)
                if not user:
                    return JSONResponse(
                        status_code=403,
                        content={"ok": False, "error": "access_start_first"},
                        headers={"Cache-Control": "no-store"},
                    )
                service = profile_service_factory(session)
                profile = await service.get_or_create(user.id)
                if payload.goal is not None:
                    profile.goal = payload.goal
                    # O'quvchi maqsadni O'ZI tanladi — endi qayta so'ralmaydi.
                    if getattr(profile, "goal_chosen_at", None) is None:
                        profile.goal_chosen_at = datetime.now(timezone.utc)
                if payload.daily_minutes is not None:
                    profile.daily_minutes = int(payload.daily_minutes)
                if payload.preferred_focus is not None:
                    profile.preferred_focus = payload.preferred_focus
                if payload.daily_goal_auto:
                    await service.set_daily_goal_xp(profile, None)
                elif payload.daily_goal_xp is not None:
                    await service.set_daily_goal_xp(profile, payload.daily_goal_xp)
                # Sozlama o'zgarsa bugungi reja qayta qurilishi kerak: aks
                # holda o'quvchi kunlik vaqtni qisqartirib ham eski, uzun
                # rejani ko'rib turaverardi.
                if (
                    payload.goal is not None
                    or payload.daily_minutes is not None
                    or payload.preferred_focus is not None
                ):
                    profile.daily_plan_key = None
                    profile.daily_plan_json = None
                await session.commit()
                body = _profile_payload(profile)
            return JSONResponse(
                content={"ok": True, "profile": body},
                headers={"Cache-Control": "no-store"},
            )
        except PreferencesError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "error": exc.code},
                headers={"Cache-Control": "no-store"},
            )
        except ValueError:
            return JSONResponse(
                status_code=422,
                content={"ok": False, "error": "preferences_request_invalid"},
                headers={"Cache-Control": "no-store"},
            )
        except Exception:
            logger.exception("Mini App preferences update failed")
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "preferences_unavailable"},
                headers={"Cache-Control": "no-store"},
            )

    return router
