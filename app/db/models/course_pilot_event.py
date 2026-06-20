from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CoursePilotEvent(Base):
    __tablename__ = "course_pilot_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    lesson_order: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    block_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    step_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="course")
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
