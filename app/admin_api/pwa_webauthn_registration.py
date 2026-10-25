"""DB-bound WebAuthn passkey registration for the HSK AI Admin PWA.

The external py_webauthn verifier checks challenge, RP ID hash, origin,
attestation and the user-verification (UV) flag. Never treat a client-returned
credential_id, signature, or claimed user as verified without that call.

Registration consumes the previously verified Google+Telegram enrollment grant
in the SAME transaction that inserts the credential. This module NEVER mints a
browser admin session, accepts an API token, or implements passkey sign-in.
"""
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from webauthn import (
    generate_registration_options, options_to_json,
    verify_registration_response,
)
from webauthn.helpers.exceptions import InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AttestationConveyancePreference, AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor, ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_enrollment_grants import (
    _TOKEN, _digest, verify_passkey_enrollment_grant,
)
from app.db.models.admin_pwa_enrollment_grant import AdminPwaEnrollmentGrant
from app.db.models.admin_pwa_webauthn import (
    AdminPwaCredential, AdminPwaRegistrationChallenge,
)

_RP_ID = "hskai.app"
_ORIGIN = "https://hskai.app"
_MAX_CREDENTIAL_JSON = 16384
_CHALLENGE_TTL = timedelta(minutes=2)


class WebAuthnEnrollmentError(RuntimeError):
    """Expected invalid or expired registration (fail closed)."""


@dataclass(frozen=True)
class PasskeyRegistrationOptions:
    options: dict[str, Any]
    expires_at: datetime


def _enabled(settings_obj: Any) -> bool:
    return (bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False))
            and getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", None) == _ORIGIN)


def _registration_token_shape(token: str, proof: str) -> bool:
    from app.admin_api.pwa_approval import _PROOF
    return (isinstance(token, str) and _TOKEN.fullmatch(token) is not None
            and isinstance(proof, str) and _PROOF.fullmatch(proof) is not None)


async def begin_passkey_registration(
    db: Any, *, token: str, browser_proof: str, settings_obj: Any,
    now: datetime | None = None,
) -> PasskeyRegistrationOptions | None:
    if not _enabled(settings_obj) or not _registration_token_shape(token, browser_proof):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        # Lock grant to prevent simultaneous registration ceremonies across
        # processes and replicas from reusing the same one-time enrollment.
        grant = (await db.execute(select(AdminPwaEnrollmentGrant).where(
            AdminPwaEnrollmentGrant.token_hash == _digest(token),
        ).with_for_update())).scalar_one_or_none()
        if grant is None:
            return None
        actor = await verify_passkey_enrollment_grant(
            db, token=token, browser_proof=browser_proof,
            settings_obj=settings_obj, now=stamp,
        )
        if actor is None or actor.grant_id != grant.id:
            return None
        prior = (await db.execute(select(AdminPwaRegistrationChallenge).where(
            AdminPwaRegistrationChallenge.grant_id == grant.id,
        ))).scalar_one_or_none()
        if prior is not None:
            return None

        existing = (await db.execute(select(AdminPwaCredential).where(
            AdminPwaCredential.user_id == actor.user_id,
            AdminPwaCredential.revoked_at.is_(None),
        ).order_by(AdminPwaCredential.created_at))).scalars().all()
        # For a returning user, use the existing WebAuthn user handle, not
        # a new per-credential handle. No Telegram ID/email is embedded.
        handle = existing[0].user_handle if existing else secrets.token_bytes(32)
        challenge = secrets.token_bytes(32)
        expiry = min(_utc(grant.expires_at), stamp + _CHALLENGE_TTL)
        if expiry <= stamp:
            return None
        options = generate_registration_options(
            rp_id=_RP_ID,
            rp_name="HSK AI Admin",
            user_name=f"admin-{actor.user_id}",
            user_display_name="HSK AI Admin",
            user_id=bytes(handle),
            challenge=challenge,
            timeout=max(1000, int((expiry - stamp).total_seconds() * 1000)),
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=bytes(credential.credential_id))
                for credential in existing
            ],
        )
        # Browser sees public challenge/options only; the server retains the
        # exact bytes for verification after navigator.credentials.create().
        db.add(AdminPwaRegistrationChallenge(
            id=str(uuid4()), grant_id=grant.id,
            challenge=challenge, user_handle=bytes(handle),
            created_at=stamp, expires_at=expiry,
        ))
        await db.flush()
        return PasskeyRegistrationOptions(
            options=json.loads(options_to_json(options)),
            expires_at=expiry,
        )


