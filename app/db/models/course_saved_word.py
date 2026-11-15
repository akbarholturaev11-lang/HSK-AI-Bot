"""Account-owned dictionary bookmarks; independent of course error/SRS truth."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CourseSavedWord(Base):
    __tablename__ = "course_saved_words"
    __table_args__ = (
        UniqueConstraint("user_id", "hanzi", name="uq_course_saved_words_user_hanzi"),
        Index("ix_course_saved_words_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hanzi: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
