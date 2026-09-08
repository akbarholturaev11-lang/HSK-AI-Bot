"""Admin limit va ko'chirish endpointlari.

Bu endpointlar bepul daraja chegaralarini va dvigatelning yoqilishini
boshqaradi — ya'ni to'g'ridan-to'g'ri daromadga tegadi. `app/main.py` dagi
admin endpointlarining birortasi test bilan qoplanmagan; bular qoplanadi.

Eng muhim uch tekshiruv:

* admin bo'lmagan hech kim bu yerga yeta olmaydi;
* yaroqsiz tahrir JIMGINA tuzatilmaydi, `400` qaytadi;
* bepul darajani butunlay cheksiz qilib qo'yish rad etiladi.
"""

import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.admin_entitlements import create_admin_entitlements_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.entitlement_shadow_event import EntitlementShadowEvent
from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import WINDOW_DAILY, LimitConfigService
from app.services.entitlements.shadow import (
    MODE_ENGINE,
    MODE_SHADOW,
    ROLLOUT_MIN_SAMPLES,
)
from app.services.entitlements.state import EntitlementState


ADMIN_ID = 777
OUTSIDER_ID = 12


class _Guard:
    """`app/main.py` dagi admin tekshiruvining test o'rnini bosuvchi."""

    def __init__(self):
        self.telegram_id = ADMIN_ID

    def __call__(self, request):
        header = request.headers.get("X-Test-Admin")
        if header is None:
            return None, JSONResponse(
                status_code=401,
                content={"ok": False, "error": "invalid_telegram_init_data"},
            )
        telegram_id = int(header)
        if telegram_id != ADMIN_ID:
            return None, JSONResponse(
                status_code=403, content={"ok": False, "error": "admin_only"}
            )
        return telegram_id, None


class AdminLimitsApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

        self.app = FastAPI()
        self.app.include_router(
            create_admin_entitlements_router(
                session_factory=self.sessions, admin_guard=_Guard()
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://admin.test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.dispose()

    async def _post(self, path, body=None, *, admin=ADMIN_ID):
        headers = {} if admin is None else {"X-Test-Admin": str(admin)}
        return await self.client.post(path, json=body or {}, headers=headers)

    # --- ruxsat -----------------------------------------------------------

    async def test_an_anonymous_caller_is_refused(self):
        for path in (
            "/api/admin-miniapp/limits",
            "/api/admin-miniapp/limits/save",
            "/api/admin-miniapp/entitlement-shadow",
            "/api/admin-miniapp/entitlement-shadow/rollout",
        ):
            with self.subTest(path=path):
                response = await self._post(path, admin=None)
                self.assertEqual(401, response.status_code)

    async def test_a_non_admin_is_refused(self):
        response = await self._post("/api/admin-miniapp/limits", admin=OUTSIDER_ID)
        self.assertEqual(403, response.status_code)

    # --- o'qish -----------------------------------------------------------

    async def test_reading_without_a_saved_row_returns_the_defaults(self):
        response = await self._post("/api/admin-miniapp/limits")

        self.assertEqual(200, response.status_code)
        limits = response.json()["limits"]
        self.assertEqual(
            2, limits["plans"][EntitlementState.FREE][A.LESSON_START]["limit"]
        )
        self.assertIsNone(
            limits["plans"][EntitlementState.PRO_ACTIVE]["*"]["limit"]
        )
        self.assertTrue(limits["trial"]["enabled"])

    # --- yozish -----------------------------------------------------------

    async def test_a_saved_limit_takes_effect_without_a_restart(self):
        saved = await self._post(
            "/api/admin-miniapp/limits/save",
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": 3, "window": WINDOW_DAILY},
                        A.AI_TEXT: {"limit": 8, "window": WINDOW_DAILY},
                    }
                }
            },
        )
        self.assertEqual(200, saved.status_code)

        # Yangi sessiya — ya'ni qiymat haqiqatan saqlangan, keshda emas.
        async with self.sessions() as session:
            config = await LimitConfigService(session).get_config()

        self.assertEqual(3, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)
        self.assertEqual(8, config.limit_for(EntitlementState.FREE, A.AI_TEXT).limit)
        self.assertEqual(ADMIN_ID, config.updated_by_telegram_id)

    async def test_untouched_plans_keep_their_defaults(self):
        await self._post(
            "/api/admin-miniapp/limits/save",
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": 1, "window": WINDOW_DAILY}
                    }
                }
            },
        )

        async with self.sessions() as session:
            config = await LimitConfigService(session).get_config()

        self.assertTrue(
            config.limit_for(EntitlementState.PRO_ACTIVE, A.LESSON_START).unlimited
        )
        self.assertEqual(
            0, config.limit_for(EntitlementState.BLOCKED, A.LESSON_START).limit
        )

    async def test_an_all_unlimited_free_tier_is_refused(self):
        response = await self._post(
            "/api/admin-miniapp/limits/save",
            {"plans": {EntitlementState.FREE: {"*": {"limit": None, "window": "none"}}}},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_limits_config", response.json()["error"])

    async def test_a_bad_edit_is_refused_rather_than_quietly_fixed(self):
        bad = [
            {},
            {"plans": {"WAT": {A.LESSON_START: {"limit": 1, "window": WINDOW_DAILY}}}},
            {"plans": {EntitlementState.FREE: {"nope.nope": {"limit": 1, "window": WINDOW_DAILY}}}},
            {"plans": {EntitlementState.FREE: {A.LESSON_START: {"limit": 1, "window": "weekly"}}}},
            {"plans": {EntitlementState.FREE: {A.LESSON_START: {"limit": -5, "window": WINDOW_DAILY}}}},
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                response = await self._post("/api/admin-miniapp/limits/save", payload)
                self.assertEqual(400, response.status_code)

        # Rad etilgan tahrirdan keyin ham eski qiymat joyida.
        async with self.sessions() as session:
            config = await LimitConfigService(session).get_config()
        self.assertEqual(2, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)

    async def test_the_trial_kill_switch_is_one_save_away(self):
        await self._post(
            "/api/admin-miniapp/limits/save",
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": 2, "window": WINDOW_DAILY}
                    }
                },
                "trial": {"enabled": False, "disabled_reason": "fake akkauntlar"},
            },
        )

        async with self.sessions() as session:
            config = await LimitConfigService(session).get_config()

        self.assertFalse(config.trial["enabled"])
        self.assertEqual("fake akkauntlar", config.trial["disabled_reason"])


class AdminShadowReportApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

        self.app = FastAPI()
        self.app.include_router(
            create_admin_entitlements_router(
                session_factory=self.sessions, admin_guard=_Guard()
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://admin.test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.dispose()

    async def _post(self, path, body=None):
        return await self.client.post(
            path, json=body or {}, headers={"X-Test-Admin": str(ADMIN_ID)}
        )

    async def _seed(self, *, action, client, agree, count):
        from datetime import datetime, timezone

        async with self.sessions() as session:
            for index in range(count):
                session.add(
                    EntitlementShadowEvent(
                        telegram_id=2000 + index,
                        action=action,
                        client=client,
                        agree=agree,
                        legacy_allowed=agree,
                        engine_allowed=True,
                        day_key="d0",
                        created_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()

    async def test_an_empty_report_is_not_an_error(self):
        response = await self._post("/api/admin-miniapp/entitlement-shadow")

        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json()["rows"])
        self.assertEqual(ROLLOUT_MIN_SAMPLES, response.json()["min_samples"])

    async def test_a_clean_busy_action_is_marked_ready(self):
        await self._seed(
            action=A.PRACTICE_RECOGNITION,
            client="miniapp",
            agree=True,
            count=ROLLOUT_MIN_SAMPLES,
        )

        row = (await self._post("/api/admin-miniapp/entitlement-shadow")).json()["rows"][0]

        self.assertTrue(row["ready_to_enable"])
        self.assertNotIn("examples", row)

    async def test_a_mismatch_comes_with_examples(self):
        await self._seed(
            action=A.PRACTICE_MEMORIZE, client="android", agree=False, count=4
        )

        row = (await self._post("/api/admin-miniapp/entitlement-shadow")).json()["rows"][0]

        self.assertEqual(4, row["disagreements"])
        self.assertFalse(row["ready_to_enable"])
        self.assertEqual(3, len(row["examples"]))

    async def test_enabling_one_action_is_a_settings_write(self):
        response = await self._post(
            "/api/admin-miniapp/entitlement-shadow/rollout",
            {"default": MODE_SHADOW, "actions": {A.PRACTICE_RECOGNITION: MODE_ENGINE}},
        )

        self.assertEqual(200, response.status_code)
        rollout = response.json()["rollout"]
        self.assertEqual(MODE_ENGINE, rollout["actions"][A.PRACTICE_RECOGNITION])
        self.assertEqual(ADMIN_ID, rollout["updated_by_telegram_id"])

        # Va uni qaytarish ham bitta yozuv.
        back = await self._post(
            "/api/admin-miniapp/entitlement-shadow/rollout", {"default": MODE_SHADOW}
        )
        self.assertEqual({}, back.json()["rollout"]["actions"])

    async def test_an_invalid_rollout_is_refused(self):
        response = await self._post(
            "/api/admin-miniapp/entitlement-shadow/rollout",
            {"default": "wat"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("invalid_entitlement_rollout", response.json()["error"])

    async def test_the_report_window_is_bounded(self):
        response = await self._post(
            "/api/admin-miniapp/entitlement-shadow", {"days": 9999}
        )
        self.assertEqual(90, response.json()["days"])

        response = await self._post(
            "/api/admin-miniapp/entitlement-shadow", {"days": "wat"}
        )
        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()
