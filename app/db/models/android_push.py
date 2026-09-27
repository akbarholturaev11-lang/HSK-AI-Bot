from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AndroidPushToken(Base):
    """One FCM token per authenticated Android installation."""

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
