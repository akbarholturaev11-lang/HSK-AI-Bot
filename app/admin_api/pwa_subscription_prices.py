"""First-party subscription prices with exact passkey proof and raw-state CAS.

Canonical currency/default/normalization and writes remain owned by the shared
subscription service. No billing, access, payment or external MCP mutation.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError
from sqlalchemy import select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_sessions import (
    ADMIN_PWA_COOKIE_NAME, _authorized_admin, authenticate_admin_pwa_session,
)
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.subscription_price import SubscriptionPrice
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.subscription_price_service import (
    DEFAULT_SUBSCRIPTION_PRICES, PAYMENT_METHODS, PLANS, SubscriptionPriceService,
)

logger = logging.getLogger(__name__)


class EmptyPriceRequest(StrictModel):
    pass


class PrepareSubscriptionPrice(StrictModel):
    method: Literal["visa", "alipay", "wechat"]
    plan: Literal["10_days", "1_month", "3_months"]
    amount: Annotated[int, Field(strict=True, ge=1, le=1_000_000)]


class SubscriptionPriceCommand(PrepareSubscriptionPrice):
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        return {"action": "subscription.prices", "target": f"{self.method}-{self.plan}",
                "payload": self.model_dump()}


class ExecuteSubscriptionPrice(SubscriptionPriceCommand):
    step_up_id: StepId


def _revision(row):
    # Hash the stored state, including legacy currency and missing-row state;
    # display normalization must never conceal an intervening configuration
    # write. No internal actor/row metadata leaves the server except this hash.
    raw = None if row is None else {
        "id": row.id, "method": row.payment_method, "plan": row.plan_type,
        "amount": row.amount, "currency": row.currency,
        "updated_by": row.updated_by_telegram_id,
        "updated_at": _utc(row.updated_at).isoformat(),
    }
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _public_price(method, plan, row):
    if row is None:
        amount, currency = DEFAULT_SUBSCRIPTION_PRICES[(method, plan)]
    else:
        amount, currency = SubscriptionPriceService._normalize_price(
            method, plan, row.amount, row.currency)
    return {"method": method, "plan": plan, "amount": amount, "currency": currency,
            "target": f"{method}-{plan}", "revision_hash": _revision(row)}


async def _row(db, method, plan, *, lock=False):
    if lock:
        await BotSettingRepository(db).lock_key(f"subscription_price:{method}:{plan}")
    query = select(SubscriptionPrice).where(
        SubscriptionPrice.payment_method == method, SubscriptionPrice.plan_type == plan,
    ).execution_options(populate_existing=True)
    return await db.scalar(query.with_for_update() if lock else query)


async def _authenticate(db, cookie, settings_obj):
    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
    if actor is None or actor.auth_method != "webauthn":
        raise CommandError("admin_pwa_unauthorized", 401)
    return actor


async def read_subscription_prices(db, *, session_cookie, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        await _authenticate(db, session_cookie, settings_obj)
        # Exactly nine allowlisted targets, read in one bounded query. Unknown
        # legacy targets do not expand the response or require a table scan.
        rows = (await db.scalars(select(SubscriptionPrice).where(
            SubscriptionPrice.payment_method.in_(PAYMENT_METHODS),
            SubscriptionPrice.plan_type.in_(PLANS),
        ).limit(9))).all()
        stored = {(row.payment_method, row.plan_type): row for row in rows}
        prices = [_public_price(method, plan, stored.get((method, plan)))
                  for method in PAYMENT_METHODS for plan in PLANS]
    return {"prices": prices}


async def prepare_subscription_price(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with db.begin():
        await _authenticate(db, session_cookie, settings_obj)
        row = await _row(db, request.method, request.plan)
        current = _public_price(request.method, request.plan, row)
        if request.method in {"alipay", "wechat"} and request.amount != current["amount"]:
            # QR-backed prices must change together with a matching QR image;
            # the dedicated payment-qr signed command handles both atomically.
            raise CommandError("admin_pwa_payment_qr_required", 409)
        command = SubscriptionPriceCommand(**request.model_dump(), expected_hash=_revision(row))
    return {"operation": command.operation(), "current": current}


async def execute_subscription_price(db, *, session_cookie, request, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = SubscriptionPriceCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    operation = command.operation()
    async with db.begin():
        if db.get_bind().dialect.name == "postgresql":
            await db.execute(text("SET LOCAL lock_timeout = '5000'"))
            await db.execute(text("SET LOCAL statement_timeout = '8000'"))
        if not await consume_step_up_in_mutation(db, session_cookie=session_cookie,
                step_up_id=request.step_up_id, settings_obj=settings_obj, **operation):
            raise CommandError("admin_pwa_step_up_denied", 403)
        step = await db.get(AdminPwaStepUp, request.step_up_id)
        session = await db.get(AdminPwaSession, step.session_id)
        actor = await db.get(User, step.user_id)
        row = await _row(db, command.method, command.plan, lock=True)
        now = datetime.now(timezone.utc)
        if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
                or min(_utc(step.expires_at), _utc(session.expires_at)) <= now):
            raise CommandError("admin_pwa_step_up_denied", 403)
        if _revision(row) != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        before = _public_price(command.method, command.plan, row)
        if command.method in {"alipay", "wechat"} and command.amount != before["amount"]:
            raise CommandError("admin_pwa_payment_qr_required", 409)
        price = await SubscriptionPriceService(db).set_price(
            payment_method=command.method, plan_type=command.plan, amount=command.amount,
            updated_by_telegram_id=actor.telegram_id)
        if price is None:
            raise CommandError("invalid_subscription_price", 400)
        row = await _row(db, command.method, command.plan)
        after = _public_price(command.method, command.plan, row)
        audit_id = str(uuid4())
        db.add(AdminPwaCommandAudit(id=audit_id, step_up_id=step.id,
            actor_user_id=actor.id, target_user_id=None, action=operation["action"],
            target=operation["target"], payload_hash=operation_digest(**operation),
            result_json=json.dumps({"before": before, "after": after}, sort_keys=True)))
        await db.flush()
    return {"command_id": audit_id, "price": after}


def create_admin_pwa_subscription_prices_router(*, settings_obj, session_factory):
    router = APIRouter(tags=["admin-pwa-subscription-prices"])

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
                result = await task(db, session_cookie=cookie, settings_obj=settings_obj,
                                    **({} if schema is EmptyPriceRequest else {"request": parsed}))
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.error("Admin PWA subscription price command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/subscription-prices/read")
    async def read(request: Request):
        return await handle(request, read_subscription_prices, EmptyPriceRequest)

    @router.post("/api/admin/v1/subscription-prices/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_subscription_price, PrepareSubscriptionPrice)

    @router.post("/api/admin/v1/subscription-prices/save")
    async def save(request: Request):
        return await handle(request, execute_subscription_price, ExecuteSubscriptionPrice)

    return router
