import asyncio
import unittest
from types import SimpleNamespace

from app.bot.middlewares import blocked_user as bu
from app.services import blocked_user_guard as guard


def _user(telegram_id, status="free", language="uz"):
    return SimpleNamespace(telegram_id=telegram_id, status=status, language=language)


class _FakeRepo:
    """UserRepository o'rniga: telegram_id -> user."""

    users: dict = {}

    def __init__(self, session):
        self.session = session

    async def get_by_telegram_id(self, telegram_id):
        return self.users.get(telegram_id)


class _FakeEvent:
    """Message/CallbackQuery emas — faqat to'siq mantig'ini tekshiramiz."""

    def __init__(self, telegram_id):
        self.from_user = SimpleNamespace(id=telegram_id)


class BlockedUserMiddlewareTest(unittest.TestCase):
    def setUp(self):
        bu.reset_block_notice_state()
        self._orig_repo = bu.UserRepository
        self._orig_is_admin = bu.is_admin_user
        bu.UserRepository = _FakeRepo
        _FakeRepo.users = {}
        self.calls = []

    def tearDown(self):
        bu.UserRepository = self._orig_repo
        bu.is_admin_user = self._orig_is_admin
        bu.reset_block_notice_state()

    async def _handler(self, event, data):
        self.calls.append(event)
        return "handled"

    def _run(self, telegram_id, *, admin_ids=()):
        bu.is_admin_user = lambda uid: uid in admin_ids
        middleware = bu.BlockedUserMiddleware(sessionmaker=None)
        event = _FakeEvent(telegram_id)
        data = {"session": object()}
        return asyncio.run(middleware(self._handler, event, data))

    def test_blocked_user_never_reaches_handler(self):
        _FakeRepo.users = {5: _user(5, status="blocked")}
        result = self._run(5)
        self.assertIsNone(result)
        self.assertEqual(self.calls, [])

    def test_free_user_passes_through(self):
        _FakeRepo.users = {5: _user(5, status="free")}
        self.assertEqual(self._run(5), "handled")
        self.assertEqual(len(self.calls), 1)

    def test_active_user_passes_through(self):
        _FakeRepo.users = {5: _user(5, status="active")}
        self.assertEqual(self._run(5), "handled")

    def test_admin_is_never_blocked(self):
        _FakeRepo.users = {9: _user(9, status="blocked")}
        self.assertEqual(self._run(9, admin_ids={9}), "handled")
        self.assertEqual(len(self.calls), 1)

    def test_unknown_user_passes_through(self):
        _FakeRepo.users = {}
        self.assertEqual(self._run(5), "handled")

    def test_missing_session_does_not_break_flow(self):
        bu.is_admin_user = lambda uid: False
        middleware = bu.BlockedUserMiddleware(sessionmaker=None)
        result = asyncio.run(middleware(self._handler, _FakeEvent(5), {}))
        self.assertEqual(result, "handled")

    def test_notice_cooldown_allows_only_one_message(self):
        self.assertTrue(bu._should_notify(77))
        self.assertFalse(bu._should_notify(77))
        self.assertFalse(bu._should_notify(77))
        # Boshqa user o'z xabarini oladi.
        self.assertTrue(bu._should_notify(78))


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, status):
        self.status = status
        self.queries = 0

    async def execute(self, _query):
        self.queries += 1
        return _FakeScalarResult(self.status)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _session_maker(status, counter):
    def make():
        session = _FakeSession(status)
        counter.append(session)
        return session

    return make


