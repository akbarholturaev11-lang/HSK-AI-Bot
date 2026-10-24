"""SQL-backed focused tests for private Telegram Bot approval and cookie status.

The adapter intentionally does NOT create an admin session or expose a Bot route.
"""

import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.admin_api.pwa_approval import start_pwa_approval
from app.admin_api.pwa_bot_approval import (
    decide_admin_pwa_bot_request,
    preview_admin_pwa_bot_request,
    read_browser_pwa_approval,
)
from app.db.models.admin_pwa_approval import AdminPwaApproval
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)
SUBJECT = hashlib.sha256(b"test-google-sub").hexdigest()


class AsyncAdapter:
    def __init__(self, session):
        self.session = session

    def add(self, value):
        self.session.add(value)

    async def execute(self, query):
        return self.session.execute(query)

    async def commit(self):
        self.session.commit()


class BotApprovalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for model in (User, UserIdentity, AdminPwaApproval):
            model.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.db = AsyncAdapter(self.session)
        self.settings = SimpleNamespace(
            ADMIN_PWA_ENABLED=True, admin_id_list=[9001],
            DESKTOP_AUTH_SIGNING_SECRET="unit-test-only-" + "x" * 64,
        )
        self.session.add_all([
            User(id=1001, telegram_id=9001, status="active"),
            User(id=1002, telegram_id=9002, status="active"),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def started(self):
        return await start_pwa_approval(
            self.db, verified_google_subject_hash=SUBJECT,
            verified_google_audience="test-web-client", now=NOW,
        )

    @staticmethod
    def event(user_id=9001, *, chat_id=None, chat_type="private",
              is_bot=False, callback=True):
        chat = SimpleNamespace(
            id=user_id if chat_id is None else chat_id, type=chat_type,
        )
        from_user = SimpleNamespace(id=user_id, is_bot=is_bot)
        return (SimpleNamespace(from_user=from_user,
                                message=SimpleNamespace(chat=chat))
                if callback else SimpleNamespace(from_user=from_user, chat=chat))

    async def preview(self, started, **kwargs):
        return await preview_admin_pwa_bot_request(
            self.db, bot_event=kwargs.get("event", self.event()),
            request_id=kwargs.get("request_id", started.request_id),
            settings_obj=self.settings, now=kwargs.get("now", NOW),
        )

    async def decide(self, started, *, approve=True, **kwargs):
        return await decide_admin_pwa_bot_request(
            self.db, bot_event=kwargs.get("event", self.event()),
            request_id=kwargs.get("request_id", started.request_id),
            approve=approve, settings_obj=self.settings,
            now=kwargs.get("now", NOW),
        )

    async def browser(self, started, **kwargs):
        return await read_browser_pwa_approval(
            self.db, request_id=kwargs.get("request_id", started.request_id),
            browser_proof=kwargs.get("browser_proof", started.browser_proof),
            settings_obj=self.settings, now=kwargs.get("now", NOW),
        )

    async def test_pairing_code_matches_both_transports_no_user_data(self):
        started = await self.started()
        preview = await self.preview(started)
        browser = await self.browser(started)
        self.assertRegex(preview.pairing_code, r"^[0-9A-F]{8}$")
        self.assertEqual(preview.pairing_code, browser.pairing_code)
        self.assertEqual(browser.status, "pending")
        self.assertFalse(hasattr(browser, "google_subject_hash"))
        self.assertFalse(hasattr(browser, "browser_proof"))

    async def test_approve_once_replay_and_browser_state(self):
        started = await self.started()
        self.assertTrue(await self.decide(started))
        self.assertFalse(await self.decide(started))
        self.assertIsNone(await self.preview(started))
        self.assertEqual((await self.browser(started)).status, "approved")
        row = self.session.execute(select(AdminPwaApproval)).scalar_one()
        self.assertEqual(row.approved_user_id, 1001)

    async def test_deny_is_terminal(self):
        started = await self.started()
        self.assertTrue(await self.decide(started, approve=False))
        self.assertFalse(await self.decide(started))
        self.assertFalse(await self.decide(started, approve=False))
        self.assertEqual((await self.browser(started)).status, "denied")

    async def test_nonadmin_group_foreign_chat_bot_and_forwarded_callback(self):
        started = await self.started()
        bad_events = (
            self.event(9002),
            self.event(9001, chat_type="group"),
            self.event(9001, chat_type="supergroup"),
            self.event(9001, chat_id=9002),
            self.event(9001, chat_id=-1001),
            self.event(9001, is_bot=True),
            self.event(9001, callback=False, chat_type="group"),
            SimpleNamespace(from_user=SimpleNamespace(id=9001)),
        )
        for event in bad_events:
            with self.subTest(event=str(event)[:90]):
                self.assertIsNone(await self.preview(started, event=event))
                self.assertFalse(await self.decide(started, event=event))
        self.assertIsNotNone(await self.preview(started))

    async def test_other_browser_proof_and_invalid_ids(self):
        first = await self.started()
        second = await self.started()
        self.assertIsNone(await self.browser(
            first, browser_proof=second.browser_proof,
        ))
        self.assertIsNone(await self.browser(first, request_id="invalid"))
        self.assertIsNone(await self.preview(first, request_id="invalid"))
        self.assertFalse(await self.decide(first, request_id="invalid"))
        self.assertIsNotNone(await self.browser(first))

    async def test_five_minute_timeout(self):
        started = await self.started()
        now = NOW + timedelta(minutes=5)
        self.assertIsNone(await self.preview(started, now=now))
        self.assertFalse(await self.decide(started, now=now))
        self.assertIsNone(await self.browser(started, now=now))

    async def test_revoked_admin_and_blocked_canonical_user(self):
        started = await self.started()
        self.settings.admin_id_list = []
        self.assertIsNone(await self.preview(started))
        self.assertFalse(await self.decide(started))
        self.settings.admin_id_list = [9001]
        self.session.get(User, 1001).status = "blocked"
        self.session.commit()
        self.assertIsNone(await self.preview(started))
        self.assertFalse(await self.decide(started))

    async def test_provider_collision_prevents_approval(self):
        started = await self.started()
        self.session.add(UserIdentity(
            id=str(uuid4()), user_id=1002, provider="google",
            subject_hash=SUBJECT,
        ))
        self.session.commit()
        self.assertIsNone(await self.preview(started))
        self.assertFalse(await self.decide(started))

    async def test_disabled_feature_denies_bot_and_browser(self):
        started = await self.started()
        self.settings.ADMIN_PWA_ENABLED = False
        self.assertIsNone(await self.preview(started))
        self.assertFalse(await self.decide(started))
        self.assertIsNone(await self.browser(started))

    async def test_wrong_approval_cookie_is_denied(self):
        started = await self.started()
        self.assertIsNone(await self.browser(
            started, browser_proof="x" * 64,
        ))
        self.assertIsNotNone(await self.browser(started))


if __name__ == "__main__":
    unittest.main()
