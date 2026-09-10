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
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.entitlements.lesson_access import LessonAccessService
from app.services.course_v3_parts import total_parts
from app.services.desktop_course_service import normalize_course_v3_level
from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.entitlements.gate_shadow import shadow_compare_gate
from app.services.miniapp_hint_service import MiniAppHintService
from app.services.pro_trial_service import ProTrialService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


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
            order = int(payload.get("lesson_id") or 0)
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_lesson_payload"})
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(status_code=403, content={"ok": False, "error": "access_start_first"})
            level = normalize_course_v3_level(user.level)
            progress = await CourseProgressRepository(session).get_by_user_id(user.id, for_update=True)
            completed = int(progress.completed_lessons_count or 0) if progress and progress.level == level else 0
            if order < 1 or order > total_parts(level) or order > completed + 1:
                return JSONResponse(status_code=403, content={"ok": False, "error": "course_lesson_not_unlocked"})
            result = await LessonAccessService(session).status(
                user, level=level, lesson_order=order, completed=completed, consume=True,
            )
            await session.commit()
            return JSONResponse(status_code=200 if result["allowed"] else 403, content=result)


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
            result = await ProTrialService(session).start(
                user, source="miniapp_trial", client=CLIENT
            )
            if not result.get("ok"):
                return JSONResponse(status_code=409, content=result)
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
