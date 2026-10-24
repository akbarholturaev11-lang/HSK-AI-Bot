"""Apple Web Push worker security/recovery with mocked provider, no live APNs."""
import base64
import unittest
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from app.db.models.admin_pwa_push import AdminPwaPushSubscription
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.services.admin_pwa_push_dispatch import dispatch_batch, sender_config
from tests.test_admin_pwa_push_outbox import AdminPwaPushOutboxTests


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class AdminPwaAppleDeliveryTests(AdminPwaPushOutboxTests):
    """Inherits prior atomic enqueue and per-device subscription coverage."""

    async def enable_sender(self):
        await self.configure()
        private = ec.generate_private_key(ec.SECP256R1())
        self.settings.ADMIN_PWA_PUSH_VAPID_PUBLIC_KEY = b64(
            private.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
        self.settings.ADMIN_PWA_PUSH_VAPID_PRIVATE_KEY = b64(
            private.private_numbers().private_value.to_bytes(32, "big"))
        self.settings.ADMIN_PWA_PUSH_VAPID_SUBJECT = "mailto:ops@example.com"
        self.settings.ADMIN_PWA_PUSH_SEND_ENABLED = True

    async def test_real_pywebpush_encrypts_and_signs_without_network(self):
        """Exercise the pinned encoder/VAPID integration, not just a fake sender."""
        from types import SimpleNamespace
        from unittest.mock import patch
        from app.services.admin_pwa_push_dispatch import _webpush

        await self.enable_sender()
        receiver = ec.generate_private_key(ec.SECP256R1())
        subscription = {
            "endpoint": "https://web.push.apple.com/isolated-no-network",
            "keys": {
                "p256dh": b64(receiver.public_key().public_bytes(
                    Encoding.X962, PublicFormat.UncompressedPoint)),
                "auth": b64(bytes(range(16))),
            },
        }
        captured = []
        def intercept_post(url, *args, **kwargs):
            captured.append((url, kwargs))
            return SimpleNamespace(status_code=201)

        # pywebpush performs RFC 8291 encryption and VAPID signing, then
        # reaches this intercepted HTTP boundary; no provider request occurs.
        with patch("requests.post", side_effect=intercept_post):
            code = await _webpush(
                subscription,
                self.settings.ADMIN_PWA_PUSH_VAPID_PRIVATE_KEY,
                self.settings.ADMIN_PWA_PUSH_VAPID_SUBJECT,
            )
        self.assertEqual(code, 201)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], subscription["endpoint"])
        opts = captured[0][1]
        headers = {str(key).lower(): str(value) for key, value in opts["headers"].items()}
        self.assertEqual(headers.get("content-encoding"), "aes128gcm")
        self.assertEqual(headers.get("ttl"), "180")
        self.assertTrue(headers.get("authorization", "").lower().startswith("vapid "))
        self.assertIsInstance(opts["data"], bytes)
        self.assertNotIn(b"important", opts["data"])

    async def test_disabled_or_wrong_key_never_claims_or_sends(self):
        await self.configure()
        device = await self.post("subscribe", self.subscription(count=1))
        self.assertEqual(device.status_code, 200, device.text)
        row_id = await self.bot_source()
        self.assertEqual((await self.triage(row_id=row_id, revision=0)).status_code, 200)
        called = []
        async def fake(*a):
            called.append(a)
            return 201
        self.assertIsNone(sender_config(self.settings))
        self.assertFalse((await dispatch_batch(self.sessions, settings_obj=self.settings,
                                               sender=fake))["enabled"])
        self.settings.ADMIN_PWA_PUSH_SEND_ENABLED = True
        self.assertFalse((await dispatch_batch(self.sessions, settings_obj=self.settings,
                                               sender=fake))["enabled"])
        self.assertEqual(called, [])
        async with self.sessions() as db:
            row = (await db.scalars(select(AdminPwaPushOutbox))).one()
            self.assertEqual((row.state, row.attempts), ("pending", 0))

    async def test_two_apple_devices_delivery_is_generic_at_most_once_per_outbox(self):
        await self.enable_sender()
        i = await self.post("subscribe", self.subscription(count=1, platform="iphone"))
        m = await self.post("subscribe", self.subscription(count=2, platform="mac"))
        self.assertEqual(i.status_code, 200)
        self.assertEqual(m.status_code, 200)
        row_id = await self.bot_source()
        self.assertEqual((await self.triage(row_id=row_id, revision=0)).status_code, 200)
        sent = []
        async def fake(payload, key, subject):
            sent.append((payload, key, subject))
            return 201
        result = await dispatch_batch(self.sessions, settings_obj=self.settings, limit=10, sender=fake)
        self.assertEqual(result["accepted"], 2, result)
        self.assertEqual(result["claimed"], 2, result)
        self.assertEqual({p["endpoint"] for p,_,_ in sent}, {
            "https://web.push.apple.com/synthetic-device-1",
            "https://web.push.apple.com/synthetic-device-2",
        })
        self.assertTrue(all(key == self.settings.ADMIN_PWA_PUSH_VAPID_PRIVATE_KEY for _, key, _ in sent))
        self.assertTrue(all(subject == "mailto:ops@example.com" for _, _, subject in sent))
        self.assertNotIn("Student", str(result))
        self.assertNotIn("Student", str(sent))
        self.assertEqual((await dispatch_batch(self.sessions, settings_obj=self.settings,
                                               sender=fake))["claimed"], 0)
        async with self.sessions() as db:
            events = (await db.scalars(select(AdminPwaPushOutbox))).all()
            self.assertEqual({(r.state, r.attempts) for r in events}, {("accepted",1)})

    async def test_410_retires_only_stale_device_and_preserves_mac(self):
        await self.enable_sender()
        i=(await self.post("subscribe",self.subscription(count=1,platform="iphone"))).json()
        m=(await self.post("subscribe",self.subscription(count=2,platform="mac"))).json()
        row_id=await self.bot_source()
        await self.triage(row_id=row_id,revision=0)
        async def provider(subscription,*_):
            return 410 if subscription["endpoint"].endswith("device-1") else 201
        out=await dispatch_batch(self.sessions,settings_obj=self.settings,limit=10,sender=provider)
        self.assertEqual(out["accepted"],1,out)
        self.assertEqual(out["dead"],1,out)
        active=(await self.post("list",{})).json()["subscriptions"]
        self.assertEqual([r["id"] for r in active],[m["subscription_id"]])
        async with self.sessions() as db:
            iphone=await db.get(AdminPwaPushSubscription,i["subscription_id"])
            self.assertIsNotNone(iphone.revoked_at)

    async def test_timeout_retries_bounded_and_not_in_the_same_batch(self):
        await self.enable_sender()
        self.assertEqual((await self.post("subscribe",self.subscription(count=4))).status_code,200)
        row_id=await self.bot_source()
        await self.triage(row_id=row_id,revision=0)
        called=[]
        async def timeout(*_):
            called.append(True)
            raise TimeoutError("private endpoint hidden")
        out=await dispatch_batch(self.sessions,settings_obj=self.settings,limit=10,sender=timeout)
        self.assertEqual(out["retry"],1,out)
        self.assertEqual(len(called),1)
        again=await dispatch_batch(self.sessions,settings_obj=self.settings,limit=10,sender=timeout)
        self.assertEqual(again["claimed"],0,again)
        async with self.sessions() as db:
            entry=(await db.scalars(select(AdminPwaPushOutbox))).one()
            self.assertEqual(entry.attempts,1)
            self.assertIsNotNone(entry.next_attempt_at)
            self.assertEqual(entry.state,"retry")

    async def test_no_push_for_non_actionable_or_cancelled_source(self):
        await self.enable_sender()
        self.assertEqual((await self.post("subscribe",self.subscription(count=5))).status_code,200)
        row_id=await self.bot_source()
        await self.triage(row_id=row_id,revision=0)
        self.assertEqual((await self.triage(row_id=row_id,revision=1,
                                            operation="clear_important")).status_code,200)
        called=[]
        async def provider(*_):
            called.append(1)
            return 201
        out=await dispatch_batch(self.sessions,settings_obj=self.settings,sender=provider)
        self.assertEqual(out["claimed"],0,out)
        self.assertEqual(called,[])
        async with self.sessions() as db:
            entry=(await db.scalars(select(AdminPwaPushOutbox))).one()
            self.assertEqual(entry.state,"cancelled")
