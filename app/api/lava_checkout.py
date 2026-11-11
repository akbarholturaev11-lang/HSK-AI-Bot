"""HTTP adapters for the lava.top checkout path.

- ``POST /api/payments/lava/webhook``: provider webhook (secret-authenticated).
- ``/api/subscription-miniapp/lava/*``: Telegram Mini App (signed initData).
- ``/api/v3/pwa/subscription/lava/*``: learner iPhone PWA (cookie + CSRF + origin).
- ``GET /pay/lava/return``: neutral return page; never proof of payment.

Authorization stays in each transport; money decisions live in
``app.services.lava``. The webhook is independent of the sales flag.
"""
from __future__ import annotations

import logging
from html import escape
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.bot.utils.i18n import t
from app.repositories.user_repo import UserRepository
from app.services.lava import events
from app.services.lava.checkout import LavaCheckoutError, LavaCheckoutService
from app.services.lava.terms import LAVA_PLAN_TYPES
from app.services.telegram_webapp_auth import extract_verified_webapp_user_id

logger = logging.getLogger(__name__)

_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
_LANGS = {"uz", "ru", "tj"}
_PWA_INLINE_SOURCES = frozenset({
    "v3_locked_lesson", "v3_pronunciation_limit", "v3_recognition_limit",
    "v3_memorize_limit", "v3_test_limit", "v3_mistake_review",
    "v3_voice_limit", "v3_qa_limit",
})


class LavaStartBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_type: str = Field(max_length=16)
    email: str = Field(max_length=254)
    language: str | None = Field(default=None, max_length=8)
    # Checkout context; the server re-resolves any discount itself.
    mode: str | None = Field(default=None, max_length=32)
    campaign_id: int | None = Field(default=None, gt=0)
    feedback_id: int | None = Field(default=None, gt=0)
    # Optional PWA-only analytics correlation, not a billing entitlement.
    attempt_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9:.-]+$")
    ui_source: str | None = Field(default=None, max_length=80, pattern=r"^[a-z0-9_]+$")


class AndroidLavaContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["subscription", "exit_discount"] = "subscription"
    origin: str = Field(default="", max_length=40)


class AndroidExitAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["view", "claim"]


class LavaStatusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checkout_id: int = Field(gt=0)


class LavaEmptyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


async def _bounded_body(request: Request, limit: int) -> bytes | None:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


def _checkout_error(exc: LavaCheckoutError) -> JSONResponse:
    return JSONResponse({"ok": False, "error": exc.code}, status_code=exc.status, headers=_NO_STORE)


async def attach_lava_block(session, runtime, user, result: dict, *, mode: str | None,
                            supports_lava: bool, campaign_id: int | None = None,
                            feedback_id: int | None = None) -> dict:
    """Add the optional ``lava`` key to an existing checkout overview.

    Plain Pro subscription qualifies; discount flows qualify only when an
    admin-mapped lava promo code carries the same discount. HSK 3.0 stays
    manual. Without a block the overview stays byte-identical."""
    if not isinstance(result, dict) or not result.get("ok") or user is None or runtime is None:
        return result
    from app.services.lava.checkout import CHECKOUT_CONTEXT_MODES
    if (mode or "") not in CHECKOUT_CONTEXT_MODES:
        return result
    try:
        block = await LavaCheckoutService(runtime).overview_block(
            session, user, supports_lava=supports_lava, context_mode=mode or "subscription",
            campaign_id=campaign_id, feedback_id=feedback_id)
    except Exception:  # noqa: BLE001 - lava trouble must never break manual checkout
        logger.exception("lava.top overview block unavailable")
        return result
    if block is not None:
        result["lava"] = block
    return result


