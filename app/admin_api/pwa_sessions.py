"""Fail-closed, database-backed Admin PWA cookie-session verification.

This module deliberately does NOT issue sessions or implement Google/Telegram or
WebAuthn authentication. A login callback must prove BOTH identity and admin
approval before any session can be minted in a later, separately tested change.
"""

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.user import User


ADMIN_PWA_COOKIE_NAME = "__Host-hskai_admin"
_COOKIE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,192}$")


@dataclass(frozen=True)
class AdminPwaActor:
    user_id: int
    telegram_id: int
    auth_method: str


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _authorized_admin(user: Any, settings_obj: Any) -> bool:
    """A verified Telegram admin identity is required, never email matching."""
    raw = getattr(user, "telegram_id", None)
    try:
        tid = int(raw) if raw is not None else 0
        allowed = getattr(settings_obj, "admin_id_list", [])
        return tid > 0 and tid in allowed and getattr(user, "status", "") != "blocked"
    except (ValueError, TypeError):
        return False


async def authenticate_admin_pwa_session(db: Any, cookie: str, settings_obj: Any, *, now: datetime | None = None) -> AdminPwaActor | None:
    """Validate token hash, DB revocation/expiry, and *current* admin rights.

    No bearer headers, client user IDs or Telegram initData can replace this
    cookie. Null is a deliberate 401 result, not a fallback to any other auth.
    """
    if not isinstance(cookie, str) or not _COOKIE_PATTERN.fullmatch(cookie):
        return None
    token_hash = hashlib.sha256(cookie.encode("ascii")).hexdigest()
    row = (await db.execute(select(AdminPwaSession).where(AdminPwaSession.token_hash == token_hash))).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return None
    current_time = now or datetime.now(timezone.utc)
    if _utc(row.expires_at) <= _utc(current_time):
        return None
    if not hmac.compare_digest(str(row.token_hash), token_hash):
        return None
    user = await db.get(User, row.user_id)
    if not _authorized_admin(user, settings_obj):
        return None
    if row.auth_method not in ("google_telegram", "webauthn"):
        return None
    return AdminPwaActor(
        user_id=int(user.id), telegram_id=int(user.telegram_id), auth_method=row.auth_method
    )


async def revoke_admin_pwa_session(
    db: Any, cookie: str, *, now: datetime | None = None,
) -> bool:
    """Idempotent cookie-only logout. Do not require admin access to log out.

    Caller must separately require HTTPS canonical origin and CSRF on POST.
    """
    if not isinstance(cookie, str) or not _COOKIE_PATTERN.fullmatch(cookie):
        return False
    from sqlalchemy import update
    current = _utc(now or datetime.now(timezone.utc))
    digest = hashlib.sha256(cookie.encode("ascii")).hexdigest()
    async with db.begin():
        outcome = await db.execute(update(AdminPwaSession).where(
            AdminPwaSession.token_hash == digest,
            AdminPwaSession.revoked_at.is_(None),
        ).values(revoked_at=current).execution_options(
            synchronize_session=False,
        ))
        return outcome.rowcount == 1
