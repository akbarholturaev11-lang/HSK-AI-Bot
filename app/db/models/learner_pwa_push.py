"""Learner-only, device-bound Web Push subscription. Admin PWA state is separate."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LearnerPwaPushSubscription(Base):
    __tablename__ = "learner_pwa_push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint_hash", name="uq_learner_pwa_push_endpoint"),
        UniqueConstraint("device_id", name="uq_learner_pwa_push_device"),
        CheckConstraint("length(endpoint_hash) = 64", name="ck_learner_pwa_push_endpoint_hash"),
        Index("ix_learner_pwa_push_revoked", "revoked_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("desktop_devices.id", ondelete="CASCADE"), nullable=False
    )
    endpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearnerPwaPushOutbox(Base):
    """Content-free, deduplicated push work for existing account/course notices."""

    __tablename__ = "learner_pwa_push_outbox"
    __table_args__ = (
        UniqueConstraint("subscription_id", "event_key", name="uq_learner_pwa_push_event_device"),
        CheckConstraint("source IN ('account', 'course', 'payment')", name="ck_learner_pwa_push_source"),
        CheckConstraint(
            "state IN ('pending', 'leased', 'retry', 'accepted', 'dead', 'cancelled')",
            name="ck_learner_pwa_push_state",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 4", name="ck_learner_pwa_push_attempts"),
        CheckConstraint("length(event_key) = 64", name="ck_learner_pwa_push_event_key"),
        Index("ix_learner_pwa_push_due", "state", "next_attempt_at"),
        Index("ix_learner_pwa_push_outbox_subscription", "subscription_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("learner_pwa_push_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(36))
    last_http_status: Mapped[int | None] = mapped_column(Integer)
