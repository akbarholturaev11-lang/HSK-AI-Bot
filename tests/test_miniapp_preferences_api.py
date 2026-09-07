"""Kunlik reja sozlamalari: vaqt, fokus va XP maqsadi.

Onboarding faqat daraja va maqsadni so'raydi; kunlik vaqt va fokus birinchi
darsdan keyin so'raladi. XP maqsadi ilgari mijozdagi `dailyGoal=50`
o'zgaruvchi edi va har ochilganda yo'qolardi — endi serverda saqlanadi.
"""

import unittest
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.miniapp_preferences import create_miniapp_preferences_router
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService


VALID_INIT_DATA = "query_id=AAA&user=%7B%22id%22%3A123%7D&hash=deadbeef"


def profile(**kwargs):
    base = {
        "goal": "hsk_exam",
        "goal_chosen_at": None,
        "daily_minutes": 10,
        "preferred_focus": None,
        "daily_goal_xp": None,
        "daily_plan_key": "v1:hsk1:2026-09-05",
        "daily_plan_json": '[{"t":"continue_lesson"}]',
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def build_client(item, *, telegram_id=123, user=SimpleNamespace(id=3, telegram_id=123)):
    @asynccontextmanager
    async def session():
        yield SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

    service = SimpleNamespace(
        get_or_create=AsyncMock(return_value=item),
        set_daily_goal_xp=AsyncMock(
            side_effect=lambda p, v: setattr(p, "daily_goal_xp", v)
            or CourseMiniAppProfileService.resolve_daily_goal_xp(p)
        ),
    )
    app = FastAPI()
    app.include_router(
        create_miniapp_preferences_router(
            session_factory=session,
            settings_obj=SimpleNamespace(BOT_TOKEN="123:test"),
            profile_service_factory=lambda s: service,
        )
    )
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    patches = (
        patch(
            "app.api.miniapp_preferences.extract_verified_webapp_user_id",
            return_value=telegram_id,
        ),
        patch(
            "app.api.miniapp_preferences.UserRepository",
            return_value=SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user)),
        ),
    )
    return client, patches, service


async def post(item, payload, **kwargs):
    client, patches, service = build_client(item, **kwargs)
    async with client:
        with patches[0], patches[1]:
            response = await client.post("/api/v3/preferences", json=payload)
    return response, service


class DailyMinutesTests(unittest.IsolatedAsyncioTestCase):
    async def test_saving_minutes_updates_the_goal_and_plan_size(self):
        item = profile(daily_minutes=10)
        response, _ = await post(item, {"daily_minutes": 30, "initData": VALID_INIT_DATA})

        self.assertEqual(response.status_code, 200)
        body = response.json()["profile"]
        self.assertEqual(item.daily_minutes, 30)
        self.assertEqual(body["daily_goal_xp"], 50)
        self.assertEqual(body["plan_size"], 4)

    async def test_an_unsupported_value_is_rejected(self):
        item = profile()
        response, _ = await post(item, {"daily_minutes": 7, "initData": VALID_INIT_DATA})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(item.daily_minutes, 10)

    async def test_changing_minutes_drops_today_plan_so_it_is_rebuilt(self):
        # Aks holda o'quvchi vaqtni qisqartirib ham eski, uzun rejani
        # ko'rib turaverardi.
        item = profile()
        await post(item, {"daily_minutes": 5, "initData": VALID_INIT_DATA})

        self.assertIsNone(item.daily_plan_key)
        self.assertIsNone(item.daily_plan_json)


