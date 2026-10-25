"""Admin PWA Bot handler tests. Use real aiogram update models and mocked DB.

No Telegram API network call, Google callback or session issuer is exercised.
"""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.types import CallbackQuery, Chat, Message, User

from app.bot.handlers import admin_pwa
from app.bot.generated.bot_i18n import bot_message

REQUEST = "a1b2c3d4-aaaa-bbbb-cccc-1234567890ab"
NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def message(*, telegram_id=9001, chat_id=None, kind="private",
            text=None, language="ru", is_bot=False):
    user = User(id=telegram_id, is_bot=is_bot, first_name="Admin", language_code=language)
    chat = Chat(id=telegram_id if chat_id is None else chat_id, type=kind)
    return Message(
        message_id=123, date=NOW, chat=chat, from_user=user,
        text=text or "/start admin_pwa_" + REQUEST,
    )


def callback(msg, *, action="approve"):
    return CallbackQuery(
        id="test-callback", from_user=msg.from_user, chat_instance="test",
        message=msg, data=f"admin_pwa:{action}:{REQUEST}",
    )


class AdminPwaBotHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(ADMIN_PWA_ENABLED=True)
        self.p_settings = patch.object(admin_pwa, "settings", self.settings)
        self.p_settings.start()
        self.addCleanup(self.p_settings.stop)

        self.p_repo = patch.object(admin_pwa, "UserRepository")
        repo = self.p_repo.start()
        repo.return_value.get_by_telegram_id = AsyncMock(
            return_value=SimpleNamespace(language="ru"),
        )
        self.addCleanup(self.p_repo.stop)

        self.p_preview = patch.object(admin_pwa, "preview_admin_pwa_bot_request",
                                      new_callable=AsyncMock)
        self.preview = self.p_preview.start()
        self.addCleanup(self.p_preview.stop)
        self.preview.return_value = SimpleNamespace(
            request_id=REQUEST, pairing_code="DEADBEEF",
            expires_at=NOW,
        )
        self.p_decide = patch.object(admin_pwa, "decide_admin_pwa_bot_request",
                                     new_callable=AsyncMock)
        self.decide = self.p_decide.start()
        self.decide.return_value = True
        self.p_message_answer = patch.object(Message, "answer", new_callable=AsyncMock)
        self.send = self.p_message_answer.start()
        self.addCleanup(self.p_message_answer.stop)
        self.p_edit = patch.object(Message, "edit_text", new_callable=AsyncMock)
        self.edit = self.p_edit.start()
        self.addCleanup(self.p_edit.stop)
        self.p_callback_answer = patch.object(CallbackQuery, "answer", new_callable=AsyncMock)
        self.ack = self.p_callback_answer.start()
        self.addCleanup(self.p_callback_answer.stop)

    async def test_real_private_start_sends_pairing_code_and_two_separate_actions(self):
        event = message()
        await admin_pwa.begin_admin_pwa_approval(event, session=object())
        self.preview.assert_awaited_once()
        args = self.preview.await_args.kwargs
        self.assertIs(args["bot_event"], event)
        self.assertEqual(args["request_id"], REQUEST)
        self.send.assert_awaited_once()
        kwargs = self.send.await_args.kwargs
        self.assertEqual(kwargs["parse_mode"], "HTML")
        self.assertIn("<code>DEADBEEF</code>", self.send.await_args.args[0])
        buttons = kwargs["reply_markup"].inline_keyboard
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0][0].callback_data, "admin_pwa:approve:" + REQUEST)
        self.assertEqual(buttons[1][0].callback_data, "admin_pwa:deny:" + REQUEST)
        self.assertLessEqual(
            len(buttons[0][0].callback_data.encode("utf-8")), 64,
        )

    async def test_group_forward_and_bot_sender_do_not_preview(self):
        events = (
            message(kind="group", chat_id=-100),
            message(kind="supergroup", chat_id=-100),
            message(chat_id=9002),
            message(is_bot=True),
            message().model_copy(update={"forward_origin": object()}),
        )
        for event in events:
            with self.subTest(kind=event.chat.type, chat_id=event.chat.id):
                await admin_pwa.begin_admin_pwa_approval(event, session=object())
        self.preview.assert_not_awaited()
        self.send.assert_not_awaited()

    async def test_forwarded_callback_cannot_approve(self):
        forwarded = message().model_copy(update={"forward_origin": object()})
        await admin_pwa.decide_admin_pwa_approval(
            callback(forwarded), session=object(),
        )
        self.decide.assert_not_awaited()
        self.ack.assert_awaited_once()
        self.assertTrue(self.ack.await_args.kwargs["show_alert"])

    async def test_disabled_flag_does_not_interfere_with_normal_bot(self):
        self.settings.ADMIN_PWA_ENABLED = False
        await admin_pwa.begin_admin_pwa_approval(message(), session=object())
        await admin_pwa.decide_admin_pwa_approval(callback(message()), session=object())
        self.preview.assert_not_awaited()
        self.decide.assert_not_awaited()
        self.ack.assert_awaited_once()

    async def test_non_admin_or_expired_preview_is_generic(self):
        self.preview.return_value = None
        await admin_pwa.begin_admin_pwa_approval(message(), session=object())
        self.assertEqual(
            self.send.await_args.args[0],
            bot_message("adminPwa.invalid", "ru"),
        )

    async def test_approve_callback_commits_before_success_and_removes_buttons(self):
        cb = callback(message())
        await admin_pwa.decide_admin_pwa_approval(cb, session=object())
        self.decide.assert_awaited_once()
        self.assertTrue(self.decide.await_args.kwargs["approve"])
        self.assertEqual(self.ack.await_args.args[0], bot_message("adminPwa.approved", "ru"))
        self.edit.assert_awaited_once()
        return_buttons = self.edit.await_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual(len(return_buttons), 1)
        self.assertEqual(return_buttons[0][0].url, "https://hskai.app/admin/")
        self.assertEqual(return_buttons[0][0].text, bot_message("adminPwa.openBrowser", "ru"))

    async def test_deny_callback_is_explicit_and_terminal_in_service(self):
        cb = callback(message(), action="deny")
        await admin_pwa.decide_admin_pwa_approval(cb, session=object())
        self.assertFalse(self.decide.await_args.kwargs["approve"])
        self.assertEqual(self.ack.await_args.args[0], bot_message("adminPwa.denied", "ru"))
        self.edit.assert_awaited_once()
        self.assertIsNone(self.edit.await_args.kwargs["reply_markup"])

    async def test_replay_rejected_no_success_edit(self):
        self.decide.return_value = False
        await admin_pwa.decide_admin_pwa_approval(callback(message()), session=object())
        self.edit.assert_not_awaited()
        self.ack.assert_awaited_once()
        self.assertTrue(self.ack.await_args.kwargs["show_alert"])

    async def test_group_callback_denied_before_service(self):
        await admin_pwa.decide_admin_pwa_approval(
            callback(message(kind="supergroup", chat_id=-100)), session=object(),
        )
        self.decide.assert_not_awaited()
        self.ack.assert_awaited_once()
        self.assertTrue(self.ack.await_args.kwargs["show_alert"])

    async def test_canonical_copy_has_parity_and_warning_for_all_locales(self):
        for lang in ("uz", "ru", "tj"):
            with self.subTest(language=lang):
                text = bot_message("adminPwa.confirm", lang)
                self.assertIn("{code}", text)
                self.assertIn("hskai.app/admin", text)
                self.assertIn("5", text)
                for key in ("approve", "deny", "approved", "denied",
                            "invalid", "privateOnly", "unavailable", "openBrowser"):
                    self.assertTrue(bot_message("adminPwa." + key, lang))

    async def test_deeplink_regex_is_scoped_and_telegram_payload_valid(self):
        self.assertIsNotNone(
            admin_pwa._START_PATTERN.fullmatch("/start admin_pwa_" + REQUEST),
        )
        self.assertIsNone(
            admin_pwa._START_PATTERN.fullmatch("/start tg_identity_" + REQUEST),
        )
        self.assertIsNone(
            admin_pwa._START_PATTERN.fullmatch("/start admin_pwa_" + REQUEST + "x"),
        )
        self.assertLessEqual(len(("admin_pwa_" + REQUEST).encode("ascii")), 64)
        for action in ("approve", "deny"):
            self.assertIsNotNone(
                admin_pwa._CALLBACK_PATTERN.fullmatch(
                    f"admin_pwa:{action}:{REQUEST}"
                ),
            )
            self.assertLessEqual(
                len(f"admin_pwa:{action}:{REQUEST}".encode("ascii")), 64,
            )


if __name__ == "__main__":
    unittest.main()
