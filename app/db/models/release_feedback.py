from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReleaseFeedbackCampaign(Base):
    __tablename__ = "release_feedback_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(16), default="text", nullable=False)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    feature_key: Mapped[str] = mapped_column(String(32), default="general", nullable=False)

    status: Mapped[str] = mapped_column(String(16), default="scheduled", index=True, nullable=False)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    target_languages: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status_filter: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    level_filter: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    mode_filter: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    payment_status_filter: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    payment_method_filter: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    plan_filter: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    discount_filter: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    course_promo_filter: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    activity_filter: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    discount_percent: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    discount_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    trial_access_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    created_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ReleaseFeedbackDelivery(Base):
    __tablename__ = "release_feedback_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "user_telegram_id",
            name="uq_release_feedback_deliveries_campaign_user",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("release_feedback_campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    try_clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_granted_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ReleaseFeedbackResponse(Base):
    __tablename__ = "release_feedback_responses"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "user_telegram_id",
            name="uq_release_feedback_responses_campaign_user",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("release_feedback_campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    attachment_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    discount_campaign_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
