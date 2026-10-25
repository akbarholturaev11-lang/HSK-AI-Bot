"""Passkey-only signature gate and session lifecycle (mock WebAuthn verifier).

The verified response is MOCKED here; actual WebAuthn signature/origin/RP
vectors and real PostgreSQL concurrency are separate release requirements.
"""
import base64
import json
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.admin_api.pwa_webauthn_login import (
    PasskeyLoginRateLimited, begin_passkey_login, complete_passkey_login,
)
from app.admin_api.pwa_sessions import authenticate_admin_pwa_session, revoke_admin_pwa_session
from app.db.models.admin_pwa_authentication import AdminPwaAuthenticationChallenge
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.user import User

NOW = datetime(2026, 10, 24, 18, tzinfo=timezone.utc)
HANDLE = b"H" * 32
CRED_ID = b"admin-passkey-1"


def enc(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def assertion(cred=CRED_ID, handle=HANDLE):
    return {
        "id": enc(cred), "rawId": enc(cred), "type": "public-key",
        "response": {
            "authenticatorData": "AA", "clientDataJSON": "AA",
            "signature": "AA", "userHandle": enc(handle),
        },
    }


class AsyncAdapter:
    def __init__(self, session):
        self.session = session

    def add(self, value):
        self.session.add(value)

    def get_bind(self):
        return self.session.get_bind()

    async def execute(self, query):
        return self.session.execute(query)

    async def get(self, typ, pk):
        return self.session.get(typ, pk)

    async def flush(self):
        self.session.flush()

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield self


class PasskeyLoginTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for m in (User, AdminPwaCredential, AdminPwaAuthenticationChallenge, AdminPwaSession):
            m.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.settings = SimpleNamespace(
            admin_id_list=[9001], ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
        )
        self.session.add_all([
            User(id=1001, telegram_id=9001, status="active"),
            User(id=1002, telegram_id=9002, status="active"),
            AdminPwaCredential(
                id="00000000-0000-0000-0000-000000000001",
                user_id=1001, credential_id=CRED_ID,
                public_key=b"server-stored-key", user_handle=HANDLE,
                sign_count=0, device_type="multi_device", backed_up=True,
                created_at=NOW,
            ),
        ])
        self.session.commit()
        self.verification = SimpleNamespace(
            credential_id=CRED_ID, new_sign_count=1,
            user_verified=True, credential_device_type="multi_device",
            credential_backed_up=True,
        )
        self.auth_patch = patch(
            "app.admin_api.pwa_webauthn_login.verify_authentication_response",
            return_value=self.verification,
        )
        self.mock_verify = self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.start_patch = patch(
            "app.admin_api.pwa_webauthn_login.generate_authentication_options",
            side_effect=lambda **kwargs: kwargs,
        )
        self.start_patch.start()
        self.addCleanup(self.start_patch.stop)
        self.json_patch = patch(
            "app.admin_api.pwa_webauthn_login.options_to_json",
            side_effect=lambda opts: json.dumps({
                "rpId": opts["rp_id"], "challenge": enc(opts["challenge"]),
            }),
        )
        self.json_patch.start()
        self.addCleanup(self.json_patch.stop)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def fresh(self):
        if self.session.in_transaction():
            self.session.commit()

    async def start(self, *, now=NOW):
        self.fresh()
        return await begin_passkey_login(self.db, settings_obj=self.settings, now=now)

    async def finish(self, started, *, assertion_data=None, now=NOW, proof=None):
        self.fresh()
        return await complete_passkey_login(
            self.db, browser_proof=started.browser_proof if proof is None else proof,
            credential=assertion() if assertion_data is None else assertion_data,
            settings_obj=self.settings, now=now,
        )

    async def test_signature_verified_before_session_and_counter_update(self):
        started = await self.start()
        self.assertEqual(started.options["rpId"], "hskai.app")
        self.assertEqual(len(self.session.execute(select(AdminPwaSession)).scalars().all()), 0)
        signed = await self.finish(started)
        self.assertIsNotNone(signed)
        self.assertNotEqual(signed.token, self.session.execute(select(AdminPwaSession)).scalar_one().token_hash)
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalar_one().auth_method, "webauthn")
        self.assertEqual(self.session.get(AdminPwaCredential, "00000000-0000-0000-0000-000000000001").sign_count, 1)
        kwargs = self.mock_verify.call_args.kwargs
        self.assertEqual(kwargs["expected_rp_id"], "hskai.app")
        self.assertEqual(kwargs["expected_origin"], "https://hskai.app")
        self.assertEqual(kwargs["expected_challenge"], self.session.execute(select(AdminPwaAuthenticationChallenge)).scalar_one().challenge)
        self.assertEqual(kwargs["credential_public_key"], b"server-stored-key")
        self.assertTrue(kwargs["require_user_verification"])
        self.assertIsNotNone(await authenticate_admin_pwa_session(self.db, signed.token, self.settings, now=NOW))
        self.fresh()
        self.assertTrue(await revoke_admin_pwa_session(self.db, signed.token, now=NOW))
        self.fresh()
        self.assertIsNone(await authenticate_admin_pwa_session(self.db, signed.token, self.settings, now=NOW))
        self.fresh()
        self.assertFalse(await revoke_admin_pwa_session(self.db, signed.token, now=NOW))

    async def test_same_challenge_cannot_replay(self):
        started = await self.start()
        self.assertIsNotNone(await self.finish(started))
        self.assertIsNone(await self.finish(started))
        self.assertEqual(len(self.session.execute(select(AdminPwaSession)).scalars().all()), 1)

    async def test_wrong_browser_proof_or_credential_never_calls_verifier(self):
        started = await self.start()
        self.assertIsNone(await self.finish(started, proof="X" * 64))
        self.assertIsNone(await self.finish(started, assertion_data=assertion(b"unknown")))
        self.assertIsNone(await self.finish(started, assertion_data=assertion(handle=b"Z" * 32)))
        self.mock_verify.assert_not_called()
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])

    async def test_expired_or_disabled_challenge_denied(self):
        started = await self.start()
        self.assertIsNone(await self.finish(started, now=NOW + timedelta(minutes=2)))
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.finish(started))
        self.settings.ADMIN_PWA_ENABLED = True
        self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://evil.example"
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])

    async def test_admin_revocation_block_and_revoked_credential(self):
        started = await self.start()
        self.settings.admin_id_list = []
        self.assertIsNone(await self.finish(started))
        self.settings.admin_id_list = [9001]
        cred = self.session.get(AdminPwaCredential, "00000000-0000-0000-0000-000000000001")
        cred.revoked_at = NOW
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        cred.revoked_at = None
        self.session.get(User, 1001).status = "blocked"
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])

    async def test_signature_or_uv_denial_does_not_consume_challenge(self):
        from webauthn.helpers.exceptions import InvalidAuthenticationResponse
        started = await self.start()
        self.mock_verify.side_effect = InvalidAuthenticationResponse("bad signature or origin")
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.execute(select(AdminPwaAuthenticationChallenge)).scalar_one().status, "pending")
        self.mock_verify.side_effect = None
        self.mock_verify.return_value = SimpleNamespace(
            **{**vars(self.verification), "user_verified": False}
        )
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])

    async def test_signature_counter_rollback_rejected(self):
        started = await self.start()
        stored = self.session.get(AdminPwaCredential, "00000000-0000-0000-0000-000000000001")
        stored.sign_count = 20
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.execute(select(AdminPwaAuthenticationChallenge)).scalar_one().status, "pending")

    async def test_browser_challenge_rate_limit_global_cap(self):
        for i in range(60):
            self.assertIsNotNone(await self.start())
        with self.assertRaises(PasskeyLoginRateLimited):
            await self.start()
        self.assertEqual(len(self.session.execute(select(AdminPwaAuthenticationChallenge)).scalars().all()), 60)

    async def test_wrong_credential_id_binary_format_is_denied(self):
        started = await self.start()
        for value in ("../", "QQ==", "?", "", "!" * 2000):
            with self.subTest(value=value):
                invalid = assertion()
                invalid["rawId"] = value
                self.assertIsNone(await self.finish(started, assertion_data=invalid))
        self.mock_verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
