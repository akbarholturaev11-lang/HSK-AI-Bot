"""One-time canonical Google account linking after verified OIDC + Telegram approval.

The existing Google callback has already verified issuer, signature, nonce,
state, PKCE and exact audience before persisting a keyed subject hash in the
DB approval. We deliberately never reconstruct or store the raw Google sub.

Only the trusted browser endpoint may invoke this operation, using a short-
lived Secure HttpOnly browser proof, with a fresh DB session. This module
NEVER issues an admin cookie, a WebAuthn credential or any API privilege.
"""
import hashlib
import hmac
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.admin_api.pwa_approval import (
    ApprovedPwaEnrollment, _PROOF, _SHA256, _allowed, _utc,
)
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services import google_auth
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService

_REQUEST_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class _ApprovalRace(RuntimeError):
    """The identity link must roll back along with failed proof consumption."""


async def _link_oidc_verified_google_hash(
    db: Any, *, user: User, subject_hash: str, audience: str,
    timestamp: datetime,
) -> None:
    """Internal-only: use a *server-created* OIDC approval inside its locked txn.

    NEVER expose this helper as HTTP API or accept subject_hash supplied by
    a browser/Bot client. It does not support arbitrary account linking.
    """
    existing = (await db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == "google",
            UserIdentity.subject_hash == subject_hash,
        ).with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if existing is not None:
        if int(existing.user_id) != int(user.id):
            raise IdentityLinkError("oauth_identity_bound_to_other_user", status_code=409)
        existing.last_login_at = timestamp
        await db.flush()
        return

    another = (await db.execute(select(UserIdentity).where(
        UserIdentity.user_id == int(user.id),
        UserIdentity.provider == "google",
    ).with_for_update())).scalar_one_or_none()
    if another is not None:
        raise IdentityLinkError("oauth_identity_already_linked", status_code=409)

    # Keep metadata absent instead of fabricating an email/name from hash.
    # DB unique constraints enforce global subject and per-user/provider
    # uniqueness across this service and native/desktop OAuth linking.
    db.add(UserIdentity(
        id=str(uuid4()), user_id=int(user.id), provider="google",
        subject_hash=subject_hash, audience=audience,
        email_hash=None, email_display=None, email_verified=False,
        display_name=None, created_at=timestamp, last_login_at=timestamp,
    ))
    await db.flush()


async def finalize_google_admin_enrollment(
    db: Any,
    *,
    request_id: str,
    browser_proof: str,
    settings_obj: Any,
    now: datetime | None = None,
) -> ApprovedPwaEnrollment | None:
    """Consume the already-verified identity proof and approved Bot challenge.

    Accepts NO client-supplied provider claims, email, Google subject, user_id,
    or Telegram ID. All identity and role fields are read and locked from the
    server-created approval and canonical User rows.

    Returns a linked user record, never an authenticated browser session.
    """
    if not bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False)):
        return None
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        return None
    if not isinstance(browser_proof, str) or not _PROOF.fullmatch(browser_proof):
        return None

    expected_audience = google_auth.desktop_client_id(settings_obj)
    if not expected_audience:
        return None

    timestamp = _utc(now or datetime.now(timezone.utc))
    digest = hashlib.sha256(browser_proof.encode("ascii")).hexdigest()
    try:
        # Both identity changes and approval consumption commit/rollback as
        # one transaction. The caller must provide a fresh AsyncSession.
        async with db.begin():
            record = (await db.execute(
                select(AdminPwaApproval)
                .where(AdminPwaApproval.id == request_id)
                .with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if (record is None or record.status != "approved"
                    or _utc(record.expires_at) <= timestamp
                    or not isinstance(record.browser_proof_hash, str)
                    or not hmac.compare_digest(record.browser_proof_hash, digest)
                    or not isinstance(record.google_subject_hash, str)
                    or not _SHA256.fullmatch(record.google_subject_hash)
                    or record.google_audience != expected_audience):
                return None

            user = (await db.execute(
                select(User).where(User.id == record.approved_user_id)
                .with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if (user is None or user.telegram_id is None
                    or int(user.telegram_id) != record.approved_telegram_id
                    or not _allowed(user.telegram_id, settings_obj)):
                return None
            IdentityLinkService._require_not_blocked(user)

            await _link_oidc_verified_google_hash(
                db, user=user, subject_hash=record.google_subject_hash,
                audience=record.google_audience, timestamp=timestamp,
            )
            result = await db.execute(
                update(AdminPwaApproval).where(
                    AdminPwaApproval.id == request_id,
                    AdminPwaApproval.status == "approved",
                    AdminPwaApproval.browser_proof_hash == digest,
                    AdminPwaApproval.expires_at > timestamp,
                ).values(status="consumed", consumed_at=timestamp)
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise _ApprovalRace()

            return ApprovedPwaEnrollment(
                user_id=int(user.id),
                telegram_id=int(user.telegram_id),
                google_subject_hash=record.google_subject_hash,
                google_audience=record.google_audience,
            )
    except (IdentityLinkError, IntegrityError, _ApprovalRace):
        # Transaction context rolls back the identity insert/update on failure.
        return None
