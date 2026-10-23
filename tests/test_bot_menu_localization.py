"""Runtime localization regressions for callback-driven Bot menu replies."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.menu import handle_promo_action_callback
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.utils.i18n import t


def make_callback(action):
    return SimpleNamespace(
        data=f"promo:action:{action}",
        from_user=SimpleNamespace(id=123),
        message=SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )


class BotMenuLocalizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_main_menu_and_hint_keep_existing_copy_in_all_locales(self):
        expected = {
            "uz": [
                ["👤 Profil", "💳 Obuna"],
                ["📚 Kurs rejimi", "⏰ Eslatma vaqti"],
                ["🤝 Hamkorlik", "❓ Yordam"],
            ],
            "ru": [
                ["👤 Профиль", "💳 Подписка"],
                ["📚 Режим курса", "⏰ Напоминание"],
                ["🤝 Партнёрство", "❓ Помощь"],
            ],
            "tj": [
                ["👤 Профил", "💳 Обуна"],
                ["📚 Режими курс", "⏰ Вақти ёдраскунак"],
                ["🤝 Ҳамкорӣ", "❓ Ёрдам"],
            ],
        }
        expected_hints = {
            "uz": "⌨️ Pastdagi menyudan profil, obuna va kurs rejimini ochasiz.",
            "ru": "⌨️ Через меню снизу открываются профиль, подписка и режим курса.",
            "tj": "⌨️ Аз менюи поён профил, обуна ва реҷаи курсро мекушоед.",
        }
        for locale, rows in expected.items():
            with self.subTest(locale=locale):
                keyboard = main_menu_keyboard(locale)
                self.assertEqual(
                    [[button.text for button in row] for row in keyboard.keyboard],
                    rows,
                )
                self.assertEqual(t("menu_bar_hint", locale), expected_hints[locale])

    async def test_disabled_course_callback_uses_saved_tajik_locale(self):
        callback = make_callback("course")
        user = SimpleNamespace(language="tj", voice_mode="none")
        state = SimpleNamespace(clear=AsyncMock(), update_data=AsyncMock())
        session = SimpleNamespace(commit=AsyncMock())
        with patch("app.bot.handlers.menu.UserRepository") as user_repo, \
                patch("app.bot.handlers.menu.COURSE_MODE_ENABLED", False):
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            await handle_promo_action_callback(callback, state, session)
        callback.answer.assert_awaited_once_with()
        self.assertEqual(
            callback.message.answer.await_args.args[0],
            "🚧 Реҷаи курс ҳоло дар таҳия аст.",
        )
        state.clear.assert_awaited_once()

    async def test_invalid_callback_shows_localized_tajik_alert(self):
        callback = make_callback("stale")
        user = SimpleNamespace(language="tj", voice_mode="none")
        state = SimpleNamespace(clear=AsyncMock(), update_data=AsyncMock())
        session = SimpleNamespace(commit=AsyncMock())
        with patch("app.bot.handlers.menu.UserRepository") as user_repo:
            user_repo.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            await handle_promo_action_callback(callback, state, session)
        callback.answer.assert_awaited_once_with(
            "Тугма дигар эътибор надорад ё нодуруст аст.", show_alert=True,
        )
        callback.message.answer.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
