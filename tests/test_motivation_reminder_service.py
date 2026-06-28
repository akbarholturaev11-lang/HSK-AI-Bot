import unittest

from app.services.motivation_reminder_service import MotivationReminderService


class MotivationReminderServiceTests(unittest.TestCase):
    def test_overtaken_gap_never_claims_zero_xp(self):
        self.assertEqual(MotivationReminderService._xp_gap_to_above(120, 120), 1)
        self.assertEqual(MotivationReminderService._xp_gap_to_above(135, 120), 15)


if __name__ == "__main__":
    unittest.main()
