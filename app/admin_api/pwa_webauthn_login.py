"""Anonymous discoverable-passkey sign-in with one-time browser-bound challenge.

Only py_webauthn cryptographic assertion verification can create a DB-backed
Admin PWA session. The challenge cookie, credential id, userHandle and
Telegram/Google enrollment cookies are never accepted as login credentials.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from webauthn import (
    generate_authentication_options,
    options_to_json,
    verify_authentication_response,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse
from webauthn.helpers.structs import UserVerificationRequirement

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_sessions import _authorized_admin
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_authentication import AdminPwaAuthenticationChallenge
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.user import User

_RP_ID = "hskai.app"
_ORIGIN = "https://hskai.app"
_CHALLENGE_TTL = timedelta(minutes=2)
_SESSION_TTL = timedelta(hours=8)
_MAX_STARTS = 60
_START_WINDOW = timedelta(minutes=10)
_PG_ADMISSION_LOCK = 661792047
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{40,192}$")
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]{1,1400}$")
_MAX_ASSERTION_JSON = 16384


@dataclass(frozen=True)
class LoginChallenge:
    options: dict[str, Any]  # public WebAuthn challenge only
    browser_proof: str        # Secure HttpOnly cookie ONLY
    expires_at: datetime


@dataclass(frozen=True)
class VerifiedPasskeyLogin:
    token: str               # Secure HttpOnly session cookie ONLY
    expires_at: datetime


class PasskeyLoginRateLimited(RuntimeError):
    pass


def _enabled(settings_obj: Any) -> bool:
    return (bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False))
            and getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", None) == _ORIGIN)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _decode_b64(value: Any, *, max_bytes: int) -> bytes | None:
    if not isinstance(value, str) or not _BASE64URL.fullmatch(value):
        return None
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error):
        return None
    if (not 1 <= len(raw) <= max_bytes or
            base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value):
        return None
    return raw


async def begin_passkey_login(
    db: Any, *, settings_obj: Any, now: datetime | None = None,
) -> LoginChallenge | None:
    """Uniform, account-agnostic challenge to avoid enumerating admins."""
    if not _enabled(settings_obj):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        if db.get_bind().dialect.name == "postgresql":
            await db.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": _PG_ADMISSION_LOCK},
            )
        starts = (await db.execute(
            select(func.count()).select_from(AdminPwaAuthenticationChallenge)
            .where(AdminPwaAuthenticationChallenge.created_at >= stamp - _START_WINDOW)
        )).scalar_one()
        if starts >= _MAX_STARTS:
            raise PasskeyLoginRateLimited()
        challenge = secrets.token_bytes(32)
        proof = secrets.token_urlsafe(48)
        expiry = stamp + _CHALLENGE_TTL
        # Discoverable credentials: no usernames, user_ids, or allowlist
        # exposed to anonymous callers. User verification REQUIRED.
        options = generate_authentication_options(
            rp_id=_RP_ID, challenge=challenge,
            timeout=int(_CHALLENGE_TTL.total_seconds() * 1000),
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        db.add(AdminPwaAuthenticationChallenge(
            id=str(uuid4()), challenge=challenge,
            browser_proof_hash=_digest(proof), status="pending",
            created_at=stamp, expires_at=expiry,
        ))
        await db.flush()
    return LoginChallenge(
        options=json.loads(options_to_json(options)),
        browser_proof=proof, expires_at=expiry,
    )


async def complete_passkey_login(
    db: Any, *, browser_proof: str, credential: Any,
    settings_obj: Any, now: datetime | None = None,
) -> VerifiedPasskeyLogin | None:
    """Verify a discoverable public-key assertion and atomically issue session.

    The credential ID is ONLY a lookup key. Account ownership is established
    solely by verifying an assertion signed with the stored key for that ID
    against the server's one-time challenge and exact origin/RP/UV.
    """
    if not _enabled(settings_obj):
        return None
    if not isinstance(browser_proof, str) or not _TOKEN.fullmatch(browser_proof):
        return None
    if not isinstance(credential, dict):
        return None
    try:
        if len(json.dumps(credential, separators=(",", ":"), ensure_ascii=True)) > _MAX_ASSERTION_JSON:
            return None
    except (TypeError, ValueError):
        return None
    raw_id = _decode_b64(credential.get("rawId"), max_bytes=1024)
    if raw_id is None:
        return None
    response = credential.get("response")
    if not isinstance(response, dict):
        return None
    user_handle = _decode_b64(response.get("userHandle"), max_bytes=32)
    if user_handle is None or len(user_handle) != 32:
        # Admin PWA uses discoverable passkeys; the returned opaque handle
        # must equal the registered user's handle.
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    proof_digest = _digest(browser_proof)
    try:
        async with db.begin():
            challenge = (await db.execute(
                select(AdminPwaAuthenticationChallenge).where(
                    AdminPwaAuthenticationChallenge.browser_proof_hash == proof_digest,
                ).with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if (challenge is None or challenge.status != "pending"
                    or challenge.consumed_at is not None
                    or _utc(challenge.expires_at) <= stamp
                    or not hmac.compare_digest(challenge.browser_proof_hash, proof_digest)):
                return None
            stored = (await db.execute(select(AdminPwaCredential).where(
                AdminPwaCredential.credential_id == raw_id,
                AdminPwaCredential.revoked_at.is_(None),
            ).with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if stored is None or not hmac.compare_digest(bytes(stored.user_handle), user_handle):
                return None
            user = (await db.execute(select(User).where(User.id == stored.user_id)
                                     .with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if not _authorized_admin(user, settings_obj):
                return None
            try:
                verification = verify_authentication_response(
                    credential=credential,
                    expected_challenge=bytes(challenge.challenge),
                    expected_rp_id=_RP_ID,
                    expected_origin=_ORIGIN,
                    credential_public_key=bytes(stored.public_key),
                    credential_current_sign_count=int(stored.sign_count),
                    require_user_verification=True,
                )
            except (InvalidAuthenticationResponse, ValueError, TypeError):
                return None
            if (bytes(verification.credential_id) != raw_id
                    or not bool(verification.user_verified)):
                return None
            new_count = int(verification.new_sign_count)
            old_count = int(stored.sign_count)
            # Zero counters are normal for synced passkeys. Nonzero counters
            # MUST increase to reject cloned/replayed authenticator state.
            if new_count < 0 or ((old_count > 0 or new_count > 0) and new_count <= old_count):
                return None
            dev_type = str(getattr(verification.credential_device_type, "value",
                                   verification.credential_device_type))
            if dev_type not in ("single_device", "multi_device"):
                return None
            updated = await db.execute(update(AdminPwaAuthenticationChallenge).where(
                AdminPwaAuthenticationChallenge.id == challenge.id,
                AdminPwaAuthenticationChallenge.status == "pending",
                AdminPwaAuthenticationChallenge.consumed_at.is_(None),
                AdminPwaAuthenticationChallenge.expires_at > stamp,
            ).values(status="consumed", consumed_at=stamp).execution_options(
                synchronize_session=False,
            ))
            if updated.rowcount != 1:
                return None
            stored.sign_count = new_count
            stored.device_type = dev_type
            stored.backed_up = bool(verification.credential_backed_up)
            token = secrets.token_urlsafe(48)
            expiry = stamp + _SESSION_TTL
            db.add(AdminPwaSession(
                id=str(uuid4()), user_id=int(user.id),
                token_hash=_digest(token), auth_method="webauthn",
                created_at=stamp, expires_at=expiry,
            ))
            await db.flush()
        return VerifiedPasskeyLogin(token=token, expires_at=expiry)
    except IntegrityError:
        # Duplicate session token (extremely unlikely) or concurrent
        # challenge consumption: entire authentication transaction rolls back.
        return None
