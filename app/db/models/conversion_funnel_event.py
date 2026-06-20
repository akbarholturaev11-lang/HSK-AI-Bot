from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


CONVERSION_FUNNEL_EVENT_NAMES = (
    "course_cta_seen",
    "course_started",
    "lesson_started",
    "quiz_completed",
    "ai_explanation_seen",
    "homework_completed",
    "paywall_seen",
    "checkout_opened",
    "payment_screenshot_submitted",
    "payment_approved",
    "payment_rejected",
)


class ConversionFunnelEvent(Base):
    __tablename__ = "conversion_funnel_events"
    __table_args__ = (
        CheckConstraint(
            "event_name IN ("
            "'course_cta_seen', "
            "'course_started', "
            "'lesson_started', "
            "'quiz_completed', "
            "'ai_explanation_seen', "
            "'homework_completed', "
            "'paywall_seen', "
            "'checkout_opened', "
            "'payment_screenshot_submitted', "
            "'payment_approved', "
            "'payment_rejected'"
            ")",
            name="ck_conversion_funnel_events_event_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    event_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(80), index=True, nullable=True)
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
