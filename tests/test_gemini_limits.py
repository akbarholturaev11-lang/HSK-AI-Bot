import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.access_service import AccessService
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


class GeminiTextLimitTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.access_service.gemini_active", return_value=True)
    async def test_text_unlimited_when_gemini(self, _):
        svc = _make_access_service()
        user = _make_user()
        user.questions_used = 9999  # istalgan limitdan oshgan
        ok, key = await svc._can_use_daily_text_limit(user)
        self.assertTrue(ok)
        self.assertEqual(key, "")

    @patch("app.services.access_service.gemini_active", return_value=False)
    async def test_text_limited_when_openai(self, _):
        svc = _make_access_service()
        user = _make_user()
        user.questions_used = 10  # == question_limit
        svc.user_repo.get_bonus_balance = MagicMock(return_value=0)
        svc.user_repo.was_daily_limit_offer_sent_today = AsyncMock(return_value=True)
        svc.user_repo.mark_daily_limit_offer_sent = AsyncMock()
        ok, key = await svc._can_use_daily_text_limit(user)
        self.assertFalse(ok)
        self.assertEqual(key, "access_daily_limit_reached")


class GeminiPhotoLimitTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.access_service.gemini_active", return_value=True)
    async def test_photo_allowed_below_5_when_gemini(self, _):
        svc = _make_access_service(image_count=4)
        ok, _key = await svc._can_use_daily_image_limit(_make_user())
        self.assertTrue(ok)

    @patch("app.services.access_service.gemini_active", return_value=True)
    async def test_photo_blocked_at_5_when_gemini(self, _):
        svc = _make_access_service(image_count=5)
        ok, key = await svc._can_use_daily_image_limit(_make_user())
        self.assertFalse(ok)
        self.assertEqual(key, "access_daily_image_limit_reached")

    @patch("app.services.access_service.gemini_active", return_value=False)
    async def test_photo_blocked_at_2_when_openai(self, _):
        svc = _make_access_service(image_count=2)
        ok, key = await svc._can_use_daily_image_limit(_make_user())
        self.assertFalse(ok)
        self.assertEqual(key, "access_daily_image_limit_reached")


class GeminiVoiceLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_voice_allowed_below_5(self):
        svc = _make_access_service(voice_count=3, translator_count=1)  # jami 4
        ok, _key = await svc.can_use_free_daily_voice(_make_user())
        self.assertTrue(ok)

    async def test_voice_blocked_at_5(self):
        svc = _make_access_service(voice_count=3, translator_count=2)  # jami 5
        ok, key = await svc.can_use_free_daily_voice(_make_user())
        self.assertFalse(ok)
        self.assertEqual(key, "access_daily_voice_limit_reached")

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


if __name__ == "__main__":
    unittest.main()
