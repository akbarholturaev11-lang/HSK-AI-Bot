"""Encrypted per-install Apple Web Push subscriptions; no delivery yet."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AdminPwaPushSubscription(Base):
    __tablename__ = "admin_pwa_push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint_hash", name="uq_admin_pwa_push_endpoint"),
        CheckConstraint("platform IN ('iphone', 'mac')", name="ck_admin_pwa_push_platform"),
        Index("ix_admin_pwa_push_user", "user_id", "revoked_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_payload: Mapped[str] = mapped_column(Text(), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
