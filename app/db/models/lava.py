"""lava.top automated Pro subscription state.

``lava_invoices`` keeps the provider contract → canonical account ownership
created by our own server. A ``payments`` row is created only inside the
verified activation transaction, so pre-payment lava state never appears in
manual review queues. Financial facts outlive account deletion; purge clears
``buyer_email`` and the canonical association like ``payments``.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


LAVA_INVOICE_STATUSES = (
    "created", "paid", "failed", "expired", "refunded",
    "chargeback_open", "chargeback_won", "chargeback_lost", "unmatched",
)
LAVA_INVOICE_KINDS = ("first", "renewal", "external")
LAVA_EVENT_RESULTS = (
    "received", "queued", "applied", "duplicate", "ignored", "unmatched",
    "needs_review", "retry", "error",
)


def _in(values) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LavaInvoice(Base):
    __tablename__ = "lava_invoices"
    __table_args__ = (
        CheckConstraint(f"status IN ({_in(LAVA_INVOICE_STATUSES)})", name="status"),
        CheckConstraint(f"kind IN ({_in(LAVA_INVOICE_KINDS)})", name="kind"),
        CheckConstraint("granted_days IS NULL OR granted_days > 0", name="granted_days"),
        Index("ix_lava_invoices_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    parent_contract_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="first")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    plan_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    offer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    periodicity: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expected_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    paid_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    buyer_email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="miniapp")
    promo_code: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="created")
    review_reason: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    subscription_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    will_expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    granted_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    granted_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now,
    )


class LavaWebhookEvent(Base):
    __tablename__ = "lava_webhook_events"
    __table_args__ = (
        CheckConstraint(f"result IN ({_in(LAVA_EVENT_RESULTS)})", name="result"),
        Index("ix_lava_webhook_events_result_received", "result", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    contract_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    parent_contract_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    tier_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    refund_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    email_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Kept only until the event reaches a final result (needed to replay
    # queued/retry events); cleared afterwards so emails do not linger.
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(24), nullable=False, default="received")
    error_code: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invoice_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
