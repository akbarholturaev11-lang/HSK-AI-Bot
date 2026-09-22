"""Sign in with Apple verification and code exchange.

Apple differs from Google in three ways that shape this module:

* The client secret is not a static string but an **ES256 JWT** we mint from a
  ``.p8`` signing key, valid for at most six months. It is built with
  ``google.auth.crypt.es256`` so the raw ``r||s`` ECDSA encoding is never
  hand-rolled, and cached just under its lifetime.
* When ``scope`` includes ``name``, Apple returns the result as an HTML
  **form POST**, not a redirect with query parameters.
* The user's name arrives **only with the first authorization**, in a separate
  ``user`` form field — never in the ID token, and never again. A later sign-in
  must therefore not overwrite a stored name with nothing.

Private-relay addresses (``…@privaterelay.appleid.com``) are stored as-is and
deliberately not special-cased: an email is display metadata here and never
participates in account resolution.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
from google.auth import jwt as google_jwt
from google.auth.crypt import es256

from app.services.oidc_verifier import (
    JwksCache,
    OidcVerificationError,
    VerifiedIdentity,
    verify_id_token,
)


PROVIDER = "apple"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URI = "https://appleid.apple.com/auth/keys"
APPLE_TOKEN_URI = "https://appleid.apple.com/auth/token"
APPLE_AUTHORIZE_URI = "https://appleid.apple.com/auth/authorize"
APPLE_SCOPE = "name email"
CLIENT_SECRET_TTL_SECONDS = 3000  # just under the 50-minute cache window
CLIENT_SECRET_LIFETIME_SECONDS = 3600
TOKEN_RESPONSE_MAX_BYTES = 32 * 1024

_client_secret_cache: dict[str, tuple[float, str]] = {}


def service_id(settings_obj: Any) -> str:
    return str(getattr(settings_obj, "APPLE_SERVICE_ID", "") or "").strip()


def is_configured(settings_obj: Any) -> bool:
    """Fail-closed: any missing piece hides the provider instead of erroring."""

    if not bool(getattr(settings_obj, "APPLE_OAUTH_ENABLED", False)):
        return False
    return all(
        str(getattr(settings_obj, name, "") or "").strip()
        for name in (
            "APPLE_SERVICE_ID",
            "APPLE_TEAM_ID",
            "APPLE_KEY_ID",
            "APPLE_PRIVATE_KEY",
        )
    )


def client_secret(settings_obj: Any, *, now: float | None = None) -> str:
    """Mint (and cache) the ES256 client-secret JWT Apple requires."""

    if not is_configured(settings_obj):
        raise OidcVerificationError("oidc_provider_unconfigured")
    team_id = str(getattr(settings_obj, "APPLE_TEAM_ID", "")).strip()
    key_id = str(getattr(settings_obj, "APPLE_KEY_ID", "")).strip()
    audience = service_id(settings_obj)
    # Escaped newlines are how a .p8 usually survives an env var.
    private_key = str(
        getattr(settings_obj, "APPLE_PRIVATE_KEY", "")
    ).strip().replace("\\n", "\n")

    moment = float(now if now is not None else time.time())
    cache_key = f"{team_id}:{key_id}:{audience}"
    cached = _client_secret_cache.get(cache_key)
    if cached and moment - cached[0] < CLIENT_SECRET_TTL_SECONDS:
        return cached[1]

    issued_at = int(moment)
    payload = {
        "iss": team_id,
        "iat": issued_at,
        "exp": issued_at + CLIENT_SECRET_LIFETIME_SECONDS,
        "aud": APPLE_ISSUER,
        "sub": audience,
    }
    try:
        signer = es256.ES256Signer.from_string(private_key, key_id)
        token = google_jwt.encode(
            signer, payload, header={"alg": "ES256", "kid": key_id}
        ).decode()
    except Exception as exc:
        # Never echo the key or the library's message: both can contain key
        # material or its structure.
        raise OidcVerificationError("oidc_provider_unconfigured") from exc

    _client_secret_cache[cache_key] = (moment, token)
    return token


def reset_client_secret_cache() -> None:
    _client_secret_cache.clear()


def authorize_url(
    *,
    settings_obj: Any,
    redirect_uri: str,
    state: str,
    nonce: str,
    code_challenge: str,
) -> str:
    from urllib.parse import urlencode

    client_id = service_id(settings_obj)
    if not client_id:
        raise OidcVerificationError("oidc_provider_unconfigured")
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": APPLE_SCOPE,
            # Required by Apple whenever the scope asks for name or email.
            "response_mode": "form_post",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{APPLE_AUTHORIZE_URI}?{query}"


async def verify_id_token_for_service(
    id_token: str,
    *,
    settings_obj: Any,
    nonce: str,
    max_age_seconds: int = 300,
    cache: JwksCache | None = None,
) -> VerifiedIdentity:
    client_id = service_id(settings_obj)
    if not client_id:
        raise OidcVerificationError("oidc_provider_unconfigured")
    return await verify_id_token(
        id_token,
        provider=PROVIDER,
        jwks_uri=APPLE_JWKS_URI,
        issuers=[APPLE_ISSUER],
        audiences=[client_id],
        nonce=nonce,
        max_age_seconds=max_age_seconds,
        cache=cache,
    )


def merge_first_authorization_name(
    verified: VerifiedIdentity,
    apple_user: str | None,
) -> VerifiedIdentity:
    """Fold Apple's first-authorization ``user`` payload into the identity.

    Apple sends the name exactly once, ever. If we drop it here the account
    simply has no display name forever, so this is the only chance to read it —
    but it is untrusted client-supplied JSON, so it is bounded and only used
    when the ID token itself carried no name.
    """

    if verified.display_name or not apple_user:
        return verified
    raw = str(apple_user)
    if len(raw) > 2048:
        return verified
    try:
        payload = json.loads(raw)
        name = payload.get("name") or {}
        parts = [
            str(name.get("firstName") or "").strip(),
            str(name.get("lastName") or "").strip(),
        ]
    except (TypeError, ValueError, AttributeError):
        return verified
    display_name = " ".join(part for part in parts if part).strip()[:120]
    if not display_name:
        return verified
    return VerifiedIdentity(
        provider=verified.provider,
        subject=verified.subject,
        email=verified.email,
        email_verified=verified.email_verified,
        display_name=display_name,
        audience=verified.audience,
    )


async def exchange_code(
    code: str,
    *,
    settings_obj: Any,
    redirect_uri: str,
    code_verifier: str,
    timeout_seconds: float = 8.0,
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    client_id = service_id(settings_obj)
    if not client_id:
        raise OidcVerificationError("oidc_provider_unconfigured")
    if not code or len(code) > 2048:
        raise OidcVerificationError("oauth_exchange_failed")

    form = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret(settings_obj),
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
                    APPLE_TOKEN_URI,
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
        raise OidcVerificationError("oauth_exchange_failed") from exc

    try:
        payload = json.loads(bytes(body).decode("utf-8"))
        id_token = payload["id_token"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise OidcVerificationError("oauth_exchange_failed") from exc
    if not isinstance(id_token, str) or not id_token:
        raise OidcVerificationError("oauth_exchange_failed")
    # Apple's refresh_token is intentionally dropped: we never call Apple APIs.
    return id_token
