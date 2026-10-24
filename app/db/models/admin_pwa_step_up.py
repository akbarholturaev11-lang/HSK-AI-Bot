"""Short-lived, session- and exact-mutation-bound WebAuthn confirmations.

These records are never sessions, entitlements or executable admin commands.
The verified receipt is consumed in the *same transaction* as a future
dedicated PWA mutation. Legacy Telegram admin routes remain independent.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AdminPwaStepUp(Base):
    __tablename__ = "admin_pwa_step_ups"
    __table_args__ = (
        Index("ix_admin_pwa_step_ups_created_at", "created_at"),
        Index("ix_admin_pwa_step_ups_expires_at", "expires_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("admin_pwa_sessions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    challenge: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    credential_id: Mapped[Optional[bytes]] = mapped_column(LargeBinary(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
