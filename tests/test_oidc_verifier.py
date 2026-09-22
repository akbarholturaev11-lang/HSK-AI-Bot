"""Negative-weighted tests for OIDC ID token verification.

Every case here is a forgery or replay that must be refused. The positive path
is one test; the other twelve are the reason this module exists.
"""

import base64
import json
import time
import unittest

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt, jwt as google_jwt

from app.services.oidc_verifier import (
    JwksCache,
    OidcVerificationError,
    verify_id_token,
)


ISSUER = "https://accounts.google.com"
AUDIENCE = "111-web.apps.googleusercontent.com"
OTHER_AUDIENCE = "222-desktop.apps.googleusercontent.com"
JWKS_URI = "https://example.test/certs"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class _Key:
    def __init__(self, kid: str, bits: int = 2048):
        self.kid = kid
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=bits)
        self.pem = self.private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.signer = crypt.RSASigner.from_string(self.pem, self.kid)

    def jwk(self) -> dict:
        numbers = self.private.public_key().public_numbers()
        size = (numbers.n.bit_length() + 7) // 8
        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": _b64url(numbers.n.to_bytes(size, "big")),
            "e": _b64url(numbers.e.to_bytes(3, "big")),
        }

    def sign(self, claims: dict, *, header: dict | None = None) -> str:
        return google_jwt.encode(
            self.signer, claims, header=header, key_id=self.kid
        ).decode()


def _claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "108451234567890123456",
        "iat": now,
        "exp": now + 3600,
        "email": "learner@example.com",
        "email_verified": True,
        "name": "Test Learner",
    }
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


class _Jwks:
    """A fake JWKS endpoint that counts how often it is fetched."""

    def __init__(self, *keys: _Key):
        self.keys = list(keys)
        self.fetches = 0
        self.status = 200
        self.body: bytes | None = None

    def transport(self) -> httpx.MockTransport:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.fetches += 1
            if self.body is not None:
                return httpx.Response(self.status, content=self.body)
            document = {"keys": [key.jwk() for key in self.keys]}
            return httpx.Response(self.status, json=document)

        return httpx.MockTransport(handler)

    def cache(self, **kwargs) -> JwksCache:
        return JwksCache(http_transport=self.transport(), **kwargs)


class OidcVerifierTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.key = _Key("kid-primary")
        self.jwks = _Jwks(self.key)

    async def _verify(self, token, *, cache=None, **kwargs):
        params = {
            "provider": "google",
            "jwks_uri": JWKS_URI,
            "issuers": [ISSUER],
            "audiences": [AUDIENCE],
            "nonce": None,
        }
        params.update(kwargs)
        return await verify_id_token(
            token, cache=cache or self.jwks.cache(), **params
        )

    async def _expect(self, token, code, **kwargs):
        with self.assertRaises(OidcVerificationError) as raised:
            await self._verify(token, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    # --- the one positive case -------------------------------------------
    async def test_valid_token_is_accepted_and_mapped(self):
        identity = await self._verify(self.key.sign(_claims(nonce="n0nce")), nonce="n0nce")
        self.assertEqual(identity.provider, "google")
        self.assertEqual(identity.subject, "108451234567890123456")
        self.assertEqual(identity.email, "learner@example.com")
        self.assertTrue(identity.email_verified)
        self.assertEqual(identity.display_name, "Test Learner")
        self.assertEqual(identity.audience, AUDIENCE)

    # --- signature and algorithm forgeries -------------------------------
    async def test_alg_none_is_rejected_before_any_key_is_loaded(self):
        claims = _claims()
        token = ".".join(
            [
                _b64url(json.dumps({"alg": "none", "kid": self.key.kid}).encode()),
                _b64url(json.dumps(claims).encode()),
                "",
            ]
        )
        await self._expect(token, "oidc_alg_unsupported")
        self.assertEqual(self.jwks.fetches, 0)

    async def test_hs256_signed_with_the_public_key_is_rejected(self):
        import hmac
        import hashlib

        public_pem = self.key.private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        signing_input = ".".join(
            [
                _b64url(json.dumps({"alg": "HS256", "kid": self.key.kid}).encode()),
                _b64url(json.dumps(_claims()).encode()),
            ]
        )
        signature = hmac.new(
            public_pem, signing_input.encode(), hashlib.sha256
        ).digest()
        await self._expect(
            f"{signing_input}.{_b64url(signature)}", "oidc_alg_unsupported"
        )

    async def test_token_signed_by_a_foreign_key_is_rejected(self):
        attacker = _Key(self.key.kid)  # same kid, different key material
        await self._expect(attacker.sign(_claims()), "oidc_token_invalid")

    async def test_unknown_kid_is_rejected(self):
        stranger = _Key("kid-not-published")
        await self._expect(stranger.sign(_claims()), "oidc_key_unknown")

    async def test_short_rsa_key_is_not_accepted_from_the_jwks(self):
        weak = _Key("kid-weak", bits=1024)
        jwks = _Jwks(weak)
        # The only published key is unusable, so the document has no keys at all.
        await self._expect(
            weak.sign(_claims()), "oidc_jwks_invalid", cache=jwks.cache()
        )

    # --- claim forgeries --------------------------------------------------
    async def test_wrong_audience_is_rejected(self):
        await self._expect(
            self.key.sign(_claims(aud=OTHER_AUDIENCE)), "oidc_token_invalid"
        )

    async def test_wrong_issuer_is_rejected(self):
        await self._expect(
            self.key.sign(_claims(iss="https://evil.example")), "oidc_token_invalid"
        )

    async def test_expired_token_is_rejected(self):
        now = int(time.time())
        await self._expect(
            self.key.sign(_claims(iat=now - 7200, exp=now - 3600)),
            "oidc_token_invalid",
        )

    async def test_token_issued_in_the_future_is_rejected(self):
        now = int(time.time())
        await self._expect(
            self.key.sign(_claims(iat=now + 600, exp=now + 4200)),
            "oidc_token_invalid",
        )

    async def test_old_but_unexpired_token_is_rejected_as_stale(self):
        """Provider lifetimes are ~1h; a captured token must not stay usable."""

        now = int(time.time())
        await self._expect(
            self.key.sign(_claims(iat=now - 900, exp=now + 2700)),
            "oidc_token_stale",
        )

    async def test_missing_subject_is_rejected(self):
        await self._expect(self.key.sign(_claims(sub=None)), "oidc_token_invalid")

    async def test_azp_outside_our_audiences_is_rejected(self):
        await self._expect(
            self.key.sign(_claims(azp=OTHER_AUDIENCE)), "oidc_token_invalid"
        )

    # --- replay protection ------------------------------------------------
    async def test_token_without_the_requested_nonce_is_rejected(self):
        await self._expect(
            self.key.sign(_claims()), "oidc_nonce_mismatch", nonce="expected-nonce"
        )

    async def test_mismatched_nonce_is_rejected(self):
        await self._expect(
            self.key.sign(_claims(nonce="someone-elses")),
            "oidc_nonce_mismatch",
            nonce="expected-nonce",
        )

    # --- transport and shape ---------------------------------------------
    async def test_oversized_token_is_rejected_without_parsing(self):
        await self._expect("a" * 9000, "oidc_token_malformed")
        self.assertEqual(self.jwks.fetches, 0)

    async def test_malformed_token_is_rejected(self):
        for label, token in (
            ("empty", ""),
            ("two segments", "aaa.bbb"),
            ("bad base64 header", "!!!.bbb.ccc"),
        ):
            with self.subTest(case=label):
                await self._expect(token, "oidc_token_malformed")

    async def test_unavailable_jwks_fails_closed(self):
        jwks = _Jwks(self.key)
        jwks.status = 500
        jwks.body = b"nope"
        await self._expect(
            self.key.sign(_claims()), "oidc_jwks_unavailable", cache=jwks.cache()
        )

    async def test_oversized_jwks_document_is_refused(self):
        jwks = _Jwks(self.key)
        jwks.body = b"{" + b"x" * (70 * 1024) + b"}"
        await self._expect(
            self.key.sign(_claims()), "oidc_jwks_unavailable", cache=jwks.cache()
        )

    # --- caching and rotation --------------------------------------------
    async def test_repeated_verification_uses_the_cache(self):
        cache = self.jwks.cache()
        for _ in range(3):
            await self._verify(self.key.sign(_claims()), cache=cache)
        self.assertEqual(self.jwks.fetches, 1)

    async def test_rotation_refetches_once_and_then_succeeds(self):
        cache = self.jwks.cache()
        await self._verify(self.key.sign(_claims()), cache=cache)
        self.assertEqual(self.jwks.fetches, 1)

        rotated = _Key("kid-rotated")
        self.jwks.keys.append(rotated)
        identity = await self._verify(rotated.sign(_claims()), cache=cache)
        self.assertEqual(identity.subject, "108451234567890123456")
        self.assertEqual(self.jwks.fetches, 2)

        # The new key is now cached: no third fetch.
        await self._verify(rotated.sign(_claims()), cache=cache)
        self.assertEqual(self.jwks.fetches, 2)

    async def test_unknown_kid_storm_does_not_refetch_per_attempt(self):
        cache = self.jwks.cache()
        await self._verify(self.key.sign(_claims()), cache=cache)
        self.assertEqual(self.jwks.fetches, 1)
        for index in range(5):
            stranger = _Key(f"kid-bogus-{index}")
            await self._expect(
                stranger.sign(_claims()), "oidc_key_unknown", cache=cache
            )
        # One forced refresh, then the rate limit holds for the rest.
        self.assertEqual(self.jwks.fetches, 2)

    async def test_unconfigured_audience_fails_closed(self):
        await self._expect(
            self.key.sign(_claims()), "oidc_provider_unconfigured", audiences=[]
        )


if __name__ == "__main__":
    unittest.main()
