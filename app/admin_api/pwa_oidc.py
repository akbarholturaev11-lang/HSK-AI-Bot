"""Admin PWA browser-bound Google OIDC state (NOT an HTTP or login route).

The transport must set the generated browser proof in a fresh Secure HttpOnly
__Host- cookie with SameSite=Lax and Path=/, enforce exact HTTPS Origin and CSRF
on start, and only pass that cookie back on Google's same-site redirect.
It must never put the proof in HTML, JSON, a URL, or browser storage.
No token/session is issued here. An approved Telegram Bot callback, identity
linking and session issuer remain separate, explicitly gated work.
"""
import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import select, update

from app.admin_api.pwa_approval import PendingPwaApproval, start_pwa_approval, _utc
from app.db.models.admin_pwa_oauth import AdminPwaOAuthAttempt
from app.services.desktop_auth_service import DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from app.services import google_auth

_TTL = timedelta(minutes=10)
_STATE_PATTERN = re.compile(r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.([0-9a-f]{43})$")
_BROWSER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,192}$")


class AdminPwaOidcError(RuntimeError):
    pass


@dataclass(frozen=True)
class StartedAdminPwaGoogle:
    authorize_url: str
    browser_proof: str  # Never return this value to browser JS.
    expires_at: datetime


def _require_configuration(settings_obj: Any) -> str:
    if not bool(getattr(settings_obj, "ADMIN_PWA_ENABLED", False)):
        raise AdminPwaOidcError("disabled")
    origin = str(getattr(settings_obj, "ADMIN_PWA_PUBLIC_ORIGIN", "") or "")
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.netloc != parsed.hostname
            or parsed.path or parsed.query or parsed.fragment):
        raise AdminPwaOidcError("invalid_origin")
    if not google_auth.is_configured(settings_obj, platform="macos"):
        raise AdminPwaOidcError("google_unconfigured")
    # A missing signing secret must fail closed, as with existing native OIDC.
    DesktopAuthService(None, settings_obj)._signing_secret()
    return origin


def _derive(settings_obj: Any, purpose: str, request_id: str) -> str:
    return DesktopAuthService(None, settings_obj)._hash("admin-pwa-" + purpose, request_id)


def _state(settings_obj: Any, request_id: str) -> str:
    return f"{request_id}.{_derive(settings_obj, 'oidc-state', request_id)[:43]}"


def _nonce(settings_obj: Any, request_id: str) -> str:
    return _derive(settings_obj, "oidc-nonce", request_id)


def _verifier(settings_obj: Any, request_id: str) -> str:
    return _derive(settings_obj, "oidc-pkce", request_id)


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def start_admin_pwa_google(db: Any, *, settings_obj: Any,
                                 now: datetime | None = None) -> StartedAdminPwaGoogle:
    """Call exclusively from rate-limited same-origin POST; session owns commit."""
    origin = _require_configuration(settings_obj)
    timestamp = _utc(now or datetime.now(timezone.utc))
    request_id = str(uuid4())
    proof = secrets.token_urlsafe(48)
    url = google_auth.authorize_url(
        settings_obj=settings_obj,
        redirect_uri=origin + "/api/admin/v1/auth/google/callback",
        state=_state(settings_obj, request_id),
        nonce=_nonce(settings_obj, request_id),
        code_challenge=_challenge(_verifier(settings_obj, request_id)),
    )
    db.add(AdminPwaOAuthAttempt(
        id=request_id,
        browser_proof_hash=hashlib.sha256(proof.encode("ascii")).hexdigest(),
        status="pending", created_at=timestamp, expires_at=timestamp + _TTL,
    ))
    await db.commit()
    return StartedAdminPwaGoogle(url, proof, timestamp + _TTL)


async def finish_admin_pwa_google(db: Any, *, settings_obj: Any,
                                  state: str, code: str, browser_proof: str,
                                  now: datetime | None = None) -> PendingPwaApproval | None:
    """Verified Google ID -> one new pending Telegram approval, exactly once.

    Call from a dedicated provider callback with a fresh database session. The
    HTTP handler must set the *returned* pending approval proof only in its
    own Secure HttpOnly cookie. Never expose raw Google subject or session.
    """
    origin = _require_configuration(settings_obj)
    if not isinstance(state, str) or len(state) > 120:
        return None
    match = _STATE_PATTERN.fullmatch(state)
    if not match or not isinstance(browser_proof, str) or not _BROWSER_PATTERN.fullmatch(browser_proof):
        return None
    request_id, received_mac = match.groups()
    if not hmac.compare_digest(received_mac, _derive(settings_obj, "oidc-state", request_id)[:43]):
        return None
    if not isinstance(code, str) or not code or len(code) > 2048:
        return None
    timestamp = _utc(now or datetime.now(timezone.utc))
    digest = hashlib.sha256(browser_proof.encode("ascii")).hexdigest()
    row = (await db.execute(select(AdminPwaOAuthAttempt).where(
        AdminPwaOAuthAttempt.id == request_id
    ))).scalar_one_or_none()
    if (row is None or row.status != "pending" or _utc(row.expires_at) <= timestamp
            or not hmac.compare_digest(row.browser_proof_hash, digest)):
        return None
    # No database transaction is held during Google's network exchange.
    await db.rollback()
    id_token = await google_auth.exchange_code(
        code, settings_obj=settings_obj,
        redirect_uri=origin + "/api/admin/v1/auth/google/callback",
        code_verifier=_verifier(settings_obj, request_id),
    )
    verified = await google_auth.verify_desktop_id_token(
        id_token, settings_obj=settings_obj, nonce=_nonce(settings_obj, request_id)
    )
    if (verified.provider != "google" or not verified.subject
            or verified.audience != google_auth.desktop_client_id(settings_obj)):
        return None
    # CAS ensures one callback wins. start_pwa_approval() commits BOTH writes
    # together in this session. Roll back if creating the approval fails.
    updated = await db.execute(update(AdminPwaOAuthAttempt).where(
        AdminPwaOAuthAttempt.id == request_id,
        AdminPwaOAuthAttempt.status == "pending",
        AdminPwaOAuthAttempt.browser_proof_hash == digest,
        AdminPwaOAuthAttempt.expires_at > timestamp,
    ).values(status="consumed", consumed_at=timestamp)
    .execution_options(synchronize_session=False))
    if updated.rowcount != 1:
        await db.rollback()
        return None
    try:
        return await start_pwa_approval(
            db,
            verified_google_subject_hash=IdentityLinkService(db, settings_obj).subject_hash(
                "google", verified.subject),
            verified_google_audience=verified.audience, now=timestamp,
        )
    except Exception:
        await db.rollback()
        raise
