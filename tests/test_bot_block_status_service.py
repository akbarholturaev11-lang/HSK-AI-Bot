import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from aiogram.exceptions import TelegramForbiddenError

from app.services.bot_block_status_service import BotBlockStatusService


class _ScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return self._values

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None


class _FakeSession:
    def __init__(self, users):
        self._users = users
        self.committed = False

    async def execute(self, _query):
        return _ScalarsResult(self._users)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True


class _FakeBot:
    def __init__(self, behavior):
        # telegram_id -> Exception (raise) yoki None (muvaffaqiyat)
        self.behavior = behavior
        self.calls = []

    async def get_chat(self, telegram_id):
        self.calls.append(telegram_id)
        exc = self.behavior.get(telegram_id)
        if exc is not None:
            raise exc
        return SimpleNamespace(id=telegram_id)


def _user(telegram_id, **kwargs):
    base = dict(
        id=telegram_id,
        telegram_id=telegram_id,
        bot_blocked_at=None,
        bot_unblocked_at=None,
        last_bot_block_check_at=None,
        bot_block_reason=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


class BotBlockStatusServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_chat_success_does_not_unblock_previously_blocked(self):
        # Avval bloklangan user; get_chat OK qaytaradi (Telegram blokda ham OK qaytaradi).
        blocked_at = datetime.now(timezone.utc) - timedelta(days=2)
        user = _user(101, bot_blocked_at=blocked_at)
        self.assertTrue(BotBlockStatusService.is_bot_blocked(user))

        session = _FakeSession([user])
        bot = _FakeBot({101: None})  # success
        checked = await BotBlockStatusService(session).scan_due_users(bot, limit=10)

        self.assertEqual(checked, 1)
        # MUHIM: blok o'chib ketmasligi kerak.
        self.assertTrue(BotBlockStatusService.is_bot_blocked(user))
        self.assertIsNone(user.bot_unblocked_at)
        self.assertIsNotNone(user.last_bot_block_check_at)

    async def test_forbidden_marks_user_blocked(self):
        user = _user(202)
        self.assertFalse(BotBlockStatusService.is_bot_blocked(user))

        session = _FakeSession([user])
        bot = _FakeBot({202: TelegramForbiddenError(method=None, message="bot blocked")})
        await BotBlockStatusService(session).scan_due_users(bot, limit=10)

        self.assertTrue(BotBlockStatusService.is_bot_blocked(user))
        self.assertIsNotNone(user.bot_blocked_at)

    async def test_handle_send_exception_marks_block_on_forbidden(self):
        user = _user(303)
        session = _FakeSession([user])
        service = BotBlockStatusService(session)

        marked = await service.handle_send_exception(
            303, TelegramForbiddenError(method=None, message="blocked"), reason="broadcast"
        )

        self.assertTrue(marked)
        self.assertTrue(BotBlockStatusService.is_bot_blocked(user))

    async def test_handle_send_exception_ignores_other_errors(self):
        user = _user(404)
        session = _FakeSession([user])
        service = BotBlockStatusService(session)

        marked = await service.handle_send_exception(404, RuntimeError("timeout"))

        self.assertFalse(marked)
        self.assertFalse(BotBlockStatusService.is_bot_blocked(user))


if __name__ == "__main__":
    unittest.main()