async def complete_passkey_registration(
    db: Any, *, token: str, browser_proof: str, credential: Any,
    settings_obj: Any, now: datetime | None = None,
) -> bool:
    """Commit only after cryptographic attestation and CURRENT admin recheck.

    Invalid credentials never create a row or consume the enrollment grant.
    The caller must supply a new SQLAlchemy AsyncSession with no open txn.
    """
    if not _enabled(settings_obj) or not _registration_token_shape(token, browser_proof):
        return False
    if not isinstance(credential, dict):
        return False
    try:
        serialized = json.dumps(credential, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError):
        return False
    if len(serialized.encode("utf-8")) > _MAX_CREDENTIAL_JSON:
        return False
    stamp = _utc(now or datetime.now(timezone.utc))
    try:
        async with db.begin():
            grant = (await db.execute(select(AdminPwaEnrollmentGrant).where(
                AdminPwaEnrollmentGrant.token_hash == _digest(token),
            ).with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if grant is None:
                return False
            actor = await verify_passkey_enrollment_grant(
                db, token=token, browser_proof=browser_proof,
                settings_obj=settings_obj, now=stamp,
            )
            if actor is None or actor.grant_id != grant.id:
                return False
            row = (await db.execute(select(AdminPwaRegistrationChallenge).where(
                AdminPwaRegistrationChallenge.grant_id == grant.id,
            ).with_for_update().execution_options(populate_existing=True)
            )).scalar_one_or_none()
            if (row is None or row.consumed_at is not None
                    or _utc(row.expires_at) <= stamp):
                return False
            # The published py_webauthn verifier checks the browser origin,
            # SHA-256 RP ID hash, challenge, authenticator and UV flags.
            try:
                verified = verify_registration_response(
                    credential=credential,
                    expected_challenge=bytes(row.challenge),
                    expected_rp_id=_RP_ID,
                    expected_origin=_ORIGIN,
                    require_user_verification=True,
                )
            except (InvalidRegistrationResponse, ValueError, TypeError):
                return False
            cred_id = bytes(verified.credential_id)
            public_key = bytes(verified.credential_public_key)
            if not (1 <= len(cred_id) <= 1024 and 1 <= len(public_key) <= 2048):
                return False
            sign_count = int(verified.sign_count)
            if sign_count < 0:
                return False
            dev_type = verified.credential_device_type
            device_type = str(getattr(dev_type, "value", dev_type))
            if device_type not in ("single_device", "multi_device"):
                return False
            details = credential.get("response", {})
            transports = details.get("transports") if isinstance(details, dict) else None
            if not isinstance(transports, list):
                transports = None
            else:
                permitted = {"internal", "hybrid", "usb", "nfc", "ble"}
                transports = sorted(set(x for x in transports if isinstance(x, str) and x in permitted))
            grant_update = await db.execute(update(AdminPwaEnrollmentGrant).where(
                AdminPwaEnrollmentGrant.id == grant.id,
                AdminPwaEnrollmentGrant.status == "pending",
                AdminPwaEnrollmentGrant.consumed_at.is_(None),
                AdminPwaEnrollmentGrant.expires_at > stamp,
            ).values(status="consumed", consumed_at=stamp).execution_options(
                synchronize_session=False,
            ))
            if grant_update.rowcount != 1:
                return False
            row.consumed_at = stamp
            db.add(AdminPwaCredential(
                id=str(uuid4()), user_id=actor.user_id,
                credential_id=cred_id, public_key=public_key,
                user_handle=bytes(row.user_handle),
                sign_count=sign_count, device_type=device_type,
                backed_up=bool(verified.credential_backed_up),
                transports=json.dumps(transports) if transports is not None else None,
                created_at=stamp,
            ))
            await db.flush()
        return True
    except IntegrityError:
        # A credential ID already belongs to an account, or a duplicate
        # ceremony won the race. Roll back grant consumption together with
        # the failed credential insert; do not reassign identities.
        return False
