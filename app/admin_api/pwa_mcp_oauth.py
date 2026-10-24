"""Unexposed pre-registered public-client MCP OAuth code + PKCE S256 ceremony.

NOT AN OAUTH SERVER: No HTTP routes, consent UI, OAuth metadata, client-ID
metadata resolution, refresh token or MCP transport are mounted here.
Public client ID and HTTPS redirect MUST be reviewed and configured server
side, never inferred from browser input. Do not accept arbitrary URLs or
fetch remote client metadata. Server persists only code/access-token hashes.
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

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.admin_api.pwa_approval import _utc
from app.admin_api.pwa_sessions import _authorized_admin
from app.admin_api.pwa_step_up import _locked_session
from app.admin_api.pwa_mcp_resource import _ready, _REQUIRED_RESOURCE, _ANALYTICS_SCOPE
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_mcp import AdminPwaMcpAccessGrant
from app.db.models.admin_pwa_mcp_authorization import AdminPwaMcpAuthorization
from app.db.models.user import User

_VERIFIER = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
_CHALLENGE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_STATE = re.compile(r"^[A-Za-z0-9._~-]{16,256}$")
_CODE = re.compile(r"^[A-Za-z0-9_-]{40,192}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_PENDING_TTL = timedelta(minutes=3)
_CODE_TTL = timedelta(seconds=60)
_TOKEN_TTL = timedelta(minutes=5)
_WINDOW = timedelta(minutes=10)
_MAX_ATTEMPTS = 10


@dataclass(frozen=True)
class PendingMcpConsent:
    request_id: str
    client_id: str
    redirect_uri: str
    resource: str
    scope: str
    state: str
    expires_at: datetime
    # One-time secret returned ONLY to a trusted first-party consent page.
    csrf_proof: str = ""


@dataclass(frozen=True)
class ApprovedMcpCode:
    code: str                  # Redirect to EXACT registered client only.
    redirect_uri: str
    state: str                 # OAuth client-owned; NOT an auth secret.
    expires_at: datetime


@dataclass(frozen=True)
class McpAccessToken:
    token: str                 # Returned ONLY by future HTTPS OAuth token endpoint.
    token_type: str
    expires_in: int
    scope: str


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def pkce_s256(verifier: str) -> str | None:
    if not isinstance(verifier, str) or not _VERIFIER.fullmatch(verifier):
        return None
    return base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")


def _registered_client(settings_obj: Any, client_id: Any, redirect_uri: Any,
                       resource: Any, scope: Any) -> bool:
    """Pre-registration ONLY. No SSRF fetching and no unapproved redirects."""
    if not _ready(settings_obj):
        return False
    configured_id = getattr(settings_obj, "ADMIN_PWA_MCP_CLIENT_ID", "")
    configured_redirect = getattr(settings_obj, "ADMIN_PWA_MCP_REDIRECT_URI", "")
    if (not isinstance(client_id, str) or not isinstance(configured_id, str)
            or not 3 <= len(configured_id) <= 128 or client_id != configured_id
            or not isinstance(redirect_uri, str)
            or not isinstance(configured_redirect, str)
            or len(configured_redirect) > 512 or redirect_uri != configured_redirect
            or resource != _REQUIRED_RESOURCE or scope != _ANALYTICS_SCOPE):
        return False
    try:
        parsed = urlsplit(redirect_uri)
    except ValueError:
        return False
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.fragment or not parsed.netloc or parsed.hostname.endswith(".")):
        return False
    return True


async def begin_mcp_authorization(
    db: Any, *, session_cookie: str, client_id: str, redirect_uri: str,
    resource: str, scope: str, state: str, code_challenge: str,
    code_challenge_method: str, settings_obj: Any, now: datetime | None = None,
    csrf_proof: str | None = None,
) -> PendingMcpConsent | None:
    """Start pending browser consent. NEVER redirects/consents automatically."""
    if (not _registered_client(settings_obj, client_id, redirect_uri, resource, scope)
            or code_challenge_method != "S256" or not isinstance(code_challenge, str)
            or not _CHALLENGE.fullmatch(code_challenge)
            or not isinstance(state, str) or not _STATE.fullmatch(state)
            or (csrf_proof is not None and
                (not isinstance(csrf_proof, str) or not _CODE.fullmatch(csrf_proof)))):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None:
            return None
        session, user = pair
        count = (await db.execute(select(func.count()).select_from(
            AdminPwaMcpAuthorization).where(
            AdminPwaMcpAuthorization.session_id == session.id,
            AdminPwaMcpAuthorization.created_at >= stamp - _WINDOW,
        ))).scalar_one()
        if count >= _MAX_ATTEMPTS:
            return None
        expires_at = min(_utc(session.expires_at), stamp + _PENDING_TTL)
        if expires_at <= stamp:
            return None
        identifier = str(uuid4())
        db.add(AdminPwaMcpAuthorization(
            id=identifier, user_id=int(user.id), session_id=session.id,
            client_id=client_id, redirect_uri=redirect_uri,
            resource=resource, scope=scope, pkce_challenge=code_challenge,
            client_state=state, status="pending", created_at=stamp,
            expires_at=expires_at,
            consent_csrf_hash=_digest(csrf_proof) if csrf_proof else None,
        ))
        await db.flush()
    return PendingMcpConsent(identifier, client_id, redirect_uri, resource,
                             scope, state, expires_at, csrf_proof or "")


async def decide_mcp_consent(
    db: Any, *, request_id: str, session_cookie: str, approved: bool,
    settings_obj: Any, now: datetime | None = None,
    csrf_proof: str | None = None,
) -> ApprovedMcpCode | None:
    """Require an explicit yes/no click from SAME HTTPS/CSRF-checked browser.

    Caller MUST enforce origin, Fetch Metadata, content-type and a separate
    CSRF nonce bound to the consent view. This service has NO public router.
    """
    if (not _ready(settings_obj) or not isinstance(request_id, str)
            or not _UUID.fullmatch(request_id) or type(approved) is not bool):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    async with db.begin():
        row = (await db.execute(select(AdminPwaMcpAuthorization).where(
            AdminPwaMcpAuthorization.id == request_id,
        ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if (row is None or row.status != "pending" or _utc(row.expires_at) <= stamp
                or not _registered_client(settings_obj, row.client_id, row.redirect_uri,
                                          row.resource, row.scope)):
            return None
        # Require exact double-bound one-time CSRF for any consent created
        # through the HTTPS browser route. Never accept client OAuth state
        # as a CSRF proof (it is public to the requesting client).
        if row.consent_csrf_hash is not None:
            if (not isinstance(csrf_proof, str) or not _CODE.fullmatch(csrf_proof)
                    or not hmac.compare_digest(row.consent_csrf_hash, _digest(csrf_proof))):
                return None
        pair = await _locked_session(db, session_cookie, settings_obj, stamp)
        if pair is None:
            return None
        session, user = pair
        if row.session_id != session.id or int(row.user_id) != int(user.id):
            return None
        if not approved:
            row.status = "denied"
            await db.flush()
            return None
        code = secrets.token_urlsafe(48)
        expires_at = min(_utc(session.expires_at), stamp + _CODE_TTL)
        if expires_at <= stamp:
            return None
        row.code_hash = _digest(code)
        row.status = "approved"
        row.approved_at = stamp
        row.expires_at = expires_at
        redirect = row.redirect_uri
        client_state = row.client_state
        await db.flush()
    return ApprovedMcpCode(code, redirect, client_state, expires_at)


async def exchange_mcp_code(
    db: Any, *, code: str, code_verifier: str, client_id: str,
    redirect_uri: str, resource: str, settings_obj: Any,
    now: datetime | None = None,
) -> McpAccessToken | None:
    """Public-client PKCE S256 exchange; one DB atomic redemption.

    Token delivery needs HTTPS application/x-www-form-urlencoded transport,
    explicit no-store headers, OAuth error contracts and no sensitive logs;
    it is NOT exposed by this module. No refresh tokens are issued.
    """
    expected_challenge = pkce_s256(code_verifier)
    if (not isinstance(code, str) or not _CODE.fullmatch(code)
            or expected_challenge is None
            or not _registered_client(settings_obj, client_id, redirect_uri,
                                      resource, _ANALYTICS_SCOPE)):
        return None
    stamp = _utc(now or datetime.now(timezone.utc))
    digest = _digest(code)
    try:
        async with db.begin():
            row = (await db.execute(select(AdminPwaMcpAuthorization).where(
                AdminPwaMcpAuthorization.code_hash == digest,
            ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
            if (row is None or row.status != "approved" or row.redeemed_at is not None
                    or row.approved_at is None or _utc(row.expires_at) <= stamp
                    or not hmac.compare_digest(str(row.code_hash), digest)
                    or not hmac.compare_digest(row.pkce_challenge, expected_challenge)
                    or row.client_id != client_id or row.redirect_uri != redirect_uri
                    or row.resource != resource or row.scope != _ANALYTICS_SCOPE):
                return None
            sess = (await db.execute(select(AdminPwaSession).where(
                AdminPwaSession.id == row.session_id,
            ).with_for_update())).scalar_one_or_none()
            if (sess is None or int(sess.user_id) != int(row.user_id)
                    or sess.revoked_at is not None or _utc(sess.expires_at) <= stamp
                    or sess.auth_method != "webauthn"):
                return None
            user = (await db.execute(select(User).where(
                User.id == row.user_id,
            ).with_for_update())).scalar_one_or_none()
            if not _authorized_admin(user, settings_obj):
                return None
            token = secrets.token_urlsafe(48)
            db.add(AdminPwaMcpAccessGrant(
                id=str(uuid4()), user_id=int(user.id),
                token_hash=_digest(token), audience=_REQUIRED_RESOURCE,
                client_id=client_id, consent_event_id=row.id,
                scope=_ANALYTICS_SCOPE, created_at=stamp,
                expires_at=stamp + _TOKEN_TTL,
            ))
            row.status = "redeemed"
            row.redeemed_at = stamp
            await db.flush()
        return McpAccessToken(token, "Bearer", int(_TOKEN_TTL.total_seconds()),
                              _ANALYTICS_SCOPE)
    except IntegrityError:
        return None
