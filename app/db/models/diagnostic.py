"""Automatic failure incidents and their per-event receipts (design D2).

Content-free by construction: only catalog codes, versions, times and counts.
No message, stack, URL, payload or device identifier is ever stored here.
The triage status lives only in ``admin_pwa_inbox_triage`` (source
``diagnostic``), never in these tables.
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String,
    UniqueConstraint, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiagnosticIncident(Base):
    __tablename__ = "diagnostic_incidents"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_diagnostic_incidents_fingerprint"),
        CheckConstraint("platform IN ('android', 'iphone_pwa', 'telegram', 'server')",
                        name="ck_diagnostic_incidents_platform"),
        CheckConstraint("severity IN ('normal', 'high', 'critical')", name="ck_diagnostic_incidents_severity"),
        CheckConstraint("occurrence_count >= 0 AND refused_count >= 0", name="ck_diagnostic_incidents_counts"),
        CheckConstraint("last_alert_reason IS NULL OR last_alert_reason IN ('new', 'escalated', 'reopened')",
                        name="ck_diagnostic_incidents_alert_reason"),
        Index("ix_diagnostic_incidents_last_seen", "last_seen_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    feature_code: Mapped[str] = mapped_column(String(40), nullable=False)
    failure_code: Mapped[str] = mapped_column(String(40), nullable=False)
    site_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refused_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Comparable build order: Android versionCode, PWA token date; null for backend.
    last_build: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    resolved_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resolved_build: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    alert_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_alert_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)


class DiagnosticReceipt(Base):
    __tablename__ = "diagnostic_receipts"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_diagnostic_receipts_owner_event"),
        CheckConstraint("channel IS NULL OR channel IN ('play', 'direct')", name="ck_diagnostic_receipts_channel"),
        CheckConstraint("outcome IN ('failed', 'recovered')", name="ck_diagnostic_receipts_outcome"),
        CheckConstraint("occurrences BETWEEN 1 AND 10000", name="ck_diagnostic_receipts_occurrences"),
        # Server rows have no owner; PostgreSQL treats NULL owners as distinct.
        Index("uq_diagnostic_receipts_server_event", "event_id", unique=True,
              postgresql_where=text("user_id IS NULL"), sqlite_where=text("user_id IS NULL")),
        Index("ix_diagnostic_receipts_owner_received", "user_id", "received_at"),
        Index("ix_diagnostic_receipts_incident_received", "incident_id", "received_at"),
        Index("ix_diagnostic_receipts_received", "received_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True,
                                    autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_incidents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    client_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_time_untrusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    build: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(8), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str | None] = mapped_column(String(24), nullable=True)
    # Coalesced backend writes carry their count; client receipts are always 1.
    occurrences: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
