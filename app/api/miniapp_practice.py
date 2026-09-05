"""Telegram Mini App uchun mashq dvigateli adapteri.

Mini App'ning mashq bo'limlari (Ieroglif tanish, Yodlash, Talaffuz) ilgari
savollarni MIJOZDA qurardi (`hsk-words.js`) va natijani hech qayerga
yozmasdi — server faqat "bo'lim ochildi" faktini bilardi. Natijada
kuzatilgan zaiflik (`course_mistakes`) faqat darslar, testlar va voice
orqali to'planardi; mashqlar signal bermasdi.

Bu router o'sha bo'limlarni Android va Desktop allaqachon ishlatadigan
`CourseMiniAppPracticeService` ga ulaydi: bir xil savol banki, bir xil
ballash, bir xil xatoga yozish va XP.

RUXSAT (Qaror A, ARCHITECTURE_DECISION.md): bu yerda gate QAYTA
tekshirilmaydi. Mini App o'zining `/api/v3/practice/daily-gate` va
`/api/v3/practice/ad-gate` yo'lidan yuradi — u yerda bepul limit UMRBOD va
feature kaliti boshqa (`recognition` / `memorize` / `pronunciation`).
Servisning o'z gate'i esa `training_test` slotini sarflaydi, uni Xatolar
bo'limi va Test markazi ham bo'lishadi. Ikkinchi marta gate qilsak, bitta
ieroglif mashqi o'quvchining Xatolar bo'limini jimgina yopib qo'yardi.
Shuning uchun servis `gate_checked=True` bilan chaqiriladi va monetizatsiya
qoidasi bugungicha qoladi.
"""

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
    model_validator,
)

from app.repositories.user_repo import UserRepository
from app.services.course_drill_signal_service import CourseDrillSignalService
from app.services.course_word_mastery_service import CourseWordMasteryService
from app.services.course_miniapp_practice_service import (
    PRACTICE_MODES,
    TRAINING_SKILLS,
    CourseMiniAppPracticeService,
)
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


logger = logging.getLogger(__name__)

MAX_PRACTICE_BODY_BYTES = 16 * 1024
MAX_PRACTICE_COMPLETE_BODY_BYTES = 64 * 1024
MAX_ANSWERS = 100
# initData Telegram tomonidan imzolanadi; uzunligi odatda ~1 KB dan kam.
MAX_INIT_DATA_CHARS = 4096
# Interval takrori bor bo'limlar. `memorize` hozircha faqat xato yozadi:
# uning ekrani chiziq tartibi modeli bo'yicha ishlaydi, so'z tanlash
# oqimi boshqa. U keyingi ishda ulanadi.
MASTERY_FEATURES = ("recognition", "pronunciation")

PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

PracticeMode = Literal["placement", "mock", "training"]
PracticeLanguage = Literal["uz", "ru", "tj"]
PracticeSkill = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=32, pattern=r"^[a-z]*$"),
]
PracticeLevel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=16, pattern=r"^[a-z0-9_]+$"),
]
PracticeSessionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=160),
]
PracticeQuestionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


class MiniAppPracticeError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class PracticeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: PracticeQuestionId
    selected: int


class PracticeStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: PracticeMode
    level: PracticeLevel
    language: PracticeLanguage
    skill: PracticeSkill = ""
    # Telegram imzolagan initData. Header'da ham kelishi mumkin, shuning
    # uchun bu yerda ixtiyoriy.
    initData: str = Field(default="", max_length=MAX_INIT_DATA_CHARS)


class PracticeCompleteRequest(PracticeStartRequest):
    session_id: PracticeSessionId
    answers: list[PracticeAnswer]


class DrillMistakeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Mijoz FAQAT xato bo'lgan ieroglifni va nima tanlaganini aytadi. Savol
    # matni ham, to'g'ri javob ham server lug'atidan quriladi.
    hanzi: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)]
    selected: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] = ""


class DrillResultEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hanzi: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)]
    correct: bool


class DrillReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # `pronunciation` faqat NATIJA yubora oladi: uning xatosini server
    # `score_pronunciation` ichida allaqachon yozadi, shuning uchun bu yerda
    # `mistakes` qabul qilinsa dublikat qator paydo bo'lardi.
    feature: Literal["recognition", "memorize", "pronunciation"]
    level: PracticeLevel
    language: PracticeLanguage
    mistakes: list[DrillMistakeEntry] = Field(default_factory=list)
    results: list[DrillResultEntry] = Field(default_factory=list)
    initData: str = Field(default="", max_length=MAX_INIT_DATA_CHARS)

    @model_validator(mode="after")
    def _feature_rules(self):
        if not self.mistakes and not self.results:
            raise ValueError("nothing to report")
        if self.feature == "pronunciation":
            if self.mistakes:
                raise ValueError("pronunciation mistakes are written by the voice service")
            if any(item.correct for item in self.results):
                # To'g'ri talaffuzni faqat server baholay oladi.
                raise ValueError("pronunciation success is scored server-side")
        return self


class DrillWordsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: Literal["recognition", "pronunciation"]
    limit: Annotated[int, Field(ge=1, le=30)] = 10
    initData: str = Field(default="", max_length=MAX_INIT_DATA_CHARS)


def _init_data(request: Request, payload: BaseModel) -> str:
    header = str(request.headers.get("X-Telegram-Init-Data", "") or "")
    if header:
        return header[:MAX_INIT_DATA_CHARS]
    return str(getattr(payload, "initData", "") or "")[:MAX_INIT_DATA_CHARS]


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
    *,
    max_body_bytes: int = MAX_PRACTICE_BODY_BYTES,
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise MiniAppPracticeError("practice_request_invalid", status_code=415)

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError as exc:
            raise MiniAppPracticeError("practice_request_invalid", status_code=400) from exc
        if parsed_length < 0 or parsed_length > max_body_bytes:
            raise MiniAppPracticeError("practice_request_too_large", status_code=413)

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_body_bytes:
            raise MiniAppPracticeError("practice_request_too_large", status_code=413)
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise MiniAppPracticeError("practice_request_invalid", status_code=422) from exc


def _validate_selection(payload: PracticeStartRequest) -> None:
    if payload.mode not in PRACTICE_MODES:
        raise MiniAppPracticeError("practice_request_invalid", status_code=422)
    if payload.mode == "training":
        if payload.skill not in TRAINING_SKILLS:
            raise MiniAppPracticeError("unknown_training_skill", status_code=422)
    elif payload.skill:
        raise MiniAppPracticeError("practice_request_invalid", status_code=422)


