from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrialRiskEvent(Base):
    """Successful Pro-trial start paytidagi privacy-safe risk snapshot."""

    __tablename__ = "trial_risk_events"
    __table_args__ = (
        Index(
            "ix_trial_risk_events_installation_created",
            "installation_key_hash",
            "created_at",
        ),
        Index("ix_trial_risk_events_ip_created", "ip_hash", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    client: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    # Both are one-way HMAC/hash values. Raw IP and raw installation keys are
    # deliberately never persisted.
    installation_key_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    account_age_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prior_device_trial_users: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    prior_ip_trial_users_24h: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    prior_ip_trial_users_7d: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    signals_json: Mapped[str] = mapped_column(
        Text, default="[]", server_default="[]", nullable=False
    )
    mode: Mapped[str] = mapped_column(
        String(16), default="shadow", server_default="shadow", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
