"""First-party Admin PWA control of the lava.top second checkout path.

Read: status, connection preflight (provider catalog), config and bounded
lists. Commands (exact passkey proof + content-free audit):

- ``lava.settings``  mode, currency and the four lava terms (CAS on config)
- ``lava.recheck``   re-verify one contract with the lava API and apply it
- ``lava.link``      attach an unmatched contract to an explicit account
- ``lava.cancel``    turn off a learner's auto-renewal (paid term kept)
- ``lava.chargeback`` close an open chargeback as won (days restored) or lost

Secrets are never read back or editable here. Provider IO never runs inside
the proof transaction; ``manual_only`` can always be saved without lava.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError
from sqlalchemy import func, or_, select, text

from app.admin_api.pwa_access_grants import CommandError, StepId
from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_payment_review import StrictModel
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session, _authorized_admin
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.admin_api.pwa_webauthn_transport import _body, _guard_post
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.bot_setting import BotSetting
from app.db.models.lava import LavaInvoice, LavaWebhookEvent
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.lava import events, ledger
from app.services.lava.checkout import LavaCheckoutError, LavaCheckoutService
from app.services.lava.client import LavaError
from app.services.lava.config import (
    LAVA_CONFIG_KEY, LavaConfig, LavaConfigError, LavaTermConfig, config_from_dict, effective_mode,
    parse_config, sales_configured,
)
from app.services.lava.events import LAST_AUTH_FAILURE_KEY, LAST_WEBHOOK_KEY
from app.services.lava.preflight import check_config_against_catalog, offer_catalog, run_preflight
from app.services.lava.reconcile import LAST_RUN_KEY
from app.services.lava.terms import CHECKOUT_MODES, LAVA_CURRENCIES, LAVA_PLAN_TYPES

logger = logging.getLogger(__name__)

_UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
_LIST_LIMIT = 20


class EmptyLavaRequest(StrictModel):
    pass


class LavaTermInput(StrictModel):
    enabled: bool
    offer_id: Annotated[str, Field(max_length=36, pattern=r"^$|" + _UUID)]


class LavaSettingsInput(StrictModel):
    checkout_mode: Literal["manual_only", "lava_only", "both"]
    currency: Literal["USD", "RUB"]
    plans: dict[Literal["1_month", "3_months", "6_months", "12_months"], LavaTermInput]
    # "<referral|feedback_price_offer|admin_campaign>:<percent>" -> lava promo
    # code; validated by the shared config parser (lava 3-36 char rule).
    promo_codes: dict[Annotated[str, Field(max_length=32)], Annotated[str, Field(max_length=36)]] = Field(
        default_factory=dict, max_length=12)


class LavaSettingsCommand(LavaSettingsInput):
    # Exact prices the admin saw; persisted as the buyer-facing snapshot.
    prices: dict[Literal["1_month", "3_months", "6_months", "12_months"],
                 Annotated[str, Field(max_length=16, pattern=r"^[0-9]{1,8}\.[0-9]{2}$")]]
    expected_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def operation(self):
        return {"action": "lava.settings", "target": "global", "payload": self.model_dump()}


class ExecuteLavaSettings(LavaSettingsCommand):
    step_up_id: StepId


class LavaActionInput(StrictModel):
    kind: Literal["recheck", "link", "cancel", "chargeback"]
    invoice_id: Annotated[int, Field(strict=True, ge=1)] | None = None
    user_id: Annotated[int, Field(strict=True, ge=1)] | None = None
    plan_type: Literal["1_month", "3_months", "6_months", "12_months"] | None = None
    outcome: Literal["won", "lost"] | None = None


class LavaActionCommand(LavaActionInput):
    def operation(self):
        target = (f"user-{self.user_id}" if self.kind == "cancel" else f"invoice-{self.invoice_id}")
        return {"action": f"lava.{self.kind}", "target": target, "payload": self.model_dump()}


class ExecuteLavaAction(LavaActionCommand):
    step_up_id: StepId


def _validate_action(command: LavaActionInput) -> None:
    need = {
        "recheck": ("invoice_id",), "link": ("invoice_id", "user_id", "plan_type"),
        "cancel": ("user_id",), "chargeback": ("invoice_id", "outcome"),
    }[command.kind]
    allowed = set(need) | {"kind"}
    for field in ("invoice_id", "user_id", "plan_type", "outcome"):
        value = getattr(command, field)
        if field in need and value is None:
            raise CommandError("admin_pwa_invalid_payload", 400)
        if field not in allowed and value is not None:
            raise CommandError("admin_pwa_invalid_payload", 400)


async def _actor(db, cookie, settings_obj):
    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
    if actor is None or actor.auth_method != "webauthn":
        raise CommandError("admin_pwa_unauthorized", 401)
    return actor


async def _config_hash(db, *, lock: bool = False) -> tuple[str, LavaConfig]:
    if lock:
        await BotSettingRepository(db).lock_key(LAVA_CONFIG_KEY)
    statement = select(BotSetting.value, BotSetting.updated_at).where(BotSetting.key == LAVA_CONFIG_KEY)
    row = (await db.execute(statement.with_for_update() if lock else statement)).first()
    raw = json.dumps(None if row is None else [row.value, _utc(row.updated_at).isoformat()],
                     ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest(), parse_config(row.value if row else None)


def _mask(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, _, domain = email.partition("@")
    return (local[:1] + "***@" + domain)[:80]


def _iso(value) -> str | None:
    return _utc(value).isoformat() if value is not None else None


def _invoice_row(row: LavaInvoice) -> dict:
    return {
        "id": row.id, "contract": row.contract_id[:8], "kind": row.kind, "user_id": row.user_id,
        "plan_type": row.plan_type, "status": row.status, "subscription_status": row.subscription_status,
        "review_reason": row.review_reason,
        "amount": None if row.paid_amount is None else str(row.paid_amount), "currency": row.currency,
        "email": _mask(row.buyer_email), "created_at": _iso(row.created_at), "paid_at": _iso(row.paid_at),
    }


async def _setting(db, key):
    return await BotSettingRepository(db).get(key)


async def read_lava(db, *, session_cookie, settings_obj):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        await _actor(db, session_cookie, settings_obj)
        digest, config = await _config_hash(db)
        now = datetime.now(timezone.utc)
        counts = {
            "active_subscriptions": await db.scalar(select(func.count(LavaInvoice.id)).where(
                LavaInvoice.kind.in_(("first", "external")), LavaInvoice.status == "paid",
                or_(LavaInvoice.subscription_status.is_(None), LavaInvoice.subscription_status == "active"))),
            "paid_30d": await db.scalar(select(func.count(LavaInvoice.id)).where(
                LavaInvoice.status == "paid", LavaInvoice.paid_at >= now - timedelta(days=30))),
            "queued_events": await db.scalar(select(func.count(LavaWebhookEvent.id)).where(
                LavaWebhookEvent.result.in_(("queued", "retry")))),
            "review_events": await db.scalar(select(func.count(LavaWebhookEvent.id)).where(
                LavaWebhookEvent.result == "needs_review")),
        }
        attention = (await db.execute(select(LavaInvoice).where(or_(
            LavaInvoice.status.in_(("unmatched", "chargeback_open")),
            LavaInvoice.review_reason.is_not(None) & (LavaInvoice.review_reason != "reserving"),
        )).order_by(LavaInvoice.id.desc()).limit(_LIST_LIMIT))).scalars().all()
        recent = (await db.execute(select(LavaInvoice).where(
            LavaInvoice.status.in_(("paid", "refunded", "chargeback_won", "chargeback_lost")),
        ).order_by(LavaInvoice.id.desc()).limit(_LIST_LIMIT))).scalars().all()
        reviews = (await db.execute(select(LavaWebhookEvent).where(
            LavaWebhookEvent.result == "needs_review").order_by(LavaWebhookEvent.id.desc())
            .limit(_LIST_LIMIT))).scalars().all()
        status = {
            "sales_flag": getattr(settings_obj, "LAVA_ENABLED", False) is True,
            "api_key_configured": bool(getattr(settings_obj, "LAVA_API_KEY", "")),
            "webhook_secret_configured": bool(getattr(settings_obj, "LAVA_WEBHOOK_SECRET", "")),
            "processing_paused": getattr(settings_obj, "LAVA_PROCESSING_PAUSED", False) is True,
            "effective_mode": effective_mode(config, settings_obj, client_supports_lava=True),
            "last_webhook_at": await _setting(db, LAST_WEBHOOK_KEY),
            "last_auth_failure_at": await _setting(db, LAST_AUTH_FAILURE_KEY),
            "last_reconcile_at": await _setting(db, LAST_RUN_KEY),
        }
    return {"lava": {
        "status": status, "counts": counts, "config": config.to_json(), "config_hash": digest,
        "attention": [_invoice_row(row) for row in attention],
        "recent": [_invoice_row(row) for row in recent],
        "events": [{"id": event.id, "type": event.event_type, "error": event.error_code,
                    "amount": None if event.amount is None else str(event.amount), "currency": event.currency,
                    "received_at": _iso(event.received_at)} for event in reviews],
    }}


async def read_lava_catalog(db, *, session_cookie, settings_obj, runtime_getter):
    """Connection preflight. Authentication closes before provider IO."""
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    async with read_transaction(db):
        await _actor(db, session_cookie, settings_obj)
        _, config = await _config_hash(db)
    runtime = runtime_getter()
    client = runtime.client() if runtime is not None and getattr(settings_obj, "LAVA_API_KEY", "") else None
    report = await run_preflight(client, config, settings_obj=settings_obj)
    return {"preflight": report.as_dict()}


def _desired_config(request: LavaSettingsInput, prices: dict[str, str]) -> LavaConfig:
    try:
        return config_from_dict({
            "checkout_mode": request.checkout_mode, "currency": request.currency,
            "plans": {plan: {
                "enabled": term.enabled, "offer_id": term.offer_id,
                "price": ({"amount": prices[plan], "currency": request.currency} if plan in prices else None),
            } for plan, term in request.plans.items()},
            "promo_codes": dict(request.promo_codes),
        })
    except LavaConfigError as exc:
        raise CommandError(str(exc), 400) from None


async def _catalog_prices(runtime, settings_obj, desired: LavaConfig) -> dict[str, str]:
    """Validate enabled terms against the live lava catalog (outside any
    transaction) and return the exact prices. manual_only never needs lava."""
    enabled = [term for term in desired.terms.values() if term.enabled]
    if desired.checkout_mode == "manual_only" and not enabled:
        return {}
    if desired.checkout_mode != "manual_only":
        if not sales_configured(settings_obj):
            raise CommandError("lava_not_configured", 409)
        if not enabled:
            raise CommandError("lava_no_enabled_term", 409)
    if runtime is None or not getattr(settings_obj, "LAVA_API_KEY", ""):
        if desired.checkout_mode == "manual_only":
            return {}
        raise CommandError("lava_not_configured", 409)
    try:
        products = await runtime.client().list_products()
    except LavaError:
        if desired.checkout_mode == "manual_only":
            return {}
        raise CommandError("lava_provider_unavailable", 503) from None
    checks = check_config_against_catalog(desired, products)
    failed = [check for check in checks if not check.ok]
    if failed:
        if desired.checkout_mode == "manual_only":
            return {}
        raise CommandError("lava_offer_invalid", 409)
    prices = {}
    for term in enabled:
        for product in products:
            for offer in product.offers:
                if offer.offer_id == term.offer_id:
                    price = offer.price_for(desired.currency, term.periodicity)
                    if price is not None:
                        prices[term.plan_type] = str(price.amount)
    return prices


def _normalize_plans(request: LavaSettingsInput) -> LavaSettingsInput:
    if set(request.plans) != set(LAVA_PLAN_TYPES):
        raise CommandError("admin_pwa_invalid_payload", 400)
    return request


async def prepare_lava_settings(db, *, session_cookie, request, settings_obj, runtime_getter):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    request = _normalize_plans(request)
    async with read_transaction(db):
        await _actor(db, session_cookie, settings_obj)
        digest, current = await _config_hash(db)
    desired = _desired_config(request, {})
    prices = await _catalog_prices(runtime_getter(), settings_obj, desired)
    command = LavaSettingsCommand(**request.model_dump(), prices=prices, expected_hash=digest)
    return {"operation": command.operation(), "current": current.to_json()}


async def _proof_boundary(db, *, session_cookie, request, settings_obj, operation):
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text("SET LOCAL lock_timeout = '5000'"))
        await db.execute(text("SET LOCAL statement_timeout = '8000'"))
    if not await consume_step_up_in_mutation(db, session_cookie=session_cookie,
            step_up_id=request.step_up_id, settings_obj=settings_obj, **operation):
        raise CommandError("admin_pwa_step_up_denied", 403)
    step = await db.get(AdminPwaStepUp, request.step_up_id)
    session = await db.get(AdminPwaSession, step.session_id)
    actor = await db.get(User, step.user_id)
    return step, session, actor


def _recheck_actor(step, session, actor, settings_obj):
    stamp = datetime.now(timezone.utc)
    if (not _enabled(settings_obj) or not _authorized_admin(actor, settings_obj)
            or session.revoked_at is not None
            or min(_utc(step.expires_at), _utc(session.expires_at)) <= stamp):
        raise CommandError("admin_pwa_step_up_denied", 403)


def _audit(db, *, step, actor, operation, result, target_user_id=None) -> str:
    audit_id = str(uuid4())
    db.add(AdminPwaCommandAudit(
        id=audit_id, step_up_id=step.id, actor_user_id=int(actor.id), target_user_id=target_user_id,
        action=operation["action"], target=operation["target"], payload_hash=operation_digest(**operation),
        result_json=json.dumps(result, sort_keys=True, separators=(",", ":"))))
    return audit_id


async def execute_lava_settings(db, *, session_cookie, request, settings_obj, runtime_getter):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = LavaSettingsCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    _normalize_plans(command)
    operation = command.operation()
    desired = _desired_config(command, command.prices)
    # Re-validate against the live catalog before the proof transaction; the
    # signed prices must still be exactly what lava sells.
    live = await _catalog_prices(runtime_getter(), settings_obj, _desired_config(command, {}))
    if desired.checkout_mode != "manual_only" and live != command.prices:
        raise CommandError("confirmation_changed", 409)
    async with db.begin():
        step, session, actor = await _proof_boundary(db, session_cookie=session_cookie, request=request,
                                                     settings_obj=settings_obj, operation=operation)
        current_hash, _ = await _config_hash(db, lock=True)
        _recheck_actor(step, session, actor, settings_obj)
        if current_hash != command.expected_hash:
            raise CommandError("confirmation_changed", 409)
        await BotSettingRepository(db).set(LAVA_CONFIG_KEY, json.dumps(
            desired.to_json(), sort_keys=True, separators=(",", ":")))
        audit_id = _audit(db, step=step, actor=actor, operation=operation,
                          result={"before_hash": current_hash, "mode": desired.checkout_mode,
                                  "enabled": sorted(t.plan_type for t in desired.terms.values() if t.enabled),
                                  # Codes are merchant secrets of a kind: audit keys only.
                                  "promo_keys": sorted(desired.promo_codes)})
        await db.flush()
    return {"command_id": audit_id, "config": desired.to_json()}


async def prepare_lava_action(db, *, session_cookie, request, settings_obj, runtime_getter):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    _validate_action(request)
    async with read_transaction(db):
        await _actor(db, session_cookie, settings_obj)
        if request.invoice_id is not None:
            row = await db.get(LavaInvoice, request.invoice_id)
            if row is None:
                raise CommandError("not_found", 404)
            if request.kind == "link" and row.status != "unmatched":
                raise CommandError("lava_not_unmatched", 409)
            if request.kind == "chargeback" and row.status != "chargeback_open":
                raise CommandError("lava_no_open_chargeback", 409)
            current = _invoice_row(row)
        else:
            current = None
        if request.user_id is not None and await db.get(User, request.user_id) is None:
            raise CommandError("user_not_found", 404)
    command = LavaActionCommand(**request.model_dump())
    return {"operation": command.operation(), "current": current}


async def execute_lava_action(db, *, session_cookie, request, settings_obj, runtime_getter):
    if not _enabled(settings_obj):
        raise CommandError("not_found", 404)
    command = LavaActionCommand.model_validate(request.model_dump(exclude={"step_up_id"}))
    _validate_action(command)
    operation = command.operation()
    runtime = runtime_getter()
    if runtime is None:
        raise CommandError("lava_not_configured", 409)
    contract_id = None
    async with db.begin():
        step, session, actor = await _proof_boundary(db, session_cookie=session_cookie, request=request,
                                                     settings_obj=settings_obj, operation=operation)
        _recheck_actor(step, session, actor, settings_obj)
        if command.invoice_id is not None:
            row = (await db.execute(select(LavaInvoice).where(LavaInvoice.id == command.invoice_id)
                                    .with_for_update())).scalar_one_or_none()
            if row is None:
                raise CommandError("not_found", 404)
            contract_id = row.contract_id
            if command.kind == "link":
                if row.status != "unmatched" or await db.get(User, command.user_id) is None:
                    raise CommandError("confirmation_changed", 409)
                row.user_id, row.plan_type, row.status = command.user_id, command.plan_type, "created"
                row.review_reason = None
            if command.kind == "chargeback" and row.status != "chargeback_open":
                raise CommandError("confirmation_changed", 409)
        audit_id = _audit(db, step=step, actor=actor, operation=operation,
                          result={"requested": command.kind},
                          target_user_id=command.user_id)
        await db.flush()
    # Money effects run through the shared idempotent ledger after the proof
    # commits; an uncertain provider answer is reported, never retried here.
    result: dict = {"command_id": audit_id, "kind": command.kind}
    if command.kind in {"recheck", "link"}:
        outcome, _, error = await events.verify_and_apply(runtime, contract_id)
        result.update(outcome=outcome, error=error)
    elif command.kind == "chargeback":
        closed = await ledger.close_chargeback(runtime.session_factory, command.invoice_id,
                                               won=command.outcome == "won")
        result.update(outcome=closed.outcome)
        if closed.outcome == "restored":
            await runtime.notifier.user_notice(closed.user, "chargeback_restored", end_date=closed.new_end_date)
    else:
        try:
            cancelled = await LavaCheckoutService(runtime).cancel(runtime.session_factory, user_id=command.user_id)
            result.update(outcome=cancelled.get("status") or cancelled.get("error"))
        except LavaCheckoutError as exc:
            result.update(outcome="failed", error=exc.code)
    return result


def create_admin_pwa_lava_router(*, settings_obj, session_factory, runtime_getter):
    router = APIRouter(tags=["admin-pwa-lava"])

    async def handle(request, task, schema, *, runtime=False):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        try:
            parsed = schema.model_validate(await _body(request, 8192))
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        kwargs = {} if schema is EmptyLavaRequest else {"request": parsed}
        if runtime:
            kwargs["runtime_getter"] = runtime_getter
        try:
            async with session_factory() as db:
                data = await task(db, session_cookie=cookie, settings_obj=settings_obj, **kwargs)
        except CommandError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.exception("Admin PWA lava.top command unavailable")
            return _reply(503, "admin_pwa_command_unavailable")
        return JSONResponse({"ok": True, **data}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/lava/read")
    async def read(request: Request):
        return await handle(request, read_lava, EmptyLavaRequest)

    @router.post("/api/admin/v1/lava/catalog")
    async def catalog(request: Request):
        return await handle(request, read_lava_catalog, EmptyLavaRequest, runtime=True)

    @router.post("/api/admin/v1/lava/prepare")
    async def prepare(request: Request):
        return await handle(request, prepare_lava_settings, LavaSettingsInput, runtime=True)

    @router.post("/api/admin/v1/lava/save")
    async def save(request: Request):
        return await handle(request, execute_lava_settings, ExecuteLavaSettings, runtime=True)

    @router.post("/api/admin/v1/lava/prepare-action")
    async def prepare_action(request: Request):
        return await handle(request, prepare_lava_action, LavaActionInput, runtime=True)

    @router.post("/api/admin/v1/lava/action")
    async def action(request: Request):
        return await handle(request, execute_lava_action, ExecuteLavaAction, runtime=True)

    return router