class BlockedUserGuardCacheTest(unittest.TestCase):
    def setUp(self):
        guard.invalidate()

    def tearDown(self):
        guard.invalidate()

    def test_blocked_status_detected(self):
        sessions = []
        maker = _session_maker("blocked", sessions)
        self.assertTrue(asyncio.run(guard.is_blocked_telegram_id(maker, 5)))

    def test_free_status_not_blocked(self):
        sessions = []
        maker = _session_maker("free", sessions)
        self.assertFalse(asyncio.run(guard.is_blocked_telegram_id(maker, 5)))

    def test_second_call_uses_cache(self):
        sessions = []
        maker = _session_maker("blocked", sessions)
        asyncio.run(guard.is_blocked_telegram_id(maker, 5))
        asyncio.run(guard.is_blocked_telegram_id(maker, 5))
        self.assertEqual(len(sessions), 1)

    def test_invalidate_forces_refetch(self):
        sessions = []
        maker = _session_maker("blocked", sessions)
        asyncio.run(guard.is_blocked_telegram_id(maker, 5))
        guard.invalidate(5)
        asyncio.run(guard.is_blocked_telegram_id(maker, 5))
        self.assertEqual(len(sessions), 2)


class _Recorder:
    """Guard ostidagi ASGI app — chaqirilganini yozib boradi."""

    def __init__(self):
        self.called = 0

    async def __call__(self, scope, receive, send):
        self.called += 1


def _scope(path, *, init_data=b""):
    headers = [(b"x-telegram-init-data", init_data)] if init_data else []
    return {"type": "http", "path": path, "headers": headers}


async def _collect(middleware, scope):
    messages = []

    async def send(message):
        messages.append(message)

    async def receive():
        return {"type": "http.request"}

    await middleware(scope, receive, send)
    return messages


class BlockedUserApiMiddlewareTest(unittest.TestCase):
    def setUp(self):
        guard.invalidate()
        self.app = _Recorder()
        self._orig_extract = guard.extract_verified_webapp_user_id

    def tearDown(self):
        guard.extract_verified_webapp_user_id = self._orig_extract
        guard.invalidate()

    def _middleware(self, status="blocked", admin_ids=()):
        guard.extract_verified_webapp_user_id = lambda init_data, token: 5
        return guard.BlockedUserApiMiddleware(
            self.app,
            session_maker=_session_maker(status, []),
            bot_token="token",
            admin_ids=admin_ids,
        )

    def test_non_api_path_passes_through(self):
        middleware = self._middleware()
        asyncio.run(_collect(middleware, _scope("/course-v3.html", init_data=b"x")))
        self.assertEqual(self.app.called, 1)

    def test_admin_api_path_is_exempt(self):
        middleware = self._middleware()
        asyncio.run(_collect(middleware, _scope("/api/admin-miniapp/overview", init_data=b"x")))
        self.assertEqual(self.app.called, 1)

    def test_request_without_init_data_passes_through(self):
        middleware = self._middleware()
        asyncio.run(_collect(middleware, _scope("/api/v3/map")))
        self.assertEqual(self.app.called, 1)

    def test_blocked_user_gets_403(self):
        middleware = self._middleware(status="blocked")
        messages = asyncio.run(_collect(middleware, _scope("/api/v3/map", init_data=b"x")))
        self.assertEqual(self.app.called, 0)
        start = next(m for m in messages if m["type"] == "http.response.start")
        self.assertEqual(start["status"], 403)
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        self.assertIn(b"user_blocked", body)

    def test_free_user_reaches_app(self):
        middleware = self._middleware(status="free")
        asyncio.run(_collect(middleware, _scope("/api/v3/map", init_data=b"x")))
        self.assertEqual(self.app.called, 1)

    def test_admin_id_bypasses_guard(self):
        middleware = self._middleware(status="blocked", admin_ids={5})
        asyncio.run(_collect(middleware, _scope("/api/v3/map", init_data=b"x")))
        self.assertEqual(self.app.called, 1)

    def test_websocket_scope_passes_through(self):
        middleware = self._middleware()
        asyncio.run(_collect(middleware, {"type": "websocket", "path": "/api/x", "headers": []}))
        self.assertEqual(self.app.called, 1)


if __name__ == "__main__":
    unittest.main()
