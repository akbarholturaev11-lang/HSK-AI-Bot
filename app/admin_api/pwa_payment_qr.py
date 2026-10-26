"""Bounded, passkey-bound replacement of subscription payment QR media.

QR images remain Telegram-hosted because existing checkout commands consume
Telegram file IDs. The PWA accepts bounded Alipay/WeChat standard, 20% and campaign QR targets;
no price, payment or access record is changed by uploading a QR.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from aiogram.types import BufferedInputFile
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError
from sqlalchemy import select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_marketing import _PWA_PROMO_IMAGE_TYPES, _validate_promo_image
from app.admin_api.pwa_payment_review import StrictModel, PositiveId
from app.admin_api.pwa_sessions import (
    ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session,
)
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post, _no_duplicate_json_keys
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment_qr_code import PaymentQrCode
from app.db.models.subscription_price import SubscriptionPrice
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.payment_qr_code_service import (
    PaymentQrCodeService, SUBSCRIPTION_QR_SCOPE, SUBSCRIPTION_DISCOUNT_20_QR_SCOPE,
)
from app.services.subscription_price_service import (
    DEFAULT_SUBSCRIPTION_PRICES, SubscriptionPriceService,
)

logger = logging.getLogger(__name__)
_MAX_BYTES = 1024 * 1024
_METHOD = Literal["alipay", "wechat"]
_PLAN = Literal["10_days", "1_month", "3_months"]
_SCOPE = Literal["subscription", "subscription_20", "admin_campaign"]


class ReadPaymentQr(StrictModel):
    method: _METHOD
    plan: _PLAN
    scope: _SCOPE = "subscription"
    campaign_id: PositiveId | None = None
    amount: Annotated[int, Field(strict=True, ge=1, le=1_000_000)] | None = None


class PreparePaymentQr(ReadPaymentQr):
    media_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    media_size: Annotated[int, Field(strict=True, ge=1, le=_MAX_BYTES)]


class PaymentQrCommand(PreparePaymentQr):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        return {
            "action": "subscription.qr_media",
            "target": (f"{self.method}-{self.plan}" if self.scope == "subscription" and self.amount is None
                       else f"{self.scope}-{self.campaign_id or 0}-{self.method}-{self.plan}-{self.amount or 0}"),
            "payload": {
                "method": self.method,
                "plan": self.plan,
                **({"scope": self.scope} if self.scope != "subscription" else {}),
                **({"campaign_id": self.campaign_id} if self.campaign_id is not None else {}),
                **({"amount": self.amount} if self.amount is not None else {}),
                "expected_hash": self.expected_hash,
                "media_sha256": self.media_sha256,
                "media_size": self.media_size,
            },
        }


class ExecutePaymentQr(PaymentQrCommand):
    step_up_id: StepId


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _price_raw(row):
    if row is None:
        return None
    return {
        "id": row.id,
        "method": row.payment_method,
        "plan": row.plan_type,
        "amount": row.amount,
        "currency": row.currency,
        "updated_by": row.updated_by_telegram_id,
        "updated_at": _utc(row.updated_at).isoformat(),
    }


def _qr_raw(row):
    if row is None:
        return None
    # Never return or audit the provider file ID. Its digest lets the reviewed
    # revision detect a competing replacement without exposing that identifier.
    return {
        "id": row.id,
        "scope": row.scope,
        "method": row.payment_method,
        "plan": row.plan_type,
        "amount": row.amount,
        "currency": row.currency,
        "file_hash": hashlib.sha256(row.file_id.encode("utf-8")).hexdigest(),
        "updated_at": _utc(row.updated_at).isoformat(),
    }


async def _price_row(db, method, plan, *, lock=False):
    query = select(SubscriptionPrice).where(
        SubscriptionPrice.payment_method == method,
        SubscriptionPrice.plan_type == plan,
    ).execution_options(populate_existing=True)
    return await db.scalar(query.with_for_update() if lock else query)


async def _target(db, method, plan, *, scope="subscription", campaign_id=None,
                  target_amount=None, lock=False):
    if scope not in {SUBSCRIPTION_QR_SCOPE, SUBSCRIPTION_DISCOUNT_20_QR_SCOPE, "admin_campaign"}:
        raise CommandError("invalid_payment_qr_target", 400)
    if (scope == "admin_campaign") != (campaign_id is not None):
        raise CommandError("invalid_payment_qr_target", 400)
    if scope == "admin_campaign" and target_amount is not None:
        raise CommandError("invalid_payment_qr_target", 400)
    price_row = await _price_row(db, method, plan, lock=lock)
    if price_row is None:
        base_amount, currency = DEFAULT_SUBSCRIPTION_PRICES[(method, plan)]
    else:
        base_amount, currency = SubscriptionPriceService._normalize_price(
            method, plan, price_row.amount, price_row.currency,
        )
    campaign = None
    if scope == "admin_campaign":
        campaign_query = select(DiscountCampaign).where(DiscountCampaign.id == campaign_id)
        campaign = await db.scalar(campaign_query.with_for_update() if lock else campaign_query)
        if (campaign is None or campaign.payment_method not in (None, method)
                or campaign.plan_type not in (None, plan) or plan not in ("10_days", "1_month")):
            raise CommandError("invalid_payment_qr_target", 409)
        percent = campaign.percent
        qr_scope = PaymentQrCodeService.admin_campaign_scope(campaign_id)
    elif scope == SUBSCRIPTION_DISCOUNT_20_QR_SCOPE:
        percent = 20
        qr_scope = scope
    else:
        percent = 0
        qr_scope = scope
    basis = target_amount if target_amount is not None else base_amount
    amount = basis if not percent else int(round(basis * (100 - percent) / 100))
    if amount < 1 or currency != "¥":
        raise CommandError("invalid_payment_qr_target", 409)
    query = select(PaymentQrCode).where(
        PaymentQrCode.scope == qr_scope,
        PaymentQrCode.payment_method == method,
        PaymentQrCode.plan_type == plan,
        PaymentQrCode.amount == amount,
        PaymentQrCode.currency == currency,
    ).execution_options(populate_existing=True)
    qr_row = await db.scalar(query.with_for_update() if lock else query)
    campaign_revision = (None if campaign is None else {
        "id": campaign.id, "percent": campaign.percent,
        "method": campaign.payment_method, "plan": campaign.plan_type,
        "ends_at": _utc(campaign.ends_at).isoformat(),
    })
    revision = _hash({"price": _price_raw(price_row), "qr": _qr_raw(qr_row),
                      "scope": qr_scope, "amount": amount, "campaign": campaign_revision})
    current = {
        "method": method, "plan": plan, "scope": scope,
        "campaign_id": campaign_id, "discount_percent": percent,
        "amount": amount, "currency": currency,
        "qr_set": qr_row is not None, "revision_hash": revision,
    }
    return price_row, qr_row, current

async def _authenticate(db, cookie, settings_obj):
    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
    if actor is None or actor.auth_method != "webauthn":
        raise CommandError("admin_pwa_unauthorized", 401)
    return actor


async def read_payment_qr(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        await _authenticate(db, session_cookie, settings_obj)
        _, _, current = await _target(db, request.method, request.plan, scope=request.scope,
                                      campaign_id=request.campaign_id, target_amount=request.amount)
    return {"qr": current}


async def prepare_payment_qr(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        await _authenticate(db, session_cookie, settings_obj)
        _, _, current = await _target(db, request.method, request.plan, scope=request.scope,
                                      campaign_id=request.campaign_id, target_amount=request.amount)
        command = PaymentQrCommand(**request.model_dump(), expected_hash=current["revision_hash"])
    return {"operation": command.operation(), "current": current}


async def _preflight(db, *, cookie, request, settings_obj):
    """Check proof and target before Bot IO; the write transaction checks again."""
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    operation = request.operation()
    digest = operation_digest(**operation)
    async with db.begin():
        actor = await _authenticate(db, cookie, settings_obj)
        step = await db.get(AdminPwaStepUp, request.step_up_id)
        session = await db.get(AdminPwaSession, step.session_id) if step else None
        cookie_hash = hashlib.sha256(cookie.encode("ascii")).hexdigest()
        current_session = await db.scalar(select(AdminPwaSession).where(
            AdminPwaSession.token_hash == cookie_hash,
        ))
        now = datetime.now(timezone.utc)
        if (step is None or session is None or current_session is None
                or step.session_id != current_session.id or step.status != "verified"
                or step.verified_at is None or step.consumed_at is not None
                or step.action != operation["action"] or step.target != operation["target"]
                or step.payload_hash != digest
                or int(step.user_id) != int(actor.user_id)
                or _utc(step.expires_at) <= now or _utc(session.expires_at) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        _, _, current = await _target(db, request.method, request.plan, scope=request.scope,
                                      campaign_id=request.campaign_id, target_amount=request.amount)
        if current["revision_hash"] != request.expected_hash:
            raise CommandError("confirmation_changed", 409)
        return actor.telegram_id, current


async def _remove_provider_message(bot_client, chat_id, message_id):
    if bot_client is None or message_id is None:
        return
    try:
        await bot_client.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logger.warning("Admin PWA QR upload compensation needs review")


async def _is_referenced(session_factory, request, file_id):
    """Return True/False if DB proves the Bot asset is referenced/unreferenced."""
    try:
        async with session_factory() as db:
            async with db.begin():
                found = await db.scalar(select(PaymentQrCode.id).where(
                    PaymentQrCode.scope == (PaymentQrCodeService.admin_campaign_scope(request.campaign_id)
                                            if request.scope == 'admin_campaign' else request.scope),
                    PaymentQrCode.payment_method == request.method,
                    PaymentQrCode.plan_type == request.plan,
                    PaymentQrCode.file_id == file_id,
                ).limit(1))
                return found is not None
    except Exception:
        # An unknown commit outcome must preserve an asset that may be live.
        return None


async def execute_payment_qr(
    *, session_factory, bot_client, session_cookie, request, settings_obj,
    media_bytes: bytes, media_content_type: str,
):
    operation = request.operation()
    if (not isinstance(media_bytes, bytes) or len(media_bytes) != request.media_size
            or len(media_bytes) > _MAX_BYTES
            or hashlib.sha256(media_bytes).hexdigest() != request.media_sha256):
        raise CommandError("admin_pwa_invalid_media", 400)
    if media_content_type not in _PWA_PROMO_IMAGE_TYPES:
        raise CommandError("admin_pwa_invalid_media", 400)
    try:
        extension = _validate_promo_image(media_bytes, media_content_type)
    except CommandError as exc:
        raise CommandError("admin_pwa_invalid_media", 400) from exc
    # The generic validator caps 8M pixels and one frame; QR's byte limit is
    # smaller than the shared promo validator's cap and was checked above.
    actor_id = None
    async with session_factory() as db:
        actor_id, _ = await _preflight(
            db, cookie=session_cookie, request=request, settings_obj=settings_obj,
        )
    if bot_client is None:
        raise CommandError("admin_pwa_qr_provider_unavailable", 503)
    sent = None
    message_id = None
    try:
        sent = await bot_client.send_photo(
            chat_id=actor_id,
            photo=BufferedInputFile(media_bytes, filename="payment-qr" + extension),
        )
        message_id = getattr(sent, "message_id", None)
        photo = getattr(sent, "photo", None) or []
        file_id = str(getattr(photo[-1], "file_id", "") or "") if photo else ""
        if not file_id or len(file_id) > 512:
            raise ValueError("provider returned no usable media identifier")
    except Exception as exc:
        await _remove_provider_message(bot_client, actor_id, message_id)
        logger.warning("Admin PWA QR media provider upload failed")
        raise CommandError("admin_pwa_qr_upload_failed", 502) from exc

    try:
        async with session_factory() as db:
            async with db.begin():
                if db.get_bind().dialect.name == "postgresql":
                    await db.execute(text("SET LOCAL lock_timeout = '5000'"))
                    await db.execute(text("SET LOCAL statement_timeout = '8000'"))
                if not await consume_step_up_in_mutation(
                    db, session_cookie=session_cookie,
                    step_up_id=request.step_up_id, settings_obj=settings_obj,
                    **operation,
                ):
                    raise CommandError("admin_pwa_step_up_denied", 403)
                step = await db.get(AdminPwaStepUp, request.step_up_id)
                session = await db.get(AdminPwaSession, step.session_id)
                actor = await db.get(User, step.user_id)
                # The image is hosted by Telegram; lock the price target and
                # its exact QR key only for this short DB transaction.
                _, _, observed = await _target(db, request.method, request.plan, scope=request.scope,
                                      campaign_id=request.campaign_id, target_amount=request.amount)
                keys = sorted((
                    f"payment_qr:{PaymentQrCodeService.admin_campaign_scope(request.campaign_id) if request.scope == 'admin_campaign' else request.scope}:{request.method}:{request.plan}:{observed['amount']}:{observed['currency']}",
                    f"subscription_price:{request.method}:{request.plan}",
                ))
                lock_repo = BotSettingRepository(db)
                for key in keys:
                    await lock_repo.lock_key(key)
                _, _, current = await _target(db, request.method, request.plan, scope=request.scope,
                                      campaign_id=request.campaign_id, target_amount=request.amount, lock=True)
                now = datetime.now(timezone.utc)
                if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                        or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
                    raise CommandError("admin_pwa_step_up_denied", 403)
                if current["revision_hash"] != request.expected_hash:
                    raise CommandError("confirmation_changed", 409)
                before_hash = current["revision_hash"]
                await PaymentQrCodeService(db).save_qr_codes([{
                    "scope": (PaymentQrCodeService.admin_campaign_scope(request.campaign_id)
                              if request.scope == "admin_campaign" else request.scope),
                    "payment_method": request.method,
                    "plan_type": request.plan,
                    "amount": current["amount"],
                    "currency": current["currency"],
                    "file_id": file_id,
                }], created_by_telegram_id=actor.telegram_id)
                _, _, after = await _target(db, request.method, request.plan, scope=request.scope,
                                      campaign_id=request.campaign_id, target_amount=request.amount)
                audit_id = str(uuid4())
                db.add(AdminPwaCommandAudit(
                    id=audit_id, step_up_id=step.id, actor_user_id=actor.id,
                    target_user_id=None, action=operation["action"],
                    target=operation["target"], payload_hash=operation_digest(**operation),
                    result_json=json.dumps({
                        "before_hash": before_hash,
                        "after_hash": after["revision_hash"],
                    }, sort_keys=True),
                ))
                await db.flush()
        return {"command_id": audit_id, "qr": after}
    except Exception:
        # The Bot upload precedes the short SQL transaction because no DB
        # connection is held across provider IO. Compensate only when a fresh
        # read proves the file_id is not referenced; preserve on uncertainty.
        referenced = await _is_referenced(session_factory, request, file_id)
        if referenced is False:
            await _remove_provider_message(bot_client, actor_id, message_id)
        raise


def create_admin_pwa_payment_qr_router(*, settings_obj, session_factory, bot_client=None):
    router = APIRouter(tags=["admin-pwa-payment-qr"])

    async def handle(request, task, schema):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            parsed = schema.model_validate(await _body(request, 2048))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                result = await task(db, session_cookie=cookie, request=parsed,
                                    settings_obj=settings_obj)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA payment QR command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/payment-qr/read")
    async def read(request: Request):
        return await handle(request, read_payment_qr, ReadPaymentQr)

    @router.post("/api/admin/v1/payment-qr/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_payment_qr, PreparePaymentQr)

    @router.post("/api/admin/v1/payment-qr/media/save")
    async def save_media(request: Request):
        failure = _gate(request, settings_obj)
        if failure is not None:
            return failure
        origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
        if (request.headers.getlist("origin") != [origin]
                or request.headers.get("sec-fetch-site", "same-origin") != "same-origin"):
            return _reply(403, "admin_pwa_csrf")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in _PWA_PROMO_IMAGE_TYPES:
            return _reply(415, "unsupported_media_type")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        encoded_command = request.headers.get("x-admin-pwa-command", "")
        if not encoded_command or len(encoded_command) > 8192:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            raw = json.loads(encoded_command, object_pairs_hook=_no_duplicate_json_keys)
            parsed = ExecutePaymentQr.model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                async with db.begin():
                    await _authenticate(db, cookie, settings_obj)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA payment QR media authentication unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        declared = request.headers.get("content-length")
        if declared:
            try:
                if int(declared) > _MAX_BYTES:
                    return _reply(413, "admin_pwa_media_too_large")
            except ValueError:
                return _reply(400, "admin_pwa_invalid_payload")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > _MAX_BYTES:
                return _reply(413, "admin_pwa_media_too_large")
            data.extend(chunk)
        if len(data) != parsed.media_size:
            return _reply(400, "admin_pwa_invalid_media")
        try:
            result = await execute_payment_qr(
                session_factory=session_factory, bot_client=bot_client,
                session_cookie=cookie, request=parsed, settings_obj=settings_obj,
                media_bytes=bytes(data), media_content_type=content_type,
            )
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA payment QR media command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    return router
