from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseMiniAppProfile(Base):
    __tablename__ = "course_miniapp_profiles"
    __table_args__ = (
        CheckConstraint(
            "goal IN ('hsk_exam', 'study_china', 'work_china', 'daily_communication', 'travel')",
            name="ck_course_miniapp_profiles_goal",
        ),
        CheckConstraint(
            "daily_minutes IN (5, 10, 15, 20, 30)",
            name="ck_course_miniapp_profiles_daily_minutes",
        ),
        CheckConstraint(
            "start_mode IN ('lesson_1', 'continue', 'placement')",
            name="ck_course_miniapp_profiles_start_mode",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    goal: Mapped[str] = mapped_column(String(32), default="hsk_exam", nullable=False)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    start_mode: Mapped[str] = mapped_column(String(24), default="continue", nullable=False)
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
