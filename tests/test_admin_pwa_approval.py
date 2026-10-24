"""Isolation tests: real SQLAlchemy conditional updates, not a public login API."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.admin_api.pwa_approval import (
    start_pwa_approval, approve_pwa_approval, consume_pwa_approval,
)

NOW = datetime(2026, 10, 23, 15, tzinfo=timezone.utc)
SUBJECT = hashlib.sha256(b"test-subject").hexdigest()


class AsyncAdapter:
    """Synchronous SQLite DB with async execute/commit adapter for SQL tests."""
    def __init__(self, session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)

    async def execute(self, query):
        return self.session.execute(query)

    async def get(self, cls, pk):
        return self.session.get(cls, pk)

    async def commit(self):
        self.session.commit()


class ApprovalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for table in (User.__table__, UserIdentity.__table__, AdminPwaApproval.__table__):
            table.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.session.add_all([
            User(id=1001, telegram_id=9001, status="active"),
            User(id=1002, telegram_id=9002, status="active"),
        ])
        self.session.commit()
        self.settings = SimpleNamespace(admin_id_list=[9001])

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def started(self):
        return await start_pwa_approval(
            self.db, verified_google_subject_hash=SUBJECT,
            verified_google_audience="browser-client.apps.googleusercontent.com",
            now=NOW,
        )

    async def approve(self, request_id, telegram_id=9001, now=NOW):
        return await approve_pwa_approval(
            self.db, request_id=request_id,
            verified_bot_telegram_id=telegram_id,
            settings_obj=self.settings, now=now,
        )

    async def consume(self, request_id, proof, now=NOW):
        return await consume_pwa_approval(
            self.db, request_id=request_id, browser_proof=proof,
            settings_obj=self.settings, now=now,
        )

    async def test_approval_requires_allowlisted_admin_and_consumes_once(self):
        started = await self.started()
        self.assertFalse(await self.approve(started.request_id, 9002))
        self.assertTrue(await self.approve(started.request_id))
        self.assertFalse(await self.approve(started.request_id))
        self.assertIsNone(await self.consume(started.request_id, "B" * 64))
        result = await self.consume(started.request_id, started.browser_proof)
        self.assertEqual((result.user_id, result.telegram_id), (1001, 9001))
        self.assertIsNone(await self.consume(started.request_id, started.browser_proof))
        self.session.expire_all()
        row = self.session.get(AdminPwaApproval, started.request_id)
        self.assertEqual(row.status, "consumed")
        self.assertNotEqual(row.browser_proof_hash, started.browser_proof)

    async def test_expired_and_unapproved(self):
        started = await self.started()
        self.assertIsNone(await self.consume(started.request_id, started.browser_proof))
        self.assertFalse(await self.approve(started.request_id, now=NOW + timedelta(minutes=5)))

    async def test_cross_browser_secret_cannot_claim(self):
        first, second = await self.started(), await self.started()
        self.assertTrue(await self.approve(first.request_id))
        self.assertIsNone(await self.consume(first.request_id, second.browser_proof))
        self.assertIsNotNone(await self.consume(first.request_id, first.browser_proof))

    async def test_existing_google_identity_collision_denied(self):
        self.session.add(UserIdentity(
            id=str(uuid4()), user_id=1002, provider="google",
            subject_hash=SUBJECT,
        ))
        self.session.commit()
        started = await self.started()
        self.assertFalse(await self.approve(started.request_id))

    async def test_removed_privileges_and_blocked_user_fail(self):
        started = await self.started()
        self.assertTrue(await self.approve(started.request_id))
        self.settings.admin_id_list = []
        self.assertIsNone(await self.consume(started.request_id, started.browser_proof))
        self.settings.admin_id_list = [9001]
        self.session.get(User, 1001).status = "blocked"
        self.session.commit()
        self.assertIsNone(await self.consume(started.request_id, started.browser_proof))

    async def test_invalid_oidc_parameters_denied(self):
        for subject, audience in (("not-a-hash", "client"), ("a"*64, ""), ("a"*64, "a"*191)):
            with self.subTest(subject=subject[:8]):
                with self.assertRaises(ValueError):
                    await start_pwa_approval(
                        self.db, verified_google_subject_hash=subject,
                        verified_google_audience=audience, now=NOW,
                    )
