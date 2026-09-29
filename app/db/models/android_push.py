from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AndroidPushToken(Base):
    """One FCM token and its push preferences per authenticated Android install."""

    __tablename__ = "android_push_tokens"

    device_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("desktop_devices.id", ondelete="CASCADE"),
        primary_key=True,
    )
    token: Mapped[str] = mapped_column(String(4096), unique=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    study_reminders_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    timezone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_study_push_day: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Whether the phone can show an account notice right now. NULL means the
    # installed build predates account notices, so they go to Telegram.
    notifications_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
