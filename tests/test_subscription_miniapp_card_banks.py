"""Obuna Mini App: region → tarif → (to'lov turi) → rekvizit.

User avval karta regionini tanlaydi. Tojikistonda ikki bank bor — Dushanbe
City va Alif, har biri admin panelda o'z rekviziti bilan. Rossiya, O'zbekiston
va boshqa davlat kartalari doim Alif (Visa) rekvizitiga to'laydi. Bank
yubormagan klient (Android, desktop) eski yagona Dushanbe City rekvizitida
qoladi.
"""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.admin_notify_service import AdminNotifyService
from app.services.subscription_miniapp_service import (
    PAYMENT_DETAILS_ALIF_KEY,
    PAYMENT_DETAILS_KEY,
    SubscriptionMiniAppService,
)


SUBSCRIPTION_HTML = Path("app/static/subscription.html").read_text(encoding="utf-8")
ADMIN_HTML = Path("app/static/admin.html").read_text(encoding="utf-8")

PNG_1X1_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
DC_DETAILS = "DC CITY 4713380023849546\nDC HOLDER"
ALIF_DETAILS = "ALIF VISA 4444555566667777\nALIF HOLDER"


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


class CardBankRequisitesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.bot = _BotStub()
        async with self.sessions() as session:
            session.add(_user(5001))
            await BotSettingRepository(session).set(PAYMENT_DETAILS_KEY, DC_DETAILS)
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _set_alif(self, value: str = ALIF_DETAILS):
        async with self.sessions() as session:
            await BotSettingRepository(session).set(PAYMENT_DETAILS_ALIF_KEY, value)
            await session.commit()

    async def _quote(self, card_country, card_bank=None):
        async with self.sessions() as session:
            return await SubscriptionMiniAppService(session).quote(
                telegram_id=5001,
                plan_type="1_month",
                payment_method="visa",
                card_country=card_country,
                card_bank=card_bank,
                mode="subscription",
            )

    async def test_tajik_card_pays_to_the_bank_the_user_chose(self):
        await self._set_alif()

        dc_city = await self._quote("tj", "dc_city")
        alif = await self._quote("tj", "alif")

        self.assertEqual(dc_city["quote"]["payment_details"], DC_DETAILS)
        self.assertEqual(dc_city["quote"]["card_bank"], "dc_city")
        self.assertEqual(alif["quote"]["payment_details"], ALIF_DETAILS)
        self.assertEqual(alif["quote"]["card_bank"], "alif")

    async def test_foreign_cards_always_pay_to_alif(self):
        await self._set_alif()

        for country in ("ru", "uz", "other"):
            with self.subTest(country=country):
                # Mini App boshqa bank yuborsa ham server Alif'ni tanlaydi.
                result = await self._quote(country, "dc_city")
                self.assertEqual(result["quote"]["payment_details"], ALIF_DETAILS)
                self.assertEqual(result["quote"]["card_bank"], "alif")

    async def test_missing_alif_requisites_never_fall_back_to_dc_city(self):
        # Alif kiritilmagan bo'lsa user boshqa bankka pul o'tkazib yubormasin.
        result = await self._quote("ru", "alif")

        self.assertEqual(result, {"ok": False, "error": "payment_details_missing"})

    async def test_clients_that_send_no_bank_keep_the_old_requisites(self):
        # Android va desktop hali bank yubormaydi — ular o'zgarmasligi kerak.
        await self._set_alif()

        result = await self._quote("ru")

        self.assertEqual(result["quote"]["payment_details"], DC_DETAILS)
        self.assertIsNone(result["quote"]["card_bank"])

    async def test_admin_sees_which_bank_received_the_money(self):
        await self._set_alif()

        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).submit(
                telegram_id=5001,
                plan_type="1_month",
                payment_method="visa",
                card_country="uz",
                card_bank="alif",
                screenshot_data_url=PNG_1X1_DATA_URL,
                bot=self.bot,
                mode="subscription",
            )

        self.assertTrue(result["ok"], result)
        self.assertEqual(len(self.bot.photos), 1)
        self.assertIn("🏦 Rekvizit: Alif", self.bot.photos[0]["caption"])

    async def test_plan_prices_come_in_each_region_currency(self):
        async with self.sessions() as session:
            overview = await SubscriptionMiniAppService(session).overview(5001, mode="subscription")

        card_prices = overview["card_prices"]
        self.assertEqual(set(card_prices), {"uz", "ru", "other"})
        currencies = {"uz": "UZS", "ru": "RUB", "other": "USD"}
        for country, currency in currencies.items():
            with self.subTest(country=country):
                self.assertEqual(
                    set(card_prices[country]), {"10_days", "1_month", "3_months"}
                )
                month = card_prices[country]["1_month"]
                self.assertEqual(month["currency"], currency)
                # Tarif ekranidagi narx to'lov ekranidagi summa bilan bir xil.
                quote = await self._quote(country)
                self.assertEqual(month["final_amount"], quote["quote"]["pay_amount"])


class AdminNotifyBankLineTests(unittest.TestCase):
    def _text(self, **kwargs):
        return AdminNotifyService().build_payment_review_text(
            lang="uz",
            telegram_id=5001,
            full_name="Test",
            plan_type="1_month",
            amount=89,
            currency="TJS",
            payment_id=1,
            payment_method="visa",
            card_country="tj",
            local_amount="89",
            local_currency="TJS",
            source="miniapp",
            **kwargs,
        )

    def test_bank_line_appears_only_when_the_bank_is_known(self):
        self.assertIn("🏦 Rekvizit: Dushanbe City", self._text(card_bank="dc_city"))
        self.assertNotIn("Rekvizit:", self._text())


class RegionFlowCopyTests(unittest.TestCase):
    def test_region_comes_first_and_only_tj_and_china_ask_for_a_payment_type(self):
        self.assertIn('const REGION_ORDER=["tj","uz","ru","cn","other"];', SUBSCRIPTION_HTML)
        self.assertIn('function hasMethodStep(){return state.region==="tj"||state.region==="cn"}', SUBSCRIPTION_HTML)
        self.assertIn('["country","plans","method","pay"]:["country","plans","pay"]', SUBSCRIPTION_HTML)

    def test_quote_and_submit_send_the_chosen_bank(self):
        self.assertEqual(
            SUBSCRIPTION_HTML.count('card_bank:state.method==="visa"?cardBank():null'), 2
        )
        self.assertIn('function cardBank(){return state.country==="tj"?state.bank:"alif"}', SUBSCRIPTION_HTML)

    def test_new_copy_exists_in_all_three_languages(self):
        # `\n      alif:"` — cardHints ichidagi Alif yo'riqnomasi.
        for needle in ('cn:["', 'dc_city:["', 'alif:["', '\n      alif:"'):
            with self.subTest(needle=needle):
                self.assertEqual(SUBSCRIPTION_HTML.count(needle), 3)

    def test_bank_instructions_name_the_app_button_in_all_three_languages(self):
        # Tugma nomi ilovadagidek: Dushanbe City — «DC (по номеру карты)»,
        # Alif — «На карту».
        self.assertEqual(SUBSCRIPTION_HTML.count("«DC (по номеру карты)»"), 3)
        self.assertEqual(SUBSCRIPTION_HTML.count("«На карту»"), 3)

    def test_admin_panel_edits_both_requisites(self):
        self.assertIn('id="payDetails"', ADMIN_HTML)
        self.assertIn('id="payDetailsAlif"', ADMIN_HTML)
        self.assertIn('data-pdsave data-bank="alif"', ADMIN_HTML)


if __name__ == "__main__":
    unittest.main()
