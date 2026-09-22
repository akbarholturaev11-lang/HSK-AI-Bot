"""Provider identities linked to one internal user.

A Google or Apple login is NEVER a separate account. It is an additional
identity row pointing at the same ``users.id`` that Telegram already owns, so
subscription, referral, progress and analytics stay on one account. This is the
model required by ``DESKTOP_AUTH_CONTRACT.md`` and ``PROJECT_MEMORY.md``.

``subject_hash`` is a keyed HMAC of the provider ``sub`` claim, not the raw
value. Lookups are exact-match only, so plaintext is never needed, and a
database dump does not hand out directly usable, cross-service-linkable
Google/Apple account identifiers.

``email_hash`` / ``email_display`` are display and abuse-analytics metadata
ONLY. No account-resolution branch may read them: an email address is
attacker-influenceable, provider-scoped and recyclable, so merging accounts on
it would turn "sign in with Google" into takeover of a paying subscriber.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Telegram is not written in Phase 1 — ``users.telegram_id`` stays the single
# source of truth for it. The value is allowed here so Phase 2 can backfill
# without a second schema change.
IDENTITY_PROVIDERS = ("google", "apple", "telegram")


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        # Core invariant: one provider identity belongs to at most one internal
        # user, globally. Everything else in the link service depends on it.
        UniqueConstraint(
            "provider", "subject_hash", name="uq_user_identities_provider_subject"
        ),
        UniqueConstraint(
            "user_id", "provider", name="uq_user_identities_user_provider"
        ),
        Index("ix_user_identities_user_id", "user_id"),
        Index("ix_user_identities_email_hash", "email_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    email_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email_display: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    # The client_id the verified token was minted for. Audit trail for
    # cross-client replay investigations.
    audience: Mapped[Optional[str]] = mapped_column(String(190), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
