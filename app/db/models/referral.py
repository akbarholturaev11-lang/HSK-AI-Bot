from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)

    referrer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True,
    )
    invited_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True,
    )
    # Optional transport metadata; canonical ownership always takes priority.
    referrer_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    invited_user_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    bonus_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    counts_for_discount: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discount_platform: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    discount_qualified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
