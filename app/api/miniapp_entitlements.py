"""Mini App limit darvozalari — `app/main.py` dan ajratilgan.

Nega ajratildi: bu ikki endpoint bepul foydalanuvchining har bir mashq
sessiyasini boshlashdan oldin o'tadigan yagona darvozasi, lekin ular
`app/main.py` ichida edi va **birorta test `app.main` ni import qilmaydi** (u
botni ishga tushiradi). Ya'ni monetizatsiyaning eng issiq yo'li HTTP
darajasida umuman qoplanmagan edi.

Xatti-harakat so'zma-so'z ko'chirildi. Yagona qo'shimcha — shadow solishtiruvi:
markaziy dvigatel o'sha so'rov uchun qanday qaror qilishini hisoblaydi va
farqni yozadi. Qaror baribir ESKI yo'ldan chiqadi, toki sozlama uni
`engine` ga o'tkazmaguncha.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.entitlements.lesson_access import LessonAccessService
from app.services.course_p3_grammar_localization import miniapp_reserved_grammar_patch
from app.services.course_v3_parts import total_parts
from app.services.course_levels import content_level
from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.entitlements.gate_shadow import shadow_compare_gate
from app.services.entitlements.state import EntitlementState, resolve_state
from app.services.miniapp_hint_service import MiniAppHintService
from app.services.pro_trial_service import ProTrialService, REASON_NOT_APPLICABLE
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id
from app.services.trial_risk_service import TrialRiskService


logger = logging.getLogger(__name__)

CLIENT = "miniapp"
SHADOW_COMPARE_TIMEOUT_SECONDS = 0.25

#: Kunlik darvoza ochadigan bo'limlar. `app/main.py` dagi
#: `_COURSE_DAILY_GATE_FEATURES` ning aynan o'zi — u yerdan ko'chirildi va
#: endi yagona nusxa shu.
COURSE_DAILY_GATE_FEATURES = frozenset(
    {"recognition", "memorize", "pronunciation", "placement", "training_test"}
)
COURSE_AD_GATE_FEATURES = COURSE_DAILY_GATE_FEATURES | {"mistake_review", "lesson"}

MAX_INIT_DATA_CHARS = 4096
COURSE_DATA_ROOT = Path(__file__).resolve().parents[1] / "static" / "course_v3_data"
COURSE_LEVELS = frozenset({"hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"})
SKIP_TEST_CARD_TYPES = frozenset({
    "meaning_guess", "pinyin_choice", "translation_choice", "hanzi_choice",
    "gap_fill", "listening_choice", "quick_quiz", "sentence_builder", "match_pairs",
})
PRIVATE_CONTENT_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}


def _init_data(request: Request, payload: dict) -> str:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        init_data = str(payload.get("initData") or "")
    return init_data[:MAX_INIT_DATA_CHARS]


async def _body(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 — bo'sh yoki buzilgan tana 400 ga olib boradi
        return {}
    return payload if isinstance(payload, dict) else {}


def _ref(payload: dict) -> str | None:
    raw = payload.get("ref")
    return str(raw).strip()[:48] if raw else None


def _read_course_lesson(level: str, lesson_order: int) -> dict | None:
    path = COURSE_DATA_ROOT / level / f"lesson_{lesson_order:02d}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(value, dict)
        or str(value.get("level") or "").strip().lower() != level
        or value.get("lesson_id") != lesson_order
    ):
        return None
    return value


def _sales_value_projection(lesson: dict) -> dict | None:
    """Expose only the fixed, authored marketing examples from HSK1 lesson 3."""
    def example(value):
        if not isinstance(value, dict):
            return None
        projected = {key: value[key] for key in ("zh", "pinyin", "translation") if key in value}
        translation = projected.get("translation")
        if (
            not projected.get("zh")
            or not projected.get("pinyin")
            or not all(
                isinstance(translation, dict)
                and isinstance(translation.get(lang), str)
                and translation.get(lang)
                for lang in ("uz", "ru", "tj")
            )
        ):
            return None
        projected["translation"] = {lang: translation[lang] for lang in ("uz", "ru", "tj")}
        return projected

    outcome = lesson.get("outcome")
    next_outcome = lesson.get("next_outcome_preview")
    if not isinstance(outcome, dict) or not isinstance(next_outcome, dict):
        return None
    can_do = outcome.get("can_do")
    if not isinstance(can_do, list) or len(can_do) != 3:
        return None
    examples = [example(item) for item in can_do]
    next_example = example(next_outcome.get("example"))
    title = outcome.get("title")
    next_title = next_outcome.get("title")
    if (not all(examples) or not next_example
            or not all(isinstance(title, dict) and title.get(lang) for lang in ("uz", "ru", "tj"))
            or not all(isinstance(next_title, dict) and next_title.get(lang) for lang in ("uz", "ru", "tj"))):
        return None
    return {
        "outcome": {
            **({"id": outcome["id"]} if isinstance(outcome.get("id"), str) else {}),
            "title": {lang: title[lang] for lang in ("uz", "ru", "tj")},
            "can_do": examples,
        },
        "next_outcome_preview": {
            **({"id": next_outcome["id"]} if isinstance(next_outcome.get("id"), str) else {}),
            "title": {lang: next_title[lang] for lang in ("uz", "ru", "tj")},
            "example": next_example,
        },
    }


def _skip_test_questions(lesson: dict) -> list[dict]:
    """Build a small randomized question set; never return the full lesson."""
    candidates = []
    for section in lesson.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for card in section.get("cards") or []:
            if isinstance(card, dict) and card.get("type") in SKIP_TEST_CARD_TYPES:
                candidates.append(card)

    words = (lesson.get("active_words") or [])[:8]
    word_choices = [{"word": word} for word in words]
    for index, word in enumerate(words):
        candidates.append({
            "type": "_word_pick_hanzi" if index % 2 else "_word_pick_meaning",
            "word": word,
            "words": word_choices,
        })
    if not candidates:
        return []
    selected = secrets.SystemRandom().sample(candidates, min(6, len(candidates)))
    return [dict(card) for card in selected]


def _private_content_response(content: dict, *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=PRIVATE_CONTENT_HEADERS,
    )


def create_miniapp_entitlements_router(
    *,
    session_factory,
    settings_obj,
    bot=None,
) -> APIRouter:
    router = APIRouter()

    async def _authenticated(request: Request):
        payload = await _body(request)
        init_data = _init_data(request, payload)
        telegram_id = (
            extract_verified_webapp_user_id(init_data, settings_obj.BOT_TOKEN)
            if init_data
            else None
        )
        return telegram_id, payload

    async def _foundation_is_blocked(session, user, level: str) -> bool:
        if (level != "hsk1"
                or str(getattr(user, "level", "") or "").strip().lower() != "beginner"):
            return False
        state = await CourseMiniAppProfileService(session).foundation_status(user)
        return bool(state.get("required") and not state.get("completed"))

    @router.get("/api/v3/lesson/sales-preview")
    async def v3_course_lesson_sales_preview():
        lesson = _read_course_lesson("hsk1", 3)
        projection = _sales_value_projection(lesson) if lesson else None
        if projection is None:
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "sales_preview_unavailable"},
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse(content={"ok": True, **projection}, headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        })

    @router.get("/api/v3/lesson/foundation")
    async def v3_course_lesson_foundation(request: Request):
        telegram_id, _ = await _authenticated(request)
        if not telegram_id:
            return _private_content_response(
                {"ok": False, "error": "invalid_telegram_init_data"}, status_code=401,
            )
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return _private_content_response(
                    {"ok": False, "error": "access_start_first"}, status_code=403,
                )
            lesson = _read_course_lesson("hsk1", 1)
            foundation = lesson.get("foundation") if lesson else None
            if not isinstance(foundation, dict) or not foundation.get("cards"):
                return _private_content_response(
                    {"ok": False, "error": "foundation_unavailable"}, status_code=503,
                )
            return _private_content_response({"ok": True, "foundation": foundation})

    @router.get("/api/v3/lesson/content/{level}/{lesson_order}")
    async def v3_course_lesson_content(request: Request, level: str, lesson_order: int):
        telegram_id, _ = await _authenticated(request)
        if not telegram_id:
            return _private_content_response(
                {"ok": False, "error": "invalid_telegram_init_data"}, status_code=401,
            )
        normalized_level = str(level or "").strip().lower()
        if normalized_level not in COURSE_LEVELS or lesson_order < 1:
            return _private_content_response(
                {"ok": False, "error": "course_lesson_not_found"}, status_code=404,
            )
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return _private_content_response(
                    {"ok": False, "error": "access_start_first"}, status_code=403,
                )
            user_level = content_level(getattr(user, "level", None))
            if normalized_level != user_level:
                return _private_content_response(
                    {"ok": False, "error": "course_level_not_allowed"}, status_code=403,
                )
            total = total_parts(normalized_level)
            if not total or lesson_order > total:
                return _private_content_response(
                    {"ok": False, "error": "course_lesson_not_found"}, status_code=404,
                )
            progress = await CourseProgressRepository(session).get_by_user_id(user.id)
            completed = (
                int(getattr(progress, "completed_lessons_count", 0) or 0)
                if progress and getattr(progress, "level", None) == normalized_level
                else 0
            )
            if lesson_order > completed + 1:
                return _private_content_response(
                    {"ok": False, "error": "course_lesson_not_unlocked"}, status_code=403,
                )
            if await _foundation_is_blocked(session, user, normalized_level):
                return _private_content_response(
                    {"ok": False, "error": "android_foundation_required"}, status_code=403,
                )
            access = await LessonAccessService(session).status(
                user, level=normalized_level, lesson_order=lesson_order,
                completed=completed, consume=False,
            )
            if not access.get("allowed"):
                return _private_content_response(access, status_code=403)
            unlimited_access = resolve_state(user) in {
                EntitlementState.PRO_ACTIVE, EntitlementState.TEMP_ACCESS,
            }
            if (lesson_order > completed and not access.get("idempotent")
                    and not access.get("policy_free") and not unlimited_access):
                return _private_content_response(
                    {"ok": False, "error": "lesson_start_required"}, status_code=403,
                )
            lesson = _read_course_lesson(normalized_level, lesson_order)
            if not lesson:
                return _private_content_response(
                    {"ok": False, "error": "course_lesson_not_found"}, status_code=404,
                )
            return _private_content_response(lesson)

    @router.post("/api/v3/lesson/skip-test")
    async def v3_course_lesson_skip_test(request: Request):
        telegram_id, payload = await _authenticated(request)
        if not telegram_id:
            return _private_content_response(
                {"ok": False, "error": "invalid_telegram_init_data"}, status_code=401,
            )
        level = str(payload.get("level") or "").strip().lower()
        try:
            lesson_order = int(payload.get("lesson_id") or 0)
        except (TypeError, ValueError):
            lesson_order = 0
        if level not in COURSE_LEVELS or lesson_order < 1:
            return _private_content_response(
                {"ok": False, "error": "invalid_lesson_payload"}, status_code=400,
            )
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return _private_content_response(
                    {"ok": False, "error": "access_start_first"}, status_code=403,
                )
            user_level = content_level(getattr(user, "level", None))
            if level != user_level:
                return _private_content_response(
                    {"ok": False, "error": "course_level_not_allowed"}, status_code=403,
                )
            total = total_parts(level)
            if not total or lesson_order > total:
                return _private_content_response(
                    {"ok": False, "error": "course_lesson_not_found"}, status_code=404,
                )
            if await _foundation_is_blocked(session, user, level):
                return _private_content_response(
                    {"ok": False, "error": "android_foundation_required"}, status_code=403,
                )
            progress = await CourseProgressRepository(session).get_by_user_id(user.id)
            completed = (
                int(getattr(progress, "completed_lessons_count", 0) or 0)
                if progress and getattr(progress, "level", None) == level
                else 0
            )
            if lesson_order > completed + 1:
                return _private_content_response(
                    {"ok": False, "error": "course_lesson_not_unlocked"}, status_code=403,
                )
            access = await LessonAccessService(session).status(
                user, level=level, lesson_order=lesson_order,
                completed=completed, consume=False,
            )
            if not access.get("allowed"):
                return _private_content_response(access, status_code=403)
            lesson = _read_course_lesson(level, lesson_order)
            questions = _skip_test_questions(lesson) if lesson else []
            if not questions:
                return _private_content_response(
                    {"ok": False, "error": "skip_test_unavailable"}, status_code=409,
                )
            return _private_content_response({
                "ok": True, "level": level, "lesson_order": lesson_order,
                "questions": questions,
            })

    @router.post("/api/v3/practice/daily-gate")
    async def v3_practice_daily_gate(request: Request):
        """Mashq bo'limining BEPUL foydalanishi (bepul userga UMRDA 1 marta,
        reklamasiz). Sessiya boshlanishida chaqiriladi; bepul tugagan bo'lsa
        403 + reklama/obuna holati. Hisob server tomonda — user aylanib
        o'tolmaydi."""
        telegram_id, payload = await _authenticated(request)
        if not telegram_id:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )

        feature = str(payload.get("feature") or "").strip().lower()
        if feature not in COURSE_DAILY_GATE_FEATURES:
            return JSONResponse(
                status_code=400, content={"ok": False, "error": "invalid_feature"}
            )
        ref = _ref(payload)

        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    status_code=403, content={"ok": False, "error": "access_start_first"}
                )
            access = CourseMiniAppAccessService(session)
            # Admin "vaqtincha free" rejimini yoqqan bo'lsa Mashq bo'limlari ham
            # ochiq bo'lishi kerak — ilgari policy faqat kurs darslariga ta'sir
            # qilardi va user baribir "obuna kerak" devoriga urilardi.
            # Umrlik bepul foydalanish SARFLANMAYDI: rejim tugagach user o'z
            # bepul urinishini yo'qotmasin.
            if getattr(user, "status", "") != "blocked" and (await CourseAccessPolicyService(session).get_policy()).free_active:
                return JSONResponse(
                    content={
                        "ok": True,
                        "allowed": True,
                        "is_paid": access.is_paid_user(user),
                        "remaining": None,
                        "policy_free": True,
                    }
                )
            # Bepul: UMRDA 1 marta (lifetime=True — kunlik yangilanmaydi).
            result = await access.consume_daily_use(
                user, feature_key=feature, ref=ref, lifetime=True
            )
            # Asosiy limit qarori avval saqlanadi. Shadow — faqat diagnostika;
            # sekin DB yoki yangi dvigatel mashqni boshlashni ushlab turmasin.
            await session.commit()
            try:
                await asyncio.wait_for(
                    shadow_compare_gate(
                        session, user=user, feature=feature, legacy=result, client=CLIENT
                    ),
                    timeout=SHADOW_COMPARE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Skipping slow entitlement shadow comparison for %s/%s",
                    telegram_id,
                    feature,
                )

            if not result.get("allowed"):
                # Bepul tugadi — endi faqat obuna yoki 7 kunlik trial.
                #
                # Ilgari bu yerda "reklama bor" deb javob qaytardi va AI
                # bo'limi bo'lmasa u DOIM `available: true` edi. Mashq
                # reklamalari olib tashlangan bo'lsa ham klientlar shu
                # bayroqqa qarab "Reklama bilan davom etish" tugmasini
                # ko'rsatishda davom etardi — foydalanuvchi aynan shuni
                # ko'rgan.
                #
                # Kalit SAQLANADI va doim "yo'q" deydi: mustaqil mashq
                # sahifalari (`course_v3_recognition.html` va boshqalar)
                # o'sha kalitni o'qiydi, va ular yangilanmasidan oldin ham
                # to'g'ri ishlashi kerak.
                ad_info = {"available": False, "limited": False}
                return JSONResponse(
                    status_code=403,
                    content={
                        "ok": False,
                        "error": result.get("error") or "free_feature_limit_reached",
                        "is_paid": bool(result.get("is_paid", False)),
                        "ad": ad_info,
                        # Mini App ilgari buni OLMASDI, Android esa olardi.
                        # Endi ikkala klient bir xil javob ko'radi.
                        **result,
                        "reset_at": result.get("reset_at"),
                    },
                )
            return JSONResponse(
                content={
                    "ok": True,
                    "allowed": True,
                    "is_paid": bool(result.get("is_paid", False)),
                    **result,
                    "remaining": result.get("remaining"),
                }
            )

    @router.post("/api/v3/lesson/start")
    async def v3_course_lesson_start(request: Request):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        telegram_id = extract_verified_webapp_user_id(init_data, settings_obj.BOT_TOKEN) if init_data else None
        if not telegram_id:
            return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("lesson payload must be an object")
            order = int(payload.get("lesson_id") or 0)
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
            level = content_level(user.level)
            progress = await CourseProgressRepository(session).get_by_user_id(user.id, for_update=True)
            completed = int(progress.completed_lessons_count or 0) if progress and progress.level == level else 0
            # Completed lessons may be revisited without re-consuming a
            # limited free lesson. This read-only localization path requires
            # the same signed identity and server-stored completed progress.
            if payload.get("review_only") is True:
                if level != "nhsk2" or order < 1 or order > completed or order > total_parts(level):
                    return JSONResponse(
                        status_code=403,
                        content={"ok": False, "error": "course_lesson_not_unlocked"},
                        headers={"Cache-Control": "no-store"},
                    )
                # A signed completed-lesson read is quota-free, but must
                # still pass the SAME blocked-user and HSK 3.0 track gates
                # as native/Desktop. Progress alone is not an entitlement.
                review_status = await LessonAccessService(session).status(
                    user, level=level, lesson_order=order,
                    completed=completed, consume=False,
                )
                if not review_status["allowed"]:
                    return JSONResponse(
                        status_code=403, content=review_status,
                        headers={"Cache-Control": "no-store"},
                    )
                localized = miniapp_reserved_grammar_patch(level=level, lesson_order=order)
                response = {"ok": True, "allowed": True}
                if localized is not None:
                    response["p3_grammar"] = localized
                return JSONResponse(content=response, headers={"Cache-Control": "no-store"})
            if order < 1 or order > total_parts(level) or order > completed + 1:
                return JSONResponse(status_code=403, content={"ok": False, "error": "course_lesson_not_unlocked"})
            result = await LessonAccessService(session).status(
                user, level=level, lesson_order=order, completed=completed, consume=True,
            )
            await session.commit()
            # Display-only grammar translations are returned ONLY after the
            # existing authenticated, unlocked, successful consume=True gate.
            # Denials, direct static GETs and speculative prefetch get none.
            if result["allowed"] and level == "nhsk2":
                localized = miniapp_reserved_grammar_patch(
                    level=level, lesson_order=order,
                )
                if localized is not None:
                    result = {**result, "p3_grammar": localized}
            return JSONResponse(
                status_code=200 if result["allowed"] else 403,
                content=result, headers={"Cache-Control": "no-store"},
            )


    @router.post("/api/v3/limits/status")
    async def limits_status(request: Request):
        telegram_id, payload = await _authenticated(request)
        if not telegram_id:
            return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})
        feature = str(payload.get("feature") or "lesson").strip()
        if feature not in COURSE_AD_GATE_FEATURES | {"voice"}:
            return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_feature"})
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
            if feature == "mistake_review":
                feature = "training_test"
            result = await CourseMiniAppAccessService(session).configured_decision(user, feature)
            return JSONResponse(content={**result, "ok": True}, headers={"Cache-Control": "no-store"})

    @router.post("/api/v3/trial/start")
    async def v3_trial_start(request: Request):
        """7 kunlik Pro trialni boshlaydi.

        Email tasdiqlash YO'Q — auditoriya Telegram orqali keladi va pochta
        so'rash aktivatsiyani keskin tushirardi. Himoya: bitta Telegram
        akkaunt = bitta trial, plus admin qo'lidagi kill-switch.
        """
        telegram_id, _payload = await _authenticated(request)
        if not telegram_id:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )

        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    status_code=403, content={"ok": False, "error": "access_start_first"}
                )
            risk_service = TrialRiskService(session, settings_obj)
            risk_snapshot = await risk_service.analyze(
                user,
                client=CLIENT,
                source="miniapp_trial",
                remote_ip=request.headers.get("X-Real-IP"),
            )
            risk_decision = risk_service.evaluate(risk_snapshot)
            if risk_decision.denied:
                logger.info(
                    "trial_risk_denied telegram_id=%s client=%s score=%s reasons=%s",
                    telegram_id,
                    CLIENT,
                    risk_decision.score,
                    ",".join(risk_decision.reasons),
                )
                return JSONResponse(
                    status_code=409,
                    content={"ok": False, "error": REASON_NOT_APPLICABLE},
                )
            result = await ProTrialService(session).start(
                user, source="miniapp_trial", client=CLIENT
            )
            if not result.get("ok"):
                return JSONResponse(status_code=409, content=result)
            await risk_service.record_started(user, risk_snapshot)
            await session.commit()
        return JSONResponse(content=result)

    @router.post("/api/v3/trial/status")
    async def v3_trial_status(request: Request):
        """Trial taklif qilinadimi va nima uchun yo'q."""
        telegram_id, _payload = await _authenticated(request)
        if not telegram_id:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    status_code=403, content={"ok": False, "error": "access_start_first"}
                )
            verdict = await ProTrialService(session).eligibility(user)
            if verdict.get("eligible"):
                risk_service = TrialRiskService(session, settings_obj)
                risk_snapshot = await risk_service.analyze(
                    user,
                    client=CLIENT,
                    source="miniapp_status",
                    remote_ip=request.headers.get("X-Real-IP"),
                )
                risk_decision = risk_service.evaluate(risk_snapshot)
                if risk_decision.denied:
                    verdict = {
                        **verdict,
                        "eligible": False,
                        "reason": REASON_NOT_APPLICABLE,
                    }
        return JSONResponse(content={"ok": True, "trial": verdict})

    @router.post("/api/v3/hints/dismiss")
    async def v3_hint_dismiss(request: Request):
        """Tushuntirish blokchasi yopildi.

        Kalitni SERVER quradi, klient emas: yozuv kunni o'z ichiga oladi va
        uni klient soatiga qoldirish "uzoq tanaffusdan keyin qayta chiqarish"
        o'lchovini buzadi.

        Javob HAR DOIM 200: blokchani yopish oqimni to'xtatmasligi kerak, va
        klient allaqachon uni ekrandan olib tashlagan bo'ladi.
        """
        telegram_id, payload = await _authenticated(request)
        if not telegram_id:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )
        key = str(payload.get("hint") or payload.get("key") or "").strip()[:48]
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    status_code=403, content={"ok": False, "error": "access_start_first"}
                )
            saved = await MiniAppHintService(session).dismiss(
                user, key, client="course_v3"
            )
            if saved:
                await session.commit()
        return JSONResponse(content={"ok": True, "saved": saved})

    @router.post("/api/v3/practice/ad-gate")
    async def v3_practice_ad_gate(request: Request):
        """Reklama ko'rib bo'limni ochish — OLIB TASHLANDI.

        Yo'lning o'zi saqlanadi, chunki do'kondagi va keshdagi eski klientlar
        hali shu manzilga murojaat qiladi. Javob endi doim bir xil: bepul
        foydalanish tugagan bo'lsa paywall, ochilish yo'q.

        404 qaytarilmaydi ATAYLAB: eski klient uni "server buzildi" deb
        ko'rsatardi, 403 esa u allaqachon biladigan holat — limit tugagan.
        """
        telegram_id, payload = await _authenticated(request)
        if not telegram_id:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )

        feature = str(payload.get("feature") or "").strip().lower()
        if feature not in COURSE_DAILY_GATE_FEATURES:
            return JSONResponse(
                status_code=400, content={"ok": False, "error": "invalid_feature"}
            )

        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    status_code=403, content={"ok": False, "error": "access_start_first"}
                )
            access = CourseMiniAppAccessService(session)
            # "Vaqtincha free" rejimi hamon hammani ochadi — bu reklama emas,
            # adminning sovg'asi.
            if getattr(user, "status", "") != "blocked" and (await CourseAccessPolicyService(session).get_policy()).free_active:
                return JSONResponse(
                    content={
                        "ok": True,
                        "allowed": True,
                        "is_paid": access.is_paid_user(user),
                        "remaining": None,
                        "policy_free": True,
                    }
                )
            # Obunachiga bu yo'l kerak emas, lekin unga "yo'q" deyish ham
            # noto'g'ri bo'lardi.
            if access.is_paid_user(user):
                return JSONResponse(
                    content={
                        "ok": True,
                        "allowed": True,
                        "is_paid": True,
                        "remaining": None,
                    }
                )
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "error": "free_feature_limit_reached",
                    "is_paid": False,
                    "ad": {"available": False, "limited": False},
                },
            )

    return router
