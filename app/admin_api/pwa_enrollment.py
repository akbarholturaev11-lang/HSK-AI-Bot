"""Atomically link a Google identity after one-time Telegram Admin PWA approval.

Not an HTTP endpoint and not a session issuer. Only a trusted OIDC callback
which has verified signature, issuer, audience, state, nonce and PKCE may call
this function with VerifiedIdentity. Use a *fresh* session (no open transaction).
The browser proof must come from its short-lived Secure HttpOnly cookie.
"""

import hashlib
import hmac
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.admin_api.pwa_approval import ApprovedPwaEnrollment, _PROOF, _allowed, _utc
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.user import User
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService
from app.services.oidc_verifier import VerifiedIdentity

_REQUEST_ID = re.compile(r"^[0-9a-fA-F-]{36}$")


class _ApprovalRace(RuntimeError):
    """Rolled back with the identity link; nothing may be partially committed."""


async def finalize_google_admin_enrollment(
    db: Any,
    *,
    request_id: str,
    browser_proof: str,
    verified_identity: VerifiedIdentity,
    settings_obj: Any,
    now: datetime | None = None,
) -> ApprovedPwaEnrollment | None:
    """Link the already-verified Google sub and consume approval together.

    Returns None without writing when proof, authorization or binding fails.
    Caller must independently check the feature flag, HTTPS origin and CSRF,
    and still perform separately reviewed session issuance and passkey setup.
    """
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        return None
    if not isinstance(browser_proof, str) or not _PROOF.fullmatch(browser_proof):
        return None
    if (verified_identity is None
            or verified_identity.provider != "google"
            or not isinstance(verified_identity.subject, str)
            or not verified_identity.subject
            or not isinstance(verified_identity.audience, str)
            or not verified_identity.audience):
        return None

    timestamp = _utc(now or datetime.now(timezone.utc))
    digest = hashlib.sha256(browser_proof.encode("ascii")).hexdigest()
    service = IdentityLinkService(db, settings_obj)
    # Uses the same server-side keyed hash as native Google identity linking.
    expected_subject_hash = service.subject_hash("google", verified_identity.subject)

    try:
        # This owns the transaction; on all failures, link and consume roll back.
        async with db.begin():
            record = (await db.execute(
                select(AdminPwaApproval)
                .where(AdminPwaApproval.id == request_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if (record is None or record.status != "approved"
                    or _utc(record.expires_at) <= timestamp
                    or not hmac.compare_digest(record.browser_proof_hash, digest)
                    or not hmac.compare_digest(record.google_subject_hash, expected_subject_hash)
                    or record.google_audience != verified_identity.audience):
                return None

            user = (await db.execute(
                select(User).where(User.id == record.approved_user_id)
                .with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if (user is None or str(user.status).strip().lower() == "blocked"
                    or user.telegram_id is None
                    or int(user.telegram_id) != record.approved_telegram_id
                    or not _allowed(user.telegram_id, settings_obj)):
                return None

            # Creates only the missing provider identity, rejects collisions,
            # never reassigns an existing Google subject from another account.
            await service.link_to_user(verified_identity, user_id=int(user.id))
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
            outcome = ApprovedPwaEnrollment(
                user_id=int(user.id),
                telegram_id=int(user.telegram_id),
                google_subject_hash=expected_subject_hash,
                google_audience=verified_identity.audience,
            )
        return outcome
    except (IdentityLinkError, IntegrityError, _ApprovalRace):
        # The transaction context rolls back every partial write, including
        # an inserted identity and changes to the approval row.
        return None
