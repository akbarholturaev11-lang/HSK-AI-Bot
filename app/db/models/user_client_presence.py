from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserClientPresence(Base):
    """Compact per-user client presence.

    Native installs are deliberately NOT stored here. Android/macOS/Windows
    installations already have an authoritative registry in desktop_devices.
    This table fills the missing piece: where the Telegram Mini App was
    actually opened.
    """

    __tablename__ = "user_client_presences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "surface",
            "platform",
            name="uq_user_client_presence_user_surface_platform",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    surface: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    app_version: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True, nullable=False
    )
    last_foreground_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class AppPromoState(Base):
    """Server-authoritative automatic app-promo cooldown per target platform."""

    __tablename__ = "app_promo_states"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "target_platform",
            name="uq_app_promo_state_user_platform",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    target_platform: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_dismissed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_download_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
