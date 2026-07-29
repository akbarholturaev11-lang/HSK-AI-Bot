from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DesktopLinkRequest(Base):
    __tablename__ = "desktop_link_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_code_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    polling_secret_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    installation_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    app_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True, nullable=False
    )
    approved_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    approved_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, index=True, nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True, nullable=False
    )


class DesktopDevice(Base):
    __tablename__ = "desktop_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    installation_key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    app_version: Mapped[str] = mapped_column(String(40), nullable=False)
    first_open_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class DesktopSession(Base):
    __tablename__ = "desktop_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("desktop_devices.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    previous_refresh_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    rotated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
