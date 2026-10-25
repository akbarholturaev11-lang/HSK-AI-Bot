"""Private native inbox intake; never part of the external MCP projection."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaNativeReport(Base):
    __tablename__ = "admin_pwa_native_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "deduplication_key", name="uq_admin_pwa_native_report_dedup"),
        CheckConstraint("length(description) BETWEEN 5 AND 2000", name="ck_admin_pwa_native_report_text"),
        CheckConstraint("length(attachment_bytes) <= 563200", name="ck_admin_pwa_native_report_attachment"),
        CheckConstraint("notification_state IN ('pending', 'sent', 'failed')", name="ck_admin_pwa_native_report_delivery"),
        Index("ix_admin_pwa_native_report_user_attempt", "user_id", "last_attempt_at"),
        Index("ix_admin_pwa_native_report_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    app_version: Mapped[str] = mapped_column(String(40), nullable=False)
    screen: Mapped[str] = mapped_column(String(80), nullable=False)
    attachment_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    notification_state: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
