"""The daily goal cannot have a negative amount left.

A learner who passed their goal was shown "45 / 40 XP · -5 qoldi" — the ring
already read 100% beside it. `dailyGoal - todayXp` was printed straight, so
every XP past the goal counted down below zero.

Pinned here rather than left to review because it is one character wide and
reads as correct: the subtraction is right, it is the floor that is missing.
"""

import re
import unittest
from pathlib import Path


MINI_APP = Path("app/static/course-v3.html").read_text(encoding="utf-8")


class DailyGoalLeftTests(unittest.TestCase):
    def test_the_remainder_is_floored_at_zero(self):
        self.assertIn("Math.max(0,dailyGoal-todayXp)", MINI_APP)

    def test_the_raw_subtraction_is_not_printed_anywhere(self):
        # `+(dailyGoal-todayXp)+` inside a template is the shape that shipped.
        self.assertNotRegex(MINI_APP, r"\+\(dailyGoal\s*-\s*todayXp\)\s*\+")

    def test_the_goal_and_the_progress_are_still_shown(self):
        # The fix must not have eaten the numbers either side of it.
        self.assertIn("todayXp+' / '+dailyGoal+' XP", MINI_APP)


if __name__ == "__main__":
    unittest.main()
