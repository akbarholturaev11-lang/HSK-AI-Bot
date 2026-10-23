"""Actual py_webauthn signature-verification vectors, with generated ES256 keys.

No verifier mocks: sign a WebAuthn authenticatorData + clientDataHash
using cryptography ECDSA, then assert true verification and wrong RP/origin,
wrong challenge, tampered signature, missing UV and sign-counter replay denial.

This is synthetic key material and NOT physical iPhone/macOS/Windows testing.
"""
import base64
import hashlib
import json
import unittest

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from webauthn import verify_authentication_response
from webauthn.helpers.exceptions import InvalidAuthenticationResponse

CHALLENGE = b"C" * 32
CRED_ID = b"synthetic-admin-credential"
HANDLE = b"H" * 32
ORIGIN = "https://hskai.app"
RP_ID = "hskai.app"


def b64(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def make_assertion(
    key, *, challenge=CHALLENGE, origin=ORIGIN, rp_id=RP_ID, uv=True,
    sign_count=1, signature_valid=True,
):
    client_data = json.dumps({
        "type": "webauthn.get", "challenge": b64(challenge),
        "origin": origin, "crossOrigin": False,
    }, separators=(",", ":")).encode("utf-8")
    flags = 0x01 | (0x04 if uv else 0)
    auth_data = (
        hashlib.sha256(rp_id.encode("utf-8")).digest()
        + bytes([flags]) + int(sign_count).to_bytes(4, "big")
    )
    signature = key.sign(
        auth_data + hashlib.sha256(client_data).digest(),
        ec.ECDSA(hashes.SHA256()),
    )
    if not signature_valid:
        signature = signature[:-1] + bytes([signature[-1] ^ 0x01])
    return {
        "id": b64(CRED_ID), "rawId": b64(CRED_ID), "type": "public-key",
        "response": {
            "authenticatorData": b64(auth_data),
            "clientDataJSON": b64(client_data),
            "signature": b64(signature),
            "userHandle": b64(HANDLE),
        },
    }


def cose_es256_public_key(key):
    numbers = key.public_key().public_numbers()
    # COSE EC2: kty=EC2, alg=ES256, crv=P-256, x/y coordinates.
    return cbor2.dumps({
        1: 2, 3: -7, -1: 1,
        -2: numbers.x.to_bytes(32, "big"),
        -3: numbers.y.to_bytes(32, "big"),
    })


class RealWebAuthnAssertionVectorTests(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.stored_public = cose_es256_public_key(self.key)

    def verify(self, response, *, expected_challenge=CHALLENGE, previous_count=0):
        return verify_authentication_response(
            credential=response,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=self.stored_public,
            credential_current_sign_count=previous_count,
            require_user_verification=True,
        )

    def test_actual_ecdsa_signature_and_uv_success(self):
        verified = self.verify(make_assertion(self.key))
        self.assertEqual(verified.credential_id, CRED_ID)
        self.assertTrue(verified.user_verified)
        self.assertEqual(verified.new_sign_count, 1)

    def test_wrong_browser_origin_rejected_even_with_valid_signature(self):
        signed = make_assertion(self.key, origin="https://attacker.example")
        with self.assertRaises(InvalidAuthenticationResponse):
            self.verify(signed)

    def test_wrong_rp_id_rejected_even_with_valid_signature(self):
        signed = make_assertion(self.key, rp_id="attacker.example")
        with self.assertRaises(InvalidAuthenticationResponse):
            self.verify(signed)

    def test_wrong_challenge_rejected_even_with_valid_signature(self):
        signed = make_assertion(self.key, challenge=b"B" * 32)
        with self.assertRaises(InvalidAuthenticationResponse):
            self.verify(signed)

    def test_tampered_signature_rejected(self):
        signed = make_assertion(self.key, signature_valid=False)
        with self.assertRaises(InvalidAuthenticationResponse):
            self.verify(signed)

    def test_user_presence_without_uv_is_rejected(self):
        signed = make_assertion(self.key, uv=False)
        with self.assertRaises(InvalidAuthenticationResponse):
            self.verify(signed)

    def test_replayed_sign_counter_rejected(self):
        signed = make_assertion(self.key, sign_count=1)
        with self.assertRaises(InvalidAuthenticationResponse):
            self.verify(signed, previous_count=1)

    def test_wrong_public_key_rejected(self):
        signed = make_assertion(self.key)
        stranger = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(InvalidAuthenticationResponse):
            verify_authentication_response(
                credential=signed,
                expected_challenge=CHALLENGE,
                expected_rp_id=RP_ID, expected_origin=ORIGIN,
                credential_public_key=cose_es256_public_key(stranger),
                credential_current_sign_count=0,
                require_user_verification=True,
            )


if __name__ == "__main__":
    unittest.main()
