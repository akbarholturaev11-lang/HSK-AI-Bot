from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoicePracticeSession(Base):
    __tablename__ = "voice_practice_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    level: Mapped[str] = mapped_column(String(24), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    voice: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    corrections: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    lesson_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    target_words: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
