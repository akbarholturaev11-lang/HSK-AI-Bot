"""Obuna Mini App to'lov so'rovi: xato yo'li ham aytarli bo'lsin.

2026-09-22 da foydalanuvchi screenshot yuborganda faqat «Хатогӣ шуд. Боз
кӯшиш кунед.» ko'rdi. Sabab: submit yo'lidagi TURLI nosozliklar (server
xatosi, yaroqsiz rasm, bloklangan hisob, gateway HTML javobi) bitta umumiy
matnga aylanardi va serverda hech qanday log qolmasdi — ya'ni «obuna yo'li
ishlamayapti» degan xabardan keyin sababni topib bo'lmasdi.

Bu test o'sha bo'shliqni yopadi: har bir sabab o'z kodini qaytaradi,
kutilmagan istisno 500 HTML emas, JSON kod bo'lib qaytadi, va Mini App
uchala tilda aniq matn ko'rsatadi.
"""

import base64
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.support_contact_service import ADMIN_CONTACT_KEY
from app.services.subscription_miniapp_service import (
    MAX_SCREENSHOT_BYTES,
    PAYMENT_DETAILS_KEY,
    SubscriptionMiniAppService,
)


SUBSCRIPTION_HTML = Path("app/static/subscription.html").read_text(encoding="utf-8")

PNG_1X1_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _user(user_id: int, telegram_id: int) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
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


class SubscriptionMiniAppSubmitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.bot = _BotStub()
        async with self.sessions() as session:
            session.add(_user(1, 5001))
            await BotSettingRepository(session).set(
                PAYMENT_DETAILS_KEY, "4713380023849546\nTEST HOLDER"
            )
            await session.commit()
        self.funnel_patch = patch(
            "app.services.conversion_funnel_service.async_session_maker",
            self.sessions,
        )
        self.funnel_patch.start()

    async def asyncTearDown(self):
        self.funnel_patch.stop()
        await self.engine.dispose()

    async def _submit(self, screenshot_data_url: str):
        async with self.sessions() as session:
            return await SubscriptionMiniAppService(session).submit(
                telegram_id=5001,
                plan_type="1_month",
                payment_method="visa",
                card_country="tj",
                screenshot_data_url=screenshot_data_url,
                bot=self.bot,
                mode="subscription",
            )

    async def test_card_screenshot_reaches_the_admin_review_queue(self):
        result = await self._submit(PNG_1X1_DATA_URL)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(len(self.bot.photos), 1)
        async with self.sessions() as session:
            payment = (await session.execute(select(Payment))).scalar_one()
        self.assertEqual(payment.payment_status, "pending")
        self.assertEqual(payment.screenshot_file_id, "FILE_ID_1")

    async def test_unsupported_image_format_is_reported_as_invalid_screenshot(self):
        # iPhone HEIC yoki brauzer ocholmagan format shu yo'l bilan keladi.
        result = await self._submit("data:image/heic;base64," + base64.b64encode(b"x" * 64).decode())

        # `reason` Mini App uchun: format muammosi hajm muammosidan farq qiladi.
        self.assertEqual(
            result, {"ok": False, "error": "invalid_screenshot", "reason": "format"}
        )
        self.assertEqual(self.bot.photos, [])

    async def test_oversized_screenshot_is_rejected_without_creating_a_payment(self):
        oversized = "data:image/jpeg;base64," + base64.b64encode(
            b"\xff" * (MAX_SCREENSHOT_BYTES + 1024)
        ).decode()

        result = await self._submit(oversized)

        self.assertEqual(
            result, {"ok": False, "error": "invalid_screenshot", "reason": "too_big"}
        )
        async with self.sessions() as session:
            payments = (await session.execute(select(Payment))).scalars().all()
        self.assertEqual(payments, [])


class SubscriptionMiniAppSubmitEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Kutilmagan istisno HTML 500 emas, JSON kod bo'lib qaytsin.

    Mini App javobni `response.json()` bilan o'qiydi: HTML sahifa kelsa u
    `bad_json` ga tushib, foydalanuvchiga umumiy «Xatolik» ko'rsatardi va
    serverda ham iz qolmasdi.
    """

    # aiogram faqat tokenning SHAKLINI tekshiradi; haqiqiy token kerak emas.
    FAKE_TOKEN = "123456789:AAEhBOweik6ad9r_QXWnRVhTLNRHYlBBBBB"

    @classmethod
    def _init_data(cls, telegram_id: int) -> str:
        import hashlib
        import hmac
        from urllib.parse import urlencode

        params = {"auth_date": "1", "user": '{"id": %d}' % telegram_id}
        check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
        secret = hmac.new(b"WebAppData", cls.FAKE_TOKEN.encode(), hashlib.sha256).digest()
        params["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        return urlencode(params)

    async def asyncSetUp(self):
        from app.config import settings

        with patch.object(settings, "BOT_TOKEN", self.FAKE_TOKEN), patch.object(
            settings, "BOT_USERNAME", "hsk_ai_test_bot"
        ):
            import importlib

            self.main = importlib.import_module("app.main")

        self.token_patch = patch.object(self.main.settings, "BOT_TOKEN", self.FAKE_TOKEN)
        self.token_patch.start()

        # Endpoint xato javobiga admin kontaktini qo'shadi — o'sha o'qish
        # production bazasiga emas, shu sinov bazasiga borsin.
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            await BotSettingRepository(session).set(ADMIN_CONTACT_KEY, "@hsk_ai_support")
            await session.commit()
        self.session_patch = patch.object(
            self.main, "async_session_maker", self.sessions
        )
        self.session_patch.start()

        async def _not_blocked(session_maker, telegram_id):
            return False

        self.guard_patch = patch(
            "app.services.blocked_user_guard.is_blocked_telegram_id", _not_blocked
        )
        self.guard_patch.start()

        from httpx import ASGITransport, AsyncClient

        self.client = AsyncClient(
            transport=ASGITransport(app=self.main.app),
            base_url="https://miniapp.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        self.guard_patch.stop()
        self.session_patch.stop()
        self.token_patch.stop()
        await self.engine.dispose()

    async def test_unexpected_failure_returns_a_json_code_the_mini_app_can_explain(self):
        async def _boom(*args, **kwargs):
            raise RuntimeError("database is down")

        with patch.object(SubscriptionMiniAppService, "submit", _boom):
            response = await self.client.post(
                "/api/subscription-miniapp/submit",
                headers={"X-Telegram-Init-Data": self._init_data(5001)},
                json={
                    "plan_type": "1_month",
                    "payment_method": "visa",
                    "card_country": "tj",
                    "screenshot_data_url": PNG_1X1_DATA_URL,
                },
            )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "payment_submit_failed")
        # Foydalanuvchi ekranda adminga yoza olsin: kontakt xato javobida ham keladi.
        self.assertEqual(payload["support_url"], "https://t.me/hsk_ai_support")

    async def test_truncated_body_returns_json_instead_of_a_server_error_page(self):
        # Sekin internetda yuklash yarmida uzilsa body to'liq kelmaydi.
        response = await self.client.post(
            "/api/subscription-miniapp/submit",
            headers={
                "X-Telegram-Init-Data": self._init_data(5001),
                "Content-Type": "application/json",
            },
            content=b'{"plan_type": "1_mon',
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "payment_submit_failed")
        self.assertEqual(payload["support_url"], "https://t.me/hsk_ai_support")


class SubscriptionMiniAppErrorCopyTests(unittest.TestCase):
    """Mini App har bir sababni o'z matni bilan ko'rsatadimi (uz/ru/tj)."""

    ERROR_CODES = (
        "invalid_screenshot",
        "user_blocked",
        "payment_submit_failed",
        "bad_json",
    )
    NEW_KEYS = (
        "networkError",
        "timeoutError",
        "serverError",
        "screenshotInvalid",
        "userBlocked",
    )

    def test_every_failure_code_has_its_own_message(self):
        for code in self.ERROR_CODES:
            with self.subTest(code=code):
                self.assertIn(f"{code}:text.", SUBSCRIPTION_HTML)
        self.assertNotIn("bad_json:text.error", SUBSCRIPTION_HTML)

    def test_new_copy_exists_in_all_three_languages(self):
        for key in self.NEW_KEYS:
            with self.subTest(key=key):
                # uz, ru, tj — uchtadan kam bo'lsa bir til matnsiz qoladi.
                self.assertEqual(SUBSCRIPTION_HTML.count(f"{key}:\""), 3)

    def test_network_failures_do_not_leak_the_browser_message(self):
        # Ilgari ulanish uzilganda ekranda inglizcha "Failed to fetch" chiqardi.
        self.assertIn('apiError(error&&error.name==="AbortError"?"request_timeout":"network_error")', SUBSCRIPTION_HTML)
        self.assertIn("request_timeout:text.timeoutError", SUBSCRIPTION_HTML)
        self.assertIn("network_error:text.networkError", SUBSCRIPTION_HTML)
        self.assertIn("SUBMIT_TIMEOUT_MS", SUBSCRIPTION_HTML)
        self.assertIn("signal:controller?controller.signal:undefined", SUBSCRIPTION_HTML)

    def test_screenshot_is_compressed_to_a_size_a_slow_phone_can_upload(self):
        self.assertIn("SCREENSHOT_TARGET_CHARS=300*1024", SUBSCRIPTION_HTML)
        self.assertIn("SCREENSHOT_STEPS=[[1280,0.72],[1100,0.65],[900,0.6],[720,0.55]]", SUBSCRIPTION_HTML)
        # Eski yagona qadam (1600/0.82) qaytib kelmasin.
        self.assertNotIn('canvas.toDataURL("image/jpeg",0.82)', SUBSCRIPTION_HTML)

    def test_unsupported_file_is_stopped_before_submit(self):
        self.assertIn("allowedShot(shot)", SUBSCRIPTION_HTML)
        # Chegara server bilan bir xil o'lchovda — dekodlangan baytda.
        self.assertIn("const SCREENSHOT_MAX_BYTES=8*1024*1024;", SUBSCRIPTION_HTML)
        self.assertIn("dataUrlBytes(shot)>SCREENSHOT_MAX_BYTES", SUBSCRIPTION_HTML)

    def test_rejected_screenshot_says_exactly_what_is_wrong(self):
        # Format, hajm va o'qish xatosi — har biri o'z matni bilan.
        for key in ("screenshotTooBig", "screenshotFormat", "screenshotReadFailed"):
            with self.subTest(key=key):
                self.assertEqual(SUBSCRIPTION_HTML.count(f"{key}:\""), 3)
        self.assertIn('text.screenshotFormat.replace("{type}",file.type||"?")', SUBSCRIPTION_HTML)
        self.assertIn('text.screenshotTooBig.replace("{size}",formatBytes(dataUrlBytes(shot)))', SUBSCRIPTION_HTML)
        # Sabab toast o'chgach ham ekranda qoladi.
        self.assertIn("state.screenshotNote", SUBSCRIPTION_HTML)
        self.assertIn("function rejectScreenshot(note)", SUBSCRIPTION_HTML)

    def test_selected_screenshot_shows_its_real_size(self):
        for key in ("screenshotReady", "screenshotHeavy"):
            with self.subTest(key=key):
                self.assertEqual(SUBSCRIPTION_HTML.count(f"{key}:\""), 3)
        self.assertIn("function dataUrlBytes(dataUrl)", SUBSCRIPTION_HTML)
        self.assertIn("function formatBytes(bytes)", SUBSCRIPTION_HTML)
        self.assertIn("const SCREENSHOT_HEAVY_BYTES=600*1024;", SUBSCRIPTION_HTML)

    def test_server_rejection_reason_reaches_the_user(self):
        self.assertIn("function serverScreenshotNote(error)", SUBSCRIPTION_HTML)
        self.assertIn('error.reason==="too_big"', SUBSCRIPTION_HTML)
        self.assertIn('error.reason==="format"', SUBSCRIPTION_HTML)
        self.assertIn('apiError(data.error||"api_error",data.support_url,data.reason)', SUBSCRIPTION_HTML)

    def test_failed_submit_shows_the_admin_contact_on_screen(self):
        # Xato yuz berganda foydalanuvchi adminga yoza olsin.
        self.assertIn("offerSupport(error)", SUBSCRIPTION_HTML)
        self.assertIn('SUPPORT_SKIP_CODES=["invalid_screenshot"]', SUBSCRIPTION_HTML)
        self.assertIn("if(error&&error.supportUrl)state.supportUrl=error.supportUrl;", SUBSCRIPTION_HTML)
        self.assertIn("state.supportReason", SUBSCRIPTION_HTML)
        # Kontakt sozlanmagan bo'lsa ishlamaydigan tugma ko'rinmaydi.
        self.assertIn('$("#openSupportBtn").style.display=state.supportUrl?"":"none";', SUBSCRIPTION_HTML)
        # Yangi UI bloki emas — mavjud "Yordam" varag'i ishlatiladi.
        self.assertEqual(SUBSCRIPTION_HTML.count('id="supportSheet"'), 1)


if __name__ == "__main__":
    unittest.main()
