from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OnboardingTipEvent(Base):
    __tablename__ = "onboarding_tip_events"
    __table_args__ = (
        UniqueConstraint("user_id", "tip_key", name="uq_onboarding_tip_events_user_tip"),
        Index("ix_onboarding_tip_events_status_due_at", "status", "due_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    tip_key: Mapped[str] = mapped_column(String(64), nullable=False)
    lang: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    context_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
