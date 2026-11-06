"""Database side of lava.top: verified activation, revocation, restoration.

No provider IO happens here; callers pass an already verified
``LavaInvoiceInfo`` obtained from ``GET /api/v2/invoices/{id}``.

Lock order (same as manual review): canonical User → ``lava_invoices`` row →
Payment. A ``payments`` row is created and approved inside one transaction via
the shared ``review_locked_payment`` unit of work, so a lava payment never
appears as a reviewable pending receipt.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models.ai_usage import AIUsageBudget
from app.db.models.lava import LavaInvoice
from app.db.models.partner import PartnerCredit
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_payment_review_service import PaymentReviewError, review_locked_payment
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.lava.client import LavaInvoiceInfo
from app.services.lava.terms import LAVA_PAYMENT_METHOD, amounts_equal, normalize_email, term_days
from app.services.portfolio_service import PortfolioService
from app.services.subscription_currency_service import SubscriptionCurrencyService

logger = logging.getLogger(__name__)

APPLICABLE_STATUSES = frozenset({"created", "failed", "expired"})
GRANTED_STATUSES = frozenset({"paid", "chargeback_won"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@dataclass
class ApplyOutcome:
    outcome: str  # applied | duplicate | unmatched | needs_review | activation_failed | not_completed
    invoice_id: int | None = None
    payment_id: int | None = None
    user_id: int | None = None
    review_reason: str | None = None
    review_result: object = None  # PaymentReviewResult for post-commit effects
    kind: str | None = None


@dataclass
class RevokeOutcome:
    outcome: str  # revoked | duplicate | needs_review | restored | closed
    invoice_id: int | None = None
    payment_id: int | None = None
    user: object = None
    partner_credit: bool = False
    new_end_date: datetime | None = None
    review_reason: str | None = None


async def _lock_invoice(session, invoice_id: int) -> LavaInvoice | None:
    return (await session.execute(
        select(LavaInvoice).where(LavaInvoice.id == invoice_id)
        .with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()


async def _invoice_by_contract(session, contract_id: str) -> LavaInvoice | None:
    return (await session.execute(
        select(LavaInvoice).where(LavaInvoice.contract_id == contract_id)
    )).scalar_one_or_none()


async def _insert_invoice(session_factory, **values) -> int:
    """Insert once per contract; a concurrent duplicate returns the winner's id."""
    async with session_factory() as session:
        try:
            async with session.begin():
                row = LavaInvoice(**values)
                session.add(row)
                await session.flush()
                return row.id
        except IntegrityError:
            pass
    async with session_factory() as session:
        row = await _invoice_by_contract(session, values["contract_id"])
        if row is None:
            raise RuntimeError("lava_invoice_insert_conflict")
        return row.id


async def resolve_invoice(session_factory, info: LavaInvoiceInfo) -> tuple[int, str]:
    """Return (invoice_id, kind) for a verified contract, creating renewal or
    unmatched rows when needed. Never matches by email."""
    async with session_factory() as session:
        row = await _invoice_by_contract(session, info.contract_id)
        if row is not None:
            return row.id, row.kind
        parent = None
        if info.parent_contract_id:
            parent = await _invoice_by_contract(session, info.parent_contract_id)
    now = _now()
    if parent is not None and parent.user_id is not None and info.invoice_type == "SUBSCRIPTION_RENEWAL":
        invoice_id = await _insert_invoice(
            session_factory, contract_id=info.contract_id, parent_contract_id=parent.contract_id,
            kind="renewal", user_id=parent.user_id, plan_type=parent.plan_type, offer_id=parent.offer_id,
            periodicity=parent.periodicity, currency=parent.currency,
            # A promo-discounted first payment says nothing about renewal price.
            expected_amount=None if parent.discount_source else parent.paid_amount,
            buyer_email=parent.buyer_email, source=parent.source, status="created",
            created_at=now, updated_at=now,
        )
        return invoice_id, "renewal"
    invoice_id = await _insert_invoice(
        session_factory, contract_id=info.contract_id, parent_contract_id=info.parent_contract_id,
        kind="external", user_id=None, currency=(info.currency or "USD")[:3],
        paid_amount=info.amount, buyer_email=normalize_email(info.buyer_email), source="admin_link",
        status="unmatched", created_at=now, updated_at=now,
    )
    return invoice_id, "external"


