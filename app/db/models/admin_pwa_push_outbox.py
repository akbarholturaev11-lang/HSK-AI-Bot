"""Content-free, device-scoped Admin PWA Web Push delivery outbox.

No user report text or bearer-like push endpoint/key material may appear here.
Dispatch remains separately gated and is not enabled by this model.
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class AdminPwaPushOutbox(Base):
    __tablename__ = "admin_pwa_push_outbox"
    __table_args__ = (
        UniqueConstraint("subscription_id", "event_key", name="uq_admin_pwa_push_outbox_event_device"),
        CheckConstraint("source IN ('bot', 'release', 'android', 'payment', 'technical', 'diagnostic')",
                        name="ck_admin_pwa_push_outbox_source"),
        CheckConstraint("state IN ('pending', 'leased', 'retry', 'accepted', 'dead', 'cancelled')",
                        name="ck_admin_pwa_push_outbox_state"),
        CheckConstraint("attempts BETWEEN 0 AND 4", name="ck_admin_pwa_push_outbox_attempts"),
        CheckConstraint("triage_revision >= 1", name="ck_admin_pwa_push_outbox_revision"),
        CheckConstraint("(source = 'diagnostic' AND diagnostic_kind IS NOT NULL AND diagnostic_kind IN ('new','escalated','reopened')) OR "
                        "(source <> 'diagnostic' AND diagnostic_kind IS NULL)", name=conv("ck_admin_pwa_outbox_diagnostic_kind")),
        Index("ix_admin_pwa_push_outbox_due", "state", "next_attempt_at"),
        Index("ix_admin_pwa_push_outbox_subscription", "subscription_id", "created_at"),
        Index("ix_admin_pwa_outbox_diag_cap", "source", "diagnostic_kind", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("admin_pwa_push_subscriptions.id", ondelete="CASCADE"), nullable=False)
    # Immutable key is a digest of source/id/triage_revision: never content.
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    triage_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    diagnostic_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