class PreferredFocusTests(unittest.IsolatedAsyncioTestCase):
    async def test_focus_is_saved(self):
        item = profile()
        response, _ = await post(
            item, {"preferred_focus": "listening", "initData": VALID_INIT_DATA}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(item.preferred_focus, "listening")
        self.assertEqual(response.json()["profile"]["preferred_focus"], "listening")

    async def test_no_preference_answer_is_a_real_answer(self):
        # "Farqi yo'q" javobi ham javob: savol qayta so'ralmasligi kerak.
        item = profile(goal_chosen_at=datetime.now(timezone.utc))
        await post(item, {"preferred_focus": "none", "initData": VALID_INIT_DATA})

        self.assertEqual(item.preferred_focus, "none")
        self.assertFalse(
            CourseMiniAppProfileService.study_setup(item, completed_parts=9)["pending"]
        )

    async def test_unknown_focus_is_rejected(self):
        item = profile()
        response, _ = await post(
            item, {"preferred_focus": "dancing", "initData": VALID_INIT_DATA}
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(item.preferred_focus)


class DailyGoalTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_goal_is_stored_and_marked_custom(self):
        item = profile()
        response, _ = await post(item, {"daily_goal_xp": 80, "initData": VALID_INIT_DATA})

        body = response.json()["profile"]
        self.assertEqual(body["daily_goal_xp"], 80)
        self.assertTrue(body["daily_goal_is_custom"])

    async def test_goal_outside_the_range_is_rejected(self):
        item = profile()
        response, _ = await post(item, {"daily_goal_xp": 9999, "initData": VALID_INIT_DATA})

        self.assertEqual(response.status_code, 422)

    async def test_auto_returns_the_goal_to_the_daily_minutes_value(self):
        item = profile(daily_minutes=20, daily_goal_xp=200)
        response, _ = await post(item, {"daily_goal_auto": True, "initData": VALID_INIT_DATA})

        self.assertIsNone(item.daily_goal_xp)
        self.assertEqual(response.json()["profile"]["daily_goal_xp"], 40)

    async def test_custom_goal_and_auto_together_are_rejected(self):
        item = profile()
        response, _ = await post(
            item,
            {"daily_goal_xp": 40, "daily_goal_auto": True, "initData": VALID_INIT_DATA},
        )

        self.assertEqual(response.status_code, 422)

    async def test_changing_only_the_goal_keeps_today_plan(self):
        # XP maqsadi vazifalar tarkibiga ta'sir qilmaydi — reja buzilmasin.
        item = profile()
        await post(item, {"daily_goal_xp": 40, "initData": VALID_INIT_DATA})

        self.assertEqual(item.daily_plan_key, "v1:hsk1:2026-09-05")


class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_an_empty_body_changes_nothing(self):
        item = profile()
        response, service = await post(item, {"initData": VALID_INIT_DATA})

        self.assertEqual(response.status_code, 422)
        service.get_or_create.assert_not_awaited()

    async def test_unsigned_request_is_rejected(self):
        item = profile()
        response, service = await post(
            item, {"daily_minutes": 15}, telegram_id=None
        )

        self.assertEqual(response.status_code, 401)
        service.get_or_create.assert_not_awaited()

    async def test_unknown_user_is_refused(self):
        item = profile()
        response, service = await post(
            item, {"daily_minutes": 15, "initData": VALID_INIT_DATA}, user=None
        )

        self.assertEqual(response.status_code, 403)
        service.get_or_create.assert_not_awaited()

    async def test_unexpected_fields_are_rejected(self):
        item = profile()
        response, _ = await post(
            item, {"daily_minutes": 15, "nickname": "x", "initData": VALID_INIT_DATA}
        )

        self.assertEqual(response.status_code, 422)

    async def test_goal_can_be_answered_after_onboarding(self):
        # Maqsad savoli onboardingga KEYIN qo'shildi, shuning uchun eski
        # o'quvchilardan u birinchi darsdan keyin so'raladi.
        item = profile()
        response, _ = await post(item, {"goal": "travel", "initData": VALID_INIT_DATA})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(item.goal, "travel")
        self.assertIsNotNone(item.goal_chosen_at)
        self.assertFalse(
            CourseMiniAppProfileService.study_setup(item, completed_parts=9)["pending_goal"]
        )

    async def test_answering_the_goal_rebuilds_todays_plan(self):
        # Aks holda o'quvchi maqsadni o'zgartirib ham eski rejani ko'raverardi.
        item = profile()
        await post(item, {"goal": "daily_communication", "initData": VALID_INIT_DATA})

        self.assertIsNone(item.daily_plan_key)


class StudySetupPendingTests(unittest.TestCase):
    def test_question_waits_until_the_first_part_is_finished(self):
        item = profile()
        self.assertFalse(
            CourseMiniAppProfileService.study_setup(item, completed_parts=0)["pending"]
        )
        self.assertTrue(
            CourseMiniAppProfileService.study_setup(item, completed_parts=1)["pending"]
        )

    def test_question_is_not_repeated_once_answered(self):
        item = profile(
            preferred_focus="grammar", goal_chosen_at=datetime.now(timezone.utc)
        )
        self.assertFalse(
            CourseMiniAppProfileService.study_setup(item, completed_parts=40)["pending"]
        )

    def test_an_existing_learner_is_asked_for_a_goal(self):
        # Maqsad savoli onboardingga keyin qo'shildi: eski o'quvchida `goal`
        # bor, lekin u jadval defaulti — tanlov emas.
        item = profile(preferred_focus="grammar")
        setup = CourseMiniAppProfileService.study_setup(item, completed_parts=40)

        self.assertTrue(setup["pending_goal"])
        self.assertTrue(setup["pending"])
        self.assertFalse(setup["goal_chosen"])


if __name__ == "__main__":
    unittest.main()
