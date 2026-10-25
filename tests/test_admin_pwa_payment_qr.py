"""Signed subscription QR replacement keeps billing values and SQL rows small."""
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from sqlalchemy import func, select

from app.admin_api import pwa_payment_qr as qr_api
from app.admin_api.pwa_step_up import begin_step_up, verify_step_up
from app.db.models.admin_pwa_command import AdminPwaCommandAudit
from app.db.models.admin_pwa_step_up import AdminPwaStepUp
from app.db.models.payment import Payment
from app.db.models.payment_qr_code import PaymentQrCode
from app.db.models.subscription_price import SubscriptionPrice
from app.db.models.user import User
from app.services.subscription_price_service import SubscriptionPriceService
from tests import test_admin_pwa_payment_review as fixtures
from tests.test_admin_pwa_webauthn_crypto_vectors import make_assertion


class FakeBot:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.sent = []
        self.deleted = []

    async def send_photo(self, *, chat_id, photo):
        if self.fail:
            raise RuntimeError("synthetic provider failure")
        self.sent.append((chat_id, photo))
        return SimpleNamespace(
            message_id=700 + len(self.sent),
            photo=[SimpleNamespace(file_id=f"synthetic-qr-{len(self.sent)}")],
        )

    async def delete_message(self, *, chat_id, message_id):
        self.deleted.append((chat_id, message_id))


class AdminPwaPaymentQrTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    @staticmethod
    def image_bytes():
        output = BytesIO()
        Image.new("RGB", (320, 180), (12, 98, 120)).save(output, format="PNG")
        return output.getvalue()

    async def prepare(self, *, method="alipay", plan="1_month", image=None):
        data = image or self.image_bytes()
        async with self.sessions() as db:
            result = await qr_api.prepare_payment_qr(
                db, session_cookie=fixtures.COOKIE,
                request=qr_api.PreparePaymentQr(
                    method=method, plan=plan,
                    media_sha256=hashlib.sha256(data).hexdigest(), media_size=len(data),
                ), settings_obj=self.settings,
            )
        return qr_api.PaymentQrCommand.model_validate(result["operation"]["payload"]), data

    async def proof(self, command):
        async with self.sessions() as db:
            started = await begin_step_up(
                db, session_cookie=fixtures.COOKIE, settings_obj=self.settings,
                **command.operation(),
            )
        self.assertIsNotNone(started)
        async with self.sessions() as db:
            step = await db.get(AdminPwaStepUp, started.step_up_id)
            challenge = bytes(step.challenge)
        async with self.sessions() as db:
            self.assertTrue(await verify_step_up(
                db, session_cookie=fixtures.COOKIE, step_up_id=started.step_up_id,
                credential=make_assertion(self.key, challenge=challenge),
                settings_obj=self.settings,
            ))
        return started.step_up_id

    async def execute(self, command, proof, image, bot):
        return await qr_api.execute_payment_qr(
            session_factory=self.sessions, bot_client=bot,
            session_cookie=fixtures.COOKIE,
            request=qr_api.ExecutePaymentQr(**command.model_dump(), step_up_id=proof),
            settings_obj=self.settings, media_bytes=image, media_content_type="image/png",
        )

    async def test_signed_qr_replacement_preserves_price_payment_and_stores_only_file_id(self):
        command, image = await self.prepare()
        proof = await self.proof(command)
        bot = FakeBot()
        result = await self.execute(command, proof, image, bot)

        self.assertEqual(result["qr"]["method"], "alipay")
        self.assertEqual(result["qr"]["plan"], "1_month")
        self.assertEqual((result["qr"]["amount"], result["qr"]["currency"]), (66, "¥"))
        self.assertTrue(result["qr"]["qr_set"])
        self.assertEqual(len(bot.sent), 1)
        async with self.sessions() as db:
            stored = await db.scalar(select(PaymentQrCode))
            self.assertEqual(stored.file_id, "synthetic-qr-1")
            self.assertEqual(stored.created_by_telegram_id, 9001)
            self.assertEqual(await db.scalar(select(func.count()).select_from(SubscriptionPrice)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(PaymentQrCode)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 1)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "consumed")
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")
            self.assertIsNone((await db.get(User, 1)).end_date)
            audit = await db.scalar(select(AdminPwaCommandAudit))
            self.assertEqual((audit.action, audit.target), ("subscription.qr_media", "alipay-1_month"))
            self.assertNotIn("synthetic-qr-1", audit.result_json)

        with self.assertRaisesRegex(qr_api.CommandError, "step_up_denied"):
            await self.execute(command, proof, image, bot)
        self.assertEqual(len(bot.sent), 1)

    async def test_invalid_target_and_oversized_media_are_rejected(self):
        with self.assertRaises(ValueError):
            qr_api.ReadPaymentQr(method="visa", plan="1_month")
        command, image = await self.prepare()
        proof = await self.proof(command)
        bot = FakeBot()
        with self.assertRaisesRegex(qr_api.CommandError, "invalid_media"):
            await qr_api.execute_payment_qr(
                session_factory=self.sessions, bot_client=bot,
                session_cookie=fixtures.COOKIE,
                request=qr_api.ExecutePaymentQr(**command.model_dump(), step_up_id=proof),
                settings_obj=self.settings, media_bytes=image + b"x",
                media_content_type="image/png",
            )
        self.assertEqual(bot.sent, [])
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PaymentQrCode)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")

    async def test_read_hides_telegram_file_ids_and_rejects_legacy_currency_mismatch(self):
        async with self.sessions() as db:
            db.add(PaymentQrCode(
                scope="subscription", payment_method="alipay", plan_type="1_month",
                amount=66, currency="¥", file_id="private-telegram-file-id",
            ))
            await db.commit()
        async with self.sessions() as db:
            current = await qr_api.read_payment_qr(
                db, session_cookie=fixtures.COOKIE,
                request=qr_api.ReadPaymentQr(method="alipay", plan="1_month"),
                settings_obj=self.settings,
            )
        self.assertTrue(current["qr"]["qr_set"])
        self.assertNotIn("private-telegram-file-id", json.dumps(current))
        self.assertNotIn("file_id", current["qr"])

        async with self.sessions() as db:
            db.add(SubscriptionPrice(
                payment_method="wechat", plan_type="1_month", amount=66,
                currency="USD", updated_at=datetime.now(timezone.utc),
            ))
            await db.commit()
        async with self.sessions() as db:
            with self.assertRaisesRegex(qr_api.CommandError, "invalid_payment_qr_target"):
                await qr_api.read_payment_qr(
                    db, session_cookie=fixtures.COOKIE,
                    request=qr_api.ReadPaymentQr(method="wechat", plan="1_month"),
                    settings_obj=self.settings,
                )

    async def test_stale_price_is_rejected_before_provider_upload(self):
        command, image = await self.prepare()
        proof = await self.proof(command)
        async with self.sessions() as db:
            await SubscriptionPriceService(db).set_price(
                payment_method="alipay", plan_type="1_month", amount=67,
            )
            await db.commit()
        bot = FakeBot()
        with self.assertRaisesRegex(qr_api.CommandError, "confirmation_changed"):
            await self.execute(command, proof, image, bot)
        self.assertEqual(bot.sent, [])
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(PaymentQrCode)), 0)

    async def test_provider_failure_does_not_write_or_consume_proof(self):
        command, image = await self.prepare()
        proof = await self.proof(command)
        with self.assertRaisesRegex(qr_api.CommandError, "qr_upload_failed"):
            await self.execute(command, proof, image, FakeBot(fail=True))
        async with self.sessions() as db:
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(PaymentQrCode)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)

    async def test_post_upload_cas_failure_compensates_private_bot_message(self):
        command, image = await self.prepare()
        proof = await self.proof(command)
        bot = FakeBot()
        consume = qr_api.consume_step_up_in_mutation

        async def change_target_after_upload(db, **kwargs):
            allowed = await consume(db, **kwargs)
            if allowed:
                row = await db.scalar(select(SubscriptionPrice).where(
                    SubscriptionPrice.payment_method == "alipay",
                    SubscriptionPrice.plan_type == "1_month",
                ))
                self.assertIsNone(row)
                db.add(SubscriptionPrice(
                    payment_method="alipay", plan_type="1_month", amount=67,
                    currency="¥", updated_at=datetime.now(timezone.utc),
                ))
                await db.flush()
            return allowed

        with patch.object(qr_api, "consume_step_up_in_mutation", change_target_after_upload):
            with self.assertRaisesRegex(qr_api.CommandError, "confirmation_changed"):
                await self.execute(command, proof, image, bot)
        self.assertEqual(len(bot.sent), 1)
        self.assertEqual(bot.deleted, [(9001, 701)])
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(SubscriptionPrice)))
            self.assertEqual(await db.scalar(select(func.count()).select_from(PaymentQrCode)), 0)
            self.assertEqual((await db.get(AdminPwaStepUp, proof)).status, "verified")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaCommandAudit)), 0)


if __name__ == "__main__":
    unittest.main()
