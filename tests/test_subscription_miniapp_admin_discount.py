"""Oddiy obuna sahifasi ham userning faol admin chegirmasini qo'llaydi.

Ilgari admin chegirmasi faqat chegirma xabaridagi tugmadan
(`mode=admin_discount`) ochilganda hisoblanardi: o'sha user «Obuna»
tugmasidan yoki kurs ichidan kirsa to'liq narxni ko'rardi. Endi oddiy
rejimda ham userga mos faol kampaniya referal 20% bilan solishtirilib,
kattasi qo'llanadi va sahifada admin chegirmasi bloki chiqadi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.discount_campaign import DiscountCampaign
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.discount_campaign_repo import DiscountCampaignRepository
from app.services.subscription_miniapp_service import (
    PAYMENT_DETAILS_KEY,
    SubscriptionMiniAppService,
)


SUBSCRIPTION_HTML = Path("app/static/subscription.html").read_text(encoding="utf-8")

PNG_1X1_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
OFFER_TEXT_FIELDS = (
    "title", "title_tj", "title_ru", "title_uz",
    "reason", "reason_tj", "reason_ru", "reason_uz", "details",
)


def _user(telegram_id: int) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=telegram_id,
        full_name="Test User",
        language="tj",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class _BotStub:
    def __init__(self):
        self.photos = []

    async def get_me(self):
        return SimpleNamespace(username="hsk_ai_test_bot")

    async def send_photo(self, **kwargs):
        self.photos.append(kwargs)
        return SimpleNamespace(photo=[SimpleNamespace(file_id="FILE_ID_1")])

    async def send_message(self, **kwargs):
        return SimpleNamespace(message_id=1)


_original_get_by_id = DiscountCampaignRepository.get_by_id


async def _get_by_id_utc(self, campaign_id):
    # Faqat sinov muhiti: SQLite `DateTime(timezone=True)` ni timezone'siz
    # qaytaradi (Postgres timezone bilan), `get_campaign_discount` esa uni
    # `now` bilan solishtiradi.
    campaign = await _original_get_by_id(self, campaign_id)
    if campaign is not None:
        for field in ("starts_at", "ends_at"):
            value = getattr(campaign, field)
            if value is not None and value.tzinfo is None:
                setattr(campaign, field, value.replace(tzinfo=timezone.utc))
    return campaign


class _CheckoutCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.bot = _BotStub()
        async with self.sessions() as session:
            session.add(_user(5001))
            await BotSettingRepository(session).set(PAYMENT_DETAILS_KEY, "DC 4713380023849546")
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _campaign(self, *, target=5001, ends_in=timedelta(days=3), **fields):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            campaign = DiscountCampaign(
                title="Kuzgi chegirma",
                percent=30,
                is_active=True,
                starts_at=now - timedelta(hours=1),
                ends_at=now + ends_in,
                target_telegram_id=target,
                **fields,
            )
            session.add(campaign)
            await session.commit()
            return campaign.id

    async def _overview(self, **kwargs):
        kwargs.setdefault("mode", "subscription")
        async with self.sessions() as session:
            return await SubscriptionMiniAppService(session).overview(5001, **kwargs)


class RegularCheckoutAdminDiscountTests(_CheckoutCase):
    async def test_regular_checkout_applies_the_users_admin_discount(self):
        campaign_id = await self._campaign()

        overview = await self._overview()

        month = overview["prices"]["visa"]["1_month"]
        self.assertTrue(month["discount_applied"])
        self.assertEqual(month["discount_source"], "admin_campaign")
        self.assertLess(month["final_amount"], month["base_amount"])
        offer = overview["offer"]
        self.assertEqual(offer["type"], "admin_discount")
        self.assertTrue(offer["available"])
        self.assertEqual(offer["percent"], 30)
        self.assertEqual(offer["campaign_id"], campaign_id)
        self.assertEqual(offer["title"], "Kuzgi chegirma")

    async def test_offer_text_fields_are_never_null(self):
        # Android bu maydonlarni `String` deb o'qiydi: null kelsa butun
        # overview javobi o'qilmay qoladi. Kampaniyada tarjima yo'q.
        await self._campaign()

        offer = (await self._overview())["offer"]

        for field in OFFER_TEXT_FIELDS:
            with self.subTest(field=field):
                self.assertIsInstance(offer[field], str)

    async def test_quote_and_submit_charge_the_admin_price(self):
        campaign_id = await self._campaign()
        month = (await self._overview())["prices"]["visa"]["1_month"]

        async with self.sessions() as session:
            quote = await SubscriptionMiniAppService(session).quote(
                telegram_id=5001,
                plan_type="1_month",
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
                mode="subscription",
            )
        self.assertEqual(quote["quote"]["final_amount"], month["final_amount"])
        self.assertEqual(quote["quote"]["discount_source"], "admin_campaign")

        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).submit(
                telegram_id=5001,
                plan_type="1_month",
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
                screenshot_data_url=PNG_1X1_DATA_URL,
                bot=self.bot,
                mode="subscription",
            )
        self.assertTrue(result["ok"], result)
        async with self.sessions() as session:
            payment = (await session.execute(select(Payment))).scalar_one()
        self.assertEqual(payment.amount, month["final_amount"])
        self.assertEqual(payment.discount_source, "admin_campaign")
        self.assertEqual(payment.discount_campaign_id, campaign_id)

    async def test_another_users_campaign_is_not_applied(self):
        await self._campaign(target=9999)

        overview = await self._overview()

        month = overview["prices"]["visa"]["1_month"]
        self.assertFalse(month["discount_applied"])
        self.assertEqual(month["final_amount"], month["base_amount"])
        self.assertIsNone(overview["offer"])

    async def test_ended_campaign_is_not_applied(self):
        await self._campaign(ends_in=timedelta(hours=-1))

        overview = await self._overview()

        self.assertFalse(overview["prices"]["visa"]["1_month"]["discount_applied"])
        self.assertIsNone(overview["offer"])

    async def test_card_only_campaign_leaves_china_prices_unchanged(self):
        await self._campaign(payment_method="visa")

        overview = await self._overview()

        self.assertTrue(overview["prices"]["visa"]["1_month"]["discount_applied"])
        self.assertFalse(overview["prices"]["alipay"]["1_month"]["discount_applied"])
        self.assertEqual(overview["offer"]["percent"], 30)


class ExpiredDiscountLinkTests(_CheckoutCase):
    """Chatdagi eski chegirma tugmasi muddat tugagach bosilsa."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        patcher = patch.object(DiscountCampaignRepository, "get_by_id", _get_by_id_utc)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_expired_link_falls_back_to_regular_prices(self):
        campaign_id = await self._campaign(ends_in=timedelta(hours=-1))

        overview = await self._overview(mode="admin_discount", campaign_id=campaign_id)

        # Sahifa bo'sh qolmaydi: oddiy obuna narxlari va «taklif tugagan».
        self.assertEqual(overview["mode"], "subscription")
        self.assertTrue(overview["offer_expired"])
        self.assertIsNone(overview["offer"])
        month = overview["prices"]["visa"]["1_month"]
        self.assertFalse(month["discount_applied"])
        self.assertEqual(month["final_amount"], month["base_amount"])

    async def test_active_link_keeps_the_discount_page(self):
        campaign_id = await self._campaign()

        overview = await self._overview(mode="admin_discount", campaign_id=campaign_id)

        self.assertEqual(overview["mode"], "admin_discount")
        self.assertFalse(overview["offer_expired"])
        self.assertTrue(overview["offer"]["available"])

    async def test_expired_link_does_not_silently_charge_the_full_price(self):
        # To'lov ekranida chegirmali summani ko'rib turgan user uchun so'rov
        # jimgina to'liq narxga o'tkazilmaydi — «taklif tugagan» xatosi.
        campaign_id = await self._campaign(ends_in=timedelta(hours=-1))

        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).submit(
                telegram_id=5001,
                plan_type="1_month",
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
                screenshot_data_url=PNG_1X1_DATA_URL,
                bot=self.bot,
                mode="admin_discount",
                campaign_id=campaign_id,
            )

        self.assertEqual(result, {"ok": False, "error": "payment_invalid_plan"})
        async with self.sessions() as session:
            self.assertEqual((await session.execute(select(Payment))).scalars().all(), [])


class RegularCheckoutAdminDiscountPageTests(unittest.TestCase):
    def test_regular_page_shows_the_admin_offer_instead_of_the_referral_block(self):
        self.assertIn(
            'const adminOffer=state.mode==="admin_discount"||(state.mode!=="feedback_discount"'
            '&&Boolean(offer?.available)&&offer?.type==="admin_discount");',
            SUBSCRIPTION_HTML,
        )
        self.assertIn('if(adminOffer||state.mode==="feedback_discount"){', SUBSCRIPTION_HTML)

    def test_expired_offer_is_explained_at_the_top(self):
        self.assertIn("state.offerExpired=Boolean(data?.offer_expired);", SUBSCRIPTION_HTML)
        self.assertIn("(state.offerExpired?text.offerExpired:\"\")", SUBSCRIPTION_HTML)


if __name__ == "__main__":
    unittest.main()
