"""lava.top webhook ingestion and event processing.

The webhook is authenticated with the merchant-chosen ``X-Api-Key`` and is
only a trigger: every success is re-verified with ``GET /api/v2/invoices/{id}``
before Pro is granted. Events are stored durably first (dedupe key UNIQUE) so a
paused or failed processing step is replayed by the reconcile worker.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models.lava import LavaWebhookEvent
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.user_repo import UserRepository
from app.services.lava import ledger
from app.services.lava.client import LavaClient, LavaError, LavaNotFound
from app.services.lava.terms import is_uuid, money, normalize_email

logger = logging.getLogger(__name__)

MAX_WEBHOOK_BYTES = 64 * 1024
MAX_ATTEMPTS = 30
SUCCESS_EVENTS = {"payment.success", "subscription.recurring.payment.success"}
PAYMENT_EVENTS = SUCCESS_EVENTS | {
    "payment.failed", "subscription.recurring.payment.failed", "subscription.cancelled",
}
WRAPPED_EVENTS = {"refund.success", "chargeback.initiated"}
OPEN_RESULTS = {"received", "queued", "retry"}
LAST_WEBHOOK_KEY = "lava_last_webhook_at"
LAST_AUTH_FAILURE_KEY = "lava_last_webhook_auth_failure_at"
LAST_AUTH_FAILURE_REASON_KEY = "lava_last_webhook_auth_failure_reason"


@dataclass
class LavaRuntime:
    settings: object
    session_factory: Callable
    notifier: object
    on_approved: Callable[..., Awaitable] | None = None
    client_factory: Callable[[], LavaClient] | None = None
    _state: dict = field(default_factory=dict)

    def client(self) -> LavaClient:
        if self.client_factory is not None:
            return self.client_factory()
        return LavaClient(api_key=getattr(self.settings, "LAVA_API_KEY", ""),
                          base_url=getattr(self.settings, "LAVA_API_BASE", "https://gate.lava.top"))


@dataclass
class ParsedEvent:
    event_type: str
    dedupe_key: str
    contract_id: str | None = None
    parent_contract_id: str | None = None
    provider_status: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    product_id: str | None = None
    tier_id: str | None = None
    refund_type: str | None = None
    email: str | None = None
    cancelled_at: datetime | None = None
    will_expire_at: datetime | None = None


class EventParseError(ValueError):
    pass


def _uuid(value) -> str | None:
    return value.lower() if is_uuid(value) else None


def _time(value) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _currency(value) -> str | None:
    return value.upper()[:3] if isinstance(value, str) and value.strip() else None


def parse_event(body) -> ParsedEvent:
    if not isinstance(body, dict):
        raise EventParseError("invalid_body")
    event_type = body.get("eventType") or body.get("event_type")
    if not isinstance(event_type, str) or len(event_type) > 48:
        raise EventParseError("invalid_event_type")
    if event_type in PAYMENT_EVENTS:
        contract_id = _uuid(body.get("contractId"))
        if contract_id is None:
            raise EventParseError("invalid_contract_id")
        product = body.get("product") if isinstance(body.get("product"), dict) else {}
        buyer = body.get("buyer") if isinstance(body.get("buyer"), dict) else {}
        return ParsedEvent(
            event_type=event_type, dedupe_key=f"{event_type}:{contract_id}",
            contract_id=contract_id, parent_contract_id=_uuid(body.get("parentContractId")),
            provider_status=str(body.get("status") or "")[:32] or None,
            amount=money(body.get("amount")), currency=_currency(body.get("currency")),
            product_id=_uuid(product.get("id")), email=normalize_email(buyer.get("email")),
            cancelled_at=_time(body.get("cancelledAt")), will_expire_at=_time(body.get("willExpireAt")),
        )
    if event_type in WRAPPED_EVENTS:
        event_id = _uuid(body.get("event_id"))
        data = body.get("data") if isinstance(body.get("data"), dict) else None
        if event_id is None or data is None:
            raise EventParseError("invalid_wrapped_event")
        product = data.get("product") if isinstance(data.get("product"), dict) else {}
        refund_type = data.get("refund_type")
        return ParsedEvent(
            event_type=event_type, dedupe_key=f"{event_type}:{event_id}",
            amount=money(data.get("amount")), currency=_currency(data.get("currency")),
            product_id=_uuid(product.get("product_id")), tier_id=_uuid(product.get("tier_id")),
            refund_type=refund_type if refund_type in {"full", "partial"} else None,
            email=normalize_email(data.get("customer_email")),
        )
    # Unknown event types are acknowledged and ignored (lava may add new ones).
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    return ParsedEvent(event_type=event_type[:48], dedupe_key=f"unknown:{digest[:64]}")


def _sha(value: str | None) -> str | None:
    return hashlib.sha256(value.encode()).hexdigest() if value else None


def authorized(settings_obj, api_key_header: str | None) -> bool:
    secret = getattr(settings_obj, "LAVA_WEBHOOK_SECRET", "") or ""
    if not secret or not api_key_header:
        return False
    return hmac.compare_digest(api_key_header.encode(), secret.encode())


def ip_allowed(settings_obj, client_ip: str | None) -> bool:
    raw = (getattr(settings_obj, "LAVA_WEBHOOK_ALLOWED_IPS", "") or "").strip()
    if not raw:
        return True
    allowed = {part.strip() for part in raw.split(",") if part.strip()}
    return bool(client_ip) and client_ip in allowed


async def _store_event(runtime: LavaRuntime, parsed: ParsedEvent, raw: bytes, result: str) -> tuple[int, str]:
    now = datetime.now(timezone.utc)
    values = dict(
        dedupe_key=parsed.dedupe_key, event_type=parsed.event_type, contract_id=parsed.contract_id,
        parent_contract_id=parsed.parent_contract_id, provider_status=parsed.provider_status,
        amount=parsed.amount, currency=parsed.currency, product_id=parsed.product_id,
        tier_id=parsed.tier_id, refund_type=parsed.refund_type, email_sha256=_sha(parsed.email),
        payload_sha256=hashlib.sha256(raw).hexdigest(),
        payload_json=raw.decode("utf-8") if result in OPEN_RESULTS else None,
        result=result, attempts=0, received_at=now,
        processed_at=now if result not in OPEN_RESULTS else None,
    )
    async with runtime.session_factory() as session:
        try:
            async with session.begin():
                row = LavaWebhookEvent(**values)
                session.add(row)
                await session.flush()
                return row.id, "new"
        except IntegrityError:
            pass
    async with runtime.session_factory() as session:
        existing = (await session.execute(select(LavaWebhookEvent).where(
            LavaWebhookEvent.dedupe_key == parsed.dedupe_key))).scalar_one()
        return existing.id, existing.result


async def _touch_setting(runtime: LavaRuntime, key: str, *, min_interval: float = 60.0) -> None:
    import time
    now = time.monotonic()
    if now - runtime._state.get(key, -1e9) < min_interval:
        return
    runtime._state[key] = now
    try:
        async with runtime.session_factory() as session, session.begin():
            await BotSettingRepository(session).set(key, datetime.now(timezone.utc).isoformat())
    except Exception:  # noqa: BLE001 - observability only
        logger.warning("lava.top could not record %s", key)


async def ingest(runtime: LavaRuntime, raw: bytes, *, api_key_header: str | None,
                 client_ip: str | None) -> tuple[int, dict]:
    settings_obj = runtime.settings
    if not getattr(settings_obj, "LAVA_WEBHOOK_SECRET", ""):
        return 404, {"ok": False}
    key_ok = authorized(settings_obj, api_key_header)
    ip_ok = ip_allowed(settings_obj, client_ip)
    if not key_ok or not ip_ok:
        # Diagnose webhook configuration without retaining the supplied header,
        # client IP or payload. 401 remains a fail-closed rejection.
        reason = ("missing_key" if not api_key_header else
                  "key_mismatch" if not key_ok else "ip_not_allowed")
        await _touch_setting(runtime, LAST_AUTH_FAILURE_KEY)
        if runtime._state.get(LAST_AUTH_FAILURE_REASON_KEY) != reason:
            runtime._state[LAST_AUTH_FAILURE_REASON_KEY] = reason
            try:
                async with runtime.session_factory() as session, session.begin():
                    await BotSettingRepository(session).set(LAST_AUTH_FAILURE_REASON_KEY, reason)
            except Exception:  # noqa: BLE001 - diagnostic only
                logger.warning("lava.top could not record auth failure category")
        await runtime.notifier.admin_alert("webhook_auth_failed", throttle_seconds=3600)
        return 401, {"ok": False}
    if len(raw) > MAX_WEBHOOK_BYTES:
        return 413, {"ok": False}
    try:
        parsed = parse_event(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, EventParseError):
        return 400, {"ok": False, "error": "invalid_event"}
    await _touch_setting(runtime, LAST_WEBHOOK_KEY, min_interval=30.0)
    known = parsed.event_type in PAYMENT_EVENTS or parsed.event_type in WRAPPED_EVENTS
    paused = getattr(settings_obj, "LAVA_PROCESSING_PAUSED", False) is True
    initial = "ignored" if not known else ("queued" if paused else "received")
    event_id, state = await _store_event(runtime, parsed, raw, initial)
    if state not in {"new", *OPEN_RESULTS}:
        return 200, {"ok": True, "result": "duplicate"}
    if not known:
        return 200, {"ok": True, "result": "ignored"}
    if paused:
        if state != "new":
            await _set_result(runtime, event_id, "queued", keep_payload=True)
        return 200, {"ok": True, "result": "queued"}
    result = await process_event(runtime, event_id)
    if result == "retry":
        return 503, {"ok": False, "result": "retry"}
    return 200, {"ok": True, "result": result}


async def _set_result(runtime, event_id: int, result: str, *, error_code: str | None = None,
                      invoice_id: int | None = None, keep_payload: bool = False,
                      count_attempt: bool = False) -> None:
    async with runtime.session_factory() as session, session.begin():
        row = (await session.execute(select(LavaWebhookEvent).where(LavaWebhookEvent.id == event_id)
                                     .with_for_update())).scalar_one()
        row.result = result
        row.error_code = error_code
        if invoice_id is not None:
            row.invoice_id = invoice_id
        if count_attempt:
            row.attempts = int(row.attempts or 0) + 1
        if result not in OPEN_RESULTS:
            row.processed_at = datetime.now(timezone.utc)
            if not keep_payload:
                row.payload_json = None


async def _claim(runtime, event_id: int) -> ParsedEvent | None:
    async with runtime.session_factory() as session:
        row = await session.get(LavaWebhookEvent, event_id)
        if row is None or row.result not in OPEN_RESULTS or not row.payload_json:
            return None
        try:
            return parse_event(json.loads(row.payload_json))
        except (json.JSONDecodeError, EventParseError):
            return None


async def _user(runtime, user_id: int | None):
    if user_id is None:
        return None
    async with runtime.session_factory() as session:
        return await UserRepository(session).get_by_user_id(user_id)


async def after_apply(runtime: LavaRuntime, outcome: ledger.ApplyOutcome) -> str:
    """Post-commit effects for an apply attempt; returns the event result."""
    notifier = runtime.notifier
    if outcome.outcome == "applied":
        if runtime.on_approved is not None and outcome.review_result is not None:
            try:
                async with runtime.session_factory() as session:
                    await runtime.on_approved(session, outcome.review_result)
            except Exception:  # noqa: BLE001 - committed decision stands
                logger.exception("lava.top post-approval effects failed")
        if outcome.review_reason == "amount_mismatch":
            await notifier.admin_alert("amount_mismatch", invoice_id=outcome.invoice_id)
        return "applied"
    if outcome.outcome == "duplicate":
        return "duplicate"
    if outcome.outcome == "unmatched":
        await notifier.admin_alert("unmatched", invoice_id=outcome.invoice_id)
        return "unmatched"
    if outcome.outcome == "activation_failed":
        await notifier.admin_alert("activation_failed", invoice_id=outcome.invoice_id,
                                   detail=outcome.review_reason)
        return "needs_review"
    await notifier.admin_alert("needs_review", invoice_id=outcome.invoice_id, detail=outcome.review_reason)
    return "needs_review"


async def verify_and_apply(runtime: LavaRuntime, contract_id: str, *,
                           expected_parent: str | None = None,
                           renewal: bool = False) -> tuple[str, int | None, str | None]:
    """Verify one contract with the lava API and apply it. Returns
    (event result, invoice id, error code). Provider trouble → retry."""
    try:
        info = await runtime.client().get_invoice(contract_id)
    except LavaNotFound:
        return "needs_review", None, "invoice_not_found"
    except LavaError as exc:
        return "retry", None, exc.code
    if info.status == "FAILED":
        # A provider-confirmed unsuccessful customer payment is a normal
        # checkout outcome, not a technical failure requiring admin review.
        # Provider did not supply a trusted bank-decline reason.
        invoice_id = await ledger.mark_failed(runtime.session_factory, contract_id)
        return "ignored", invoice_id, "provider_failed"
    if not info.completed:
        return "retry", None, "not_completed"
    if renewal and (info.invoice_type != "SUBSCRIPTION_RENEWAL"
                    or (expected_parent and info.parent_contract_id != expected_parent)):
        return "needs_review", None, "renewal_mismatch"
    outcome = await ledger.apply_completed(runtime.session_factory, info)
    result = await after_apply(runtime, outcome)
    return result, outcome.invoice_id, outcome.review_reason


async def process_event(runtime: LavaRuntime, event_id: int) -> str:
    parsed = await _claim(runtime, event_id)
    if parsed is None:
        return "duplicate"
    notifier = runtime.notifier
    invoice_id = None
    error_code = None
    try:
        if parsed.event_type in SUCCESS_EVENTS:
            result, invoice_id, error_code = await verify_and_apply(
                runtime, parsed.contract_id, expected_parent=parsed.parent_contract_id,
                renewal=parsed.event_type == "subscription.recurring.payment.success",
            )
        elif parsed.event_type == "payment.failed":
            invoice_id = await ledger.mark_failed(runtime.session_factory, parsed.contract_id)
            result = "applied" if invoice_id else "ignored"
        elif parsed.event_type == "subscription.recurring.payment.failed":
            row, previous = await ledger.mark_subscription(
                runtime.session_factory, parsed.parent_contract_id or parsed.contract_id, status="failed")
            invoice_id = row.id if row else None
            if row is not None and previous not in {"failed", "cancelled"}:
                await notifier.user_notice(await _user(runtime, row.user_id), "renewal_failed")
            result = "applied" if row else "ignored"
        elif parsed.event_type == "subscription.cancelled":
            row, previous = await ledger.mark_subscription(
                runtime.session_factory, parsed.contract_id, status="cancelled",
                cancelled_at=parsed.cancelled_at, will_expire_at=parsed.will_expire_at)
            invoice_id = row.id if row else None
            if row is not None and previous != "cancelled":
                user = await _user(runtime, row.user_id)
                await notifier.user_notice(user, "subscription_cancelled",
                                           end_date=getattr(user, "end_date", None))
            result = "applied" if row else "ignored"
        else:
            result, invoice_id, error_code = await _process_revocation(runtime, parsed)
    except Exception:  # noqa: BLE001 - never lose the event; worker retries
        logger.exception("lava.top event %s processing failed", event_id)
        result, error_code = "retry", "processing_exception"
    attempts_exhausted = False
    if result == "retry":
        async with runtime.session_factory() as session:
            row = await session.get(LavaWebhookEvent, event_id)
            attempts_exhausted = row is not None and int(row.attempts or 0) + 1 >= MAX_ATTEMPTS
        if attempts_exhausted:
            result = "error"
            await notifier.admin_alert("retry_exhausted", detail=f"event {event_id}")
    await _set_result(runtime, event_id, result, error_code=error_code, invoice_id=invoice_id,
                      count_attempt=True)
    return result


async def _process_revocation(runtime: LavaRuntime, parsed: ParsedEvent) -> tuple[str, int | None, str | None]:
    notifier = runtime.notifier
    is_refund = parsed.event_type == "refund.success"
    if is_refund and parsed.refund_type != "full":
        await notifier.admin_alert("refund_review", detail="partial refund")
        return "needs_review", None, "refund_partial"
    async with runtime.session_factory() as session:
        candidate, reason = await ledger.find_revocation_candidate(
            session, email=parsed.email, tier_id=parsed.tier_id, currency=parsed.currency,
            amount=parsed.amount, full_refund=is_refund,
        )
        candidate_id = candidate.id if candidate is not None else None
    if candidate_id is None:
        await notifier.admin_alert("refund_review", detail=parsed.event_type)
        return "needs_review", None, reason
    outcome = await ledger.revoke_invoice(runtime.session_factory, candidate_id,
                                          kind="refund" if is_refund else "chargeback")
    if outcome.outcome == "revoked":
        await notifier.user_notice(outcome.user, "refund_revoked" if is_refund else "chargeback_revoked",
                                   end_date=outcome.new_end_date)
        await notifier.admin_alert("refund_revoked" if is_refund else "chargeback_revoked",
                                   invoice_id=candidate_id)
        if outcome.partner_credit:
            await notifier.admin_alert("partner_credit", invoice_id=candidate_id)
        return "applied", candidate_id, None
    if outcome.outcome == "duplicate":
        return "duplicate", candidate_id, None
    await notifier.admin_alert("refund_review", invoice_id=candidate_id, detail=outcome.review_reason)
    return "needs_review", candidate_id, outcome.review_reason
