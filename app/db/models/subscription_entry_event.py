from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SubscriptionEntryEvent(Base):
    __tablename__ = "subscription_entry_events"
    __table_args__ = (
        Index("ix_subscription_entry_events_client_created_at", "client", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(40), index=True, nullable=False, default="subscription")
    plan_type: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(16), index=True, nullable=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    feedback_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    # Next-stage R3: the client of the route that recorded the entry
    # (telegram / iphone_pwa / android). Set by the route, never by the caller;
    # NULL for Desktop (frozen) and for rows written before 0155.
    client: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
