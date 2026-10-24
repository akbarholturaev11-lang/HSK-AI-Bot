"""Pending/approved MCP authorization code ceremony; no remote OAuth endpoint.

The browser administrator must explicitly approve the requested client,
redirect and stats-only scope before an exchange code exists. Codes and
resource access tokens are stored ONLY as hashes. Session cookie hashes are
never returned to the MCP client.
"""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AdminPwaMcpAuthorization(Base):
    __tablename__ = "admin_pwa_mcp_authorizations"
    __table_args__ = (
        Index("ix_admin_pwa_mcp_authorizations_user_created", "user_id", "created_at"),
        Index("ix_admin_pwa_mcp_authorizations_expires_at", "expires_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("admin_pwa_sessions.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(128), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    pkce_challenge: Mapped[str] = mapped_column(String(43), nullable=False)
    client_state: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
