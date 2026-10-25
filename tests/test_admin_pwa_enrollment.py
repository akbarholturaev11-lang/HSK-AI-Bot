"""Atomic Google identity linking following Bot-approved Admin PWA browser proof."""
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.admin_api.pwa_approval import start_pwa_approval, approve_pwa_approval
from app.admin_api.pwa_enrollment import finalize_google_admin_enrollment
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.identity_link_service import IdentityLinkService

NOW = datetime(2026, 10, 23, 15, tzinfo=timezone.utc)
AUDIENCE = "google-browser.apps.googleusercontent.com"


class AsyncAdapter:
    def __init__(self, session):
        self.session = session
        self.simulate_consume_race = False

    def add(self, value):
        self.session.add(value)

    async def execute(self, query):
        if (self.simulate_consume_race and getattr(query, "__visit_name__", "") == "update"
                and getattr(getattr(query, "table", None), "name", "") == "admin_pwa_approvals"):
            return SimpleNamespace(rowcount=0)
        return self.session.execute(query)

    async def get(self, cls, pk):
        return self.session.get(cls, pk)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield self


class AdminEnrollmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for table in (User.__table__, UserIdentity.__table__, AdminPwaSession.__table__, AdminPwaApproval.__table__):
            table.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.settings = SimpleNamespace(
            admin_id_list=[9001], DESKTOP_AUTH_SIGNING_SECRET="T" * 64,
            ADMIN_PWA_ENABLED=True, GOOGLE_DESKTOP_CLIENT_ID=AUDIENCE,
        )
        self.session.add_all([
            User(id=1001, telegram_id=9001, status="active"),
            User(id=1002, telegram_id=9002, status="active"),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def approval(self):
        subject_hash = IdentityLinkService(
            self.db, self.settings
        ).subject_hash("google", "real-google-sub")
        started = await start_pwa_approval(
            self.db, verified_google_subject_hash=subject_hash,
            verified_google_audience=AUDIENCE, now=NOW,
        )
        self.assertTrue(await approve_pwa_approval(
            self.db, request_id=started.request_id,
            verified_bot_telegram_id=9001, settings_obj=self.settings, now=NOW,
        ))
        return started

    async def finish(self, started, **kwargs):
        # A real callback creates a fresh AsyncSession. Test assertions can
        # autobegin a read transaction in this reused in-memory adapter.
        if self.session.in_transaction():
            self.session.commit()
        return await finalize_google_admin_enrollment(
            self.db, request_id=started.request_id,
            browser_proof=kwargs.get("browser_proof", started.browser_proof),
            settings_obj=self.settings,
            now=kwargs.get("now", NOW),
        )

    async def test_success_links_canonical_admin_and_consumes_without_issuing_session(self):
        started = await self.approval()
        result = await self.finish(started)
        self.assertEqual((result.user_id, result.telegram_id), (1001, 9001))
        row = self.session.execute(select(UserIdentity)).scalar_one()
        self.assertEqual((row.user_id, row.provider), (1001, "google"))
        self.assertEqual(self.session.get(AdminPwaApproval, started.request_id).status, "consumed")
        self.assertEqual(self.session.execute(select(AdminPwaSession)).scalars().all(), [])
        self.assertIsNone(await self.finish(started))  # replay must fail

    async def test_wrong_browser_proof_subject_hash_or_audience_fails_closed(self):
        started = await self.approval()
        row = self.session.get(AdminPwaApproval, started.request_id)
        self.assertIsNone(await self.finish(started, browser_proof="x" * 64))
        original_hash, original_audience = row.google_subject_hash, row.google_audience
        row.google_subject_hash = "not-a-server-verified-hash"
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        row.google_subject_hash = original_hash
        row.google_audience = "different-google-client"
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        row.google_audience = original_audience
        self.session.commit()
        self.assertIsNotNone(await self.finish(started))

    async def test_disabled_flag_and_missing_audience_never_link(self):
        started = await self.approval()
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.finish(started))
        self.settings.ADMIN_PWA_ENABLED = True
        self.settings.GOOGLE_DESKTOP_CLIENT_ID = ""
        self.assertIsNone(await self.finish(started))
        self.settings.GOOGLE_DESKTOP_CLIENT_ID = AUDIENCE
        self.assertIsNotNone(await self.finish(started))

    async def test_existing_same_google_hash_is_idempotent_only_for_same_owner(self):
        started = await self.approval()
        self.session.add(UserIdentity(
            id=str(uuid4()), user_id=1001, provider="google",
            subject_hash=IdentityLinkService(self.db, self.settings).subject_hash(
                "google", "real-google-sub"),
        ))
        self.session.commit()
        self.assertIsNotNone(await self.finish(started))
        identities = self.session.execute(select(UserIdentity)).scalars().all()
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0].user_id, 1001)

    async def test_different_google_identity_already_linked_to_admin_is_denied(self):
        started = await self.approval()
        self.session.add(UserIdentity(
            id=str(uuid4()), user_id=1001, provider="google",
            subject_hash=IdentityLinkService(self.db, self.settings).subject_hash(
                "google", "other-sub"),
        ))
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.get(AdminPwaApproval, started.request_id).status, "approved")

    async def test_expiry_and_admin_privilege_revocation(self):
        started = await self.approval()
        self.assertIsNone(await self.finish(started, now=NOW + timedelta(minutes=6)))
        self.settings.admin_id_list = []
        self.assertIsNone(await self.finish(started))
        self.settings.admin_id_list = [9001]
        self.session.get(User, 1001).status = "blocked"
        self.session.commit()
        self.assertIsNone(await self.finish(started))

    async def test_owner_telegram_identity_change_denied(self):
        started = await self.approval()
        self.session.get(User, 1001).telegram_id = 9003
        self.session.commit()
        self.assertIsNone(await self.finish(started))

    async def test_google_subject_taken_by_another_user_is_never_reassigned(self):
        started = await self.approval()
        self.session.add(UserIdentity(
            id=str(uuid4()), user_id=1002, provider="google",
            subject_hash=IdentityLinkService(self.db, self.settings).subject_hash(
                "google", "real-google-sub"),
        ))
        self.session.commit()
        self.assertIsNone(await self.finish(started))
        self.assertEqual(self.session.get(AdminPwaApproval, started.request_id).status, "approved")
        self.assertEqual(self.session.execute(select(UserIdentity)).scalar_one().user_id, 1002)

    async def test_failed_conditional_consume_rolls_back_new_identity(self):
        started = await self.approval()
        self.db.simulate_consume_race = True
        self.assertIsNone(await self.finish(started))
        self.db.simulate_consume_race = False
        self.assertEqual(self.session.execute(select(UserIdentity)).scalars().all(), [])
        self.assertEqual(self.session.get(AdminPwaApproval, started.request_id).status, "approved")
        self.assertIsNotNone(await self.finish(started))

    async def test_invalid_request_id_denied(self):
        started = await self.approval()
        result = await finalize_google_admin_enrollment(
            self.db, request_id="no", browser_proof=started.browser_proof,
            settings_obj=self.settings, now=NOW,
        )
        self.assertIsNone(result)
        self.assertEqual(self.session.get(AdminPwaApproval, started.request_id).status, "approved")


if __name__ == "__main__":
    unittest.main()
