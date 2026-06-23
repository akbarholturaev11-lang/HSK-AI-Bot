from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseXpEvent(Base):
    __tablename__ = "course_xp_events"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_ref", name="uq_course_xp_events_user_activity_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    activity_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    activity_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    xp: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
