"""WebAuthn registration challenges and verified Admin PWA public credentials."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AdminPwaRegistrationChallenge(Base):
    __tablename__ = "admin_pwa_registration_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    grant_id: Mapped[str] = mapped_column(
        ForeignKey("admin_pwa_enrollment_grants.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    # Challenge is a non-secret, unpredictable 32-byte nonce. Never trust a
    # browser-claimed challenge; compare against this database value.
    challenge: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    user_handle: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminPwaCredential(Base):
    __tablename__ = "admin_pwa_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    credential_id: Mapped[bytes] = mapped_column(LargeBinary(1024), unique=True, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary(2048), nullable=False)
    user_handle: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    device_type: Mapped[str] = mapped_column(String(24), nullable=False)
    backed_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transports: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
