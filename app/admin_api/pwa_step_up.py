"""Exact-operation WebAuthn step-up for FUTURE standalone Admin PWA mutations.

This module authorizes nothing by itself. A future dedicated PWA mutation must
validate the actual request against its own schema and then call
consume_step_up_in_mutation() inside the SAME DB transaction as its writes.
Legacy Telegram Admin Mini App routes MUST NOT be switched to this auth path.
"""
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from webauthn import (
    generate_authentication_options, options_to_json,
    verify_authentication_response,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor, UserVerificationRequirement,
)

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_sessions import _authorized_admin, _COOKIE_PATTERN
from app.admin_api.pwa_webauthn_login import _decode_b64
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.user import User

_ORIGIN = "https://hskai.app"
_RP_ID = "hskai.app"
_ACTIONS = frozenset({"payments.review", "users.delete", "broadcast.send", "users.grant_access",
                      "course.access_policy", "hsk30.settings", "subscription.prices",
                      "settings.update", "marketing.update", "users.block", "channels.update", "portfolio.add", "notifications.update", "partners.update"})
_TARGET = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_CHALLENGE_TTL = timedelta(minutes=2)
_RECEIPT_TTL = timedelta(seconds=60)
_WINDOW = timedelta(minutes=10)
_MAX_PER_SESSION = 10
_MAX_PAYLOAD_BYTES = 4096
_MAX_ASSERTION_BYTES = 16384


@dataclass(frozen=True)
class StepUpOptions:
    step_up_id: str        # Non-secret row ID; never a bearer authorization
    options: dict[str, Any]
    expires_at: datetime


def _enabled(settings_obj: Any) -> bool:
    return (
        bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False))
        and getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", None) == _ORIGIN
    )


def operation_digest(*, action: str, target: str, payload: Any) -> str | None:
    """Deterministic commitment to the EXACT operation the server will apply.

    The receiving mutation route MUST hash the fully schema-validated,
    canonical payload it will actually execute (not untrusted client hash).
    """
    if (not isinstance(action, str) or action not in _ACTIONS
            or not isinstance(target, str) or not _TARGET.fullmatch(target)
            or not isinstance(payload, dict) or not payload
            or not all(isinstance(key, str) for key in payload)):
        return None
    try:
        encoded = json.dumps(
            {"version": 1, "action": action, "target": target, "payload": payload},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError):
        return None
    if len(encoded) > _MAX_PAYLOAD_BYTES:
        return None
    return hashlib.sha256(encoded).hexdigest()


def _session_digest(cookie: str) -> str:
    return hashlib.sha256(cookie.encode("ascii")).hexdigest()


