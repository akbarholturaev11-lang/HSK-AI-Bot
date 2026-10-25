"""Atomic passkey enrollment grant after verified Google+Telegram approval.

SQLAlchemy SQLite service tests. This grants NO login/session and does not
substitute for real PostgreSQL concurrency or WebAuthn verification.
"""
import hashlib
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_api.pwa_approval import start_pwa_approval, approve_pwa_approval
from app.admin_api.pwa_enrollment import (
    GrantedPwaEnrollment, finalize_google_admin_enrollment,
)
from app.admin_api.pwa_enrollment_grants import verify_passkey_enrollment_grant
from app.db.models.admin_pwa_enrollment_grant import AdminPwaEnrollmentGrant
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.user_identity import UserIdentity
from app.db.models.user import User
from app.services.identity_link_service import IdentityLinkService

NOW = datetime(2026, 10, 24, 17, tzinfo=timezone.utc)
AUDIENCE = "test-google-browser-client"


class AsyncAdapter:
    def __init__(self, session):
        self.session = session
        self.fail_grant_flush = False

    def add(self, obj):
        self.session.add(obj)

    async def flush(self):
        if self.fail_grant_flush and any(
            isinstance(item, AdminPwaEnrollmentGrant) for item in self.session.new
        ):
            raise IntegrityError("INSERT grant", {}, ValueError("simulated constraint failure"))
        self.session.flush()

    async def execute(self, query):
        return self.session.execute(query)

    async def get(self, cls, key):
        return self.session.get(cls, key)

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield self

    async def commit(self):
        self.session.commit()


class AdminPwaPasskeyGrantTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for model in (
            User, UserIdentity, AdminPwaApproval, AdminPwaSession,
            AdminPwaEnrollmentGrant,
        ):
            model.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.settings = SimpleNamespace(
            admin_id_list=[9001], ADMIN_PWA_ENABLED=True,
            GOOGLE_DESKTOP_CLIENT_ID=AUDIENCE,
            DESKTOP_AUTH_SIGNING_SECRET="G" * 64,
        )
        self.session.add(User(id=1001, telegram_id=9001, status="active"))
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def approved(self):
        subject_hash = IdentityLinkService(
            self.db, self.settings
        ).subject_hash("google", "real-google-sub")
        pending = await start_pwa_approval(
            self.db, verified_google_subject_hash=subject_hash,
            verified_google_audience=AUDIENCE, now=NOW,
        )
        self.assertTrue(await approve_pwa_approval(
            self.db, request_id=pending.request_id,
            verified_bot_telegram_id=9001, settings_obj=self.settings, now=NOW,
        ))
        return pending

    async def finalize(self, pending, *, issue=True, proof=None):
        # Production caller must use a fresh AsyncSession.
        if self.session.in_transaction():
            self.session.commit()
        return await finalize_google_admin_enrollment(
            self.db, request_id=pending.request_id,
            browser_proof=pending.browser_proof if proof is None else proof,
            settings_obj=self.settings, now=NOW, issue_passkey_grant=issue,
        )

    async def verify(self, result, pending, *, token=None, proof=None, now=None):
        if self.session.in_transaction():
            self.session.rollback()
        return await verify_passkey_enrollment_grant(
            self.db, token=result.grant.token if token is None else token,
            browser_proof=pending.browser_proof if proof is None else proof,
            settings_obj=self.settings, now=NOW if now is None else now,
        )

    async def test_grant_and_identity_atomic_no_admin_session(self):
        pending = await self.approved()
        result = await self.finalize(pending)
        self.assertIsInstance(result, GrantedPwaEnrollment)
        self.assertEqual((result.linked.user_id, result.linked.telegram_id), (1001, 9001))
        grant = self.session.execute(select(AdminPwaEnrollmentGrant)).scalar_one()
        self.assertEqual(grant.status, "pending")
        self.assertEqual(grant.approval_id, pending.request_id)
        self.assertNotEqual(grant.token_hash, result.grant.token)
        self.assertEqual(grant.token_hash, hashlib.sha256(result.grant.token.encode()).hexdigest())
        self.assertEqual(
            self.session.get(AdminPwaApproval, pending.request_id).status, "consumed",
        )
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])
        actor = await self.verify(result, pending)
        self.assertEqual(actor.user_id, 1001)
        self.assertEqual(actor.telegram_id, 9001)

    async def test_two_cookie_browser_binding(self):
        pending = await self.approved()
        result = await self.finalize(pending)
        self.assertIsNone(await self.verify(result, pending, proof="X" * 64))
        self.assertIsNone(await self.verify(result, pending, token="Y" * 64))
        self.assertIsNotNone(await self.verify(result, pending))

    async def test_three_minute_expiry(self):
        pending = await self.approved()
        result = await self.finalize(pending)
        self.assertIsNone(await self.verify(
            result, pending, now=NOW + timedelta(minutes=3),
        ))
        self.assertIsNotNone(await self.verify(
            result, pending, now=NOW + timedelta(minutes=2),
        ))

    async def test_one_time_approval_cannot_issue_second_grant(self):
        pending = await self.approved()
        self.assertIsNotNone(await self.finalize(pending))
        self.assertIsNone(await self.finalize(pending))
        self.assertEqual(
            len(self.session.execute(select(AdminPwaEnrollmentGrant)).scalars().all()), 1,
        )

    async def test_failed_grant_insertion_rolls_back_identity_and_approval(self):
        pending = await self.approved()
        self.db.fail_grant_flush = True
        self.assertIsNone(await self.finalize(pending))
        self.assertEqual(self.session.execute(select(UserIdentity)).scalars().all(), [])
        self.assertEqual(self.session.execute(select(AdminPwaEnrollmentGrant)).scalars().all(), [])
        self.assertEqual(self.session.get(AdminPwaApproval, pending.request_id).status, "approved")
        self.db.fail_grant_flush = False
        self.assertIsNotNone(await self.finalize(pending))

    async def test_default_legacy_finalizer_does_not_create_grant(self):
        pending = await self.approved()
        result = await self.finalize(pending, issue=False)
        self.assertNotIsInstance(result, GrantedPwaEnrollment)
        self.assertEqual(result.user_id, 1001)
        self.assertEqual(self.session.execute(select(AdminPwaEnrollmentGrant)).scalars().all(), [])

    async def test_admin_revocation_and_blocked_user_invalidate_grant(self):
        pending = await self.approved()
        result = await self.finalize(pending)
        self.settings.admin_id_list = []
        self.assertIsNone(await self.verify(result, pending))
        self.settings.admin_id_list = [9001]
        self.session.get(User, 1001).status = "blocked"
        self.session.commit()
        self.assertIsNone(await self.verify(result, pending))

    async def test_unlinked_identity_and_mismatched_audience_rejected(self):
        pending = await self.approved()
        result = await self.finalize(pending)
        self.settings.GOOGLE_DESKTOP_CLIENT_ID = "other-client"
        self.assertIsNone(await self.verify(result, pending))
        self.settings.GOOGLE_DESKTOP_CLIENT_ID = AUDIENCE
        self.session.query(UserIdentity).delete()
        self.session.commit()
        self.assertIsNone(await self.verify(result, pending))

    async def test_disabled_feature_blocks_grant_access(self):
        pending = await self.approved()
        result = await self.finalize(pending)
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.verify(result, pending))

    async def test_pending_or_denied_telegram_request_cannot_issue_grant(self):
        subject_hash = IdentityLinkService(
            self.db, self.settings,
        ).subject_hash("google", "real-google-sub")
        pending = await start_pwa_approval(
            self.db, verified_google_subject_hash=subject_hash,
            verified_google_audience=AUDIENCE, now=NOW,
        )
        self.assertIsNone(await self.finalize(pending))
        self.assertEqual(self.session.execute(select(AdminPwaEnrollmentGrant)).scalars().all(), [])


if __name__ == "__main__":
    unittest.main()
