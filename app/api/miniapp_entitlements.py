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

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.services.course_access_policy_service import CourseAccessPolicyService
from app.services.course_miniapp_access_service import (
    COURSE_AI_PRACTICE_FEATURES,
    CourseMiniAppAccessService,
)
from app.services.entitlements.gate_shadow import shadow_compare_gate
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


logger = logging.getLogger(__name__)

CLIENT = "miniapp"

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
            if (await CourseAccessPolicyService(session).get_policy()).free_active:
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
                user, feature_key=feature, ref=ref, lifetime=True, notify_bot=bot
            )
            # Markaziy dvigatel shu savolga yonma-yon javob beradi va farq
            # yoziladi. Bu yerda u hech narsani hal qilmaydi.
            await shadow_compare_gate(
                session, user=user, feature=feature, legacy=result, client=CLIENT
            )

            if not result.get("allowed"):
                # Bepul tugadi. Endi reklama yoki obuna. AI token sarflaydigan
                # bo'limda (masalan talaffuz) reklama ham kuniga 2 marta
                # cheklangan; boshqa bo'limlarda reklama cheksiz.
                if feature in COURSE_AI_PRACTICE_FEATURES:
                    ad_status = await access.daily_status(user, f"{feature}_ad")
                    ad_info = {
                        "available": bool(ad_status.get("allowed")),
                        "limited": True,
                        "used": int(ad_status.get("used") or 0),
                        "limit": int(ad_status.get("limit") or 0),
                        "remaining": ad_status.get("remaining"),
                    }
                else:
                    ad_info = {"available": True, "limited": False}
                await session.commit()
                return JSONResponse(
                    status_code=403,
                    content={
                        "ok": False,
                        "error": result.get("error") or "free_feature_limit_reached",
                        "is_paid": bool(result.get("is_paid", False)),
                        "ad": ad_info,
                        # Mini App ilgari buni OLMASDI, Android esa olardi.
                        # Endi ikkala klient bir xil javob ko'radi.
                        "reset_at": result.get("reset_at"),
                    },
                )
            await session.commit()
            return JSONResponse(
                content={
                    "ok": True,
                    "allowed": True,
                    "is_paid": bool(result.get("is_paid", False)),
                    "remaining": result.get("remaining"),
                }
            )

    @router.post("/api/v3/practice/ad-gate")
    async def v3_practice_ad_gate(request: Request):
        """Bepul tugagach, user reklama ko'rib yana kirmoqchi bo'lsa
        chaqiriladi. Odatda CHEKSIZ; faqat AI token sarflaydigan bo'limda
        (masalan talaffuz) reklama ham KUNIGA 2 marta cheklanadi. Server
        tomonda hisoblanadi."""
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
            # "Vaqtincha free" rejimida reklama ham talab qilinmaydi.
            if (await CourseAccessPolicyService(session).get_policy()).free_active:
                return JSONResponse(
                    content={
                        "ok": True,
                        "allowed": True,
                        "is_paid": access.is_paid_user(user),
                        "remaining": None,
                        "policy_free": True,
                    }
                )
            # AI bo'lim emas — reklama cheksiz, slot band qilinmaydi.
            if feature not in COURSE_AI_PRACTICE_FEATURES:
                return JSONResponse(
                    content={
                        "ok": True,
                        "allowed": True,
                        "is_paid": access.is_paid_user(user),
                        "remaining": None,
                    }
                )
            # AI bo'lim — reklama ham kuniga 2 marta.
            result = await access.consume_daily_use(
                user, feature_key=f"{feature}_ad", ref=ref, notify_bot=bot
            )
            await session.commit()
            if not result.get("allowed"):
                # Reklama-ruxsati ham tugadi — endi faqat obuna
                # (ertaga yana ochiladi).
                return JSONResponse(
                    status_code=403,
                    content={
                        "ok": False,
                        "error": result.get("error") or "free_feature_limit_reached",
                        "is_paid": bool(result.get("is_paid", False)),
                        "reset_at": result.get("reset_at"),
                    },
                )
            return JSONResponse(
                content={
                    "ok": True,
                    "allowed": True,
                    "is_paid": bool(result.get("is_paid", False)),
                    "remaining": result.get("remaining"),
                }
            )

    return router
