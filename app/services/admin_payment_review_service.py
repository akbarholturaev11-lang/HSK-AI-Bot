"""Shared payment decision unit of work. The caller owns commit/rollback.

No notification, independent analytics transaction or transport authentication
belongs here. Telegram and PWA adapters retain their own authorization.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select

from app.db.models.payment import Payment
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE, Hsk30UnlockService
from app.services.partner_service import PartnerService
from app.services.payment_review_preview_service import PaymentReviewPreviewService
from app.services.subscription_service import SubscriptionService


class PaymentReviewError(ValueError):
    def __init__(self, error: str, status: int):
        super().__init__(error)
        self.status = status


@dataclass
class PaymentReviewResult:
    payment: Payment
    user: object
    decision: str
    partner: object = None
    commission_usd: Decimal = Decimal("0.00")
    unlocked_bonus: bool = False
    deferred_events: list[dict] = field(default_factory=list)

    @property
    def response(self) -> dict:
        content = {"ok": True, "status": self.payment.payment_status}
        if self.decision == "approve" and self.payment.plan_type == HSK30_UNLOCK_PLAN_TYPE:
            content["product"] = HSK30_UNLOCK_PLAN_TYPE
        return content


async def lock_pending_payment(session, payment_id: int):
    """Checkout/review lock order: canonical User, then refreshed Payment.

    The initial row is only an ownership hint. Recheck it after acquiring both
    locks; a stale ORM object must never choose the amount/plan/owner to apply.
    """
    if not session.in_transaction():
        raise RuntimeError("payment_review_requires_transaction")
    repo = PaymentRepository(session)
    payment = await repo.get_by_id(payment_id)
    if payment is None:
        raise PaymentReviewError("payment_not_found", 404)
    owner_key = (payment.user_id, payment.user_telegram_id)
    user = await repo.get_owner(payment, lock=True)
    payment = (await session.execute(select(Payment).where(
        Payment.id == payment_id,
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if payment is None:
        raise PaymentReviewError("payment_not_found", 404)
    if owner_key != (payment.user_id, payment.user_telegram_id):
        raise PaymentReviewError("payment_owner_changed", 409)
    if payment.payment_status != "pending":
        raise PaymentReviewError("payment_already_reviewed", 409)
    if user is not None and not repo.is_owned_by(payment, user):
        raise PaymentReviewError("payment_owner_changed", 409)
    return payment, user


async def review_locked_payment(
    session, *, payment: Payment, user, decision: str, comment: str,
) -> PaymentReviewResult:
    """Internal: call only after lock_pending_payment in this transaction.

    Any error must escape the enclosing transaction (or trigger its rollback).
    Conditional repository writes are an additional guard against replay.
    """
    if not session.in_transaction():
        raise RuntimeError("payment_review_requires_transaction")
    if decision not in {"approve", "reject"}:
        raise PaymentReviewError("invalid_action", 400)
    repo = PaymentRepository(session)
    result = PaymentReviewResult(payment=payment, user=user, decision=decision)
    if decision == "approve":
        if user is None:
            raise PaymentReviewError("user_not_found", 404)
        if not await repo.approve(payment, admin_comment=comment):
            raise PaymentReviewError("payment_already_reviewed", 409)
        if payment.plan_type == HSK30_UNLOCK_PLAN_TYPE:
            if not await Hsk30UnlockService(session).grant(user=user, payment=payment):
                raise PaymentReviewError("hsk30_unlock_failed", 400)
        else:
            activated = await SubscriptionService(session).activate_plan(
                telegram_id=user, plan_type=payment.plan_type,
                discount_source=payment.discount_source, payment=payment,
                deferred_events=result.deferred_events,
            )
            if not activated:
                raise PaymentReviewError("subscription_activation_failed", 400)
            result.partner, result.commission_usd, result.unlocked_bonus = (
                await PartnerService(session).record_approved_payment(payment)
            )
    else:
        if not await repo.reject(payment, admin_comment=comment):
            raise PaymentReviewError("payment_already_reviewed", 409)
        if user is not None and payment.plan_type != HSK30_UNLOCK_PLAN_TYPE:
            await UserRepository(session).set_selected_plan_type(user, None)
            await PaymentReviewPreviewService(session).review(user, payment, approved=False)
    await session.flush()
    return result
