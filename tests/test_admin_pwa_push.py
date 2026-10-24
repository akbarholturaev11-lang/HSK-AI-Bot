"""Apple-only encrypted Web Push subscription foundation; no actual dispatch."""
import base64
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from app.admin_api.pwa_push import create_admin_pwa_push_router, _configuration
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class AdminPwaApplePushTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def configure(self):
        self.settings.ADMIN_PWA_PUSH_ENABLED = True
        self.settings.ADMIN_PWA_PUSH_STORAGE_KEY = Fernet.generate_key().decode("ascii")
        curve = ec.generate_private_key(ec.SECP256R1())
        self.settings.ADMIN_PWA_PUSH_VAPID_PUBLIC_KEY = b64(
            curve.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))

    def subscription(self, *, count=1, platform="iphone", endpoint=None):
        device_key = ec.generate_private_key(ec.SECP256R1())
        return {
            "platform":platform,
            "endpoint":endpoint or f"https://web.push.apple.com/synthetic-device-{count}",
            "keys":{
                "p256dh":b64(device_key.public_key().public_bytes(
                    Encoding.X962, PublicFormat.UncompressedPoint)),
                "auth":b64(bytes([count % 256])*16),
            }
        }

    async def post(self, path, body, *, cookie=fixtures.COOKIE, origin="https://hskai.app"):
        app=FastAPI()
        app.include_router(create_admin_pwa_push_router(
            settings_obj=self.settings, session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app),base_url="https://hskai.app",
                               headers={"origin":origin},
                               cookies={ADMIN_PWA_COOKIE_NAME:cookie} if cookie else {}) as client:
            return await client.post("/api/admin/v1/push/"+path,json=body)

    async def test_flag_off_missing_secrets_invalid_origin_and_nonpasskey_fail_closed(self):
        request=self.subscription()
        self.assertEqual((await self.post("subscribe",request)).status_code,404)
        await self.configure()
        self.settings.ADMIN_PWA_PUSH_STORAGE_KEY = ""
        self.assertEqual((await self.post("subscribe",request)).status_code,503)
        self.settings.ADMIN_PWA_PUSH_STORAGE_KEY = Fernet.generate_key().decode("ascii")
        self.assertEqual((await self.post("subscribe",request,origin="https://evil.test")).status_code,403)
        self.assertEqual((await self.post("subscribe",request,cookie=None)).status_code,401)
        self.assertEqual((await self.post("subscribe",request,cookie="A"*64)).status_code,403)
        async with self.sessions() as db:
            await db.execute(update(AdminPwaSession).values(auth_method="google_telegram"))
            await db.commit()
        self.assertEqual((await self.post("subscribe",request)).status_code,403)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushSubscription)),0)

    async def test_private_push_configuration_accepts_valid_staging_https_origin(self):
        await self.configure()
        self.assertIsNotNone(_configuration(self.settings))
        self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://staging.hskai.app"
        self.assertIsNotNone(_configuration(self.settings))
        for invalid in ("http://staging.hskai.app", "https://staging.hskai.app/path",
                        "https://staging.hskai.app:443",
                        "https://attacker@staging.hskai.app", ""):
            self.settings.ADMIN_PWA_PUBLIC_ORIGIN = invalid
            self.assertIsNone(_configuration(self.settings), invalid)

    async def test_encryption_two_apple_devices_revoke_idempotence_and_no_delivery(self):
        await self.configure()
        iphone=self.subscription(count=1, platform="iphone")
        mac=self.subscription(count=2, platform="mac")
        i=await self.post("subscribe",iphone)
        self.assertEqual(i.status_code,200,i.text)
        self.assertFalse(i.json()["sending_enabled"])
        m=await self.post("subscribe",mac)
        self.assertEqual(m.status_code,200,m.text)
        self.assertNotEqual(i.json()["subscription_id"],m.json()["subscription_id"])
        again=await self.post("subscribe",iphone)
        self.assertEqual(again.json()["subscription_id"],i.json()["subscription_id"])
        listing=await self.post("list",{})
        self.assertEqual(listing.status_code,200,listing.text)
        self.assertEqual({v["platform"] for v in listing.json()["subscriptions"]},{"iphone","mac"})
        self.assertFalse(listing.json()["sending_enabled"])
        self.assertNotIn("web.push.apple.com",listing.text)
        self.assertNotIn("p256dh",listing.text)
        self.assertNotIn("auth",listing.text)
        async with self.sessions() as db:
            rows=(await db.scalars(select(AdminPwaPushSubscription))).all()
            self.assertEqual(len(rows),2)
            for row in rows:
                self.assertTrue(row.encrypted_payload.startswith("gAAAA"))
                self.assertNotIn("push.apple.com",row.encrypted_payload)
                self.assertNotIn("p256dh",row.encrypted_payload)
                self.assertEqual(row.endpoint_hash,hashlib.sha256(
                    (iphone if row.platform=="iphone" else mac)["endpoint"].encode()).hexdigest())
        revoked=await self.post("revoke",{"subscription_id":i.json()["subscription_id"]})
        self.assertEqual(revoked.status_code,200,revoked.text)
        self.assertTrue(revoked.json()["revoked"])
        self.assertEqual((await self.post("revoke",{"subscription_id":i.json()["subscription_id"]})).status_code,200)
        self.assertEqual([v["platform"] for v in (await self.post("list",{})).json()["subscriptions"]],["mac"])
        reenroll=await self.post("subscribe",iphone)
        self.assertEqual(reenroll.json()["subscription_id"],i.json()["subscription_id"])
        self.assertEqual(len((await self.post("list",{})).json()["subscriptions"]),2)

    async def test_invalid_target_bad_keys_unknown_fields_and_device_limit(self):
        await self.configure()
        valid=self.subscription()
        bad_targets=[
            "https://evil.example/fake", "http://web.push.apple.com/bad",
            "https://evilpush.apple.com.example/target", "https://web.push.apple.com:443/p",
            "https://attacker@web.push.apple.com/p", "https://web.push.apple.com/p?q=1",
            "https://web.push.apple.com/", "https://127.0.0.1/p",
        ]
        for target in bad_targets:
            self.assertEqual((await self.post("subscribe",valid|{"endpoint":target})).status_code,400,target)
        self.assertEqual((await self.post("subscribe",valid|{"platform":"windows"})).status_code,400)
        self.assertEqual((await self.post("subscribe",valid|{"keys":{"p256dh":"invalid","auth":"invalid"}})).status_code,400)
        self.assertEqual((await self.post("subscribe",valid|{"unexpected":"secret"})).status_code,400)
        self.assertEqual((await self.post("list",{"user_id":1})).status_code,400)
        self.assertEqual((await self.post("revoke",{"subscription_id":"bad"})).status_code,400)
        self.assertEqual((await self.post("revoke",{"subscription_id":str(uuid4())})).status_code,403)
        ids=[]
        for n in range(4):
            response=await self.post("subscribe",self.subscription(count=n+1))
            self.assertEqual(response.status_code,200,response.text)
            ids.append(response.json()["subscription_id"])
        self.assertEqual((await self.post("subscribe",self.subscription(count=5))).status_code,409)
        self.assertEqual((await self.post("revoke",{"subscription_id":ids[0]})).status_code,200)
        self.assertEqual((await self.post("subscribe",self.subscription(count=5))).status_code,200)
        self.assertEqual((await self.post("subscribe",self.subscription(count=1))).status_code,409)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPushSubscription)),5)
