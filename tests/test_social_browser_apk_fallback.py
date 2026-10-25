"""Social in-app browser Android APK handoff to the existing Telegram delivery."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_JS = (ROOT / "app/static/desktop-download-page.js").read_text(encoding="utf-8")


class DownloadFallbackContractTests(unittest.TestCase):
    def test_only_android_social_browser_attempts_external_intent(self):
        self.assertIn("function isAndroidSocialBrowser()", DOWNLOAD_JS)
        self.assertIn("/Android/i.test(agent)", DOWNLOAD_JS)
        self.assertIn("Instagram|FBAN|FBAV|FB_IAB|FB4A|TikTok", DOWNLOAD_JS)
        self.assertIn("window.location.assign(externalAndroidBrowserIntent())", DOWNLOAD_JS)

    def test_same_download_button_becomes_manual_telegram_fallback(self):
        self.assertIn("socialApkFallbackArmed = true;", DOWNLOAD_JS)
        self.assertIn("button.href = websiteApkBotLink();", DOWNLOAD_JS)
        self.assertIn('button.dataset.action = "open";', DOWNLOAD_JS)
        self.assertIn("apk_web_", DOWNLOAD_JS)


class TelegramWebsiteApkStartTests(unittest.IsolatedAsyncioTestCase):
    async def _assert_delivery(self, payload, referral_code):
        from app.bot.handlers.start import cmd_start

        bot = SimpleNamespace()
        message = SimpleNamespace(
            bot=bot,
            chat=SimpleNamespace(id=3001),
            from_user=SimpleNamespace(
                id=4002, first_name="Learner", full_name="Learner User", username=None
            ),
        )
        state = SimpleNamespace(clear=AsyncMock())
        session = object()
        onboarding = SimpleNamespace(
            get_or_create_user=AsyncMock(return_value=(SimpleNamespace(language="uz"), True))
        )
        with patch("app.bot.handlers.start.OnboardingService", return_value=onboarding), patch(
            "app.bot.handlers.start.send_android_app", new_callable=AsyncMock
        ) as send_apk:
            await cmd_start(
                message,
                state,
                session,
                SimpleNamespace(args=payload),
            )

        self.assertEqual(onboarding.get_or_create_user.await_args.kwargs["referral_code"], referral_code)
        state.clear.assert_awaited_once()
        send_apk.assert_awaited_once_with(
            bot, 3001, 4002, session, source="website_social_fallback"
        )

    async def test_regular_social_fallback_delivers_apk(self):
        await self._assert_delivery("apk_web", None)

    async def test_discount_referral_survives_social_fallback(self):
        await self._assert_delivery("apk_web_ra_a1b2c3d4", "ra_a1b2c3d4")

    async def test_trial_referral_survives_social_fallback(self):
        await self._assert_delivery("apk_web_rt_a1b2c3d4", "a1b2c3d4")


if __name__ == "__main__":
    unittest.main()
