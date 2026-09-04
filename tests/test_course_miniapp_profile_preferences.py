import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.course_miniapp_profile_service import (
    COURSE_DAILY_TARGETS,
    DAILY_GOAL_XP_MAX,
    DAILY_GOAL_XP_MIN,
    CourseMiniAppProfileService,
)


def profile(**kwargs) -> SimpleNamespace:
    base = {
        "goal": "hsk_exam",
        "daily_minutes": 10,
        "start_mode": "lesson_1",
        "timezone_offset_minutes": 0,
        "preferred_focus": None,
        "daily_goal_xp": None,
        "onboarding_completed_at": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def service() -> CourseMiniAppProfileService:
    session = AsyncMock()
    return CourseMiniAppProfileService(session)


class PreferredFocusTests(unittest.TestCase):
    def test_known_values_are_accepted_case_insensitively(self):
        normalize = CourseMiniAppProfileService.normalize_preferred_focus
        for value in ("speaking", "listening", "vocabulary", "grammar", "none"):
            self.assertEqual(normalize(value), value)
            self.assertEqual(normalize(value.upper()), value)
            self.assertEqual(normalize(f"  {value} "), value)

    def test_missing_value_means_not_asked_yet(self):
        normalize = CourseMiniAppProfileService.normalize_preferred_focus
        self.assertIsNone(normalize(None))
        self.assertIsNone(normalize(""))
        self.assertIsNone(normalize("   "))

    def test_none_answer_is_not_the_same_as_missing(self):
        # "none" = o'quvchi "farqi yo'q" dedi; None = savol berilmagan.
        self.assertEqual(CourseMiniAppProfileService.normalize_preferred_focus("none"), "none")
        self.assertIsNone(CourseMiniAppProfileService.normalize_preferred_focus(None))

    def test_unknown_value_is_rejected(self):
        with self.assertRaises(ValueError):
            CourseMiniAppProfileService.normalize_preferred_focus("writing")


class DailyPlanSizeTests(unittest.TestCase):
    def test_every_supported_daily_minutes_has_a_plan_size(self):
        expected = {5: 1, 10: 2, 15: 2, 20: 3, 30: 4}
        for minutes, size in expected.items():
            self.assertEqual(CourseMiniAppProfileService.daily_plan_size(minutes), size)

    def test_thirty_minutes_gets_more_tasks_than_twenty(self):
        # Aks holda ikkala sozlama bir xil natija berardi.
        self.assertGreater(
            CourseMiniAppProfileService.daily_plan_size(30),
            CourseMiniAppProfileService.daily_plan_size(20),
        )

    def test_unknown_or_missing_minutes_fall_back_to_ten_minute_plan(self):
        for value in (None, 0, 7, "x"):
            self.assertEqual(CourseMiniAppProfileService.daily_plan_size(value), 2)


class DailyGoalXpTests(unittest.TestCase):
    def test_goal_is_derived_from_daily_minutes_when_not_chosen(self):
        expected = {5: 25, 10: 30, 15: 35, 20: 40, 30: 50}
        for minutes, goal_xp in expected.items():
            self.assertEqual(
                CourseMiniAppProfileService.resolve_daily_goal_xp(
                    profile(daily_minutes=minutes)
                ),
                goal_xp,
            )

    def test_stored_choice_wins_over_derived_value(self):
        self.assertEqual(
            CourseMiniAppProfileService.resolve_daily_goal_xp(
                profile(daily_minutes=5, daily_goal_xp=120)
            ),
            120,
        )

    def test_stored_choice_is_clamped(self):
        self.assertEqual(
            CourseMiniAppProfileService.resolve_daily_goal_xp(
                profile(daily_goal_xp=99999)
            ),
            DAILY_GOAL_XP_MAX,
        )
        self.assertEqual(
            CourseMiniAppProfileService.resolve_daily_goal_xp(profile(daily_goal_xp=1)),
            DAILY_GOAL_XP_MIN,
        )

    def test_corrupt_stored_value_falls_back_to_derived(self):
        self.assertEqual(
            CourseMiniAppProfileService.resolve_daily_goal_xp(
                profile(daily_minutes=20, daily_goal_xp="oops")
            ),
            40,
        )

    def test_unknown_daily_minutes_falls_back_to_ten_minute_goal(self):
        self.assertEqual(
            CourseMiniAppProfileService.resolve_daily_goal_xp(profile(daily_minutes=7)),
            30,
        )

    def test_plan_of_one_or_two_tasks_can_actually_fill_the_goal(self):
        # Reja "pol", maqsad "shift": kichik rejalar maqsadni to'liq yopishi
        # kerak, aks holda halqa hech qachon to'lmaydi.
        lesson_xp, mistake_review_xp, first_activity_bonus = 20, 5, 5
        one_task = lesson_xp + first_activity_bonus
        two_tasks = one_task + mistake_review_xp
        self.assertGreaterEqual(one_task, COURSE_DAILY_TARGETS[5][1])
        self.assertGreaterEqual(two_tasks, COURSE_DAILY_TARGETS[10][1])


class SavePreferencesTests(unittest.IsolatedAsyncioTestCase):
    async def test_focus_is_stored_when_supplied(self):
        item = profile()
        await service().save_preferences(
            item,
            goal="travel",
            daily_minutes=15,
            start_mode="lesson_1",
            preferred_focus="speaking",
        )
        self.assertEqual(item.preferred_focus, "speaking")
        self.assertEqual(item.goal, "travel")
        self.assertEqual(item.daily_minutes, 15)

    async def test_existing_focus_survives_a_call_that_omits_it(self):
        # Bot onboarding oqimi fokusni bilmaydi — u yozgan preferensiya
        # o'quvchining oldingi tanlovini tozalab yubormasligi kerak.
        item = profile(preferred_focus="listening")
        await service().save_preferences(
            item,
            goal="hsk_exam",
            daily_minutes=10,
            start_mode="continue",
        )
        self.assertEqual(item.preferred_focus, "listening")

    async def test_unknown_focus_is_rejected_before_anything_is_written(self):
        item = profile(goal="hsk_exam")
        with self.assertRaises(ValueError):
            await service().save_preferences(
                item,
                goal="travel",
                daily_minutes=15,
                start_mode="lesson_1",
                preferred_focus="dancing",
            )
        self.assertEqual(item.goal, "hsk_exam")


class SetDailyGoalXpTests(unittest.IsolatedAsyncioTestCase):
    async def test_value_is_clamped_and_returned_resolved(self):
        item = profile(daily_minutes=10)
        resolved = await service().set_daily_goal_xp(item, 99999)
        self.assertEqual(item.daily_goal_xp, DAILY_GOAL_XP_MAX)
        self.assertEqual(resolved, DAILY_GOAL_XP_MAX)

    async def test_none_returns_to_automatic_mode(self):
        item = profile(daily_minutes=30, daily_goal_xp=200)
        resolved = await service().set_daily_goal_xp(item, None)
        self.assertIsNone(item.daily_goal_xp)
        self.assertEqual(resolved, 50)


if __name__ == "__main__":
    unittest.main()
