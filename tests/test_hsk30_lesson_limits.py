import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.entitlements import actions as A
from app.services.entitlements.lesson_access import LessonAccessService


def _decision(payload):
    return SimpleNamespace(as_dict=lambda **_: dict(payload))


def _user():
    return SimpleNamespace(
        id=7,
        telegram_id=7001,
        language="uz",
        status="free",
        payment_status="none",
        end_date=None,
    )


def _hsk30_access_payload():
    return {
        "feature_enabled": True,
        "paid_access": False,
        "permanently_unlocked": True,
        "allowed": True,
        "reason": "permanent_unlock",
    }


class Hsk30LessonLimitTests(unittest.IsolatedAsyncioTestCase):
    async def _patched_status(self, *, consume, check_payload, consume_payload=None):
        session = SimpleNamespace(execute=AsyncMock())
        service = LessonAccessService(session)
        service._reserved = AsyncMock(return_value=False)
        user = _user()

        access = SimpleNamespace(
            allowed=True,
            reason="permanent_unlock",
            payload=lambda: _hsk30_access_payload(),
        )
        track = SimpleNamespace(
            hsk30_access=AsyncMock(return_value=access),
            hsk30_feature=SimpleNamespace(
                is_level_live=AsyncMock(return_value=True)
            ),
        )

        with (
            patch(
                "app.services.entitlements.lesson_access.CourseTrackService",
                return_value=track,
            ),
            patch(
                "app.services.entitlements.lesson_access.CourseAccessPolicyService"
            ) as policy_cls,
            patch(
                "app.services.entitlements.lesson_access.EntitlementEngine"
            ) as engine_cls,
        ):
            policy_cls.return_value.get_policy = AsyncMock(
                return_value=SimpleNamespace(free_active=False)
            )
            engine = engine_cls.return_value
            engine.check = AsyncMock(return_value=_decision(check_payload))
            engine.consume = AsyncMock(
                return_value=_decision(consume_payload or check_payload)
            )

            result = await service.status(
                user,
                level="nhsk1",
                lesson_order=3 if consume else 1,
                completed=0,
                consume=consume,
            )

            return result, engine, user

    async def test_one_time_hsk30_unlock_keeps_the_free_lesson_limit(self):
        result, engine, user = await self._patched_status(
            consume=False,
            check_payload={
                "ok": True,
                "allowed": True,
                "limit": 2,
                "used": 0,
                "remaining": 2,
                "window": "daily",
                "reset_at": "2026-10-04T00:00:00+00:00",
            },
        )

        engine.check.assert_awaited_once_with(user, A.LESSON_START)
        engine.consume.assert_not_awaited()
        self.assertTrue(result["allowed"])
        self.assertEqual(2, result["limit"])
        self.assertEqual(2, result["remaining"])
        self.assertEqual("daily", result["window"])
        self.assertTrue(result["hsk30_access"]["permanently_unlocked"])
        self.assertTrue(result["hsk30_access"]["level_live"])

    async def test_hsk30_start_uses_the_admin_configured_engine_limit(self):
        result, engine, user = await self._patched_status(
            consume=True,
            check_payload={
                "ok": True,
                "allowed": True,
                "limit": 7,
                "used": 6,
                "remaining": 1,
                "window": "daily",
                "reset_at": "2026-10-04T00:00:00+00:00",
            },
            consume_payload={
                "ok": False,
                "allowed": False,
                "error": "free_feature_limit_reached",
                "limit": 7,
                "used": 7,
                "remaining": 0,
                "window": "daily",
                "reset_at": "2026-10-04T00:00:00+00:00",
            },
        )

        engine.consume.assert_awaited_once_with(
            user,
            A.LESSON_START,
            ref="lesson:nhsk1:3",
            notify_bot=None,
        )
        self.assertFalse(result["allowed"])
        self.assertEqual("free_feature_limit_reached", result["error"])
        self.assertEqual(7, result["limit"])
        self.assertEqual(0, result["remaining"])
        self.assertTrue(result["hsk30_access"]["permanently_unlocked"])
        self.assertTrue(result["hsk30_access"]["level_live"])


if __name__ == "__main__":
    unittest.main()