async def _base_amount_tjs(session, amount: Decimal, currency: str) -> int | None:
    rates = await SubscriptionCurrencyService(session).all_rates()
    try:
        if currency == "USD":
            usd = amount
        elif currency == "RUB":
            usd = amount / Decimal(rates["rub"])
        else:
            return None
        return int((usd * Decimal(rates["tjs"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (KeyError, ArithmeticError):
        return None


async def apply_completed(session_factory, info: LavaInvoiceInfo) -> ApplyOutcome:
    """Grant Pro for a lava contract the API reported COMPLETED, at most once."""
    if not info.completed or info.amount is None:
        return ApplyOutcome("not_completed")
    invoice_id, kind = await resolve_invoice(session_factory, info)
    async with session_factory() as session:
        hint = await session.get(LavaInvoice, invoice_id)
        owner_id = hint.user_id if hint is not None else None
        await session.rollback()  # end the autobegun read before the locked unit of work
        if owner_id is None:
            return ApplyOutcome("unmatched", invoice_id=invoice_id, kind=kind)
        try:
            async with session.begin():
                user = await UserRepository(session).get_by_user_id(owner_id, lock=True)
                row = await _lock_invoice(session, invoice_id)
                if row is None or row.status not in APPLICABLE_STATUSES:
                    return ApplyOutcome("duplicate", invoice_id=invoice_id, kind=kind,
                                        payment_id=getattr(row, "payment_id", None), user_id=owner_id)
                if row.user_id != owner_id:
                    return ApplyOutcome("needs_review", invoice_id=invoice_id, review_reason="owner_changed")
                days = term_days(row.plan_type or "")
                reason = None
                if user is None:
                    reason = "user_missing"
                elif info.currency != row.currency:
                    reason = "currency_mismatch"
                elif not days:
                    reason = "unknown_plan"
                if reason:
                    row.review_reason = reason
                    row.last_checked_at = _now()
                    return ApplyOutcome("needs_review", invoice_id=invoice_id, user_id=owner_id,
                                        review_reason=reason, kind=kind)
                amount = info.amount
                # The promo-code discount applies to the first contract only;
                # renewals are recorded at the amount lava actually charged.
                promo = row.kind != "renewal" and row.discount_source and row.discount_percent
                payment = await PaymentRepository(session).create(
                    user, plan_type=row.plan_type,
                    amount=int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
                    currency=row.currency, payment_status="pending", payment_method=LAVA_PAYMENT_METHOD,
                    base_amount=await _base_amount_tjs(session, amount, row.currency),
                    local_amount=str(amount), local_currency=row.currency, source=row.source,
                    discount_source=row.discount_source if promo else "none",
                    discount_percent=int(row.discount_percent) if promo else 0,
                    discount_campaign_id=row.discount_campaign_id if promo else None,
                    discount_title=f"lava promo {row.promo_code}" if promo and row.promo_code else None,
                )
                result = await review_locked_payment(
                    session, payment=payment, user=user, decision="approve",
                    comment=f"lava:{row.contract_id}",
                )
                granted_until = _utc(user.end_date)
                now = _now()
                row.status = "paid"
                row.paid_amount = amount
                row.paid_at = now
                row.last_checked_at = now
                row.payment_id = payment.id
                row.granted_days = days
                row.granted_until = granted_until
                row.granted_from = granted_until - timedelta(days=days) if granted_until else None
                if row.expected_amount is not None and not amounts_equal(row.expected_amount, amount):
                    row.review_reason = "amount_mismatch"
                if kind == "renewal" and row.parent_contract_id:
                    parent = (await session.execute(
                        select(LavaInvoice).where(LavaInvoice.contract_id == row.parent_contract_id)
                        .with_for_update()
                    )).scalar_one_or_none()
                    if parent is not None and parent.subscription_status != "cancelled":
                        parent.subscription_status = "active"
                    if parent is not None and parent.review_reason == "renewal_overdue":
                        parent.review_reason = None
                elif info.invoice_type == "SUBSCRIPTION_FIRST_INVOICE":
                    row.subscription_status = "active"
                outcome = ApplyOutcome(
                    "applied", invoice_id=invoice_id, payment_id=payment.id, user_id=owner_id,
                    review_reason=row.review_reason, review_result=result, kind=kind,
                )
        except PaymentReviewError as exc:
            logger.error("lava.top activation failed for invoice %s: %s", invoice_id, exc)
            async with session_factory() as fail_session, fail_session.begin():
                row = await _lock_invoice(fail_session, invoice_id)
                if row is not None and row.status in APPLICABLE_STATUSES:
                    row.review_reason = "activation_failed"
                    row.last_checked_at = _now()
            return ApplyOutcome("activation_failed", invoice_id=invoice_id, user_id=owner_id,
                                review_reason=str(exc), kind=kind)
    return outcome


async def mark_failed(session_factory, contract_id: str) -> int | None:
    async with session_factory() as session, session.begin():
        row = await _invoice_by_contract(session, contract_id)
        if row is None:
            return None
        row = await _lock_invoice(session, row.id)
        if row.status == "created":
            row.status = "failed"
            row.last_checked_at = _now()
        return row.id


async def mark_subscription(session_factory, contract_id: str, *, status: str,
                            cancelled_at: datetime | None = None,
                            will_expire_at: datetime | None = None) -> tuple[LavaInvoice | None, str | None]:
    """Record cancellation/failure on the first (parent) contract. Never touches
    ``users.end_date`` or payments: the paid term is kept."""
    async with session_factory() as session, session.begin():
        row = await _invoice_by_contract(session, contract_id)
        if row is not None and row.kind == "renewal" and row.parent_contract_id:
            row = await _invoice_by_contract(session, row.parent_contract_id)
        if row is None:
            return None, None
        row = await _lock_invoice(session, row.id)
        previous = row.subscription_status
        if status == "cancelled" or row.subscription_status != "cancelled":
            row.subscription_status = status
        if status == "cancelled":
            row.cancelled_at = row.cancelled_at or cancelled_at or _now()
            row.will_expire_at = will_expire_at or row.will_expire_at
        await session.flush()
        session.expunge(row)
        return row, previous


async def find_revocation_candidate(session, *, email: str | None, tier_id: str | None,
                                    currency: str | None, amount: Decimal | None,
                                    full_refund: bool) -> tuple[LavaInvoice | None, str | None]:
    """Refund/chargeback payloads have no contract id: match only our own
    invoice data (buyer email we stored, offer id, currency, amount)."""
    email = normalize_email(email)
    if email is None or currency is None or amount is None:
        return None, "refund_unmatched"
    query = select(LavaInvoice).where(
        LavaInvoice.status == "paid", LavaInvoice.buyer_email == email,
        LavaInvoice.currency == currency, LavaInvoice.user_id.is_not(None),
    )
    if tier_id:
        query = query.where(LavaInvoice.offer_id == tier_id.lower())
    rows = list((await session.execute(query.order_by(LavaInvoice.paid_at.desc(), LavaInvoice.id.desc())
                                       .limit(20))).scalars())
    if full_refund:
        rows = [row for row in rows if amounts_equal(row.paid_amount, amount)]
    else:
        rows = [row for row in rows if row.paid_amount is not None and amount <= row.paid_amount]
    if not rows:
        return None, "refund_unmatched"
    return rows[0], None


async def _expire_payment_budgets(session, payment_id: int) -> None:
    budgets = (await session.execute(select(AIUsageBudget).where(
        AIUsageBudget.payment_id == payment_id, AIUsageBudget.status == "active",
    ))).scalars().all()
    service = AIUsageBudgetService(session)
    for budget in budgets:
        await service.expire_budget(budget)


async def revoke_invoice(session_factory, invoice_id: int, *, kind: str) -> RevokeOutcome:
    """Remove exactly the days one verified lava payment granted."""
    assert kind in {"refund", "chargeback"}
    async with session_factory() as session:
        hint = await session.get(LavaInvoice, invoice_id)
        owner_id = hint.user_id if hint is not None else None
        await session.rollback()
        if owner_id is None:
            return RevokeOutcome("needs_review", invoice_id=invoice_id, review_reason="refund_unmatched")
        async with session.begin():
            user = await UserRepository(session).get_by_user_id(owner_id, lock=True)
            row = await _lock_invoice(session, invoice_id)
            if row is None or row.status not in GRANTED_STATUSES or row.payment_id is None:
                return RevokeOutcome("duplicate", invoice_id=invoice_id)
            payment = (await session.execute(
                select(Payment).where(Payment.id == row.payment_id).with_for_update()
                .execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if payment is None or user is None:
                row.review_reason = "revoke_owner_missing"
                return RevokeOutcome("needs_review", invoice_id=invoice_id, review_reason=row.review_reason)
            now = _now()
            new_end = None
            current_end = _utc(user.end_date)
            if current_end is not None and row.granted_days:
                new_end = current_end - timedelta(days=row.granted_days)
                user.end_date = new_end
                if new_end <= now and user.status == "active":
                    user.status = "expired"
            payment.payment_status = "refunded" if kind == "refund" else "chargeback"
            payment.admin_comment = f"lava:{kind}:{row.contract_id}"
            await session.execute(delete(PortfolioTransaction).where(
                PortfolioTransaction.payment_id == payment.id,
                PortfolioTransaction.source == "subscription_profit",
            ))
            await _expire_payment_budgets(session, payment.id)
            credit = (await session.execute(
                select(PartnerCredit.id).where(PartnerCredit.payment_id == payment.id)
            )).first()
            row.status = "refunded" if kind == "refund" else "chargeback_open"
            row.revoked_at = now
            await session.flush()
            session.expunge(user)
            return RevokeOutcome("revoked", invoice_id=invoice_id, payment_id=payment.id, user=user,
                                 partner_credit=credit is not None, new_end_date=new_end)


async def close_chargeback(session_factory, invoice_id: int, *, won: bool) -> RevokeOutcome:
    """Admin-recorded chargeback outcome. Won restores the removed days."""
    async with session_factory() as session:
        hint = await session.get(LavaInvoice, invoice_id)
        owner_id = hint.user_id if hint is not None else None
        await session.rollback()
        if owner_id is None:
            return RevokeOutcome("needs_review", invoice_id=invoice_id, review_reason="chargeback_unknown")
        async with session.begin():
            user = await UserRepository(session).get_by_user_id(owner_id, lock=True)
            row = await _lock_invoice(session, invoice_id)
            if row is None or row.status != "chargeback_open":
                return RevokeOutcome("duplicate", invoice_id=invoice_id)
            if not won:
                row.status = "chargeback_lost"
                return RevokeOutcome("closed", invoice_id=invoice_id, payment_id=row.payment_id)
            payment = (await session.execute(
                select(Payment).where(Payment.id == row.payment_id).with_for_update()
                .execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if payment is None or user is None or not row.granted_days:
                return RevokeOutcome("needs_review", invoice_id=invoice_id, review_reason="restore_missing")
            now = _now()
            current_end = _utc(user.end_date)
            extends = bool(user.payment_status == "approved" and current_end and current_end > now)
            starts = current_end if extends else now
            ends = starts + timedelta(days=row.granted_days)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = ends
            if not extends or user.start_date is None:
                user.start_date = now
            payment.payment_status = "approved"
            payment.admin_comment = f"lava:chargeback_won:{row.contract_id}"
            await PortfolioService(session).record_subscription_profit(payment)
            await AIUsageBudgetService(session).create_for_payment(
                payment=payment, starts_at=starts, ends_at=ends, preserve_existing=extends,
            )
            row.status = "chargeback_won"
            row.revoked_at = None
            row.granted_from, row.granted_until = starts, ends
            await session.flush()
            session.expunge(user)
            return RevokeOutcome("restored", invoice_id=invoice_id, payment_id=payment.id, user=user,
                                 new_end_date=ends)
