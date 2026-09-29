from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountNoticeDelivery(Base):
    """One subscription/limit notice sent to Android first, Telegram second.

    The Android app has to confirm that it actually showed the notice: FCM
    accepting a message only means Google took it. Until that confirmation
    arrives the row stays ``android_pending``; once ``fallback_due_at`` passes
    the scheduler sends the stored Telegram message instead.
    """

    __tablename__ = "account_notice_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    # Plain text for the phone; the Telegram copy keeps its HTML in the payload.
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="subscription", nullable=False)
    # android_pending | android_shown | telegram_sent | telegram_failed
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    android_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    android_blocked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    telegram_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(String(40), default="account_notice", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    fallback_due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    android_shown_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    telegram_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
