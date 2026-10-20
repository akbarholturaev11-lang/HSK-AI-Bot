"""Runtime localization regressions for callback-driven Bot menu replies."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.menu import handle_promo_action_callback


def make_callback(action):
    return SimpleNamespace(
        data=f"promo:action:{action}",
        from_user=SimpleNamespace(id=123),
        message=SimpleNamespace(answer=AsyncMock()),
        answer=AsyncMock(),
    )


class BotMenuLocalizationTests(unittest.IsolatedAsyncioTestCase):
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
