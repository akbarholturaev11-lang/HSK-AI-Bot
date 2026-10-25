"""Browser-bound, one-time WebAuthn sign-in challenges.

These rows are NOT authenticated sessions. No Telegram or Google identity
is embedded in an anonymous challenge. Authenticator identity must be
cryptographically verified against a stored public key later.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AdminPwaAuthenticationChallenge(Base):
    __tablename__ = "admin_pwa_authentication_challenges"
    __table_args__ = (
        Index("ix_admin_pwa_authentication_challenges_created_at", "created_at"),
        Index("ix_admin_pwa_authentication_challenges_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    challenge: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    browser_proof_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
