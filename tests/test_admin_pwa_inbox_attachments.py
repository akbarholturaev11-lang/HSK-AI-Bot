"""Native report JPEG delivery is guarded, retained, and never public."""
import io
import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.admin_api.pwa_inbox_attachments import create_admin_pwa_inbox_attachment_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
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
