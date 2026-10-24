"""Short-lived, browser-bound Admin PWA passkey-enrollment grant.

Created ONLY in the same transaction that consumes an approved Google+Bot
challenge and links the verified Google subject to the canonical admin.
Not a login session or a WebAuthn credential.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaEnrollmentGrant(Base):
    __tablename__ = "admin_pwa_enrollment_grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    approval_id: Mapped[str] = mapped_column(
        ForeignKey("admin_pwa_approvals.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # The original Google/Telegram browser-proof cookie must accompany the
    # independent enrollment-grant cookie; neither credential suffices alone.
    browser_proof_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