async def _locked_session(db: Any, cookie: str, settings_obj: Any, stamp: datetime):
    if not isinstance(cookie, str) or not _COOKIE_PATTERN.fullmatch(cookie):
        return None
    row = (await db.execute(select(AdminPwaSession).where(
        AdminPwaSession.token_hash == _session_digest(cookie),
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if (row is None or row.revoked_at is not None or _utc(row.expires_at) <= stamp
            or row.auth_method != "webauthn"):
        return None
    user = (await db.execute(select(User).where(
        User.id == row.user_id,
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if not _authorized_admin(user, settings_obj):
        return None
    return row, user


async def begin_step_up(
    db: Any, *, session_cookie: str, action: str, target: str, payload: Any,
    settings_obj: Any, now: datetime | None = None,
) -> StepUpOptions | None:
    digest = operation_digest(action=action, target=target, payload=payload)
    if not _enabled(settings_obj) or digest is None:
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None:
            return None
        session, user = pair
        count = (await db.execute(select(func.count()).select_from(AdminPwaStepUp).where(
            AdminPwaStepUp.session_id == session.id,
            AdminPwaStepUp.created_at >= stamp - _WINDOW,
        ))).scalar_one()
        if count >= _MAX_PER_SESSION:
            return None
        credentials = (await db.execute(select(AdminPwaCredential).where(
            AdminPwaCredential.user_id == user.id,
            AdminPwaCredential.revoked_at.is_(None),
        ))).scalars().all()
        if not credentials:
            return None
        challenge = secrets.token_bytes(32)
        expiry = min(_utc(session.expires_at), stamp + _CHALLENGE_TTL)
        if expiry <= stamp:
            return None
        options = generate_authentication_options(
            rp_id=_RP_ID,
            challenge=challenge,
            timeout=max(1000, int((expiry - stamp).total_seconds() * 1000)),
            user_verification=UserVerificationRequirement.REQUIRED,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=bytes(cred.credential_id))
                for cred in credentials
            ],
        )
        step_id = str(uuid4())
        db.add(AdminPwaStepUp(
            id=step_id, session_id=session.id, user_id=int(user.id),
            action=action, target=target, payload_hash=digest,
            challenge=challenge, status="pending", created_at=stamp, expires_at=expiry,
        ))
        await db.flush()
    return StepUpOptions(
        step_up_id=step_id,
        options=json.loads(options_to_json(options)),
        expires_at=expiry,
    )


async def verify_step_up(
    db: Any, *, session_cookie: str, step_up_id: str, credential: Any,
    settings_obj: Any, now: datetime | None = None,
) -> bool:
    if (not _enabled(settings_obj) or not isinstance(step_up_id, str)
            or not _UUID.fullmatch(step_up_id) or not isinstance(credential, dict)):
        return False
    try:
        size = len(json.dumps(credential, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
    except (TypeError, ValueError, RecursionError):
        return False
    if size > _MAX_ASSERTION_BYTES:
        return False
    raw_id = _decode_b64(credential.get("rawId"), max_bytes=1024)
    if raw_id is None:
        return False
    stamp = _utc(now or datetime.now(timezone.utc))
    try:
        async with db.begin():
            step = (await db.execute(select(AdminPwaStepUp).where(
                AdminPwaStepUp.id == step_up_id,
            ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if (step is None or step.status != "pending" or step.verified_at is not None
                    or step.consumed_at is not None or _utc(step.expires_at) <= stamp):
                return False
            # Acquire the credential lock BEFORE the User lock, as in the
            # existing passkey sign-in flow. Reverse order would risk a PG
            # deadlock on concurrent login and step-up for the same actor.
            stored = (await db.execute(select(AdminPwaCredential).where(
                AdminPwaCredential.credential_id == raw_id,
                AdminPwaCredential.user_id == step.user_id,
                AdminPwaCredential.revoked_at.is_(None),
            ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if stored is None:
                return False
            pair = await _locked_session(db, session_cookie, settings_obj, stamp)
            if pair is None:
                return False
            session, user = pair
            if step.session_id != session.id or int(step.user_id) != int(user.id):
                return False
            stamp = _utc(now or datetime.now(timezone.utc))
            if _utc(step.expires_at) <= stamp or _utc(session.expires_at) <= stamp:
                return False
            response = credential.get("response")
            if not isinstance(response, dict):
                return False
            from_handle = response.get("userHandle")
            if from_handle is not None:
                handle = _decode_b64(from_handle, max_bytes=32)
                if handle is None or not hmac.compare_digest(handle, bytes(stored.user_handle)):
                    return False
            try:
                verified = verify_authentication_response(
                    credential=credential,
                    expected_challenge=bytes(step.challenge),
                    expected_rp_id=_RP_ID,
                    expected_origin=_ORIGIN,
                    credential_public_key=bytes(stored.public_key),
                    credential_current_sign_count=int(stored.sign_count),
                    require_user_verification=True,
                )
            except (InvalidAuthenticationResponse, ValueError, TypeError):
                return False
            if bytes(verified.credential_id) != raw_id or not bool(verified.user_verified):
                return False
            old_count = int(stored.sign_count)
            new_count = int(verified.new_sign_count)
            if new_count < 0 or ((new_count > 0 or old_count > 0) and new_count <= old_count):
                return False
            device_type = str(getattr(
                verified.credential_device_type, "value", verified.credential_device_type,
            ))
            if device_type not in ("single_device", "multi_device"):
                return False
            updated = await db.execute(update(AdminPwaStepUp).where(
                AdminPwaStepUp.id == step.id,
                AdminPwaStepUp.status == "pending",
                AdminPwaStepUp.verified_at.is_(None),
                AdminPwaStepUp.expires_at > stamp,
            ).values(
                status="verified", verified_at=stamp, credential_id=raw_id,
                expires_at=min(_utc(session.expires_at), stamp + _RECEIPT_TTL),
            ).execution_options(synchronize_session=False))
            if updated.rowcount != 1:
                return False
            stored.sign_count = new_count
            stored.device_type = device_type
            stored.backed_up = bool(verified.credential_backed_up)
            await db.flush()
        return True
    except IntegrityError:
        return False


async def consume_step_up_in_mutation(
    db: Any, *, session_cookie: str, step_up_id: str, action: str,
    target: str, payload: Any, settings_obj: Any,
    now: datetime | None = None,
) -> bool:
    """Consume proof INSIDE an enclosing mutation transaction (no auto-commit).

    The route must call this on the same AsyncSession/transaction as the
    actual payment/delete/broadcast write. Rollbacks MUST undo consumption.
    A caller cannot use this function to directly invoke legacy mutations.
    """
    digest = operation_digest(action=action, target=target, payload=payload)
    if (not _enabled(settings_obj) or digest is None or not isinstance(step_up_id, str)
            or not _UUID.fullmatch(step_up_id) or not db.in_transaction()):
        return False
    stamp = _utc(now or datetime.now(timezone.utc))
    step = (await db.execute(select(AdminPwaStepUp).where(
        AdminPwaStepUp.id == step_up_id,
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if (step is None or step.status != "verified"
            or step.verified_at is None or step.consumed_at is not None
            or _utc(step.expires_at) <= stamp
            or step.action != action or step.target != target
            or not hmac.compare_digest(step.payload_hash, digest)):
        return False
    # Recheck credential ownership/revocation at the EXACT write boundary.
    # Acquire credential before User, consistent with passkey login/verify
    # lock order to avoid reciprocal credential-vs-user PostgreSQL deadlocks.
    if not step.credential_id:
        return False
    credential = (await db.execute(select(AdminPwaCredential).where(
        AdminPwaCredential.credential_id == bytes(step.credential_id),
        AdminPwaCredential.user_id == step.user_id,
        AdminPwaCredential.revoked_at.is_(None),
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if credential is None:
        return False
    pair = await _locked_session(db, session_cookie, settings_obj, stamp)
    if pair is None:
        return False
    session, user = pair
    if step.session_id != session.id or int(step.user_id) != int(user.id):
        return False
    # Row-lock waits can outlive the receipt/session. Authorize at the actual
    # write boundary, not at the time before waiting for another transaction.
    stamp = _utc(now or datetime.now(timezone.utc))
    if _utc(step.expires_at) <= stamp or _utc(session.expires_at) <= stamp:
        return False
    updated = await db.execute(update(AdminPwaStepUp).where(
        AdminPwaStepUp.id == step.id,
        AdminPwaStepUp.status == "verified",
        AdminPwaStepUp.consumed_at.is_(None),
        AdminPwaStepUp.expires_at > stamp,
        AdminPwaStepUp.payload_hash == digest,
    ).values(status="consumed", consumed_at=stamp).execution_options(
        synchronize_session=False,
    ))
    return updated.rowcount == 1
