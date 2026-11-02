"""PWA bot approval is private-chat, source localized and platform-isolated."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.handlers import desktop_auth as handler


def telegram_message(telegram_id=1001, text="/start pwa_link_12345678-1234-1234-1234-123456789abc_uz", *, private=True):
    chat = SimpleNamespace(id=telegram_id if private else -23, type="private" if private else "group")
    return SimpleNamespace(
        chat=chat, from_user=SimpleNamespace(id=telegram_id, full_name="Student", username="student"),
        text=text, bot=MagicMock(), answer=AsyncMock(),
    )


def telegram_callback(action="approve", telegram_id=1001):
    message = telegram_message(telegram_id)
    message.edit_text = AsyncMock()
    return SimpleNamespace(
        from_user=SimpleNamespace(id=telegram_id),
        message=message,
        data=f"pwa_link:{action}:12345678-1234-1234-1234-123456789abc",
        answer=AsyncMock(),
    )


class PwaTelegramBotTests(unittest.IsolatedAsyncioTestCase):
    async def test_pwa_only_pending_bot_request_uses_exact_platform(self):
        message = telegram_message()
        state = SimpleNamespace(clear=AsyncMock())
        user = SimpleNamespace(language="uz", telegram_id=1001, status="free")
        with patch.object(handler.settings, "PWA_AUTH_ENABLED", True), patch.object(
            handler, "DesktopAuthService"
        ) as service_class, patch.object(handler, "OnboardingService") as onboarding_class:
            service = service_class.return_value
            service.link_request_preview = AsyncMock(return_value={"referral_code": None})
            service.link_request_confirmation = AsyncMock(return_value={
                "ok": True, "platform": "pwa",
            })
            onboarding_class.return_value.get_or_create_user = AsyncMock(return_value=(user, False))
            await handler.begin_pwa_telegram_login(message, state, MagicMock())
            kwargs = service.link_request_confirmation.await_args.kwargs
            self.assertEqual(kwargs["platform"], "pwa")
            self.assertEqual(kwargs["telegram_id"], 1001)
            self.assertEqual(kwargs["link_request_id"], "12345678-1234-1234-1234-123456789abc")
            sent = message.answer.await_args.kwargs
            actions = [
                button.callback_data for row in sent["reply_markup"].inline_keyboard
                for button in row
            ]
            self.assertTrue(all(v.startswith("pwa_link:") for v in actions))
            self.assertIn("pwa_link:approve:12345678-1234-1234-1234-123456789abc", actions)
            self.assertIn("HSK AI", message.answer.await_args.args[0])
            state.clear.assert_awaited_once()

    async def test_pwa_telegram_approval_and_denial_never_use_android_platform(self):
        state = MagicMock()
        with patch.object(handler.settings, "PWA_AUTH_ENABLED", True), patch.object(
            handler, "DesktopAuthService"
        ) as service_class, patch.object(
            handler, "_android_language_for", new=AsyncMock(return_value="uz"),
        ):
            service = service_class.return_value
            service.approve_link_request = AsyncMock(return_value={"ok": True})
            service.cancel_link_request = AsyncMock(return_value={"ok": True})
            approved = telegram_callback("approve")
            await handler.confirm_pwa_telegram_login(approved, state)
            self.assertEqual(service.approve_link_request.await_args.kwargs["platform"], "pwa")
            approved.message.edit_text.assert_awaited_once()
            denied = telegram_callback("cancel")
            await handler.confirm_pwa_telegram_login(denied, state)
            self.assertEqual(service.cancel_link_request.await_args.kwargs["platform"], "pwa")
            denied.message.edit_text.assert_awaited_once()

    async def test_disabled_or_nonprivate_pwa_link_never_reserves_approval(self):
        state = SimpleNamespace(clear=AsyncMock())
        with patch.object(handler.settings, "PWA_AUTH_ENABLED", False), patch.object(
            handler, "DesktopAuthService"
        ) as service_class:
            msg = telegram_message()
            await handler.begin_pwa_telegram_login(msg, state, MagicMock())
            msg.answer.assert_not_awaited()
            service_class.assert_not_called()
        with patch.object(handler.settings, "PWA_AUTH_ENABLED", True), patch.object(
            handler, "DesktopAuthService"
        ) as service_class:
            msg = telegram_message(private=False)
            await handler.begin_pwa_telegram_login(msg, state, MagicMock())
            msg.answer.assert_not_awaited()
            service_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
