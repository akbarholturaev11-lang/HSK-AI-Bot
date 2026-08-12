from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseUserNotification(Base):
    __tablename__ = "course_user_notifications"
    __table_args__ = (
        UniqueConstraint(
            "telegram_id",
            "key",
            "dedupe_key",
            name="uq_course_user_notifications_telegram_key_dedupe",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="course_notification", index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Template name plus its arguments, so the feed can be re-rendered in the
    # language the reader is using now instead of the one that was active when
    # the reminder was sent. Null on rows written before this column existed.
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    action: Mapped[str] = mapped_column(String(32), default="course", nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    lesson_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
