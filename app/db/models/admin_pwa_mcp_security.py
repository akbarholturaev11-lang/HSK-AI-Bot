"""Minimal MCP audit and shared fixed-window quotas. Never store credentials."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaMcpAudit(Base):
    __tablename__ = "admin_pwa_mcp_audit"
    __table_args__ = (Index("ix_admin_pwa_mcp_audit_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminPwaMcpQuota(Base):
    __tablename__ = "admin_pwa_mcp_quotas"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False)
