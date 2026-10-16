"""Deletion-only ownership challenges and durable, explicitly confirmed requests."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountDeletionRequest(Base):
    __tablename__ = "account_deletion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # One outstanding request per account, even across concurrent replicas.
    active_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    browser_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
