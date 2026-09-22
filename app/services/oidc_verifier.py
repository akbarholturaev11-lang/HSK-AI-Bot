"""Shared OpenID Connect ID token verification for Google and Apple.

Both providers sign with RS256 and publish a JWKS document, so there is one
verification path and no hand-rolled cryptography: signature, ``iat`` and
``exp`` are checked by ``google.auth.jwt.decode`` (already a dependency via
``google-genai``), and everything else is checked explicitly here.

Design rules that must not be relaxed:

* JWKS URIs are hard-coded constants supplied by the caller. They are never
  read from the token and never taken from configuration, so a forged token
  cannot point verification at a key set the attacker controls. Discovery
  documents are not fetched.
* ``alg`` is pinned to RS256 and checked BEFORE any key is loaded, which
  removes ``alg: none`` and HS/RS confusion.
* Each caller passes only its OWN audience. Passing a union would let a token
  minted for one client be replayed at another client's endpoint.
* When a nonce was requested, a token without one is rejected. Otherwise a
  captured ID token stays replayable for its full lifetime.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hmac
import json
import time
from dataclasses import dataclass
from typing import Iterable, Mapping

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import jwt as google_jwt


# A JWKS document is a few kilobytes; anything larger is not one.
JWKS_MAX_BYTES = 64 * 1024
JWKS_CACHE_TTL_SECONDS = 3600
# Rate limit for forced refetches after an unknown `kid`, so a stream of bogus
# key ids cannot turn into a stream of outbound requests.
JWKS_REFRESH_MIN_INTERVAL_SECONDS = 60
JWKS_NEGATIVE_CACHE_SECONDS = 60
ID_TOKEN_MAX_CHARS = 8192
SUBJECT_MAX_CHARS = 255
MIN_RSA_KEY_BITS = 2048
CLOCK_SKEW_SECONDS = 60


class OidcVerificationError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str
    email: str | None
    email_verified: bool
    display_name: str | None
    audience: str | None


def _constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _jwk_to_pem(jwk: Mapping[str, object]) -> bytes:
    """Convert one RSA signing JWK to PEM, rejecting anything unusual."""

    if str(jwk.get("kty") or "") != "RSA":
        raise OidcVerificationError("oidc_key_unsupported")
    use = jwk.get("use")
    if use is not None and str(use) != "sig":
        raise OidcVerificationError("oidc_key_unsupported")
    alg = jwk.get("alg")
    if alg is not None and str(alg) != "RS256":
        raise OidcVerificationError("oidc_key_unsupported")
    try:
        modulus = int.from_bytes(_b64url_decode(str(jwk["n"])), "big")
        exponent = int.from_bytes(_b64url_decode(str(jwk["e"])), "big")
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        raise OidcVerificationError("oidc_key_unsupported") from exc
    if modulus.bit_length() < MIN_RSA_KEY_BITS:
        raise OidcVerificationError("oidc_key_unsupported")
    try:
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
    except ValueError as exc:
        raise OidcVerificationError("oidc_key_unsupported") from exc
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class JwksCache:
    """Process-wide JWKS cache with per-URI locking and bounded refetching."""

    def __init__(
        self,
        *,
        ttl_seconds: int = JWKS_CACHE_TTL_SECONDS,
        timeout_seconds: float = 8.0,
        max_bytes: int = JWKS_MAX_BYTES,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.max_bytes = max(1024, int(max_bytes))
        self.http_transport = http_transport
        self._keys: dict[str, dict[str, bytes]] = {}
        self._fetched_at: dict[str, float] = {}
        # Last time an unknown `kid` forced a refetch. Tracked separately from
        # `_fetched_at`, otherwise the initial fetch would start the cooldown
        # and the very first key rotation would be ignored for a full window —
        # breaking sign-in every time the provider rotates.
        self._forced_at: dict[str, float] = {}
        self._failed_at: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, jwks_uri: str) -> asyncio.Lock:
        lock = self._locks.get(jwks_uri)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[jwks_uri] = lock
        return lock

    async def _fetch(self, jwks_uri: str) -> dict[str, bytes]:
        timeout = httpx.Timeout(self.timeout_seconds)
        async with asyncio.timeout(self.timeout_seconds):
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                transport=self.http_transport,
            ) as client:
                async with client.stream(
                    "GET",
                    jwks_uri,
                    headers={"Accept": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        raise OidcVerificationError("oidc_jwks_unavailable")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_bytes:
                            raise OidcVerificationError("oidc_jwks_unavailable")
        try:
            document = json.loads(bytes(body).decode("utf-8"))
            entries = document["keys"]
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise OidcVerificationError("oidc_jwks_invalid") from exc
        if not isinstance(entries, list) or not entries:
            raise OidcVerificationError("oidc_jwks_invalid")

        keys: dict[str, bytes] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            kid = str(entry.get("kid") or "")
            if not kid:
                continue
            try:
                keys[kid] = _jwk_to_pem(entry)
            except OidcVerificationError:
                # One unusable key (a different algorithm, an encryption key)
                # must not make the whole rotating key set unusable.
                continue
        if not keys:
            raise OidcVerificationError("oidc_jwks_invalid")
        return keys

    async def _refresh(self, jwks_uri: str, *, forced: bool) -> dict[str, bytes]:
        async with self._lock(jwks_uri):
            now = time.monotonic()
            cached = self._keys.get(jwks_uri)
            if forced and cached is not None:
                # A concurrent waiter may already have refreshed for this same
                # rotation, and a stream of bogus key ids must not become a
                # stream of outbound requests.
                if now - self._forced_at.get(jwks_uri, 0.0) < JWKS_REFRESH_MIN_INTERVAL_SECONDS:
                    return cached
                self._forced_at[jwks_uri] = now
            if now - self._failed_at.get(jwks_uri, 0.0) < JWKS_NEGATIVE_CACHE_SECONDS:
                if cached is not None:
                    return cached
                raise OidcVerificationError("oidc_jwks_unavailable")
            try:
                keys = await self._fetch(jwks_uri)
            except Exception as exc:
                self._failed_at[jwks_uri] = time.monotonic()
                # A transient JWKS outage must not invalidate keys we already
                # hold: fall back to the cache and let the caller decide.
                if cached is not None:
                    return cached
                if isinstance(exc, OidcVerificationError):
                    raise
                raise OidcVerificationError("oidc_jwks_unavailable") from exc
            self._keys[jwks_uri] = keys
            self._fetched_at[jwks_uri] = time.monotonic()
            self._failed_at.pop(jwks_uri, None)
            return keys

    async def public_key(self, jwks_uri: str, kid: str) -> bytes:
        now = time.monotonic()
        keys = self._keys.get(jwks_uri)
        fresh = (
            keys is not None
            and now - self._fetched_at.get(jwks_uri, 0.0) < self.ttl_seconds
        )
        if fresh and kid in keys:
            return keys[kid]
        # Unknown `kid` on a fresh cache means the provider probably rotated;
        # a stale cache just needs its scheduled refresh.
        keys = await self._refresh(jwks_uri, forced=bool(fresh))
        key = keys.get(kid)
        if key is None:
            raise OidcVerificationError("oidc_key_unknown")
        return key


_shared_cache = JwksCache()


def shared_jwks_cache() -> JwksCache:
    return _shared_cache


def _unverified_header(token: str) -> Mapping[str, object]:
    segments = token.split(".")
    if len(segments) != 3:
        raise OidcVerificationError("oidc_token_malformed")
    try:
        header = json.loads(_b64url_decode(segments[0]))
    except (ValueError, binascii.Error) as exc:
        raise OidcVerificationError("oidc_token_malformed") from exc
    if not isinstance(header, dict):
        raise OidcVerificationError("oidc_token_malformed")
    return header


async def verify_id_token(
    token: str,
    *,
    provider: str,
    jwks_uri: str,
    issuers: Iterable[str],
    audiences: Iterable[str],
    nonce: str | None = None,
    max_age_seconds: int = 300,
    cache: JwksCache | None = None,
    now_timestamp: int | None = None,
) -> VerifiedIdentity:
    raw = str(token or "")
    if not raw or len(raw) > ID_TOKEN_MAX_CHARS:
        raise OidcVerificationError("oidc_token_malformed")

    audience_list = sorted({str(value) for value in audiences if str(value or "")})
    issuer_set = {str(value) for value in issuers if str(value or "")}
    if not audience_list or not issuer_set:
        raise OidcVerificationError("oidc_provider_unconfigured")

    header = _unverified_header(raw)
    # Pinned before any key is loaded: this is what makes `alg: none` and
    # HS256-signed-with-the-public-key forgeries impossible.
    if str(header.get("alg") or "") != "RS256":
        raise OidcVerificationError("oidc_alg_unsupported")
    kid = str(header.get("kid") or "")
    if not kid or len(kid) > 128:
        raise OidcVerificationError("oidc_token_malformed")

    public_key = await (cache or _shared_cache).public_key(jwks_uri, kid)
    try:
        claims = google_jwt.decode(
            raw,
            certs={kid: public_key},
            audience=audience_list,
            clock_skew_in_seconds=CLOCK_SKEW_SECONDS,
        )
    except ValueError as exc:
        # google-auth reports signature, expiry and audience failures the same
        # way. The client never needs to know which, and telling it would help
        # an attacker tune a forgery.
        raise OidcVerificationError("oidc_token_invalid") from exc

    if str(claims.get("iss") or "") not in issuer_set:
        raise OidcVerificationError("oidc_token_invalid")

    subject = str(claims.get("sub") or "")
    if not subject or len(subject) > SUBJECT_MAX_CHARS:
        raise OidcVerificationError("oidc_token_invalid")

    if nonce is not None:
        token_nonce = claims.get("nonce")
        # A token minted without the nonce we asked for is a replay candidate.
        if not isinstance(token_nonce, str) or not _constant_time_equals(
            token_nonce, nonce
        ):
            raise OidcVerificationError("oidc_nonce_mismatch")

    try:
        issued_at = int(claims["iat"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OidcVerificationError("oidc_token_invalid") from exc
    now = int(now_timestamp if now_timestamp is not None else time.time())
    if issued_at > now + CLOCK_SKEW_SECONDS:
        raise OidcVerificationError("oidc_token_invalid")
    if now - issued_at > max(60, int(max_age_seconds)):
        raise OidcVerificationError("oidc_token_stale")

    audience = claims.get("aud")
    if isinstance(audience, list):
        audience = audience[0] if audience else None
    authorized_party = claims.get("azp")
    if authorized_party is not None and str(authorized_party) not in audience_list:
        raise OidcVerificationError("oidc_token_invalid")

    email = claims.get("email")
    email = str(email) if isinstance(email, str) and email.strip() else None
    email_verified = claims.get("email_verified")
    if isinstance(email_verified, str):
        email_verified = email_verified.strip().lower() == "true"
    display_name = claims.get("name")
    display_name = (
        str(display_name)[:120]
        if isinstance(display_name, str) and display_name.strip()
        else None
    )

    return VerifiedIdentity(
        provider=str(provider),
        subject=subject,
        email=email,
        email_verified=bool(email_verified),
        display_name=display_name,
        audience=str(audience) if audience else None,
    )
