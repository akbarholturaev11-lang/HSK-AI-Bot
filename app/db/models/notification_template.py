from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationTemplate(Base):
    """Admin-editable motivational reminder templates.

    One row per reminder ``key`` (see MOTIVATION_KEYS). Text is stored per
    language; when a language text is empty the scheduler falls back to the
    built-in default text so a misconfiguration can never silence the reminder.
    A single shared media file (photo/video) can be attached to all languages.
    """

    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    text_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_tj: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    media_type: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    media_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
