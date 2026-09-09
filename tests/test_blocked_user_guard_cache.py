import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_guard_with_dependency_stubs():
    class _Column:
        def __eq__(self, other):
            return ("eq", other)

    class _Select:
        def __init__(self, *_columns):
            self.columns = _columns

        def where(self, *_conditions):
            return self

    sqlalchemy = types.ModuleType("sqlalchemy")
    sqlalchemy.select = lambda *columns: _Select(*columns)
    sys.modules.setdefault("sqlalchemy", sqlalchemy)

    responses = types.ModuleType("starlette.responses")

    class JSONResponse:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    responses.JSONResponse = JSONResponse
    starlette = types.ModuleType("starlette")
    sys.modules.setdefault("starlette", starlette)
    sys.modules.setdefault("starlette.responses", responses)

    db = types.ModuleType("app.db")
    db.__path__ = []
    models = types.ModuleType("app.db.models")
    models.__path__ = []
    user_module = types.ModuleType("app.db.models.user")

    class User:
        status = _Column()
        telegram_id = _Column()

    user_module.User = User
    sys.modules.setdefault("app.db", db)
    sys.modules.setdefault("app.db.models", models)
    sys.modules.setdefault("app.db.models.user", user_module)

    support = types.ModuleType("app.services.support_contact_service")
    support.get_admin_contact_url = lambda session: ""
    auth = types.ModuleType("app.services.telegram_webapp_auth")
    auth.extract_verified_webapp_user_id = lambda init_data, bot_token: None
    sys.modules.setdefault("app.services.support_contact_service", support)
    sys.modules.setdefault("app.services.telegram_webapp_auth", auth)

    spec = importlib.util.spec_from_file_location(
        "_blocked_user_guard_under_test",
        ROOT / "app/services/blocked_user_guard.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


try:
    from app.services import blocked_user_guard as guard
except ModuleNotFoundError as exc:
    if exc.name != "sqlalchemy":
        raise
    guard = _load_guard_with_dependency_stubs()


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, status):
        self.status = status

    async def execute(self, _query):
        await asyncio.sleep(0.01)
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


class BlockedUserGuardCacheCoalescingTest(unittest.TestCase):
    def setUp(self):
        guard.invalidate()

    def tearDown(self):
        guard.invalidate()

    def test_parallel_cache_miss_shares_one_db_lookup(self):
        sessions = []
        maker = _session_maker("free", sessions)

        async def run_many():
            return await asyncio.gather(
                *(guard.is_blocked_telegram_id(maker, 5) for _ in range(6))
            )

        self.assertEqual(asyncio.run(run_many()), [False] * 6)
        self.assertEqual(len(sessions), 1)

    def test_invalidate_forces_refetch(self):
        sessions = []
        maker = _session_maker("blocked", sessions)
        self.assertTrue(asyncio.run(guard.is_blocked_telegram_id(maker, 5)))
        guard.invalidate(5)
        self.assertTrue(asyncio.run(guard.is_blocked_telegram_id(maker, 5)))
        self.assertEqual(len(sessions), 2)


if __name__ == "__main__":
    unittest.main()
