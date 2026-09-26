import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.account_deletion import begin_account_deletion, confirm_account_deletion


def callback():
    user = SimpleNamespace(id=123, username="learner", full_name="Learner")
    bot = SimpleNamespace(send_message=AsyncMock())
    message = SimpleNamespace(
        chat=SimpleNamespace(id=123, type="private"),
        edit_reply_markup=AsyncMock(), answer=AsyncMock(),
    )
    return SimpleNamespace(from_user=user, message=message, bot=bot, answer=AsyncMock())


class AccountDeletionRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_requires_private_chat_and_asks_for_confirmation(self):
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            chat=SimpleNamespace(type="private"), answer=AsyncMock(),
        )
        await begin_account_deletion(message)
        self.assertIn("o‘chirishni so‘ramoqchimisiz", message.answer.await_args.args[0])
        self.assertEqual(
            message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data,
            "account_deletion:confirm",
        )
        message.chat.type = "group"
        message.answer.reset_mock()
        await begin_account_deletion(message)
        message.answer.assert_not_awaited()

    async def test_confirm_forwards_identity_and_acknowledges_only_after_delivery(self):
        request = callback()
        with patch("app.bot.handlers.account_deletion.settings") as settings:
            settings.admin_id_list = [456]
            await confirm_account_deletion(request)
        request.bot.send_message.assert_awaited_once()
        self.assertEqual(request.bot.send_message.await_args.args[0], 456)
        self.assertIn("123", request.bot.send_message.await_args.args[1])
        request.message.edit_reply_markup.assert_awaited_once_with(reply_markup=None)
        request.message.answer.assert_awaited_once()

    async def test_failed_delivery_does_not_acknowledge_request(self):
        request = callback()
        request.bot.send_message.side_effect = RuntimeError("offline")
        with patch("app.bot.handlers.account_deletion.settings") as settings:
            settings.admin_id_list = [456]
            await confirm_account_deletion(request)
        request.message.edit_reply_markup.assert_not_awaited()
        request.message.answer.assert_not_awaited()
        self.assertTrue(request.answer.await_args.kwargs["show_alert"])