def create_lava_router(*, runtime_getter, session_factory, settings_obj) -> APIRouter:
    router = APIRouter()

    async def _parse(request: Request, model, limit: int = 2048):
        if request.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise LavaCheckoutError("invalid_request", 415)
        raw = await _bounded_body(request, limit)
        if raw is None:
            raise LavaCheckoutError("invalid_request", 413)
        try:
            return model.model_validate_json(raw or b"{}")
        except ValidationError:
            raise LavaCheckoutError("invalid_request", 422) from None

    async def _start(user, data: LavaStartBody, source: str):
        is_inline = (
            source == "pwa" and bool(data.attempt_id)
            and data.ui_source in _PWA_INLINE_SOURCES
        )
        if data.plan_type not in LAVA_PLAN_TYPES:
            raise LavaCheckoutError("plan_unavailable", 400)
        result = await LavaCheckoutService(runtime_getter()).start(
            session_factory, user_id=user.id, plan_type=data.plan_type, email=data.email,
            source=source, language=data.language or getattr(user, "language", None),
            context_mode=data.mode, campaign_id=data.campaign_id, feedback_id=data.feedback_id,
            analytics_attempt_id=data.attempt_id if is_inline else None,
            analytics_source=data.ui_source if is_inline else None,
            pwa_inline_return=is_inline,
        )
        if is_inline and result.get("ok"):
            from app.services.conversion_funnel_service import ConversionFunnelService
            # A checkout is counted ONLY after a real provider invoice exists.
            await ConversionFunnelService().record(
                event_name="pwa_pro_checkout_started", user=user,
                source=(data.ui_source or "iphone_pwa")[:80],
                payload={
                    "checkout_id": result.get("checkout_id"),
                    "attempt_id": data.attempt_id or "",
                    "plan_type": data.plan_type,
                    "payment_method": "lava",
                    "mode": data.mode or "subscription",
                    "transport": "iphone_pwa",
                },
            )
        if source == "android" and result.get("ok"):
            from app.services.conversion_funnel_service import ConversionFunnelService
            await ConversionFunnelService().record(
                event_name="checkout_opened", user=user, source="android_subscription",
                payload={"attempt_id": "android-lava-" + str(result["checkout_id"]),
                         "mode": data.mode or "subscription", "payment_method": "lava",
                         "transport": "android"})
        return result

    # -- provider webhook -------------------------------------------------
    @router.post("/api/payments/lava/webhook")
    async def lava_webhook(request: Request):
        runtime = runtime_getter()
        if runtime is None:
            return JSONResponse({"ok": False}, status_code=404)
        raw = await _bounded_body(request, events.MAX_WEBHOOK_BYTES)
        if raw is None:
            return JSONResponse({"ok": False}, status_code=413)
        status, body = await events.ingest(
            runtime, raw, api_key_header=request.headers.get("X-Api-Key"), client_ip=_client_ip(request),
        )
        return JSONResponse(body, status_code=status)

    # -- Telegram Mini App -------------------------------------------------
    async def _miniapp_user(request: Request):
        telegram_id = extract_verified_webapp_user_id(
            request.headers.get("X-Telegram-Init-Data", ""), getattr(settings_obj, "BOT_TOKEN", ""))
        if not telegram_id:
            raise LavaCheckoutError("invalid_telegram_init_data", 401)
        async with session_factory() as session:
            user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if user is None:
            raise LavaCheckoutError("access_start_first", 404)
        return user

    @router.post("/api/subscription-miniapp/lava/start")
    async def miniapp_lava_start(request: Request):
        try:
            user = await _miniapp_user(request)
            data = await _parse(request, LavaStartBody)
            return JSONResponse(await _start(user, data, "miniapp"), headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/subscription-miniapp/lava/status")
    async def miniapp_lava_status(request: Request):
        try:
            user = await _miniapp_user(request)
            data = await _parse(request, LavaStatusBody)
            result = await LavaCheckoutService(runtime_getter()).status(
                session_factory, user_id=user.id, checkout_id=data.checkout_id)
            return JSONResponse(result, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/subscription-miniapp/lava/cancel")
    async def miniapp_lava_cancel(request: Request):
        try:
            user = await _miniapp_user(request)
            await _parse(request, LavaEmptyBody)
            result = await LavaCheckoutService(runtime_getter()).cancel(session_factory, user_id=user.id)
            return JSONResponse(result, status_code=200 if result.get("ok") else 409, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    # -- learner iPhone PWA -------------------------------------------------
    async def _pwa_user(request: Request):
        from app.services.pwa_auth_service import (
            PWA_SESSION_COOKIE, PwaAuthError, PwaAuthService, require_same_origin,
        )
        try:
            require_same_origin(request, settings_obj)
            if request.headers.get("X-Telegram-Init-Data"):
                raise LavaCheckoutError("invalid_request", 422)
            async with session_factory() as session:
                actor, _ = await PwaAuthService(session, settings_obj).mutation_actor(
                    request.cookies.get(PWA_SESSION_COOKIE), request.headers.get("X-HSK-PWA-CSRF"))
            return actor
        except PwaAuthError as exc:
            raise LavaCheckoutError(exc.code, exc.status_code) from None

    @router.post("/api/v3/pwa/subscription/lava/start")
    async def pwa_lava_start(request: Request):
        try:
            user = await _pwa_user(request)
            data = await _parse(request, LavaStartBody)
            return JSONResponse(await _start(user, data, "pwa"), headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/v3/pwa/subscription/lava/status")
    async def pwa_lava_status(request: Request):
        try:
            user = await _pwa_user(request)
            data = await _parse(request, LavaStatusBody)
            result = await LavaCheckoutService(runtime_getter()).status(
                session_factory, user_id=user.id, checkout_id=data.checkout_id)
            return JSONResponse(result, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/v3/pwa/subscription/lava/cancel")
    async def pwa_lava_cancel(request: Request):
        try:
            user = await _pwa_user(request)
            await _parse(request, LavaEmptyBody)
            result = await LavaCheckoutService(runtime_getter()).cancel(session_factory, user_id=user.id)
            return JSONResponse(result, status_code=200 if result.get("ok") else 409, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    # -- native Android Direct (no cookie or Telegram credential fallback) ---
    async def _android_user(request: Request):
        from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
        if (request.headers.get("X-HSK-Android-Channel") != "direct"
                or request.headers.get("X-HSK-Lava-Capability") != "1"
                or request.headers.get("X-Telegram-Init-Data") or request.headers.get("Cookie")):
            raise LavaCheckoutError("invalid_request", 422)
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise LavaCheckoutError("native_auth_required", 401)
        try:
            async with session_factory() as db:
                context = await DesktopAuthService(db, settings_obj).authenticate(token.strip())
                if context.device.platform != "android":
                    raise LavaCheckoutError("invalid_platform", 403)
                return context.user
        except DesktopAuthError as exc:
            raise LavaCheckoutError(exc.code, exc.status_code) from None

    @router.post("/api/v3/android/subscription/lava/overview")
    async def android_lava_overview(request: Request):
        try:
            user = await _android_user(request)
            data = await _parse(request, AndroidLavaContext)
            from app.api.android_features import ANDROID_CHECKOUT_ORIGIN_SOURCES
            if data.origin and (data.origin not in ANDROID_CHECKOUT_ORIGIN_SOURCES or data.origin.startswith("hsk30")):
                raise LavaCheckoutError("invalid_request", 422)
            async with session_factory() as db:
                block = await LavaCheckoutService(runtime_getter()).overview_block(
                    db, user, supports_lava=True, context_mode=data.mode)
                from sqlalchemy import select
                from datetime import datetime, timedelta, timezone
                from app.db.models.lava import LavaInvoice
                # Existing invoices/reservations remain recoverable even if
                # sales are disabled after the first request was committed.
                pending_id = await db.scalar(select(LavaInvoice.id).where(
                    LavaInvoice.user_id == user.id, LavaInvoice.source == "android",
                    LavaInvoice.kind == "first", LavaInvoice.status == "created",
                    LavaInvoice.created_at > datetime.now(timezone.utc) - timedelta(hours=24),
                ).order_by(LavaInvoice.id.desc()).limit(1))
                uncertain = await db.scalar(select(LavaInvoice.id).where(
                    LavaInvoice.user_id == user.id, LavaInvoice.source == "android",
                    LavaInvoice.review_reason == "create_uncertain",
                ).limit(1))
                if block is None and (pending_id or uncertain):
                    block = {"mode": "manual_only", "plans": [], "subscription": None}
                if block is not None:
                    block["pending_checkout_id"] = pending_id
                    if uncertain:
                        block["blocked_reason"] = "checkout_needs_review"
                    from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService
                    await SubscriptionEntryAnalyticsService(db).record_entry(
                        user=user, source=ANDROID_CHECKOUT_ORIGIN_SOURCES.get(data.origin, "android_subscription"),
                        mode=data.mode, payment_method="lava")
            return JSONResponse({"ok": True, "lava": block}, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/v3/android/subscription/lava/start")
    async def android_lava_start(request: Request):
        try:
            user = await _android_user(request)
            data = await _parse(request, LavaStartBody)
            if data.attempt_id or data.ui_source:
                raise LavaCheckoutError("invalid_request", 422)
            return JSONResponse(await _start(user, data, "android"), headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/v3/android/subscription/lava/status")
    async def android_lava_status(request: Request):
        try:
            user = await _android_user(request)
            data = await _parse(request, LavaStatusBody)
            result = await LavaCheckoutService(runtime_getter()).status(
                session_factory, user_id=user.id, checkout_id=data.checkout_id)
            return JSONResponse(result, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/v3/android/subscription/lava/cancel")
    async def android_lava_cancel(request: Request):
        try:
            user = await _android_user(request)
            await _parse(request, LavaEmptyBody)
            result = await LavaCheckoutService(runtime_getter()).cancel(session_factory, user_id=user.id)
            return JSONResponse(result, status_code=200 if result.get("ok") else 409, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    @router.post("/api/v3/android/subscription/lava/exit-offer")
    async def android_exit_offer(request: Request):
        from app.db.models.user import User
        from app.services.pwa_exit_offer_service import PwaExitOfferService
        try:
            user = await _android_user(request)
            data = await _parse(request, AndroidExitAction, limit=512)
            async with session_factory() as db:
                actor = await db.get(User, user.id)
                result = await PwaExitOfferService(db, settings_obj).action(actor, action=data.action)
                await db.commit()
            return JSONResponse(result, headers=_NO_STORE)
        except LavaCheckoutError as exc:
            return _checkout_error(exc)

    # -- neutral return page ------------------------------------------------
    @router.get("/pay/lava/return")
    async def lava_return_page(request: Request):
        lang = request.query_params.get("lang", "ru")
        lang = lang if lang in _LANGS else "ru"
        title = escape(t("bot.lava.return_title", lang))
        body = escape(t("bot.lava.return_body", lang))
        html = (
            "<!doctype html><html lang=\"" + lang + "\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex\"><title>HSK AI</title>"
            "<style>body{margin:0;font-family:-apple-system,system-ui,sans-serif;background:#f7f7f5;color:#1b1b1b;"
            "display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}"
            "main{max-width:420px;text-align:center}h1{font-size:22px;margin:0 0 12px}"
            "p{font-size:16px;line-height:1.5;margin:0;color:#4a4a4a}</style></head><body><main>"
            f"<h1>{title}</h1><p>{body}</p></main></body></html>"
        )
        return HTMLResponse(html, headers={**_NO_STORE, "X-Frame-Options": "DENY",
                                           "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})

    return router
