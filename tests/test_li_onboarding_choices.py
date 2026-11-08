"""Compatibility and input validation for additional Li onboarding choices."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.onboarding_goal_selection import (
    normalize_onboarding_goals,
    normalize_streak_target,
    read_onboarding_goals,
)


class OnboardingChoicesValidationTests(unittest.TestCase):
    def test_multi_goal_is_ordered_and_primary_first(self):
        values = ["hsk_exam", "travel", "daily_communication"]
        self.assertEqual(normalize_onboarding_goals(values, primary_goal="hsk_exam"),
                         tuple(values))
        self.assertIsNone(normalize_onboarding_goals(None, primary_goal="hsk_exam"))

    def test_invalid_goal_arrays_fail_closed(self):
        bad = [[], ["travel", "travel"], ["travel", "secret"],
               ["travel", 2], ["travel"] * 6, "travel", {"value": "travel"}]
        for goals in bad:
            with self.subTest(goals=goals), self.assertRaises(ValueError):
                normalize_onboarding_goals(goals, primary_goal="travel")
        with self.assertRaises(ValueError):
            normalize_onboarding_goals(["travel", "hsk_exam"], primary_goal="hsk_exam")

    def test_legacy_reads_and_malformed_json_fall_back(self):
        self.assertEqual(read_onboarding_goals(None, primary_goal="study_china"),
                         ["study_china"])
        self.assertEqual(read_onboarding_goals('["travel"]', primary_goal="hsk_exam"),
                         ["hsk_exam"])
        self.assertEqual(read_onboarding_goals("invalid", primary_goal="travel"),
                         ["travel"])

    def test_streak_target_is_not_a_streak_count(self):
        for value in (7, 14, 30, 50):
            self.assertEqual(normalize_streak_target(value), value)
        self.assertIsNone(normalize_streak_target(None))
        for value in (0, 1, 6, 31, 365, True, False, "14", 14.0):
            with self.subTest(target=value), self.assertRaises(ValueError):
                normalize_streak_target(value)


class OnboardingChoicesSaveTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SimpleNamespace(flush=AsyncMock())
        self.service = CourseMiniAppProfileService(self.db)

    def profile(self):
        return CourseMiniAppProfile(
            user_id=42, goal="hsk_exam", daily_minutes=10, start_mode="continue",
            timezone_offset_minutes=0, current_streak=6, longest_streak=11,
        )

    async def test_explicit_goals_target_focus_persist_without_xp_change(self):
        p = self.profile()
        await self.service.save_preferences(
            p, goal="hsk_exam", daily_minutes=15, start_mode="lesson_1",
            goals=["hsk_exam", "travel"], streak_target_days=30,
            preferred_focus="speaking", goal_explicit=True, complete_onboarding=True,
        )
        self.assertEqual(json.loads(p.goals_json), ["hsk_exam", "travel"])
        self.assertEqual(p.streak_target_days, 30)
        self.assertEqual(p.preferred_focus, "speaking")
        self.assertEqual(p.current_streak, 6)
        self.assertEqual(p.longest_streak, 11)
        self.assertIsNotNone(p.goal_chosen_at)
        self.assertIsNotNone(p.onboarding_completed_at)
        self.db.flush.assert_awaited_once()

    async def test_old_client_preserves_existing_goals_and_target(self):
        p = self.profile()
        p.goals_json = '["hsk_exam", "travel"]'
        p.streak_target_days = 14
        await self.service.save_preferences(
            p, goal="hsk_exam", daily_minutes=20, start_mode="continue",
        )
        self.assertEqual(json.loads(p.goals_json), ["hsk_exam", "travel"])
        self.assertEqual(p.streak_target_days, 14)

    async def test_old_client_changed_primary_invalidates_stale_array_only(self):
        p = self.profile()
        p.goals_json = '["hsk_exam", "travel"]'
        p.streak_target_days = 50
        await self.service.save_preferences(
            p, goal="travel", daily_minutes=10, start_mode="continue",
        )
        self.assertIsNone(p.goals_json)
        self.assertEqual(p.streak_target_days, 50)
        self.assertEqual(read_onboarding_goals(p.goals_json, primary_goal=p.goal),
                         ["travel"])

    async def test_rejected_choices_do_not_mutate_profile(self):
        p = self.profile()
        with self.assertRaises(ValueError):
            await self.service.save_preferences(
                p, goal="travel", daily_minutes=10, start_mode="continue",
                goals=["hsk_exam", "travel"], streak_target_days=30,
            )
        self.assertEqual(p.goal, "hsk_exam")
        self.db.flush.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
