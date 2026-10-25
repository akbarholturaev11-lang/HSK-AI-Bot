"""One-time browser-bound Admin PWA approval; never issues a session.

Start may be called only after the server has verified a Google ID token
(signature, issuer, audience, nonce, OAuth state and PKCE). The Telegram ID in
approve MUST originate in an authenticated Bot update, never browser input.
The caller must still link the Google identity and verify it matches users.id
before issuing any secure browser session. No route calls this module yet.
"""
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update

from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROOF = re.compile(r"^[A-Za-z0-9_-]{40,192}$")
_TTL = timedelta(minutes=5)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _allowed(telegram_id: int, settings_obj: Any) -> bool:
    try:
        return int(telegram_id) > 0 and int(telegram_id) in getattr(settings_obj, "admin_id_list", ())
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class PendingPwaApproval:
    request_id: str
    browser_proof: str  # Only a short-lived Secure HttpOnly browser cookie.
    expires_at: datetime


@dataclass(frozen=True)
class ApprovedPwaEnrollment:
    user_id: int
    telegram_id: int
    google_subject_hash: str
    google_audience: str


async def start_pwa_approval(db, *, verified_google_subject_hash: str,
                             verified_google_audience: str,
                             now: datetime | None = None) -> PendingPwaApproval:
    """Called only by a trusted OIDC callback, never by an anonymous request."""
    if not _SHA256.fullmatch(str(verified_google_subject_hash or "")):
        raise ValueError("unverified_google_subject_hash")
    if (not isinstance(verified_google_audience, str) or
            not verified_google_audience.strip() or len(verified_google_audience) > 190):
        raise ValueError("invalid_google_audience")
    timestamp = _utc(now or datetime.now(timezone.utc))
    secret = secrets.token_urlsafe(48)
    record = AdminPwaApproval(
        id=str(uuid4()),
        browser_proof_hash=hashlib.sha256(secret.encode("ascii")).hexdigest(),
        google_subject_hash=verified_google_subject_hash,
        google_audience=verified_google_audience,
        status="pending",
        created_at=timestamp,
        expires_at=timestamp + _TTL,
    )
    db.add(record)
    await db.commit()
    return PendingPwaApproval(record.id, secret, record.expires_at)


async def approve_pwa_approval(db, *, request_id: str,
                               verified_bot_telegram_id: int,
                               settings_obj: Any,
                               now: datetime | None = None) -> bool:
    """Atomic approval from verified Telegram Bot update only."""
    if not _allowed(verified_bot_telegram_id, settings_obj):
        return False
    timestamp = _utc(now or datetime.now(timezone.utc))
    user = (await db.execute(select(User).where(
        User.telegram_id == verified_bot_telegram_id
    ))).scalar_one_or_none()
    if user is None or user.status == "blocked":
        return False
    record = (await db.execute(select(AdminPwaApproval).where(
        AdminPwaApproval.id == request_id
    ))).scalar_one_or_none()
    if record is None or record.status != "pending" or _utc(record.expires_at) <= timestamp:
        return False
    existing = (await db.execute(select(UserIdentity.user_id).where(
        UserIdentity.provider == "google",
        UserIdentity.subject_hash == record.google_subject_hash,
    ))).scalar_one_or_none()
    if existing is not None and int(existing) != int(user.id):
        return False
    result = await db.execute(
        update(AdminPwaApproval).where(
            AdminPwaApproval.id == request_id,
            AdminPwaApproval.status == "pending",
            AdminPwaApproval.expires_at > timestamp,
        ).values(
            status="approved",
            approved_user_id=user.id,
            approved_telegram_id=verified_bot_telegram_id,
            approved_at=timestamp,
        ).execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount == 1


async def consume_pwa_approval(db, *, request_id: str, browser_proof: str,
                               settings_obj: Any,
                               now: datetime | None = None) -> ApprovedPwaEnrollment | None:
    """Atomic, browser-bound one-time consumption. NOT a login credential.

    A separate trusted callback must bind the verified provider to this same
    canonical account via IdentityLinkService before minting a browser session.
    """
    if not isinstance(browser_proof, str) or not _PROOF.fullmatch(browser_proof):
        return None
    timestamp = _utc(now or datetime.now(timezone.utc))
    digest = hashlib.sha256(browser_proof.encode("ascii")).hexdigest()
    record = (await db.execute(select(AdminPwaApproval).where(
        AdminPwaApproval.id == request_id
    ))).scalar_one_or_none()
    if record is None or record.status != "approved" or _utc(record.expires_at) <= timestamp:
        return None
    if not hmac.compare_digest(record.browser_proof_hash, digest):
        return None
    user = await db.get(User, record.approved_user_id)
    if (user is None or user.status == "blocked"
            or user.telegram_id != record.approved_telegram_id
            or not _allowed(record.approved_telegram_id, settings_obj)):
        return None
    existing = (await db.execute(select(UserIdentity.user_id).where(
        UserIdentity.provider == "google",
        UserIdentity.subject_hash == record.google_subject_hash,
    ))).scalar_one_or_none()
    if existing is not None and int(existing) != int(user.id):
        return None
    result = await db.execute(
        update(AdminPwaApproval).where(
            AdminPwaApproval.id == request_id,
            AdminPwaApproval.status == "approved",
            AdminPwaApproval.browser_proof_hash == digest,
            AdminPwaApproval.expires_at > timestamp,
        ).values(
            status="consumed", consumed_at=timestamp,
        ).execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return None
    await db.commit()
    return ApprovedPwaEnrollment(
        int(user.id), int(user.telegram_id),
        record.google_subject_hash, record.google_audience
    )
