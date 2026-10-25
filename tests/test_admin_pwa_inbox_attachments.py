"""Private source-bound image delivery, current authorization and IO budgets."""
import io
import asyncio
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import event
from unittest.mock import AsyncMock, patch

from app.admin_api.pwa_inbox_attachments import create_admin_pwa_inbox_attachment_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.release_feedback import ReleaseFeedbackCampaign, ReleaseFeedbackResponse
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


def _jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (5, 5), "white").save(buf, format="JPEG")
    return buf.getvalue()


class AdminPwaNativeAttachmentTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def seed(self, *, raw=None, expired=False):
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            row = AdminPwaNativeReport(
                user_id=1, deduplication_key="a" * 64,
                description="Synthetic private report", app_version="qa", screen="course",
                attachment_bytes=_jpeg() if raw is None else raw, notification_state="sent",
                created_at=now-timedelta(days=1), last_attempt_at=now,
                expires_at=now-timedelta(seconds=1) if expired else now+timedelta(days=29),
            )
            db.add(row)
            await db.commit()
            return row.id

    async def get(self, report_id, *, cookie=fixtures.COOKIE, headers=None, suffix=""):
        app=FastAPI()
        app.include_router(create_admin_pwa_inbox_attachment_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="https://hskai.app",
                               cookies={ADMIN_PWA_COOKIE_NAME:cookie} if cookie else {}) as client:
            return await client.get(f"/api/admin/v1/inbox/android/{report_id}/attachment{suffix}",
                                    headers=headers)

    async def test_real_stored_jpeg_is_private_and_never_cached(self):
        row_id=await self.seed()
        response=await self.get(row_id)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.content,_jpeg())
        self.assertEqual(response.headers["content-type"],"image/jpeg")
        self.assertEqual(response.headers["cache-control"],"no-store")
        self.assertEqual(response.headers["x-content-type-options"],"nosniff")
        self.assertEqual(response.headers["content-disposition"],"inline")
        self.assertNotIn("Synthetic private report",str(response.headers))
        self.assertNotIn("telegram",str(response.headers).lower())

    async def test_cookie_privilege_cross_site_and_flags_are_required(self):
        row_id=await self.seed()
        self.assertEqual((await self.get(row_id,cookie="")).status_code,401)
        self.assertEqual((await self.get(row_id,cookie="forged")).status_code,401)
        self.assertEqual((await self.get(row_id,headers={"sec-fetch-site":"cross-site"})).status_code,403)
        self.assertEqual((await self.get(row_id,headers={"sec-fetch-site":"same-site"})).status_code,403)
        self.assertEqual((await self.get(row_id,headers={"origin":"https://attacker.example"})).status_code,403)
        self.assertEqual((await self.get(row_id,suffix="?raw=true")).status_code,400)
        self.settings.ADMIN_PWA_ENABLED=False
        self.assertEqual((await self.get(row_id)).status_code,404)
        self.assertEqual((await self.get("{report_id}")).status_code,404)
        self.settings.ADMIN_PWA_ENABLED=True
        self.assertEqual((await self.get("{report_id}")).status_code,400)

    async def test_current_passkey_session_and_allowlist_rechecked(self):
        row_id=await self.seed()
        async with self.sessions() as db:
            record=await db.get(AdminPwaSession,self.session_id)
            record.auth_method="google_telegram"
            await db.commit()
        self.assertEqual((await self.get(row_id)).status_code,403)
        async with self.sessions() as db:
            record=await db.get(AdminPwaSession,self.session_id)
            record.auth_method="webauthn"
            await db.commit()
        self.settings.admin_id_list=[]
        self.assertEqual((await self.get(row_id)).status_code,401)

    async def test_absent_expired_and_malformed_images_denied(self):
        row_id=await self.seed()
        self.assertEqual((await self.get(row_id+100)).status_code,404)
        self.assertEqual((await self.get(0)).status_code,400)
        self.assertEqual((await self.get(2_147_483_648)).status_code,400)
        async with self.sessions() as db:
            record=await db.get(AdminPwaNativeReport,row_id)
            record.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
            await db.commit()
        self.assertEqual((await self.get(row_id)).status_code,404)
        async with self.sessions() as db:
            record=await db.get(AdminPwaNativeReport,row_id)
            record.expires_at=datetime.now(timezone.utc)+timedelta(days=1)
            record.attachment_bytes=b"\xff\xd8\xffnot-a-real-jpeg"
            await db.commit()
        self.assertEqual((await self.get(row_id)).status_code,404)


class AdminPwaTelegramAttachmentTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.AdminPwaPaymentReviewTests.asyncSetUp(self)
        now = datetime.now(timezone.utc)
        async with self.sessions() as db:
            (await db.get(User, 1)).telegram_id = 1001
            db.add_all([ReleaseFeedbackCampaign(id=i, title="Synthetic campaign", send_at=now) for i in (1, 2)])
            await db.flush()
            bot = BotFeedback(user_id=1, telegram_id=1001, status="completed",
                disliked_attachment_file_id="private-bot-image", disliked_attachment_type="photo")
            release = ReleaseFeedbackResponse(campaign_id=1, user_telegram_id=1001, rating=5,
                attachment_file_id="private-release-image", attachment_type="document")
            db.add_all([bot, release]);await db.commit()
            self.ids = {"bot": bot.id, "release": release.id}
        self.loader = AsyncMock(return_value=(_jpeg(), "image/jpeg"))
        self.app = self.make_app(self.sessions)

    def make_app(self, sessions):
        app = FastAPI()
        app.include_router(create_admin_pwa_inbox_attachment_router(
            settings_obj=self.settings, session_factory=sessions, loader=self.loader))
        return app

    async def get(self, source="bot", item_id=None, *, cookie=fixtures.COOKIE, headers=None, suffix=""):
        key = self.ids.get(source, 1) if item_id is None else item_id
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url="https://hskai.app",
            cookies={ADMIN_PWA_COOKIE_NAME: cookie} if cookie else {}) as client:
            return await client.get(f"/api/admin/v1/inbox/{source}/{key}/attachment{suffix}", headers=headers)

    async def source_change(self, source, **values):
        model = BotFeedback if source == "bot" else ReleaseFeedbackResponse
        async with self.sessions() as db:
            row = await db.get(model, self.ids[source])
            for key, value in values.items():setattr(row, key, value)
            await db.commit()

    async def test_private_source_bound_images_have_no_provider_references(self):
        self.assertEqual(self.ids["bot"], self.ids["release"])
        for source in ("bot", "release"):
            self.loader.reset_mock()
            response = await self.get(source)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.content, _jpeg())
            self.assertEqual(response.headers["content-type"], "image/jpeg")
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.headers["content-disposition"], "inline")
            self.assertNotIn("private-", str(response.headers))
            self.loader.assert_awaited_once_with(f"private-{source}-image")

    async def test_cookie_origin_source_and_flag_fail_closed_before_provider_io(self):
        cases = [({"cookie": ""}, 401), ({"cookie": "forged"}, 401),
            ({"cookie": "", "headers": {"authorization": "Bearer forged"}}, 401),
            ({"headers": {"sec-fetch-site": "cross-site"}}, 403),
            ({"headers": {"sec-fetch-site": "same-site"}}, 403),
            ({"headers": {"origin": "https://attacker.example"}}, 403),
            ({"suffix": "?file_id=private-bot-image"}, 400)]
        for source in ("bot", "release"):
            for kwargs, status in cases:
                self.assertEqual((await self.get(source, **kwargs)).status_code, status)
            for key in ("{item_id}", "0", "2147483648", "-1", "１２"):
                self.assertEqual((await self.get(source, key)).status_code, 400)
        self.assertEqual((await self.get("payment")).status_code, 404)
        self.loader.assert_not_awaited()
        self.settings.ADMIN_PWA_ENABLED = False
        for source in ("bot", "release", "{source}"):
            self.assertEqual((await self.get(source, "{item_id}")).status_code, 404)
        self.loader.assert_not_awaited()

    async def test_passkey_current_admin_and_source_ownership_are_required(self):
        await self.change(AdminPwaSession, auth_method="google_telegram")
        self.assertEqual((await self.get()).status_code, 403)
        await self.change(AdminPwaSession, auth_method="webauthn")
        await self.source_change("bot", user_id=999)
        await self.source_change("release", user_telegram_id=9999)
        self.assertEqual((await self.get("bot")).status_code, 404)
        self.assertEqual((await self.get("release")).status_code, 404)
        self.settings.admin_id_list = []
        self.assertEqual((await self.get()).status_code, 401)
        self.loader.assert_not_awaited()

    async def test_canonical_bot_owner_does_not_fall_back_to_telegram_metadata(self):
        await self.source_change("bot", telegram_id=2002)
        self.assertEqual((await self.get()).status_code, 200)
        await self.source_change("bot", user_id=999, telegram_id=1001)
        self.loader.reset_mock()
        self.assertEqual((await self.get()).status_code, 404)
        self.loader.assert_not_awaited()

    async def test_missing_and_nonimage_source_types_never_download(self):
        for source, field in (("bot", "disliked_attachment_type"), ("release", "attachment_type")):
            for kind in ("voice", "video", "text", None):
                await self.source_change(source, **{field: kind})
                self.assertEqual((await self.get(source)).status_code, 404)
            self.assertEqual((await self.get(source, 999)).status_code, 404)
        self.loader.assert_not_awaited()

    async def test_reference_owner_or_campaign_change_during_io_rejects_old_bytes(self):
        for source, values in (("bot", {"disliked_attachment_file_id": "replacement"}),
                ("bot", {"user_id": 2}), ("release", {"attachment_file_id": "replacement"}),
                ("release", {"user_telegram_id": 2002}), ("release", {"campaign_id": 2})):
            model = BotFeedback if source == "bot" else ReleaseFeedbackResponse
            async with self.sessions() as db:
                row = await db.get(model, self.ids[source])
                old = {key: getattr(row, key) for key in values}
            async def replace(_):
                await self.source_change(source, **values)
                return _jpeg(), "image/jpeg"
            self.loader.side_effect = replace
            self.assertEqual((await self.get(source)).status_code, 409)
            await self.source_change(source, **old)

    async def test_revoke_block_expiry_and_rollout_change_during_io_deny_bytes(self):
        async def revoke(_):
            await self.change(AdminPwaSession, revoked_at=datetime.now(timezone.utc))
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = revoke
        self.assertEqual((await self.get()).status_code, 401)
        await self.change(AdminPwaSession, revoked_at=None)
        async def expire(_):
            await self.change(AdminPwaSession, expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = expire
        self.assertEqual((await self.get()).status_code, 401)
        await self.change(AdminPwaSession, expires_at=datetime.now(timezone.utc)+timedelta(hours=1))
        async def block(_):
            async with self.sessions() as db:
                (await db.get(User, 101)).status = "BLOCKED"
                await db.commit()
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = block
        self.assertEqual((await self.get()).status_code, 401)
        async with self.sessions() as db:
            (await db.get(User, 101)).status = "active"
            await db.commit()
        async def disable(_):
            self.settings.ADMIN_PWA_ENABLED = False
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = disable
        self.assertEqual((await self.get()).status_code, 404)

    async def test_raw_bytes_media_type_and_size_are_independently_verified(self):
        for raw, kind in ((b"<svg onload='alert(1)'/>", "image/jpeg"), (_jpeg(), "image/png"),
                (b"x"*(8*1024*1024+1), "image/jpeg"), (b"invalid", None), (b"", "image/jpeg")):
            self.loader.return_value = (raw, kind)
            self.assertEqual((await self.get()).status_code, 404)
        for format, kind in (("PNG", "image/png"), ("WEBP", "image/webp")):
            raw = io.BytesIO();Image.new("RGB", (6, 6), "white").save(raw, format=format)
            self.loader.return_value = (raw.getvalue(), kind)
            self.assertEqual((await self.get("release")).status_code, 200)

    async def test_deleted_source_or_rebound_admin_during_io_denies_old_bytes(self):
        for source in ("bot", "release"):
            model = BotFeedback if source == "bot" else ReleaseFeedbackResponse
            async def remove(_):
                async with self.sessions() as db:
                    await db.delete(await db.get(model, self.ids[source]))
                    await db.commit()
                return _jpeg(), "image/jpeg"
            self.loader.side_effect = remove
            self.assertEqual((await self.get(source)).status_code, 404)

    async def test_another_current_admin_cannot_receive_an_old_actors_download(self):
        self.settings.admin_id_list = [9001, 2002]
        async def rebound(_):
            await self.change(AdminPwaSession, user_id=2)
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = rebound
        self.assertEqual((await self.get()).status_code, 409)

    async def test_provider_failures_and_timeout_are_private_and_release_capacity(self):
        self.loader.side_effect = RuntimeError("private-telegram-url-and-token")
        response = await self.get()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-telegram", response.text)
        async def slow(_):await asyncio.sleep(30)
        self.loader.side_effect = slow
        with patch("app.admin_api.pwa_inbox_attachments._DOWNLOAD_TIMEOUT", .01):
            self.assertEqual((await self.get()).status_code, 503)
        self.loader.side_effect = None
        self.assertEqual((await self.get()).status_code, 200)

    async def test_minute_budget_is_shared_across_sources_without_db_writes(self):
        with patch("app.admin_api.pwa_inbox_attachments._DOWNLOADS_PER_MINUTE", 2):
            self.assertEqual((await self.get("bot")).status_code, 200)
            self.assertEqual((await self.get("release")).status_code, 200)
            response = await self.get("bot")
            self.assertEqual(response.status_code, 429)
            self.assertTrue(1 <= int(response.headers["retry-after"]) <= 60)
            self.assertEqual(self.loader.await_count, 2)

    async def test_concurrent_provider_loads_are_bounded_per_router(self):
        entered = 0
        started, release = asyncio.Event(), asyncio.Event()
        async def hold(_):
            nonlocal entered
            entered += 1
            if entered == 2:started.set()
            await release.wait()
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = hold
        tasks = [asyncio.create_task(self.get()) for _ in range(2)]
        try:
            await asyncio.wait_for(started.wait(), 5)
            response = await self.get("release")
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers["retry-after"], "1")
            self.assertEqual(entered, 2)
        finally:
            release.set()
            results = await asyncio.gather(*tasks)
        self.assertTrue(all(row.status_code == 200 for row in results))

    async def test_db_phases_are_read_only_and_closed_during_download(self):
        active, statements = [], []
        @asynccontextmanager
        async def tracked_sessions():
            async with self.sessions() as db:
                active.append(db)
                try:yield db
                finally:active.remove(db)
        async def download(_):
            self.assertFalse(active)
            return _jpeg(), "image/jpeg"
        self.loader.side_effect = download
        self.app = self.make_app(tracked_sessions)
        def record(_conn, _cursor, statement, *_args):statements.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", record)
        try:
            self.assertEqual((await self.get()).status_code, 200)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", record)
        self.assertTrue(statements)
        self.assertTrue(all(sql.lstrip().upper().startswith("SELECT") for sql in statements), statements)
        self.assertTrue(any("FROM bot_feedbacks" in sql for sql in statements))
        self.assertFalse(any("bot_feedbacks.disliked_text" in sql for sql in statements))
