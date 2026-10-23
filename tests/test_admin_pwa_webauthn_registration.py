"""Database WebAuthn registration contracts (mock cryptographic provider).

Tests ensure the production verifier is called with exact challenge, RP ID,
origin and UV. Fake verifier acceptance is NOT a FIDO2 cryptographic E2E test.
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

from app.admin_api.pwa_approval import start_pwa_approval, approve_pwa_approval
from app.admin_api.pwa_enrollment import finalize_google_admin_enrollment
from app.admin_api.pwa_webauthn_registration import (
    begin_passkey_registration, complete_passkey_registration,
)
from app.db.models.admin_pwa_enrollment_grant import AdminPwaEnrollmentGrant
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_webauthn import (
    AdminPwaCredential, AdminPwaRegistrationChallenge,
)
from app.db.models.user_identity import UserIdentity
from app.db.models.user import User
from app.services.identity_link_service import IdentityLinkService

NOW = datetime(2026, 10, 24, 17, tzinfo=timezone.utc)
AUDIENCE = "test-webauthn-client"
CREATED = {"id": "placeholder", "rawId": "placeholder",
           "type": "public-key",
           "response": {"clientDataJSON": "abc", "attestationObject": "xyz",
                        "transports": ["internal"]}}


class AsyncAdapter:
    def __init__(self, session):
        self.session = session

    def add(self, item):
        self.session.add(item)

    async def execute(self, query):
        return self.session.execute(query)

    async def get(self, cls, key):
        return self.session.get(cls, key)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield self


class WebAuthnRegistrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for model in (
            User, UserIdentity, AdminPwaApproval, AdminPwaEnrollmentGrant,
            AdminPwaRegistrationChallenge, AdminPwaCredential, AdminPwaSession,
        ):
            model.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.settings = SimpleNamespace(
            admin_id_list=[9001], ADMIN_PWA_ENABLED=True,
            ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
            GOOGLE_DESKTOP_CLIENT_ID=AUDIENCE,
            DESKTOP_AUTH_SIGNING_SECRET="H" * 64,
        )
        self.session.add(User(id=1001, telegram_id=9001, status="active"))
        self.session.commit()

        def fake_options(**kwargs):
            self.last_options = kwargs
            return kwargs

        def fake_json(options):
            value = {"challenge": base64.urlsafe_b64encode(
                options["challenge"]).rstrip(b"=").decode(),
                     "rp": {"id": options["rp_id"]}}
            return json.dumps(value)

        fake_verified = SimpleNamespace(
            credential_id=b"credential-001", credential_public_key=b"public-key",
            sign_count=0, credential_device_type="multi_device",
            credential_backed_up=True,
        )
        self.verify_mock = patch(
            "app.admin_api.pwa_webauthn_registration.verify_registration_response",
            return_value=fake_verified,
        )
        self.mock_verifier = self.verify_mock.start()
        self.addCleanup(self.verify_mock.stop)
        self.option_patch = patch(
            "app.admin_api.pwa_webauthn_registration.generate_registration_options",
            side_effect=fake_options,
        )
        self.option_patch.start()
        self.addCleanup(self.option_patch.stop)
        self.json_patch = patch(
            "app.admin_api.pwa_webauthn_registration.options_to_json",
            side_effect=fake_json,
        )
        self.json_patch.start()
        self.addCleanup(self.json_patch.stop)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def fresh(self):
        if self.session.in_transaction():
            self.session.commit()

    async def granted(self):
        subject_hash = IdentityLinkService(self.db, self.settings).subject_hash(
            "google", "verified-sub",
        )
        approval = await start_pwa_approval(
            self.db, verified_google_subject_hash=subject_hash,
            verified_google_audience=AUDIENCE, now=NOW,
        )
        self.assertTrue(await approve_pwa_approval(
            self.db, request_id=approval.request_id,
            verified_bot_telegram_id=9001, settings_obj=self.settings, now=NOW,
        ))
        self.fresh()
        result = await finalize_google_admin_enrollment(
            self.db, request_id=approval.request_id,
            browser_proof=approval.browser_proof,
            settings_obj=self.settings, now=NOW, issue_passkey_grant=True,
        )
        return approval, result

    async def begin(self, approval, granted, **kwargs):
        self.fresh()
        return await begin_passkey_registration(
            self.db, token=kwargs.get("token", granted.grant.token),
            browser_proof=kwargs.get("proof", approval.browser_proof),
            settings_obj=self.settings, now=kwargs.get("now", NOW),
        )

    async def finish(self, approval, granted, **kwargs):
        self.fresh()
        return await complete_passkey_registration(
            self.db, token=kwargs.get("token", granted.grant.token),
            browser_proof=kwargs.get("proof", approval.browser_proof),
            credential=kwargs.get("credential", CREATED),
            settings_obj=self.settings, now=kwargs.get("now", NOW),
        )

    async def test_verified_registration_consumes_grant_atomically_without_session(self):
        approval, granted = await self.granted()
        started = await self.begin(approval, granted)
        self.assertEqual(started.options["rp"]["id"], "hskai.app")
        self.assertEqual(self.last_options["rp_id"], "hskai.app")
        self.assertEqual(len(self.last_options["challenge"]), 32)
        self.assertEqual(len(self.last_options["user_id"]), 32)
        self.assertTrue(await self.finish(approval, granted))
        self.mock_verifier.assert_called_once()
        args = self.mock_verifier.call_args.kwargs
        self.assertEqual(args["expected_origin"], "https://hskai.app")
        self.assertEqual(args["expected_rp_id"], "hskai.app")
        self.assertTrue(args["require_user_verification"])
        self.assertEqual(args["expected_challenge"], self.last_options["challenge"])
        row = self.session.execute(select(AdminPwaCredential)).scalar_one()
        self.assertEqual(row.user_id, 1001)
        self.assertEqual(row.credential_id, b"credential-001")
        self.assertEqual(self.session.execute(select(AdminPwaEnrollmentGrant)).scalar_one().status, "consumed")
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])

    async def test_double_registration_start_and_replay_fail(self):
        approval, granted = await self.granted()
        self.assertIsNotNone(await self.begin(approval, granted))
        self.assertIsNone(await self.begin(approval, granted))
        self.assertTrue(await self.finish(approval, granted))
        self.assertFalse(await self.finish(approval, granted))

    async def test_wrong_browser_binding_prevents_options_and_attestation(self):
        approval, granted = await self.granted()
        self.assertIsNone(await self.begin(approval, granted, proof="X" * 64))
        self.assertIsNotNone(await self.begin(approval, granted))
        self.assertFalse(await self.finish(approval, granted, proof="X" * 64))
        self.assertEqual(self.session.execute(select(AdminPwaCredential)).scalars().all(), [])

    async def test_expired_challenge_and_feature_off_are_rejected(self):
        approval, granted = await self.granted()
        self.assertIsNotNone(await self.begin(approval, granted))
        self.assertFalse(await self.finish(approval, granted, now=NOW + timedelta(minutes=2)))
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertFalse(await self.finish(approval, granted))
        self.settings.ADMIN_PWA_ENABLED = True
        self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://evil.example"
        self.assertFalse(await self.finish(approval, granted))

    async def test_admin_revocation_before_attestation_denies_credential(self):
        approval, granted = await self.granted()
        self.assertIsNotNone(await self.begin(approval, granted))
        self.settings.admin_id_list = []
        self.assertFalse(await self.finish(approval, granted))
        self.assertEqual(self.session.execute(select(AdminPwaCredential)).scalars().all(), [])

    async def test_invalid_verifier_does_not_consume_grant(self):
        from webauthn.helpers.exceptions import InvalidRegistrationResponse
        approval, granted = await self.granted()
        self.assertIsNotNone(await self.begin(approval, granted))
        self.mock_verifier.side_effect = InvalidRegistrationResponse("wrong origin or challenge")
        self.assertFalse(await self.finish(approval, granted))
        self.assertEqual(self.session.execute(select(AdminPwaEnrollmentGrant)).scalar_one().status, "pending")
        self.assertEqual(self.session.execute(select(AdminPwaCredential)).scalars().all(), [])

    async def test_duplicate_credential_id_cannot_bind_another_account(self):
        approval, granted = await self.granted()
        self.assertIsNotNone(await self.begin(approval, granted))
        self.session.add(User(id=1002, telegram_id=9002, status="active"))
        self.session.add(AdminPwaCredential(
            id="00000000-0000-0000-0000-000000000001",
            user_id=1002, credential_id=b"credential-001",
            public_key=b"some-previous-key", user_handle=b"u" * 32,
            sign_count=0, device_type="multi_device", backed_up=False,
            created_at=NOW,
        ))
        self.session.commit()
        self.assertFalse(await self.finish(approval, granted))
        self.assertEqual(self.session.execute(select(AdminPwaEnrollmentGrant)).scalar_one().status, "pending")

    async def test_unverified_malformed_credential_is_rejected(self):
        approval, granted = await self.granted()
        self.assertIsNotNone(await self.begin(approval, granted))
        for value in (None, "raw-json", [], {"not_a_credential": True}):
            with self.subTest(value=value):
                if isinstance(value, dict):
                    self.mock_verifier.side_effect = ValueError("malformed")
                self.assertFalse(await self.finish(approval, granted, credential=value))
        self.assertEqual(self.session.execute(select(AdminPwaCredential)).scalars().all(), [])


if __name__ == "__main__":
    unittest.main()
