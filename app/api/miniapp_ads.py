"""Reklama endpointlari — aynan ikkita joy uchun.

Ilgari bu yerda uchta narsa bor edi: reklama olish, "urinish" tokeni
(`/ad/attempt`) va ko'rilganini tasdiqlash. O'rtadagi ikkitasi reklama ko'rib
DARSNI OCHISH mexanizmi uchun kerak edi — server tomonda soxta `watched_seconds`
ni tutish uchun butun bir token/binding tarmog'i qurilgan.

Endi reklama hech narsani ochmaydi: limit tugasa paywall chiqadi. Shuning
uchun o'sha tarmoq ham kerak emas va olib tashlandi. Qolgani ikkita oddiy
chaqiruv: "menga shu joy uchun reklama ber" va "ko'rildi".

Kunlik chegara SERVERDA, Telegram akkaunti bo'yicha sanaladi — qurilma
almashtirish yoki brauzer xotirasini tozalash uni aylanib o'tmaydi.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.repositories.user_repo import UserRepository
from app.services.ad_placement_service import (
    AD_PLACEMENTS,
    AdPlacementService,
    normalize_placement,
)
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id


logger = logging.getLogger(__name__)

CLIENT = "miniapp"
MAX_INIT_DATA_CHARS = 4096


async def _body(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def create_miniapp_ads_router(
    *, session_factory, settings_obj
) -> APIRouter:
    router = APIRouter()

    def _telegram_id(request: Request, payload: dict | None = None):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        if not init_data and payload:
            init_data = str(payload.get("initData") or "")
        if not init_data:
            init_data = str(request.query_params.get("initData") or "")
        init_data = init_data[:MAX_INIT_DATA_CHARS]
        if not init_data:
            return None
        return extract_verified_webapp_user_id(init_data, settings_obj.BOT_TOKEN)

    @router.get("/api/v3/pwa/ad")
    @router.post("/api/v3/pwa/ad/view")
    async def pwa_ad(request: Request):
        from app.services.pwa_auth_service import (
            PWA_SESSION_COOKIE, PwaAuthError, PwaAuthService, require_same_origin,
        )

        headers = {"Cache-Control": "no-store"}
        try:
            if request.headers.get("X-Telegram-Init-Data"):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            writing = request.method == "POST"
            if writing:
                require_same_origin(request, settings_obj)
                if request.query_params or len(await request.body()) > 2048:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                payload = await _body(request)
                if set(payload) - {"ad_id", "placement", "watched_seconds", "level", "lesson_order", "lang"}:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
            else:
                if set(request.query_params) - {"placement", "lesson", "lang"}:
                    raise PwaAuthError("pwa_request_invalid", status_code=422)
                payload = dict(request.query_params)
            placement = payload.get("placement")
            if not isinstance(placement, str) or placement not in {"screen_center", "lesson_end"}:
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            try:
                lesson = int(payload.get("lesson_order") or payload.get("lesson") or 0)
                watched = int(payload.get("watched_seconds") or 0)
                ad_id = int(payload.get("ad_id") or 0)
                if not 0 <= lesson <= 500 or not 0 <= watched <= 3600:
                    raise ValueError
            except (TypeError, ValueError):
                raise PwaAuthError("pwa_request_invalid", status_code=422)
            async with session_factory() as session:
                auth = PwaAuthService(session, settings_obj)
                if writing:
                    user, _ = await auth.mutation_actor(
                        request.cookies.get(PWA_SESSION_COOKIE), request.headers.get("X-HSK-PWA-CSRF"),
                    )
                    user = await UserRepository(session).get_by_user_id(user.id, lock=True)
                else:
                    user, _ = await auth.actor(request.cookies.get(PWA_SESSION_COOKIE))
                if user is None or user.status == "blocked":
                    raise PwaAuthError("pwa_session_required")
                service = AdPlacementService(session)
                # PWA is the browser delivery of the same Mini App placements;
                # existing Admin client toggles remain authoritative.
                ad = await service.next_ad(
                    user, placement=placement, client=CLIENT, lesson_order=lesson,
                    language=payload.get("lang") if isinstance(payload.get("lang"), str) and payload["lang"] in {"uz", "ru", "tj"} else user.language,
                )
                if writing:
                    if not ad or ad["id"] != ad_id:
                        raise PwaAuthError("ad_not_available", status_code=409)
                    result = await service.record_view(
                        user, placement=placement, ad_id=ad_id, watched_seconds=watched,
                        level=str(payload.get("level") or "hsk1")[:16], lesson_order=lesson,
                    )
                    await session.commit()
                else:
                    result = {"ok": True, "ad": ad, "placement": placement}
                headers["X-HSK-PWA-User-ID"] = str(user.id)
                return JSONResponse(result, headers=headers)
        except PwaAuthError as exc:
            return JSONResponse({"ok": False, "error": exc.code}, status_code=exc.status_code, headers=headers)

    @router.get("/api/v3/ad")
    async def v3_ad(request: Request):
        """Shu joy uchun reklama, yoki bo'sh javob.

        Bo'sh javob XATO EMAS: chegara tugagan, joy o'chirilgan, foydalanuvchi
        obunachi yoki katalog bo'sh bo'lishi mumkin. Klient bunday holatda
        oqimni davom ettiradi — reklama hech qachon devor bo'lmasligi kerak.
        """
        placement = normalize_placement(request.query_params.get("placement"))
        telegram_id = _telegram_id(request)
        if not telegram_id:
            # Imzosiz chaqiruvga reklama berilmaydi: chegara akkauntga bog'liq.
            return JSONResponse(content={"ok": True, "ad": None, "placement": placement})

        try:
            lesson_order = int(request.query_params.get("lesson") or 0)
        except (TypeError, ValueError):
            lesson_order = 0

        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    content={"ok": True, "ad": None, "placement": placement}
                )
            service = AdPlacementService(session)
            # UI tanlangan tili hisobdagidan farq qilishi mumkin. Reklama
            # auditoriyasi foydalanuvchi auth/obunasidan aniqlanadi, til
            # esa interfeysning joriy tilidan olinadi.
            requested_lang = str(request.query_params.get("lang") or "").lower()
            chosen_lang = requested_lang if requested_lang in ("tj", "uz", "ru") else getattr(user, "language", None)
            ad = await service.next_ad(
                user,
                placement=placement,
                client=CLIENT,
                language=chosen_lang,
                lesson_order=lesson_order,
            )
            status = await service.status(user, placement=placement, client=CLIENT)

        return JSONResponse(
            content={"ok": True, "ad": ad, "placement": placement, "status": status}
        )

    @router.post("/api/v3/ad/view")
    async def v3_ad_view(request: Request):
        """Reklama ko'rilganini yozadi — kunlik chegara shu qatorlardan sanaladi."""
        payload = await _body(request)
        telegram_id = _telegram_id(request, payload)
        if not telegram_id:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )

        placement = normalize_placement(payload.get("placement"))
        try:
            ad_id = int(payload.get("ad_id") or 0)
        except (TypeError, ValueError):
            ad_id = 0
        if ad_id <= 0:
            return JSONResponse(
                status_code=400, content={"ok": False, "error": "invalid_ad_id"}
            )
        try:
            watched = int(payload.get("watched_seconds") or 0)
        except (TypeError, ValueError):
            watched = 0

        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
            if not user:
                return JSONResponse(
                    status_code=403, content={"ok": False, "error": "access_start_first"}
                )
            service = AdPlacementService(session)
            result = await service.record_view(
                user,
                placement=placement,
                ad_id=ad_id,
                watched_seconds=watched,
                level=str(payload.get("level") or "")[:16],
                lesson_order=payload.get("lesson_order"),
            )
            if not result.get("ok"):
                return JSONResponse(status_code=400, content=result)
            status = await service.status(user, placement=placement, client=CLIENT)
            await session.commit()

        await ConversionFunnelService().record(
            event_name="ad_shown" if watched else "ad_skipped",
            user=user,
            source=f"ad_{placement}",
            payload={"placement": placement, "watched_seconds": watched},
        )
        return JSONResponse(content={**result, "status": status})

    @router.post("/api/v3/ad/status")
    async def v3_ad_status(request: Request):
        """Har joy uchun bugungi holat — klient reklama so'rashdan oldin biladi."""
        payload = await _body(request)
        telegram_id = _telegram_id(request, payload)
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
            service = AdPlacementService(session)
            placements = {
                placement: await service.status(
                    user, placement=placement, client=CLIENT
                )
                for placement in AD_PLACEMENTS
            }
        return JSONResponse(content={"ok": True, "placements": placements})

    return router
