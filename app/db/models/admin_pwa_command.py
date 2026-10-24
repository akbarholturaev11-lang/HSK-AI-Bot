"""Immutable command evidence survives session/credential/account deletion."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaCommandAudit(Base):
    __tablename__ = "admin_pwa_command_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    step_up_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc))
