"""The daily goal cannot have a negative amount left.

A learner who passed their goal was shown "45 / 40 XP · -5 qoldi" — the ring
already read 100% beside it. `dailyGoal - todayXp` was printed straight, so
every XP past the goal counted down below zero.

The profile "X / Y XP · N qoldi" block was later removed by the owner-merged
compact profile redesign (#161, b24371ef). These checks keep the original
regression closed for any remaining or reintroduced daily-goal display.
"""

import re
import unittest
from pathlib import Path


MINI_APP = Path("app/static/course-v3.html").read_text(encoding="utf-8")


class DailyGoalLeftTests(unittest.TestCase):
    def test_the_remainder_is_floored_at_zero(self):
        # Any "goal minus done" expression must be floored at zero.
        for match in re.finditer(r"dailyGoal\s*-\s*(?:todayXp|dx|dailyXpVal\(\))", MINI_APP):
            window = MINI_APP[max(0, match.start() - 12):match.start()]
            self.assertIn("Math.max(0,", window, match.group(0))

    def test_the_raw_subtraction_is_not_printed_anywhere(self):
        # `+(dailyGoal-todayXp)+` inside a template is the shape that shipped.
        self.assertNotRegex(MINI_APP, r"\+\(dailyGoal\s*-\s*todayXp\)\s*\+")

    def test_the_goal_and_the_progress_are_still_shown(self):
        # The daily ring clamps progress at 100% and the goal stays visible
        # in settings after the compact profile redesign.
        self.assertIn("r=Math.min(dx/dailyGoal,1)", MINI_APP)
        self.assertIn('dailyGoal+" XP"', MINI_APP)


if __name__ == "__main__":
    unittest.main()
