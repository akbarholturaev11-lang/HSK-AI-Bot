"""Short-lived, purpose-bound campaign media metadata; never binary storage."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminPwaCampaignAsset(Base):
    __tablename__ = 'admin_pwa_campaign_assets'
    __table_args__ = (
        CheckConstraint("status IN ('uploading','ready','failed','used')", name='ck_pwa_campaign_asset_status'),
        CheckConstraint("media_type IN ('photo','video')", name='ck_pwa_campaign_asset_type'),
        CheckConstraint('byte_count BETWEEN 1 AND 26214400', name='ck_pwa_campaign_asset_bytes'),
        Index('ix_pwa_campaign_asset_actor_created', 'actor_user_id', 'created_at'),
        Index('ix_pwa_campaign_asset_expiry', 'expires_at', 'id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey('admin_pwa_sessions.id', ondelete='CASCADE'), index=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    command_id: Mapped[str | None] = mapped_column(ForeignKey('admin_pwa_command_audit.id', ondelete='RESTRICT'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
