from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)

    promotion_channel: Mapped[str] = mapped_column(Text, nullable=False)
    audience_size: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_username: Mapped[str] = mapped_column(String(128), nullable=False)

    approved_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signup_bonus_granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PartnerReferral(Base):
    __tablename__ = "partner_referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    invited_user_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    first_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PartnerCredit(Base):
    __tablename__ = "partner_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    payment_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    credit_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PartnerPayout(Base):
    __tablename__ = "partner_payouts"
    __table_args__ = (
        Index(
            "uq_partner_payouts_one_open_per_partner",
            "partner_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'deadline_set', 'processing')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    local_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    local_currency: Mapped[str] = mapped_column(String(8), default="TJS", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True, nullable=False)

    payment_method: Mapped[str] = mapped_column(String(24), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    account_details: Mapped[str] = mapped_column(Text, nullable=False)
    holder_name: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recipient_qr_code_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    proof_screenshot_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    reviewed_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
