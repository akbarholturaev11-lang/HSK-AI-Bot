from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseMiniAppProfile(Base):
    __tablename__ = "course_miniapp_profiles"
    __table_args__ = (
        CheckConstraint(
            "goal IN ('hsk_exam', 'study_china', 'work_china', 'daily_communication', 'travel')",
            name="goal",
        ),
        CheckConstraint("daily_minutes IN (5, 10, 15, 20, 30)", name="daily_minutes"),
        CheckConstraint(
            "start_mode IN ('lesson_1', 'continue', 'placement')",
            name="start_mode",
        ),
        CheckConstraint(
            "preferred_focus IN ('speaking', 'listening', 'vocabulary', 'grammar', 'none')",
            # Naming convention "ck_%(table_name)s_" prefiksini o'zi qo'shadi,
            # shuning uchun bu yerda faqat qisqa nom (qolgan CHECK'lar kabi).
            name="preferred_focus",
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
    # Onboardingdagi "nimaga urg'u beraylik" javobi. Kuzatilgan zaiflikning
    # (course_mistakes) O'RNINI BOSMAYDI — reja qurishda faqat boshlang'ich
    # taxmin (prior) bo'lib, real natijalar to'plangach ta'siri so'nadi.
    # NULL = hali so'ralmagan; "none" = "farqi yo'q" deb javob bergan.
    preferred_focus: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    # Kunlik XP maqsadi. NULL bo'lsa daily_minutes dan chiqariladi
    # (CourseMiniAppProfileService.resolve_daily_goal_xp).
    daily_goal_xp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timezone_offset_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Master switch for the motivational reminders. Default ON; the user turns it
    # off from the Mini App profile (with a warning). See MotivationReminderService.
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Motivational reminder bookkeeping (managed by MotivationReminderService).
    last_known_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    motivation_overtaken_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    motivation_goal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    motivation_streak_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Kunlik reja BARQARORLIGI. Kalit: "v1:<level>:<mahalliy sana>". Kalit mos
    # kelsa saqlangan task identity'si o'zgarmaydi — reja kun davomida boshqa
    # tasklarga almashib ketmaydi. Bajarilgan/ochiq holati bu yerda SAQLANMAYDI,
    # u har so'rovda course_xp_events va access servisidan qayta hisoblanadi.
    daily_plan_key: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    daily_plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
