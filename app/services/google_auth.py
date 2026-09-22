"""Google Sign-In verification and authorization-code exchange.

Two entry points, deliberately kept apart:

* ``verify_android_id_token`` — the Android Credential Manager returns an ID
  token minted for the *Web* client ID. No browser, no code exchange.
* ``exchange_code`` + ``verify_desktop_id_token`` — the desktop clients use the
  system browser with PKCE, and the server exchanges the code.

Each path passes only its own audience. A union would let a token minted for
the Android client be replayed at the desktop endpoint and vice versa.

The ``access_token`` and ``refresh_token`` returned by the token endpoint are
discarded immediately: we authenticate the person, we never call a Google API
on their behalf, so holding those would be pure liability.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from app.services.oidc_verifier import (
    JwksCache,
    OidcVerificationError,
    VerifiedIdentity,
    verify_id_token,
)


PROVIDER = "google"
# Hard-coded: never derived from a token, never configurable.
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTHORIZE_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_ISSUERS = frozenset(
    {"https://accounts.google.com", "accounts.google.com"}
)
# We authenticate a person; we do not want API access.
GOOGLE_SCOPE = "openid email profile"
TOKEN_RESPONSE_MAX_BYTES = 32 * 1024


def android_client_id(settings_obj: Any) -> str:
    return str(
        getattr(settings_obj, "GOOGLE_ANDROID_WEB_CLIENT_ID", "") or ""
    ).strip()


def desktop_client_id(settings_obj: Any) -> str:
    return str(getattr(settings_obj, "GOOGLE_DESKTOP_CLIENT_ID", "") or "").strip()


def desktop_client_secret(settings_obj: Any) -> str:
    return str(
        getattr(settings_obj, "GOOGLE_DESKTOP_CLIENT_SECRET", "") or ""
    ).strip()


def is_configured(settings_obj: Any, *, platform: str | None = None) -> bool:
    """Whether Google sign-in can be offered at all.

    Fail-closed: an unset client id means the provider is hidden from the
    client's provider list rather than shown as a button that errors.
    """

    if not bool(getattr(settings_obj, "GOOGLE_OAUTH_ENABLED", False)):
        return False
    if platform == "android":
        return bool(android_client_id(settings_obj))
    if platform in {"macos", "windows"}:
        return bool(desktop_client_id(settings_obj) and desktop_client_secret(settings_obj))
    return bool(
        android_client_id(settings_obj)
        or (desktop_client_id(settings_obj) and desktop_client_secret(settings_obj))
    )


async def verify_android_id_token(
    id_token: str,
    *,
    settings_obj: Any,
    nonce: str,
    max_age_seconds: int = 300,
    cache: JwksCache | None = None,
) -> VerifiedIdentity:
    client_id = android_client_id(settings_obj)
    if not client_id:
        raise OidcVerificationError("oidc_provider_unconfigured")
    return await verify_id_token(
        id_token,
        provider=PROVIDER,
        jwks_uri=GOOGLE_JWKS_URI,
        issuers=GOOGLE_ISSUERS,
        audiences=[client_id],
        nonce=nonce,
        max_age_seconds=max_age_seconds,
        cache=cache,
    )


async def verify_desktop_id_token(
    id_token: str,
    *,
    settings_obj: Any,
    nonce: str,
    max_age_seconds: int = 300,
    cache: JwksCache | None = None,
) -> VerifiedIdentity:
    client_id = desktop_client_id(settings_obj)
    if not client_id:
        raise OidcVerificationError("oidc_provider_unconfigured")
    return await verify_id_token(
        id_token,
        provider=PROVIDER,
        jwks_uri=GOOGLE_JWKS_URI,
        issuers=GOOGLE_ISSUERS,
        audiences=[client_id],
        nonce=nonce,
        max_age_seconds=max_age_seconds,
        cache=cache,
    )


def authorize_url(
    *,
    settings_obj: Any,
    redirect_uri: str,
    state: str,
    nonce: str,
    code_challenge: str,
) -> str:
    from urllib.parse import urlencode

    client_id = desktop_client_id(settings_obj)
    if not client_id:
        raise OidcVerificationError("oidc_provider_unconfigured")
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_SCOPE,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            # No offline access: we never want a refresh token for Google APIs.
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTHORIZE_URI}?{query}"


async def exchange_code(
    code: str,
    *,
    settings_obj: Any,
    redirect_uri: str,
    code_verifier: str,
    timeout_seconds: float = 8.0,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    """Exchange an authorization code for an ID token. Returns the ID token only."""

    client_id = desktop_client_id(settings_obj)
    client_secret = desktop_client_secret(settings_obj)
    if not client_id or not client_secret:
        raise OidcVerificationError("oidc_provider_unconfigured")
    if not code or len(code) > 2048:
        raise OidcVerificationError("oauth_exchange_failed")

    form = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    timeout = max(1.0, float(timeout_seconds))
    try:
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                follow_redirects=False,
                transport=http_transport,
            ) as client:
                async with client.stream(
                    "POST",
                    GOOGLE_TOKEN_URI,
                    data=form,
                    headers={"Accept": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        raise OidcVerificationError("oauth_exchange_failed")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > TOKEN_RESPONSE_MAX_BYTES:
                            raise OidcVerificationError("oauth_exchange_failed")
    except OidcVerificationError:
        raise
    except Exception as exc:
        # Never surface the provider's message: it can echo our request back.
        raise OidcVerificationError("oauth_exchange_failed") from exc

    try:
        payload = json.loads(bytes(body).decode("utf-8"))
        id_token = payload["id_token"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise OidcVerificationError("oauth_exchange_failed") from exc
    if not isinstance(id_token, str) or not id_token:
        raise OidcVerificationError("oauth_exchange_failed")
    # `access_token` / `refresh_token` are intentionally dropped here.
    return id_token
