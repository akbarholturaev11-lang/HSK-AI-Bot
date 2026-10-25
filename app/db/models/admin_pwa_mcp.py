"""Server-held opaque OAuth access grants for future read-only MCP resource.

The model is inert: no issuer, OAuth endpoint, or public MCP transport exists.
Only an audited OAuth authorization-code + PKCE + consent service may create
grants in a future increment. No browser-session token is stored here.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AdminPwaMcpAccessGrant(Base):
    __tablename__ = "admin_pwa_mcp_access_grants"
    __table_args__ = (
        Index("ix_admin_pwa_mcp_access_grants_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    # No plaintext bearer token is stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # OAuth resource URI and client are fixed by a future consent ceremony.
    audience: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Future OAuth server must generate and audit this consent event identifier.
    consent_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
