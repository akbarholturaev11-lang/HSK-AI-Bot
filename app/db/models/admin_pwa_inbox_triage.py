"""Per-source admin-only inbox triage, separate from original feedback records."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AdminPwaInboxTriage(Base):
    __tablename__ = "admin_pwa_inbox_triage"
    __table_args__ = (
        CheckConstraint("source IN ('bot', 'release', 'android', 'payment', 'technical')", name="ck_admin_pwa_inbox_triage_source"),
        CheckConstraint("status IN ('new', 'read', 'assigned', 'resolved')", name="ck_admin_pwa_inbox_triage_status"),
        CheckConstraint("priority IN ('normal', 'important')", name="ck_admin_pwa_inbox_triage_priority"),
        CheckConstraint("revision >= 1", name="ck_admin_pwa_inbox_triage_revision"),
        Index("ix_admin_pwa_inbox_triage_status", "status", "priority"),
    )
    source: Mapped[str] = mapped_column(String(16), primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)


class AdminPwaInboxTriageAudit(Base):
    __tablename__ = "admin_pwa_inbox_triage_audit"
    __table_args__ = (
        CheckConstraint("source IN ('bot', 'release', 'android', 'payment', 'technical')", name="ck_admin_pwa_inbox_audit_source"),
        CheckConstraint("operation IN ('mark_read','assign_self','resolve','reopen','mark_important','clear_important')",
                        name="ck_admin_pwa_inbox_audit_operation"),
        Index("ix_admin_pwa_inbox_audit_created", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
