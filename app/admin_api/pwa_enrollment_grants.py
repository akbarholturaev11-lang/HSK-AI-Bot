"""Admin PWA one-time passkey enrollment grant primitives.

A grant is NOT an admin login session. It is an ephemeral, two-cookie-bound
capability to initiate future *verified* WebAuthn registration, and must never
be accepted by an existing user/admin API. No WebAuthn credential is created
or marked verified in this module.

Issuance MUST happen within the same external transaction that atomically
links the server-verified Google identity and consumes the Telegram approval.
"""
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.admin_api.pwa_approval import _PROOF, _allowed, _utc
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.admin_pwa_enrollment_grant import AdminPwaEnrollmentGrant
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services import google_auth

_GRANT_TTL = timedelta(minutes=3)
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{40,192}$")


@dataclass(frozen=True)
class IssuedPwaEnrollmentGrant:
    token: str  # Must be delivered ONLY by a Secure HttpOnly __Host- cookie.
    expires_at: datetime


@dataclass(frozen=True)
class AuthorizedPwaEnrollment:
    user_id: int
    telegram_id: int
    grant_id: str
    expires_at: datetime


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


async def _issue_enrollment_grant_in_transaction(
    db: Any, *, approval_id: str, user_id: int,
    browser_proof_hash: str, now: datetime,
) -> IssuedPwaEnrollmentGrant:
    """INTERNAL: call only while approval + canonical User are already locked.

    This does not commit. The enclosing transaction must commit the link,
    approval consumption, and grant issuance together; any failure rolls back.
    """
    token = secrets.token_urlsafe(48)
    expiry = _utc(now) + _GRANT_TTL
    db.add(AdminPwaEnrollmentGrant(
        id=str(uuid4()), approval_id=approval_id, user_id=int(user_id),
        token_hash=_digest(token), browser_proof_hash=browser_proof_hash,
        status="pending", created_at=_utc(now), expires_at=expiry,
    ))
    await db.flush()
    return IssuedPwaEnrollmentGrant(token=token, expires_at=expiry)


async def verify_passkey_enrollment_grant(
    db: Any, *, token: str, browser_proof: str,
    settings_obj: Any, now: datetime | None = None,
) -> AuthorizedPwaEnrollment | None:
    """Read-only gate for the FUTURE server-verified WebAuthn registration flow.

    Both independently generated HttpOnly cookie values are required. This
    operation cannot create a credential, mark a grant consumed, or mint a
    session. A successful verification must be repeated under a row lock when
    committing a verified WebAuthn credential in a later implementation.
    """
    if not bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False)):
        return None
    if (not isinstance(token, str) or not _TOKEN.fullmatch(token)
            or not isinstance(browser_proof, str) or not _PROOF.fullmatch(browser_proof)):
        return None
    timestamp = _utc(now or datetime.now(timezone.utc))
    row = (await db.execute(select(AdminPwaEnrollmentGrant).where(
        AdminPwaEnrollmentGrant.token_hash == _digest(token),
    ))).scalar_one_or_none()
    if (row is None or row.status != "pending" or row.consumed_at is not None
            or _utc(row.expires_at) <= timestamp
            or not hmac.compare_digest(row.browser_proof_hash, _digest(browser_proof))):
        return None
    approval = (await db.execute(select(AdminPwaApproval).where(
        AdminPwaApproval.id == row.approval_id,
    ))).scalar_one_or_none()
    if (approval is None or approval.status != "consumed"
            or approval.consumed_at is None
            or int(approval.approved_user_id or 0) != int(row.user_id)
            or not hmac.compare_digest(approval.browser_proof_hash, row.browser_proof_hash)
            or approval.google_audience != google_auth.desktop_client_id(settings_obj)):
        return None
    user = await db.get(User, row.user_id)
    if (user is None or user.telegram_id is None
            or int(user.telegram_id) != int(approval.approved_telegram_id or 0)
            or str(user.status).strip().lower() == "blocked"
            or not _allowed(user.telegram_id, settings_obj)):
        return None
    linked_google = (await db.execute(select(UserIdentity).where(
        UserIdentity.user_id == int(row.user_id),
        UserIdentity.provider == "google",
        UserIdentity.subject_hash == approval.google_subject_hash,
    ))).scalar_one_or_none()
    if linked_google is None:
        return None
    return AuthorizedPwaEnrollment(
        user_id=int(user.id), telegram_id=int(user.telegram_id),
        grant_id=row.id, expires_at=_utc(row.expires_at),
    )
