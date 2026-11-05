"""A day's frozen plans survive alternating levels and unchanged preferences."""
import unittest
from types import SimpleNamespace

from app.services.course_today_service import CourseTodayService as Service


class PlanStorageTests(unittest.TestCase):
    def test_legacy_single_list_is_still_read(self):
        row = SimpleNamespace(daily_plan_key="v1:hsk1:2026-11-05", daily_plan_json='[{"t":"a"}]')
        self.assertEqual(Service._stored_tasks(row, "v1:hsk1:2026-11-05"), [{"t": "a"}])
        self.assertIsNone(Service._stored_tasks(row, "v1:hsk2:2026-11-05"))

    def test_two_levels_on_one_day_keep_their_own_plan(self):
        row = SimpleNamespace(daily_plan_key=None, daily_plan_json=None)
        Service._store_tasks(row, "v1:hsk1:2026-11-05", [{"t": "a"}], "2026-11-05")
        Service._store_tasks(row, "v1:nhsk1:2026-11-05", [{"t": "b"}], "2026-11-05")
        self.assertEqual(Service._stored_tasks(row, "v1:hsk1:2026-11-05"), [{"t": "a"}])
        self.assertEqual(Service._stored_tasks(row, "v1:nhsk1:2026-11-05"), [{"t": "b"}])

    def test_new_day_drops_old_plans(self):
        row = SimpleNamespace(daily_plan_key=None, daily_plan_json=None)
        Service._store_tasks(row, "v1:hsk1:2026-11-05", [{"t": "a"}], "2026-11-05")
        Service._store_tasks(row, "v1:hsk1:2026-11-06", [{"t": "c"}], "2026-11-06")
        self.assertIsNone(Service._stored_tasks(row, "v1:hsk1:2026-11-05"))


if __name__ == "__main__":
    unittest.main()
