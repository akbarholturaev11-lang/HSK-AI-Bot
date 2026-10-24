"""One-time Admin PWA Google+Telegram approval; no login sessions stored."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AdminPwaApproval(Base):
    __tablename__ = "admin_pwa_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    browser_proof_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    google_subject_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    google_audience: Mapped[str] = mapped_column(String(190), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
