"""Exact, one-use PWA payment authorization + shared financial transaction."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_sessions import authenticate_admin_pwa_session
from app.admin_api.pwa_step_up import _enabled, consume_step_up_in_mutation, operation_digest
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentReview, AdminPwaPaymentOutbox
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.services.admin_payment_review_service import (
    PaymentReviewError, lock_pending_payment, review_locked_payment,
)
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE
from app.services.subscription_service import PLAN_DURATIONS

PositiveId = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
Money = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class PaymentSnapshot(StrictModel):
    user_id: PositiveId
    payment_owner_id: PositiveId | None
    owner_telegram_id: int | None
    payment_telegram_id: int | None
    amount: Money
    currency: Annotated[str, Field(min_length=1, max_length=16)]
    base_amount: Annotated[int, Field(ge=0)] | None
    plan_type: Literal["10_days", "1_month", "3_months", "hsk30_unlock"]
    payment_method: Annotated[str, Field(max_length=16)] | None
    source: Annotated[str, Field(max_length=32)]
    discount_source: Annotated[str, Field(max_length=32)]
    discount_percent: Annotated[int, Field(ge=0, le=100)]
    discount_campaign_id: PositiveId | None
    card_country: Annotated[str, Field(max_length=16)] | None
    local_amount: Annotated[str, Field(max_length=32)] | None
    local_currency: Annotated[str, Field(max_length=16)] | None
    exchange_rate: Annotated[str, Field(max_length=80)] | None
    submitted_at: Annotated[str, Field(max_length=40)]
    receipt_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None


class InspectPaymentReview(StrictModel):
    """Read-only receipt preview with no implicit approval or signed decision."""
    payment_id: PositiveId


class PreparePaymentReview(StrictModel):
    payment_id: PositiveId
    decision: Literal["approve", "reject"]
    reason: Annotated[str, Field(min_length=1, max_length=300)] | None

    @model_validator(mode="after")
    def validate_reason(self):
        if self.decision == "approve" and self.reason is not None:
            raise ValueError("approval_reason_not_supported")
        if self.decision == "reject" and not self.reason:
            raise ValueError("rejection_reason_required")
        if self.reason is not None and (self.reason != self.reason.strip()
                                        or any(ord(c) < 32 for c in self.reason)):
            raise ValueError("invalid_rejection_reason")
        return self


class PaymentReviewCommand(PreparePaymentReview):
    expected: PaymentSnapshot

    def operation(self):
        return {"action": "payments.review", "target": str(self.payment_id),
                "payload": self.model_dump()}


class ExecutePaymentReview(PaymentReviewCommand):
    step_up_id: Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]

    def command(self):
        return PaymentReviewCommand.model_validate(self.model_dump(exclude={"step_up_id"}))


def payment_snapshot(payment, user) -> PaymentSnapshot:
    if user is None:
        raise PaymentReviewError("user_not_found", 404)
    if payment.plan_type not in {*PLAN_DURATIONS, HSK30_UNLOCK_PLAN_TYPE}:
        raise PaymentReviewError("unsupported_payment_plan", 409)
    return PaymentSnapshot(
        user_id=user.id, payment_owner_id=payment.user_id,
        owner_telegram_id=user.telegram_id, payment_telegram_id=payment.user_telegram_id,
        amount=payment.amount, currency=payment.currency, base_amount=payment.base_amount,
        plan_type=payment.plan_type, payment_method=payment.payment_method,
        source=payment.source, discount_source=payment.discount_source,
        discount_percent=payment.discount_percent, discount_campaign_id=payment.discount_campaign_id,
        card_country=payment.card_country, local_amount=payment.local_amount,
        local_currency=payment.local_currency, exchange_rate=payment.exchange_rate,
        submitted_at=_utc(payment.submitted_at).isoformat(),
        receipt_sha256=(hashlib.sha256(payment.screenshot_file_id.encode()).hexdigest()
                        if payment.screenshot_file_id else None),
    )


async def inspect_payment_review(db, *, session_cookie, request: InspectPaymentReview, settings_obj):
    """Only return the current pending receipt snapshot; never preselect approve."""
    if not _enabled(settings_obj):
        raise PaymentReviewError("not_found", 404)
    async with db.begin():
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise PaymentReviewError("admin_pwa_unauthorized", 401)
        payment, user = await lock_pending_payment(db, request.payment_id)
        expected = payment_snapshot(payment, user).model_dump()
    return {"payment_id": request.payment_id, "expected": expected}


async def prepare_payment_review(db, *, session_cookie, request: PreparePaymentReview, settings_obj):
    if not _enabled(settings_obj):
        raise PaymentReviewError("not_found", 404)
    async with db.begin():
        actor = await authenticate_admin_pwa_session(db, session_cookie, settings_obj)
        if actor is None or actor.auth_method != "webauthn":
            raise PaymentReviewError("admin_pwa_unauthorized", 401)
        payment, user = await lock_pending_payment(db, request.payment_id)
        command = PaymentReviewCommand(**request.model_dump(), expected=payment_snapshot(payment, user))
    # This is the exact confirmation data the browser must display and sign.
    return command.operation()


async def execute_payment_review(db, *, session_cookie, request: ExecutePaymentReview, settings_obj):
    """Receipt, decision, entitlements, audit and outbox commit or roll back.

    Consume before locking the financial owner: step -> credential -> session
    -> admin User -> target User -> Payment. Never call the legacy committer.
    """
    if not _enabled(settings_obj):
        raise PaymentReviewError("not_found", 404)
    command = request.command()
    operation = command.operation()
    async with db.begin():
        if not await consume_step_up_in_mutation(
            db, session_cookie=session_cookie, step_up_id=request.step_up_id,
            settings_obj=settings_obj, **operation,
        ):
            raise PaymentReviewError("admin_pwa_step_up_denied", 403)
        step = await db.get(AdminPwaStepUp, request.step_up_id)
        payment, user = await lock_pending_payment(db, command.payment_id)
        if payment_snapshot(payment, user) != command.expected:
            raise PaymentReviewError("payment_confirmation_changed", 409)
        result = await review_locked_payment(
            db, payment=payment, user=user, decision=command.decision,
            comment=("approved by admin PWA" if command.decision == "approve"
                     else command.reason or "rejected by admin PWA"),
        )
        # Re-read the persisted row before auditing a financial decision.
        # A mismatch rolls back payment, entitlements and the one-use proof.
        await db.refresh(payment, attribute_names=["payment_status"])
        intended_status = {"approve": "approved", "reject": "rejected"}[command.decision]
        if payment.payment_status != intended_status:
            raise PaymentReviewError("payment_decision_mismatch", 409)
        audit_id = str(uuid4())
        db.add(AdminPwaPaymentReview(
            id=audit_id, step_up_id=request.step_up_id, payment_id=payment.id,
            actor_user_id=step.user_id, target_user_id=user.id,
            action="payments.review", decision=command.decision,
            payload_hash=operation_digest(**operation),
            payload_json=json.dumps(command.model_dump(), sort_keys=True, separators=(",", ":")),
            status="applied", created_at=datetime.now(timezone.utc),
        ))
        await db.flush()
        db.add(AdminPwaPaymentOutbox(
            review_id=audit_id, status="pending",
            effects_json=json.dumps({
                "partner_id": result.partner.id if result.partner else None,
                "commission_usd": str(result.commission_usd),
                "unlocked_bonus": result.unlocked_bonus,
                "deferred_events": result.deferred_events,
            }, sort_keys=True),
        ))
        await db.flush()
        content = {**result.response, "review_id": audit_id, "delivery_status": "pending"}
    return content
