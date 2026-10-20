import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.account_deletion import (
    VERIFY,
    begin_account_deletion,
    begin_web_verification,
    confirm_account_deletion,
    verify_web_account,
)
from app.services.desktop_auth_service import DesktopAuthError


def callback():
    user = SimpleNamespace(
        id=123, username="learner", full_name="Learner", language_code="uz")
    bot = SimpleNamespace(send_message=AsyncMock())
    message = SimpleNamespace(
        chat=SimpleNamespace(id=123, type="private"),
        edit_reply_markup=AsyncMock(), answer=AsyncMock(),
    )
    return SimpleNamespace(from_user=user, message=message, bot=bot, answer=AsyncMock())


class AccountDeletionRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_requires_private_chat_and_asks_for_confirmation(self):
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123, language_code="uz"),
            chat=SimpleNamespace(type="private"), answer=AsyncMock(),
        )
        with patch("app.bot.handlers.account_deletion.UserRepository") as user_repo:
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=None)
            await begin_account_deletion(message, object())
        self.assertIn("o‘chirishni so‘ramoqchimisiz", message.answer.await_args.args[0])
        self.assertEqual(
            message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data,
            "account_deletion:confirm",
        )
        message.chat.type = "group"
        message.answer.reset_mock()
        await begin_account_deletion(message, object())
        message.answer.assert_not_awaited()

    async def test_start_uses_saved_language_when_it_differs_from_telegram_locale(self):
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123, language_code="uz"),
            chat=SimpleNamespace(type="private"), answer=AsyncMock(),
        )
        with patch("app.bot.handlers.account_deletion.UserRepository") as user_repo:
            user_repo.return_value.get_by_telegram_id = AsyncMock(
                return_value=SimpleNamespace(language="ru"))
            await begin_account_deletion(message, object())
        self.assertIn("Хотите отправить запрос", message.answer.await_args.args[0])

    async def test_web_verification_start_maps_telegram_tg_to_tajik(self):
        request_token = "0123456789abcdef0123456789abcdef"
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123, language_code="tg"),
            chat=SimpleNamespace(id=123, type="private"),
            text=f"/start delete_{request_token}", answer=AsyncMock(),
        )
        with patch("app.bot.handlers.account_deletion.UserRepository") as user_repo:
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=None)
            await begin_web_verification(message, object())
        self.assertIn("Дар сомонаи HSK AI", message.answer.await_args.args[0])
        button = message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(button.text, "Ин ҳисоби ман аст")
        self.assertEqual(button.callback_data, VERIFY + "01234567-89ab-cdef-0123-456789abcdef")

    async def test_expired_web_verification_uses_saved_locale(self):
        request = callback()
        request.data = VERIFY + "01234567-89ab-cdef-0123-456789abcdef"
        with patch("app.bot.handlers.account_deletion.UserRepository") as user_repo, \
                patch("app.bot.handlers.account_deletion.is_account_deletion_event", return_value=True), \
                patch("app.bot.handlers.account_deletion.AccountDeletionService") as service:
            user_repo.return_value.get_by_telegram_id = AsyncMock(
                return_value=SimpleNamespace(language="tj"))
            service.return_value.verify_telegram = AsyncMock(
                side_effect=DesktopAuthError("expired", status_code=410))
            await verify_web_account(request, object())
        self.assertIn("Муҳлати дархост гузаштааст", request.answer.await_args.args[0])
        self.assertTrue(request.answer.await_args.kwargs["show_alert"])

    async def test_confirm_persists_before_notifying_and_acknowledging(self):
        request = callback()
        result = {"request_id": "verified-receipt", "status": "submitted", "due_at": "2026-11-14"}
        with patch("app.bot.handlers.account_deletion.settings") as settings, \
                patch("app.bot.handlers.account_deletion.UserRepository") as user_repo, \
                patch("app.bot.handlers.account_deletion.AccountDeletionService") as service:
            settings.admin_id_list = [456]
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=None)
            service.return_value.submit_telegram = AsyncMock(return_value=result)
            await confirm_account_deletion(request, object())
            service.return_value.submit_telegram.assert_awaited_once_with(123)
        request.bot.send_message.assert_awaited_once()
        self.assertEqual(request.bot.send_message.await_args.args[0], 456)
        self.assertIn("verified-receipt", request.bot.send_message.await_args.args[1])
        request.message.edit_reply_markup.assert_awaited_once_with(reply_markup=None)
        request.message.answer.assert_awaited_once()

    async def test_failed_persistence_does_not_acknowledge_request(self):
        request = callback()
        with patch("app.bot.handlers.account_deletion.UserRepository") as user_repo, \
                patch("app.bot.handlers.account_deletion.AccountDeletionService") as service:
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=None)
            service.return_value.submit_telegram = AsyncMock(side_effect=RuntimeError("offline"))
            await confirm_account_deletion(request, object())
        request.message.edit_reply_markup.assert_not_awaited()
        request.message.answer.assert_not_awaited()
        self.assertTrue(request.answer.await_args.kwargs["show_alert"])

    async def test_notification_failure_keeps_durable_receipt(self):
        request = callback()
        request.bot.send_message.side_effect = RuntimeError("offline")
        with patch("app.bot.handlers.account_deletion.settings") as settings, \
                patch("app.bot.handlers.account_deletion.UserRepository") as user_repo, \
                patch("app.bot.handlers.account_deletion.AccountDeletionService") as service:
            settings.admin_id_list = [456]
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=None)
            service.return_value.submit_telegram = AsyncMock(return_value={
                "request_id": "saved-receipt", "status": "submitted", "due_at": "2026-11-14"})
            await confirm_account_deletion(request, object())
        self.assertIn("saved-receipt", request.message.answer.await_args.args[0])
        request.message.edit_reply_markup.assert_awaited_once()
