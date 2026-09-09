import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.bot.utils.i18n import TEXTS, t
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.message import Message
from app.db.models.user import User
from app.services.access_service import AccessService
from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import LimitConfigService
from app.services.gemini_switch_announcement_service import (
    ANNOUNCEMENT_TEXT,
    _text_for_language,
    announce_if_needed,
)


def _make_access_service(*, image_count=0, voice_count=0, translator_count=0):
    svc = AccessService.__new__(AccessService)
    svc.session = MagicMock()
    svc.user_repo = MagicMock()
    svc.message_repo = MagicMock()

    async def count_today(user_id, content_type="text"):
        return {
            "image": image_count,
            "voice": voice_count,
            "voice_translator": translator_count,
        }.get(content_type, 0)

    svc.message_repo.count_user_messages_today = AsyncMock(side_effect=count_today)
    return svc


def _make_user():
    user = MagicMock()
    user.id = 1
    user.last_limit_reset_at = datetime.now(timezone.utc)
    user.questions_used = 0
    user.question_limit = 10
    return user


class ConfiguredAiLimitTests(unittest.IsolatedAsyncioTestCase):
    """AI chegaralari endi provayderga emas, admin sozlamasiga bog'liq.

    Ilgari bu yerda `gemini_active()` bo'yicha ayriladigan qattiq raqamlar
    sinalardi (matn cheksiz / foto 5 yoki 2 / ovoz 5). Endi bitta manba bor —
    admin panelidagi limit bo'limi — va u ikkala provayderda ham bir xil
    javob berishi kerak.
    """

    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _learner(self, session, *, text=0, image=0, voice=0, translator=0):
        now = datetime.now(timezone.utc)
        session.add(User(
            id=1, telegram_id=321, full_name="AI limits", language="uz", level="hsk1",
            status="free", payment_status="none", question_limit=5, questions_used=0,
            created_at=now, last_active_at=now,
        ))
        await session.flush()
        for content_type, count in (
            ("text", text), ("image", image), ("voice", voice), ("voice_translator", translator),
        ):
            session.add_all([
                Message(user_id=1, role="user", content="x", content_type=content_type)
                for _ in range(count)
            ])
        await session.commit()
        return await session.get(User, 1)

    async def _limits(self, session, **actions):
        config = LimitConfigService(session)
        payload = (await config.get_config()).public_payload()
        for action, limit in actions.items():
            payload["plans"]["FREE"][action] = {"limit": limit, "window": "daily"}
        await config.save_config(payload)
        await session.commit()

    async def test_the_same_answer_on_both_providers(self):
        async with self.sessions() as session:
            user = await self._learner(session, text=3, image=3, voice=2, translator=1)
            await self._limits(session, **{A.AI_TEXT: 3, A.AI_PHOTO: 4, A.AI_VOICE: 3})
            service = AccessService(session)

            for provider in (True, False):
                with self.subTest(gemini=provider), patch(
                    "app.services.access_service.gemini_active", return_value=provider
                ):
                    self.assertEqual(
                        (False, "access_daily_limit_reached"),
                        await service._can_use_daily_text_limit(user),
                    )
                    self.assertEqual((True, ""), await service._can_use_daily_image_limit(user))
                    self.assertEqual(
                        (False, "access_daily_voice_limit_reached"),
                        await service.can_use_free_daily_voice(user),
                    )

    async def test_an_unlimited_setting_opens_the_feature(self):
        async with self.sessions() as session:
            user = await self._learner(session, text=99)
            await self._limits(session, **{A.AI_TEXT: None})
            self.assertEqual(
                (True, ""),
                await AccessService(session)._can_use_daily_text_limit(user),
            )

    async def test_voice_counts_both_voice_kinds_against_one_setting(self):
        async with self.sessions() as session:
            user = await self._learner(session, voice=1, translator=1)
            await self._limits(session, **{A.AI_VOICE: 2})
            self.assertEqual(
                (False, "access_daily_voice_limit_reached"),
                await AccessService(session).can_use_free_daily_voice(user),
            )


class VoiceMessageCountTests(unittest.IsolatedAsyncioTestCase):
    async def test_count_voice_sums_both_types(self):
        svc = _make_access_service(voice_count=2, translator_count=3)
        self.assertEqual(await svc.count_voice_messages_today(_make_user()), 5)


class GeminiAnnouncementTests(unittest.IsolatedAsyncioTestCase):
    def test_text_fallback_to_tj(self):
        self.assertEqual(_text_for_language("uz"), ANNOUNCEMENT_TEXT["uz"])
        self.assertEqual(_text_for_language("ru"), ANNOUNCEMENT_TEXT["ru"])
        self.assertEqual(_text_for_language("en"), ANNOUNCEMENT_TEXT["tj"])
        self.assertEqual(_text_for_language(None), ANNOUNCEMENT_TEXT["tj"])

    @patch(
        "app.services.gemini_switch_announcement_service.gemini_active",
        return_value=False,
    )
    async def test_skipped_when_gemini_inactive(self, _):
        bot = MagicMock()
        bot.send_message = AsyncMock()
        await announce_if_needed(bot)  # DB'ga tegmasdan qaytadi
        bot.send_message.assert_not_awaited()


class GeminiTextVariantTests(unittest.TestCase):
    """Gemini yoqilganda limit matnlari `_gemini` variantiga o'tishi kerak."""

    LANGS = ("uz", "ru", "tj")
    KEYS = (
        "free_mode_info",
        "onboarding_special_welcome",
        "trial_24h_info",
        "referral_trial_access_unlocked",
        "access_daily_image_limit_reached",
        "referral_image_limit_offer",
    )

    def test_gemini_variant_exists_in_all_languages(self):
        for lang in self.LANGS:
            for key in self.KEYS:
                with self.subTest(lang=lang, key=key):
                    self.assertIn(f"{key}_gemini", TEXTS[lang])

    def test_openai_keeps_original_text(self):
        with patch("app.config.settings.GEMINI_API_KEY", ""):
            for lang in self.LANGS:
                for key in self.KEYS:
                    with self.subTest(lang=lang, key=key):
                        self.assertEqual(
                            t(key, lang, required=3, days=3, user_num=1),
                            TEXTS[lang][key].format(required=3, days=3, user_num=1),
                        )

    def test_gemini_uses_variant_text(self):
        with patch("app.config.settings.GEMINI_API_KEY", "test-key"):
            for lang in self.LANGS:
                for key in self.KEYS:
                    with self.subTest(lang=lang, key=key):
                        self.assertEqual(
                            t(key, lang, required=3, days=3, user_num=1),
                            TEXTS[lang][f"{key}_gemini"].format(required=3, days=3, user_num=1),
                        )

    def test_key_without_variant_falls_back(self):
        # Varianti yo'q kalit Gemini holatida ham oddiy matnini beradi.
        with patch("app.config.settings.GEMINI_API_KEY", "test-key"):
            self.assertEqual(t("daily_limit_renewed", "uz"), TEXTS["uz"]["daily_limit_renewed"])

    def test_unknown_key_still_returns_key(self):
        with patch("app.config.settings.GEMINI_API_KEY", "test-key"):
            self.assertEqual(t("bunday_kalit_yoq", "uz"), "bunday_kalit_yoq")


if __name__ == "__main__":
    unittest.main()
