from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseTrackState(Base):
    __tablename__ = "course_track_states"
    __table_args__ = (
        UniqueConstraint("user_id", "track", name="uq_course_track_states_user_track"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    completed_lessons_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    unlock_payment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
