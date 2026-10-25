"""Private provider-owned proof references; no uploaded image bytes in the DB."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaPayoutProof(Base):
    __tablename__ = 'admin_pwa_payout_proofs'
    __table_args__ = (
        CheckConstraint("status IN ('uploading','ready','failed','used')", name='ck_pwa_payout_proof_status'),
        Index('ix_pwa_payout_proof_actor_created', 'actor_user_id', 'created_at'),
        Index('ix_pwa_payout_proof_expiry', 'expires_at', 'id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey('admin_pwa_sessions.id', ondelete='CASCADE'), index=True)
    payout_id: Mapped[int] = mapped_column(ForeignKey('partner_payouts.id', ondelete='CASCADE'), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
