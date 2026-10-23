"""Exact-operation one-use WebAuthn step-up, no actual admin mutations.

The py_webauthn response is MOCKED; genuine ES256 verifier vectors live in
test_admin_pwa_webauthn_crypto_vectors.py. No legacy admin writes are mounted.
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

from app.admin_api.pwa_step_up import (
    operation_digest, begin_step_up, verify_step_up, consume_step_up_in_mutation,
)
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_webauthn import AdminPwaCredential
from app.db.models.user import User

NOW = datetime(2026, 10, 24, 18, tzinfo=timezone.utc)
COOKIE = "S" * 64
OTHER = "T" * 64
CRED_ID = b"stepup-credential"
HANDLE = b"U" * 32
ACTION = "payments.review"
TARGET = "123"
PAYLOAD = {"decision": "approve", "payment_id": 123}


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def credential(*, handle=HANDLE):
    return {
        "id": b64(CRED_ID), "rawId": b64(CRED_ID), "type": "public-key",
        "response": {"authenticatorData": "AA", "clientDataJSON": "AA",
                     "signature": "AA", "userHandle": b64(handle)},
    }


class Adapter:
    def __init__(self, session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)

    async def execute(self, query):
        return self.session.execute(query)

    async def flush(self):
        self.session.flush()

    def in_transaction(self):
        return self.session.in_transaction()

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield self


class StepUpTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for model in (User, AdminPwaSession, AdminPwaCredential, AdminPwaStepUp):
            model.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.db = Adapter(self.session)
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            admin_id_list=[9001],
        )
        self.session.add(User(id=1001, telegram_id=9001, status="active"))
        self.session.commit()
        import hashlib
        self.session.add(AdminPwaSession(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            user_id=1001, token_hash=hashlib.sha256(COOKIE.encode()).hexdigest(),
            auth_method="webauthn", created_at=NOW,
            expires_at=NOW + timedelta(hours=8),
        ))
        self.session.add(AdminPwaCredential(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            user_id=1001, credential_id=CRED_ID,
            public_key=b"stored-cose-key", user_handle=HANDLE,
            sign_count=0, device_type="multi_device",
            backed_up=True, created_at=NOW,
        ))
        self.session.commit()
        self.opts = patch(
            "app.admin_api.pwa_step_up.generate_authentication_options",
            side_effect=lambda **kw: kw,
        )
        self.opts.start()
        self.addCleanup(self.opts.stop)
        self.format = patch(
            "app.admin_api.pwa_step_up.options_to_json",
            side_effect=lambda options: json.dumps({
                "rpId": options["rp_id"], "challenge": b64(options["challenge"]),
            }),
        )
        self.format.start()
        self.addCleanup(self.format.stop)
        self.verify_patch = patch(
            "app.admin_api.pwa_step_up.verify_authentication_response",
            return_value=SimpleNamespace(
                credential_id=CRED_ID, user_verified=True,
                new_sign_count=1, credential_device_type="multi_device",
                credential_backed_up=True,
            ),
        )
        self.verifier = self.verify_patch.start()
        self.addCleanup(self.verify_patch.stop)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def fresh(self):
        if self.session.in_transaction():
            self.session.commit()

    async def start(self, *, cookie=COOKIE, action=ACTION,
                    target=TARGET, payload=PAYLOAD, now=NOW):
        self.fresh()
        return await begin_step_up(
            self.db, session_cookie=cookie, action=action,
            target=target, payload=payload, settings_obj=self.settings, now=now,
        )

    async def verify(self, start, *, cookie=COOKIE, response=None, now=NOW):
        self.fresh()
        return await verify_step_up(
            self.db, session_cookie=cookie, step_up_id=start.step_up_id,
            credential=credential() if response is None else response,
            settings_obj=self.settings, now=now,
        )

    async def consume(self, start, *, cookie=COOKIE, action=ACTION,
                      target=TARGET, payload=PAYLOAD, now=NOW):
        self.fresh()
        with self.session.begin():
            return await consume_step_up_in_mutation(
                self.db, session_cookie=cookie, step_up_id=start.step_up_id,
                action=action, target=target, payload=payload,
                settings_obj=self.settings, now=now,
            )

    async def test_exact_signed_payload_consumed_once(self):
        started = await self.start()
        self.assertEqual(started.options["rpId"], "hskai.app")
        self.assertTrue(await self.verify(started))
        kwargs = self.verifier.call_args.kwargs
        self.assertEqual(kwargs["expected_rp_id"], "hskai.app")
        self.assertEqual(kwargs["expected_origin"], "https://hskai.app")
        self.assertTrue(kwargs["require_user_verification"])
        row = self.session.execute(select(AdminPwaStepUp)).scalar_one()
        self.assertEqual(bytes(row.challenge), kwargs["expected_challenge"])
        self.assertEqual(row.payload_hash, operation_digest(
            action=ACTION, target=TARGET, payload=PAYLOAD,
        ))
        self.assertTrue(await self.consume(started))
        self.assertFalse(await self.consume(started))
        self.assertEqual(self.session.execute(select(AdminPwaStepUp)).scalar_one().status, "consumed")

    async def test_change_to_amount_decision_or_target_denied(self):
        started = await self.start()
        self.assertTrue(await self.verify(started))
        self.assertFalse(await self.consume(started, target="124"))
        self.assertFalse(await self.consume(started, action="users.delete"))
        self.assertFalse(await self.consume(started, payload={"decision": "reject", "payment_id": 123}))
        self.assertFalse(await self.consume(started, payload={"decision": "approve", "payment_id": 123, "amount": 9000}))
        self.assertTrue(await self.consume(started))

    async def test_cross_session_and_replay_verification_denied(self):
        started = await self.start()
        self.assertFalse(await self.verify(started, cookie=OTHER))
        self.verifier.assert_not_called()
        self.assertTrue(await self.verify(started))
        self.assertFalse(await self.verify(started))
        self.assertFalse(await self.consume(started, cookie=OTHER))
        self.assertTrue(await self.consume(started))

    async def test_mutation_rollback_preserves_unused_confirmation(self):
        started = await self.start()
        self.assertTrue(await self.verify(started))
        self.fresh()
        with self.assertRaisesRegex(RuntimeError, "mutated-write-rollback"):
            with self.session.begin():
                self.assertTrue(await consume_step_up_in_mutation(
                    self.db, session_cookie=COOKIE, step_up_id=started.step_up_id,
                    action=ACTION, target=TARGET, payload=PAYLOAD,
                    settings_obj=self.settings, now=NOW,
                ))
                raise RuntimeError("mutated-write-rollback")
        self.assertTrue(await self.consume(started))

    async def test_without_mutation_transaction_denied(self):
        started = await self.start()
        self.assertTrue(await self.verify(started))
        self.fresh()
        self.assertFalse(await consume_step_up_in_mutation(
            self.db, session_cookie=COOKIE, step_up_id=started.step_up_id,
            action=ACTION, target=TARGET, payload=PAYLOAD,
            settings_obj=self.settings, now=NOW,
        ))

    async def test_unverified_or_expired_receipt_denied(self):
        started = await self.start()
        self.assertFalse(await self.consume(started))
        self.assertTrue(await self.verify(started))
        self.assertFalse(await self.consume(started, now=NOW + timedelta(minutes=1)))
        self.assertTrue(await self.consume(started, now=NOW + timedelta(seconds=30)))

    async def test_revoke_admin_or_session_immediately_blocks(self):
        started = await self.start()
        self.assertTrue(await self.verify(started))
        self.settings.admin_id_list = []
        self.assertFalse(await self.consume(started))
        self.settings.admin_id_list = [9001]
        self.fresh()
        session = self.session.get(AdminPwaSession, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        session.revoked_at = NOW
        self.session.commit()
        self.assertFalse(await self.consume(started))

    async def test_wrong_public_credential_and_missing_uv_rejected(self):
        started = await self.start()
        self.assertFalse(await self.verify(started, response=credential(handle=b"X" * 32)))
        self.verifier.assert_not_called()
        from webauthn.helpers.exceptions import InvalidAuthenticationResponse
        self.verifier.side_effect = InvalidAuthenticationResponse("signature or UV failed")
        self.assertFalse(await self.verify(started))
        self.fresh()
        self.assertEqual(self.session.execute(select(AdminPwaStepUp)).scalar_one().status, "pending")

    async def test_current_admin_rights_and_flag_required(self):
        self.settings.admin_id_list = []
        self.assertIsNone(await self.start())
        self.settings.admin_id_list = [9001]
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.start())
        self.settings.ADMIN_PWA_ENABLED = True
        self.assertIsNotNone(await self.start())

    async def test_unknown_action_invalid_target_and_bad_payload_denied(self):
        for action, target, payload in (
            ("generic.write", TARGET, PAYLOAD),
            (ACTION, "12 /etc", PAYLOAD),
            (ACTION, TARGET, {}),
            (ACTION, TARGET, {"bad": float("nan")}),
            (ACTION, TARGET, {"huge": "A" * 8000}),
        ):
            with self.subTest(action=action, target=target):
                self.assertIsNone(await self.start(action=action, target=target, payload=payload))
        self.fresh()
        self.assertEqual(self.session.execute(select(AdminPwaStepUp)).scalars().all(), [])

    async def test_rate_limit_per_session(self):
        for i in range(10):
            self.assertIsNotNone(await self.start(target=str(i + 1)))
        self.assertIsNone(await self.start(target="11"))


if __name__ == "__main__":
    unittest.main()
