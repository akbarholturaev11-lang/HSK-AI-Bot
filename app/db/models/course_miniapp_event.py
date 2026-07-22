from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


COURSE_MINIAPP_EVENT_NAMES = (
    "miniapp_opened",
    "onboarding_started",
    "onboarding_completed",
    "level_selected",
    "goal_selected",
    "daily_time_selected",
    "start_point_selected",
    "lesson_started",
    "section_started",
    "section_completed",
    "chapter_started",
    "chapter_completed",
    "book_lesson_completed",
    "level_completed",
    "lesson_jump_selected",
    "card_seen",
    "interaction_completed",
    "lesson_completed",
    "test_started",
    "test_completed",
    "training_started",
    "training_completed",
    "voice_started",
    "voice_completed",
    "practice_daily_used",
    "mistake_review_started",
    "mistake_review_answered",
    "mistake_review_completed",
    "course_ad_attempt_started",
    "course_ad_viewed",
    "paywall_seen",
    "checkout_opened",
    "subscription_approved",
    "xp_earned",
    "streak_updated",
    "league_points_earned",
    "motivation_lesson_unfinished_sent",
    "d1_recovery_assigned",
    "d1_recovery_sent",
    "d1_recovery_send_failed",
)

CLIENT_COURSE_MINIAPP_EVENT_NAMES = (
    "onboarding_started",
    "level_selected",
    "goal_selected",
    "daily_time_selected",
    "start_point_selected",
    "lesson_started",
    "section_started",
    "section_completed",
    "card_seen",
    "interaction_completed",
    "test_started",
    "training_started",
    "mistake_review_started",
    "paywall_seen",
    "checkout_opened",
)


class CourseMiniAppEvent(Base):
    __tablename__ = "course_miniapp_events"
    __table_args__ = (
        UniqueConstraint(
            "telegram_id",
            "event_name",
            "dedupe_key",
            name="uq_course_miniapp_events_telegram_event_dedupe",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    event_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="course_miniapp", index=True, nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    lesson_order: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(80), index=True, nullable=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
