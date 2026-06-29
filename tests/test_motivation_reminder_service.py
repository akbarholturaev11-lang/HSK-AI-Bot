import unittest
from types import SimpleNamespace

from app.services.motivation_reminder_service import MotivationReminderService
from app.services.notification_template_service import MOTIVATION_KEYS


class _EmptyRows:
    def all(self):
        return []


class _CaptureSession:
    def __init__(self):
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        return _EmptyRows()


class MotivationReminderServiceTests(unittest.TestCase):
    def test_overtaken_gap_never_claims_zero_xp(self):
        self.assertEqual(MotivationReminderService._xp_gap_to_above(120, 120), 1)
        self.assertEqual(MotivationReminderService._xp_gap_to_above(135, 120), 15)

    def test_profile_offset_respects_saved_user_timezone(self):
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=0)
            ),
            0,
        )
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=300)
            ),
            300,
        )
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=999)
            ),
            840,
        )
        self.assertEqual(
            MotivationReminderService._profile_offset(
                SimpleNamespace(timezone_offset_minutes=None)
            ),
            300,
        )


class MotivationReminderServiceQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_reminders_are_not_limited_to_paid_active_users(self):
        session = _CaptureSession()

        await MotivationReminderService(session).send_due_reminders(SimpleNamespace())

        compiled = str(session.queries[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("blocked", compiled)
        self.assertNotIn("users.status = 'active'", compiled)


class MotivationReminderServiceRankChangeTests(unittest.TestCase):
    def test_rank_passed_is_not_a_chat_notification_template(self):
        self.assertNotIn("rating_passed", MOTIVATION_KEYS)


if __name__ == "__main__":
    unittest.main()
