"""Read-only renewal notice for a naturally ended unlimited access period.

This is presentation only: no entitlement, payment or analytics writes.
Only an authenticated course map calls it; active/never-Pro users do no SQL.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.bot.generated.bot_i18n import bot_message
from app.db.models.bot_feedback import BotFeedback
from app.db.models.lava import LavaInvoice
from app.db.models.payment import Payment
from app.services.account_identity import owner_clause
from app.services.bot_feedback_service import FEEDBACK_REWARD_DURATION
from app.services.entitlements.state import EntitlementState, resolve_state
from app.services.lava.ledger import GRANTED_STATUSES
from app.services.subscription_service import SUBSCRIPTION_PLAN_DURATIONS
from app.services.user_access_state_service import UserAccessStateService

logger = logging.getLogger(__name__)


def expired_period(user, *, now):
    if resolve_state(user, now=now) not in {EntitlementState.FREE, EntitlementState.EXPIRED}:
        return None
    utc = UserAccessStateService.as_utc
    paid_end = utc(getattr(user, "end_date", None))
    paid_start = utc(getattr(user, "start_date", None))
    trial_end = utc(getattr(user, "pro_trial_ends_at", None))
    trial_start = utc(getattr(user, "pro_trial_started_at", None))
    revoked = utc(getattr(user, "pro_trial_revoked_at", None))
    candidates = []
    if (getattr(user, "payment_status", None) == "approved"
            and paid_start and paid_end and paid_start < paid_end <= now):
        candidates.append(("paid", paid_end))
    # expire_due also sets revoked_at. A revoke BEFORE the scheduled end is
    # different: never present an administrative revocation as natural expiry.
    if trial_start and trial_end and trial_start < trial_end <= now and (revoked is None or revoked >= trial_end):
        candidates.append(("trial", trial_end))
    return max(candidates, key=lambda item: item[1]) if candidates else None


async def _resolve_expiry_notice(session, user, *, now=None):
    now = now or datetime.now(timezone.utc)
    if resolve_state(user, now=now) not in {EntitlementState.FREE, EntitlementState.EXPIRED}:
        return None
    period = expired_period(user, now=now)
    start = UserAccessStateService.as_utc(getattr(user, "start_date", None))
    access_end = UserAccessStateService.as_utc(getattr(user, "end_date", None))
    # Feedback extends the temporary access period, not the Pro trial.
    # A stale approved marker can survive a fresh 30-minute reward.
    possible_feedback = bool(start and access_end and start < access_end <= now
        and (getattr(user, "payment_status", None) != "approved"
             or access_end - start <= FEEDBACK_REWARD_DURATION + timedelta(seconds=5)))
    if period is None and not possible_feedback:
        return None
    try:
        async with session.begin_nested():
            if possible_feedback:
                reward = await session.scalar(select(BotFeedback.id).where(
                    BotFeedback.user_id == user.id,
                    BotFeedback.status == "completed",
                    BotFeedback.reward_granted_at >= start,
                    BotFeedback.reward_granted_at <= access_end - FEEDBACK_REWARD_DURATION + timedelta(seconds=5),
                ).limit(1))
                if reward is not None and (period is None or access_end >= period[1]):
                    period = ("feedback", access_end)
            if period is None:
                return None
            kind, end = period
            # A submitted manual receipt or unresolved provider payment wins.
            pending = await session.scalar(select(Payment.id).where(
                owner_clause(Payment, user), Payment.payment_status == "pending",
            ).limit(1))
            if pending is not None:
                return None
            unresolved = await session.scalar(select(LavaInvoice.id).where(
                LavaInvoice.user_id == user.id,
                or_(
                    LavaInvoice.status == "chargeback_open",
                    LavaInvoice.review_reason == "create_uncertain",
                    (LavaInvoice.status == "created") & (LavaInvoice.created_at > now - timedelta(hours=24)),
                ),
            ).limit(1))
            if unresolved is not None:
                return None
            # Never ask a learner to buy again while an auto-renewing
            # provider contract is still active, including overdue renewals.
            active = await session.scalar(select(LavaInvoice.id).where(
                LavaInvoice.user_id == user.id,
                LavaInvoice.kind.in_(("first", "external")),
                LavaInvoice.status.in_(GRANTED_STATUSES),
                or_(LavaInvoice.subscription_status.is_(None), LavaInvoice.subscription_status == "active"),
            ).limit(1))
            if active is not None:
                return None
            if kind == "paid":
                latest = (await session.execute(select(Payment).where(
                    owner_clause(Payment, user),
                    Payment.plan_type.in_(tuple(SUBSCRIPTION_PLAN_DURATIONS)),
                    Payment.payment_status.in_(("approved", "refunded", "chargeback")),
                ).order_by(Payment.reviewed_at.desc().nulls_last(), Payment.id.desc()).limit(1))).scalar_one_or_none()
                # An explicit later admin grant has no payment row. Otherwise
                # the last financial event must not be a refund/chargeback.
                start = UserAccessStateService.as_utc(user.start_date)
                reviewed = UserAccessStateService.as_utc(latest.reviewed_at) if latest else None
                if latest and not (reviewed and reviewed < start - timedelta(minutes=1)):
                    if latest.payment_status != "approved":
                        return None
                    if latest.payment_method == "lava":
                        invoice = (await session.execute(select(LavaInvoice).where(
                            LavaInvoice.user_id == user.id, LavaInvoice.payment_id == latest.id,
                        ).limit(1))).scalar_one_or_none()
                        if not invoice or invoice.status not in GRANTED_STATUSES:
                            return None
                        parent = invoice
                        if invoice.kind == "renewal":
                            parent = (await session.execute(select(LavaInvoice).where(
                                LavaInvoice.user_id == user.id,
                                LavaInvoice.contract_id == invoice.parent_contract_id,
                            ).limit(1))).scalar_one_or_none()
                        if not parent or parent.subscription_status != "cancelled":
                            return None
            # Account-bound period token, not an identity or payment credential.
            return hashlib.sha256(f"pro-expiry:v1:{user.id}:{kind}:{end.isoformat()}".encode()).hexdigest(), kind
    except Exception:
        logger.exception("Subscription expiry notice lookup failed")
        return None

async def subscription_expiry_notice(session, user, *, now=None):
    """Compatibility accessor for the account-bound notice token."""
    notice = await _resolve_expiry_notice(session, user, now=now)
    return notice[0] if notice else None


async def subscription_expiry_payload(session, user, *, now=None, language=None):
    """One read for the existing sheet and its optional feedback-specific title."""
    notice = await _resolve_expiry_notice(session, user, now=now)
    payload = {"pro_expiry_notice": notice[0] if notice else None}
    if notice and notice[1] == "feedback":
        lang = language or getattr(user, "language", None)
        payload["pro_expiry_title"] = bot_message(
            "appFeedback.expiryTitle", lang if lang in {"uz", "ru", "tj"} else "ru"
        )
    return payload
