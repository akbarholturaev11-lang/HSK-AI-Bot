"""Admin Mini App uchun entitlement boshqaruvi.

Ikkita narsani boshqaradi:

* **Limitlar** — bugun ular Python konstantasi, ya'ni "bepul dars 2 ta bo'lsin"
  degan qarorni bajarish uchun deploy kerak. Endi bitta sozlama qatori.
* **Ko'chirish holati** — qaysi harakat hali kuzatuvda, qaysi biri dvigatelga
  o'tkazilgan, va solishtiruv hisoboti.

Nega alohida router: `app/main.py` dagi admin endpointlarining birortasi test
bilan qoplanmagan, chunki hech qaysi test `app.main` ni import qilmaydi. Bu
yerdagilar esa qoplanadi — narx va limit yozadigan joyda buni qilmaslik
mumkin emas.

Autentifikatsiya `admin_guard` orqali tashqaridan beriladi, ya'ni admin
tekshiruvining mantiqi hamon bitta joyda (`app/main.py`) qoladi.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.services.ad_placement_service import AdPlacementService
from app.services.entitlements.limits_config import LimitConfigService
from app.services.pro_trial_service import ProTrialService
from app.services.entitlements.shadow import (
    ROLLOUT_CLEAN_DAYS,
    ROLLOUT_MIN_SAMPLES,
    EntitlementShadowService,
)


logger = logging.getLogger(__name__)

MAX_REPORT_DAYS = 90


async def _body(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 — bo'sh tana ham to'g'ri so'rov
        return {}
    return payload if isinstance(payload, dict) else {}


def create_admin_entitlements_router(*, session_factory, admin_guard) -> APIRouter:
    """`admin_guard(request) -> (telegram_id, error_response)`."""
    router = APIRouter()

    @router.post("/api/admin-miniapp/limits")
    async def admin_limits(request: Request):
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        async with session_factory() as session:
            payload = await LimitConfigService(session).get_payload()
        return JSONResponse(content={"ok": True, "limits": payload})

    @router.post("/api/admin-miniapp/limits/save")
    async def admin_limits_save(request: Request):
        """Limitlarni saqlaydi.

        Yaroqsiz tahrir JIMGINA tuzatilmaydi — `400` qaytadi. Admin nima
        yozganini bilishi kerak, aks holda u "saqlandi" degan javobni ko'rib,
        aslida boshqa qiymat ishlayotganidan bexabar qoladi.
        """
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        payload = await _body(request)
        async with session_factory() as session:
            try:
                config = await LimitConfigService(session).save_config(
                    payload, updated_by_telegram_id=telegram_id
                )
            except ValueError as exc:
                return JSONResponse(
                    status_code=400, content={"ok": False, "error": str(exc)}
                )
            await session.commit()
        logger.info("admin_limits_saved admin_id=%s", telegram_id)
        return JSONResponse(content={"ok": True, "limits": config.public_payload()})

    @router.post("/api/admin-miniapp/ad-placements")
    async def admin_ad_placements(request: Request):
        """Ikkala reklama joyining sozlamasi."""
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        async with session_factory() as session:
            settings = await AdPlacementService(session).get_settings()
        return JSONResponse(content={"ok": True, "ads": settings.public_payload()})

    @router.post("/api/admin-miniapp/ad-placements/save")
    async def admin_ad_placements_save(request: Request):
        """Har joy ALOHIDA boshqariladi: birini o'chirish ikkinchisiga tegmaydi."""
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        payload = await _body(request)
        async with session_factory() as session:
            try:
                settings = await AdPlacementService(session).save_settings(
                    payload, updated_by_telegram_id=telegram_id
                )
            except ValueError as exc:
                return JSONResponse(
                    status_code=400, content={"ok": False, "error": str(exc)}
                )
            await session.commit()
        logger.info("admin_ad_placements_saved admin_id=%s", telegram_id)
        return JSONResponse(content={"ok": True, "ads": settings.public_payload()})

    @router.post("/api/admin-miniapp/trial/revoke")
    async def admin_trial_revoke(request: Request):
        """Suiiste'mol aniqlansa, jonli trialni qo'lda yopish.

        `trial_used` tozalanmaydi — ya'ni qaytadan olishga yo'l ochilmaydi.
        """
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        payload = await _body(request)
        try:
            target_id = int(payload.get("telegram_id") or 0)
        except (TypeError, ValueError):
            target_id = 0
        if not target_id:
            return JSONResponse(
                status_code=400, content={"ok": False, "error": "invalid_telegram_id"}
            )
        reason = str(payload.get("reason") or "").strip()[:200]

        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(target_id)
            if not user:
                return JSONResponse(
                    status_code=404, content={"ok": False, "error": "user_not_found"}
                )
            revoked = await ProTrialService(session).revoke(
                user, admin_telegram_id=telegram_id, reason=reason
            )
            if not revoked:
                return JSONResponse(
                    status_code=409,
                    content={"ok": False, "error": "no_active_trial"},
                )
            await session.commit()
        return JSONResponse(content={"ok": True, "telegram_id": target_id})

    @router.post("/api/admin-miniapp/entitlement-shadow")
    async def admin_entitlement_shadow(request: Request):
        """Dvigatel eski qaror bilan qanchalik mos kelayotgani.

        Harakatni yoqish uchun IKKALA shart kerak: nomuvofiqlik nol VA namuna
        yetarli — "hech kim ishlatmagan" ni "hammasi to'g'ri" deb o'qib
        bo'lmaydi.
        """
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        payload = await _body(request)
        try:
            days = int(payload.get("days") or ROLLOUT_CLEAN_DAYS)
        except (TypeError, ValueError):
            days = ROLLOUT_CLEAN_DAYS
        days = max(1, min(days, MAX_REPORT_DAYS))

        async with session_factory() as session:
            service = EntitlementShadowService(session)
            rows = await service.disagreement_report(days=days)
            for entry in rows:
                if entry["disagreements"]:
                    entry["examples"] = await service.examples(
                        action=entry["action"], client=entry["client"], limit=3
                    )
            rollout = await service.get_rollout()
        return JSONResponse(
            content={
                "ok": True,
                "days": days,
                "min_samples": ROLLOUT_MIN_SAMPLES,
                "rows": rows,
                "rollout": rollout,
            }
        )

    @router.post("/api/admin-miniapp/entitlement-shadow/rollout")
    async def admin_entitlement_rollout_save(request: Request):
        """Harakatni dvigatelga o'tkazish — deploy emas, sozlama yozuvi."""
        telegram_id, auth_error = admin_guard(request)
        if auth_error:
            return auth_error
        payload = await _body(request)
        async with session_factory() as session:
            try:
                stored = await EntitlementShadowService(session).save_rollout(
                    payload, updated_by_telegram_id=telegram_id
                )
            except ValueError as exc:
                return JSONResponse(
                    status_code=400, content={"ok": False, "error": str(exc)}
                )
            await session.commit()
        logger.info("admin_entitlement_rollout_saved admin_id=%s", telegram_id)
        return JSONResponse(content={"ok": True, "rollout": stored})

    return router