def _error_response(error: MiniAppPracticeError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


def _service_response(result: dict) -> JSONResponse:
    """Kirish rad etilgani 500 emas — u ham normal javob."""
    if result.get("ok") is not True:
        code = str(result.get("error") or "practice_unavailable")
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
            content={"ok": False, "error": code},
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


def create_miniapp_practice_router(
    *,
    session_factory,
    settings_obj,
    bot=None,
    service_factory: Callable[..., CourseMiniAppPracticeService] = (
        CourseMiniAppPracticeService
    ),
    drill_service_factory: Callable[..., CourseDrillSignalService] = (
        CourseDrillSignalService
    ),
    mastery_service_factory: Callable[..., CourseWordMasteryService] = (
        CourseWordMasteryService
    ),
) -> APIRouter:
    router = APIRouter(tags=["miniapp-practice"])

    def _telegram_id(request: Request, payload: BaseModel) -> int:
        init_data = _init_data(request, payload)
        telegram_id = (
            extract_verified_webapp_user_id(init_data, settings_obj.BOT_TOKEN)
            if init_data
            else None
        )
        if not telegram_id:
            raise MiniAppPracticeError("invalid_telegram_init_data", status_code=401)
        return int(telegram_id)

    @router.post("/api/v3/practice/start")
    async def miniapp_practice_start(request: Request):
        try:
            payload = await _validated_payload(request, PracticeStartRequest)
            _validate_selection(payload)
            telegram_id = _telegram_id(request, payload)
            async with session_factory() as session:
                result = await service_factory(session, bot).start(
                    telegram_id,
                    mode=payload.mode,
                    level=payload.level,
                    lang=payload.language,
                    skill=payload.skill,
                    gate_checked=True,
                )
            return _service_response(result)
        except MiniAppPracticeError as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                MiniAppPracticeError("practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Mini App practice start failed")
            return _error_response(
                MiniAppPracticeError("practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/practice/complete")
    async def miniapp_practice_complete(request: Request):
        try:
            payload = await _validated_payload(
                request,
                PracticeCompleteRequest,
                max_body_bytes=MAX_PRACTICE_COMPLETE_BODY_BYTES,
            )
            _validate_selection(payload)
            if len(payload.answers) > MAX_ANSWERS:
                raise MiniAppPracticeError("practice_request_too_large", status_code=413)
            telegram_id = _telegram_id(request, payload)
            async with session_factory() as session:
                result = await service_factory(session, bot).complete(
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
                    gate_checked=True,
                )
            return _service_response(result)
        except MiniAppPracticeError as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                MiniAppPracticeError("practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Mini App practice complete failed")
            return _error_response(
                MiniAppPracticeError("practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/practice/report")
    async def miniapp_drill_report(request: Request):
        """Mijoz boshqaradigan mashqlarning (Ieroglif tanish, Yodlash) xatolari.

        Bu ikki bo'lim o'z savollarini o'zi quradi va o'z ekran dizayniga ega,
        shuning uchun umumiy MCQ dvigatelidan foydalanmaydi. Lekin natijasi
        yo'qolmasligi kerak — aks holda `character` zaifligi faqat darslardan
        to'planardi.

        Mijoz FAQAT xato bo'lgan ieroglifni aytadi; savol va to'g'ri javob
        server lug'atidan quriladi, ya'ni soxta xato yozib bo'lmaydi.
        """
        try:
            payload = await _validated_payload(request, DrillReportRequest)
            telegram_id = _telegram_id(request, payload)
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(telegram_id)
                if not user:
                    return _service_response({"ok": False, "error": "access_start_first"})
                recorded = 0
                if payload.mistakes:
                    # Xatolar yo'li o'zgarmadi: server ularni o'z lug'atidan
                    # qayta quradi va "Xatolarim" bo'limiga yozadi.
                    recorded = await drill_service_factory(session).record(
                        user,
                        feature=payload.feature,
                        level=payload.level,
                        language=payload.language,
                        entries=[
                            {"hanzi": entry.hanzi, "selected": entry.selected}
                            for entry in payload.mistakes
                        ],
                    )
                scheduled = 0
                if payload.results and payload.feature in MASTERY_FEATURES:
                    # Interval takrori: to'g'ri javob ham, xato ham keyingi
                    # muddatni belgilaydi.
                    scheduled = await mastery_service_factory(session).record_drill(
                        user,
                        skill=payload.feature,
                        results=[
                            {"hanzi": entry.hanzi, "correct": entry.correct}
                            for entry in payload.results
                        ],
                    )
                await session.commit()
            return _service_response(
                {"ok": True, "recorded": recorded, "scheduled": scheduled}
            )
        except MiniAppPracticeError as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                MiniAppPracticeError("practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Mini App drill report failed")
            return _error_response(
                MiniAppPracticeError("practice_unavailable", status_code=503)
            )

    @router.post("/api/v3/practice/words")
    async def miniapp_drill_words(request: Request):
        """Mashq uchun so'zlar: takrorga tayyorlari + yangilari.

        Server MASLAHATCHI. Javobda faqat ieroglif va `kind` bo'ladi —
        ko'rinadigan matn klientda qoladi, shuning uchun til almashganda
        javob o'zgarmaydi. Bo'sh ro'yxat nosozlik emas: klient o'z pooliga
        qaytadi va mashq bugungidek ishlayveradi.
        """
        try:
            payload = await _validated_payload(request, DrillWordsRequest)
            telegram_id = _telegram_id(request, payload)
            async with session_factory() as session:
                user = await UserRepository(session).get_by_telegram_id(telegram_id)
                if not user:
                    return _service_response({"ok": False, "error": "access_start_first"})
                plan = await mastery_service_factory(session).drill_words(
                    user, skill=payload.feature, limit=payload.limit
                )
                await session.commit()
            return _service_response({"ok": True, **plan})
        except MiniAppPracticeError as exc:
            return _error_response(exc)
        except ValueError:
            return _error_response(
                MiniAppPracticeError("practice_request_invalid", status_code=422)
            )
        except Exception:
            logger.exception("Mini App drill words failed")
            return _error_response(
                MiniAppPracticeError("practice_unavailable", status_code=503)
            )

    return router
