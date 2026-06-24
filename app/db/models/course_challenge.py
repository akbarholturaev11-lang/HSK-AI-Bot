from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseChallenge(Base):
    __tablename__ = "course_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenger_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    opponent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    winner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, default="hsk1")
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="uz")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    question_payload: Mapped[str] = mapped_column(Text, nullable=False)

    challenger_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    challenger_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    challenger_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    challenger_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    challenger_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    opponent_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    opponent_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    opponent_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    opponent_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    opponent_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
