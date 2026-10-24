"""Real SQL receipt privacy and bounded Telegram image IO; synthetic bytes only."""
import hashlib
import io
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from app.admin_api.pwa_payment_receipts import create_admin_pwa_receipt_router, download_receipt_image, _BoundedImage, _MAX_BYTES
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.payment import Payment
from tests import test_admin_pwa_payment_review as fixtures


def png():
    buffer=io.BytesIO()
    Image.new('RGB',(4,4),'white').save(buffer,format='PNG')
    return buffer.getvalue()


class AdminPwaReceiptTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown=fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def get(self, *, cookie=fixtures.COOKIE, fingerprint=None, headers=None, loader=None):
        self.loader=loader or AsyncMock(return_value=(png(),'image/png'))
        app=FastAPI()
        app.include_router(create_admin_pwa_receipt_router(settings_obj=self.settings,
            session_factory=self.sessions,loader=self.loader))
        digest=hashlib.sha256(b'synthetic-receipt').hexdigest() if fingerprint is None else fingerprint
        async with AsyncClient(transport=ASGITransport(app=app),base_url='https://hskai.app',
            cookies={ADMIN_PWA_COOKIE_NAME:cookie} if cookie else {}) as client:
            return await client.get(f'/api/admin/v1/payments/{self.payment_id}/receipt?receipt_sha256={digest}',headers=headers)

    async def test_valid_receipt_private_bytes_without_reference_or_url(self):
        response=await self.get()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.content,png())
        self.assertEqual(response.headers['content-type'],'image/png')
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertNotIn('synthetic-receipt',str(response.headers))
        self.loader.assert_awaited_once_with('synthetic-receipt')

    async def test_anonymous_cross_site_wrong_hash_and_duplicate_denied_before_download(self):
        for kwargs,code in (({'cookie':''},401),({'headers':{'sec-fetch-site':'cross-site'}},403),
            ({'fingerprint':'f'*64},409),({'fingerprint':'f'*64+'&receipt_sha256='+'f'*64},400),
            ({'fingerprint':'bad'},400)):
            response=await self.get(**kwargs)
            self.assertEqual(response.status_code,code,response.text)
            self.loader.assert_not_awaited()
        self.settings.ADMIN_PWA_ENABLED=False
        self.assertEqual((await self.get()).status_code,404)
        self.loader.assert_not_awaited()

    async def test_current_owner_pending_status_and_revocation_required(self):
        for model,change,code in ((Payment,{'payment_status':'approved'},404),
                (Payment,{'user_id':999,'user_telegram_id':None},404),
                (AdminPwaSession,{'revoked_at':datetime.now(timezone.utc)},401)):
            # Orphan fixture is intentional; FK enforcement remains on, so
            # owner removal is represented by a missing legacy transport.
            if change.get('user_id')==999:
                change={'user_id':None,'user_telegram_id':999}
            async with self.sessions() as db:
                row=await db.get(model,self.payment_id if model is Payment else self.session_id)
                previous={key:getattr(row,key) for key in change}
                for key,value in change.items():setattr(row,key,value)
                await db.commit()
            self.assertEqual((await self.get()).status_code,code)
            self.loader.assert_not_awaited()
            async with self.sessions() as db:
                row=await db.get(model,self.payment_id if model is Payment else self.session_id)
                for key,value in previous.items():setattr(row,key,value)
                await db.commit()

    async def test_revocation_or_receipt_replacement_during_download_never_returns_bytes(self):
        async def revoke(_):
            await self.change(AdminPwaSession,revoked_at=datetime.now(timezone.utc))
            return png(),'image/png'
        self.assertEqual((await self.get(loader=revoke)).status_code,401)
        await self.change(AdminPwaSession,revoked_at=None)
        async def replace(_):
            await self.change(Payment,screenshot_file_id='changed-receipt')
            return png(),'image/png'
        self.assertEqual((await self.get(loader=replace)).status_code,409)

    async def test_transport_failure_is_safe_no_provider_details(self):
        response=await self.get(loader=AsyncMock(side_effect=RuntimeError('private-telegram-url')))
        self.assertEqual(response.status_code,503)
        self.assertNotIn('private-telegram-url',response.text)


class AdminPwaImageBoundTests(unittest.IsolatedAsyncioTestCase):
    async def load(self, raw, file_size=None):
        bot=SimpleNamespace(get_file=AsyncMock(return_value=SimpleNamespace(file_path='private/path',file_size=file_size)))
        async def download(_, *, destination, timeout):destination.write(raw)
        bot.download_file=download
        return await download_receipt_image(bot,'private-id')

    async def test_only_verified_supported_image_bytes_accepted(self):
        raw,kind=await self.load(png())
        self.assertEqual((raw,kind),(png(),'image/png'))
        for raw in (b'<svg onload="alert(1)"/>',b'not an image',png()[:16]):
            with self.assertRaises(Exception):await self.load(raw)

    async def test_reported_and_streamed_byte_limits(self):
        with self.assertRaisesRegex(ValueError,'invalid_receipt_file'):
            await self.load(png(),file_size=_MAX_BYTES+1)
        with self.assertRaisesRegex(ValueError,'receipt_too_large'):
            await self.load(b'x'*(_MAX_BYTES+1))
        buffer=_BoundedImage()
        buffer.seek(_MAX_BYTES)
        with self.assertRaises(ValueError):buffer.write(b'x')
