"""Google / Apple sign-in and linking for the native clients.

This service only decides *who* a verified provider token belongs to and marks
the shared ``desktop_link_requests`` row accordingly. It never mints a token:
a sign-in row is finished by the existing, unchanged ``link/status`` endpoint,
so every bearer route in the app keeps working with no changes and there stays
exactly one token-minting path in the codebase.

``state``, ``nonce`` and the PKCE ``code_verifier`` are DERIVED from the link
request id with the server signing secret, never stored. That keeps the schema
free of three more secret columns and makes ``state`` self-authenticating: split
it, do one indexed primary-key lookup, then compare the MAC in constant time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from app.db.models.desktop import DesktopLinkRequest
from app.db.models.user import User
from app.services import apple_auth, google_auth
from app.services.desktop_auth_service import (
    LINK_INTENT,
    SIGNIN_INTENT,
    DesktopAuthError,
    DesktopAuthService,
)
from app.services.identity_link_service import IdentityLinkError, IdentityLinkService
from app.services.oidc_verifier import OidcVerificationError, VerifiedIdentity


logger = logging.getLogger(__name__)

PROVIDERS = ("google", "apple")
NATIVE_ID_TOKEN_MODE = "native_id_token"
BROWSER_REDIRECT_MODE = "browser_redirect"
MODES = (NATIVE_ID_TOKEN_MODE, BROWSER_REDIRECT_MODE)
# Terminal status for an intent="link" row. Deliberately not "approved":
# nothing downstream should ever mistake it for something poll_link may
# exchange for a session.
LINKED_STATUS = "linked"
FAILED_STATUS = "failed"
STATE_MAC_CHARS = 43


class NativeOAuthError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class OAuthStart:
    link_request_id: str
    polling_secret: str
    expires_in: int
    nonce: str
    authorize_url: str | None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def redirect_base_url(settings_obj: Any) -> str:
    """The https origin provider redirects come back to, or "" when unusable."""

    raw = str(getattr(settings_obj, "OAUTH_REDIRECT_BASE_URL", "") or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    # Both Google and Apple refuse non-https redirect URIs, and a base carrying
    # a path or query would silently produce a URI we never registered.
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return ""
    return f"https://{parsed.netloc}"


def available_providers(settings_obj: Any, *, platform: str | None = None) -> list[str]:
    providers = []
    if google_auth.is_configured(settings_obj, platform=platform):
        providers.append("google")
    if apple_auth.is_configured(settings_obj):
        providers.append("apple")
    return providers


class NativeOAuthService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self.auth = DesktopAuthService(session, settings_obj)
        self.identities = IdentityLinkService(session, settings_obj)

    # --- derived per-request secrets -------------------------------------
    def _derive(self, purpose: str, link_request_id: str) -> str:
        return self.auth._hash(purpose, link_request_id)

    def code_verifier(self, link_request_id: str) -> str:
        # 64 hex chars: inside PKCE's 43..128 unreserved-character range.
        return self._derive("oauth-pkce", link_request_id)

    @staticmethod
    def code_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def nonce(self, link_request_id: str) -> str:
        return self._derive("oauth-nonce", link_request_id)

    def state(self, link_request_id: str) -> str:
        mac = self._derive("oauth-state", link_request_id)[:STATE_MAC_CHARS]
        return f"{link_request_id}.{mac}"

    def link_request_id_from_state(self, state: str) -> str:
        raw = str(state or "")
        if not raw or len(raw) > 256 or raw.count(".") != 1:
            raise NativeOAuthError("oauth_state_invalid", status_code=400)
        link_request_id, _, mac = raw.partition(".")
        expected = self._derive("oauth-state", link_request_id)[:STATE_MAC_CHARS]
        if not hmac.compare_digest(mac, expected):
            raise NativeOAuthError("oauth_state_invalid", status_code=400)
        return link_request_id

    def redirect_uri(self, provider: str) -> str:
        base = redirect_base_url(self.settings)
        if not base:
            raise NativeOAuthError("oauth_provider_unconfigured", status_code=503)
        return f"{base}/api/v3/native-auth/oauth/callback/{provider}"

    # --- start ------------------------------------------------------------
    async def start(
        self,
        *,
        provider: str,
        mode: str,
        platform: str,
        app_version: str,
        installation_key: str,
        intent: str = SIGNIN_INTENT,
        bind_user_id: int | None = None,
    ) -> OAuthStart:
        if provider not in PROVIDERS:
            raise NativeOAuthError("oauth_provider_unsupported", status_code=422)
        if mode not in MODES:
            raise NativeOAuthError("oauth_mode_unsupported", status_code=422)
        # Credential Manager is Android-only and Google-only. Accepting it
        # anywhere else would accept an audience the caller cannot prove.
        if mode == NATIVE_ID_TOKEN_MODE and (
            provider != "google" or platform != "android"
        ):
            raise NativeOAuthError("oauth_mode_unsupported", status_code=422)
        if provider not in available_providers(self.settings, platform=platform):
            raise NativeOAuthError("oauth_provider_unconfigured", status_code=503)

        # Reuses the existing admission path, so the advisory-lock
        # serialisation and both rate limits apply unchanged.
        started = await self.auth.start_link(
            platform=platform,
            app_version=app_version,
            installation_key=installation_key,
            flow=provider,
            intent=intent,
            bind_user_id=bind_user_id,
        )
        link_request_id = started["link_request_id"]
        nonce = self.nonce(link_request_id)

        authorize_url = None
        if mode == BROWSER_REDIRECT_MODE:
            redirect_uri = self.redirect_uri(provider)
            challenge = self.code_challenge(self.code_verifier(link_request_id))
            state = self.state(link_request_id)
            builder = (
                google_auth.authorize_url
                if provider == "google"
                else apple_auth.authorize_url
            )
            authorize_url = builder(
                settings_obj=self.settings,
                redirect_uri=redirect_uri,
                state=state,
                nonce=nonce,
                code_challenge=challenge,
            )

        return OAuthStart(
            link_request_id=link_request_id,
            polling_secret=started["polling_secret"],
            expires_in=int(started["expires_in"]),
            nonce=nonce,
            authorize_url=authorize_url,
        )

    # --- row lookup and terminal states ----------------------------------
    async def _row(self, link_request_id: str, *, lock: bool = True):
        query = select(DesktopLinkRequest).where(
            DesktopLinkRequest.id == str(link_request_id or "")
        )
        if lock:
            query = query.with_for_update()
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NativeOAuthError("oauth_state_invalid", status_code=400)
        # Symmetric to the bot-side guard: an OAuth callback must never be able
        # to approve a Telegram confirmation row.
        if str(row.flow or "telegram") not in PROVIDERS:
            raise NativeOAuthError("oauth_state_invalid", status_code=400)
        if row.status != "pending" or row.consumed_at is not None:
            raise NativeOAuthError("desktop_link_consumed", status_code=409)
        expires_at = row.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= _utcnow():
                row.status = "expired"
                await self.session.commit()
                raise NativeOAuthError("desktop_link_expired", status_code=410)
        return row

    async def _fail(self, row, code: str) -> None:
        """Burn the row on any failure.

        Single-shot verification is what makes brute-forcing an ID token cost a
        whole link request, which the start rate limits already cap. No extra
        attempt counter is needed.
        """

        row.status = FAILED_STATUS
        row.link_failure_code = code[:48]
        await self.session.commit()

    async def _finish(self, row, verified: VerifiedIdentity) -> dict[str, Any]:
        if row.intent == LINK_INTENT:
            user_id = int(row.bind_user_id or 0)
            if not user_id:
                await self._fail(row, "oauth_state_invalid")
                raise NativeOAuthError("oauth_state_invalid", status_code=400)
            await self.identities.link_to_user(verified, user_id=user_id)
            row.status = LINKED_STATUS
            row.approved_user_id = user_id
            row.approved_at = _utcnow()
            await self.session.commit()
            return {"ok": True, "status": LINKED_STATUS, "provider": verified.provider}

        user_id = await self.identities.resolve_signin(
            verified, installation_key_hash=row.installation_key_hash
        )
        user = await self.session.get(User, user_id)
        if user is None:
            await self._fail(row, "oauth_telegram_account_required")
            raise NativeOAuthError(
                "oauth_telegram_account_required", status_code=409
            )
        row.status = "approved"
        row.approved_user_id = user_id
        row.approved_telegram_id = user.telegram_id
        row.approved_at = _utcnow()
        await self.session.commit()
        return {"ok": True, "status": "approved", "provider": verified.provider}

    async def _verify_or_fail(self, row, coroutine):
        try:
            return await coroutine
        except (OidcVerificationError, IdentityLinkError, DesktopAuthError) as exc:
            code = getattr(exc, "code", "oauth_token_invalid")
            await self._fail(row, code)
            status_code = getattr(exc, "status_code", None) or 401
            raise NativeOAuthError(code, status_code=status_code) from exc

    # --- Android: Credential Manager ID token ----------------------------
    async def assert_id_token(
        self,
        *,
        link_request_id: str,
        polling_secret: str,
        provider: str,
        id_token: str,
    ) -> dict[str, Any]:
        row = await self._row(link_request_id)
        if not hmac.compare_digest(
            str(row.polling_secret_hash or ""),
            self.auth._hash("polling", polling_secret),
        ):
            raise NativeOAuthError("oauth_state_invalid", status_code=401)
        if provider != row.flow or provider != "google":
            raise NativeOAuthError("oauth_provider_unsupported", status_code=422)

        verified = await self._verify_or_fail(
            row,
            google_auth.verify_android_id_token(
                id_token,
                settings_obj=self.settings,
                nonce=self.nonce(row.id),
                max_age_seconds=int(
                    getattr(self.settings, "OAUTH_ID_TOKEN_MAX_AGE_SECONDS", 300)
                ),
            ),
        )
        return await self._verify_or_fail(row, self._finish(row, verified))

    # --- Desktop / Apple: browser redirect -------------------------------
    async def complete_callback(
        self,
        *,
        provider: str,
        state: str,
        code: str,
        apple_user: str | None = None,
    ) -> dict[str, Any]:
        if provider not in PROVIDERS:
            raise NativeOAuthError("oauth_provider_unsupported", status_code=422)
        row = await self._row(self.link_request_id_from_state(state))
        if row.flow != provider:
            raise NativeOAuthError("oauth_state_invalid", status_code=400)

        redirect_uri = self.redirect_uri(provider)
        verifier = self.code_verifier(row.id)
        if provider == "google":
            id_token = await self._verify_or_fail(
                row,
                google_auth.exchange_code(
                    code,
                    settings_obj=self.settings,
                    redirect_uri=redirect_uri,
                    code_verifier=verifier,
                    timeout_seconds=float(
                        getattr(self.settings, "OAUTH_HTTP_TIMEOUT_SECONDS", 8.0)
                    ),
                ),
            )
            verified = await self._verify_or_fail(
                row,
                google_auth.verify_desktop_id_token(
                    id_token,
                    settings_obj=self.settings,
                    nonce=self.nonce(row.id),
                    max_age_seconds=int(
                        getattr(self.settings, "OAUTH_ID_TOKEN_MAX_AGE_SECONDS", 300)
                    ),
                ),
            )
        else:
            id_token = await self._verify_or_fail(
                row,
                apple_auth.exchange_code(
                    code,
                    settings_obj=self.settings,
                    redirect_uri=redirect_uri,
                    code_verifier=verifier,
                    timeout_seconds=float(
                        getattr(self.settings, "OAUTH_HTTP_TIMEOUT_SECONDS", 8.0)
                    ),
                ),
            )
            verified = await self._verify_or_fail(
                row,
                apple_auth.verify_id_token_for_service(
                    id_token,
                    settings_obj=self.settings,
                    nonce=self.nonce(row.id),
                    max_age_seconds=int(
                        getattr(self.settings, "OAUTH_ID_TOKEN_MAX_AGE_SECONDS", 300)
                    ),
                ),
            )
            # Apple sends the display name only with the first authorization.
            verified = apple_auth.merge_first_authorization_name(verified, apple_user)

        return await self._verify_or_fail(row, self._finish(row, verified))

    # --- link-intent polling (never returns tokens) ----------------------
    async def link_status(
        self,
        *,
        link_request_id: str,
        polling_secret: str,
        user_id: int,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            select(DesktopLinkRequest).where(
                DesktopLinkRequest.id == str(link_request_id or "")
            )
        )
        row = result.scalar_one_or_none()
        if (
            row is None
            or row.intent != LINK_INTENT
            or int(row.bind_user_id or 0) != int(user_id)
            or not hmac.compare_digest(
                str(row.polling_secret_hash or ""),
                self.auth._hash("polling", polling_secret),
            )
        ):
            raise NativeOAuthError("oauth_state_invalid", status_code=401)
        if row.status == LINKED_STATUS:
            return {"ok": True, "status": LINKED_STATUS, "provider": row.flow}
        if row.status == FAILED_STATUS:
            return {
                "ok": True,
                "status": FAILED_STATUS,
                "provider": row.flow,
                "error": row.link_failure_code or "oauth_link_failed",
            }
        expires_at = row.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= _utcnow():
                return {"ok": True, "status": "expired", "provider": row.flow}
        return {"ok": True, "status": "pending", "provider": row.flow}
