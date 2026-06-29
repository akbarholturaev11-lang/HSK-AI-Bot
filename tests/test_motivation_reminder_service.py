import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.motivation_reminder_service import MotivationReminderService
from app.services.notification_template_service import KEY_PASSED, default_text


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


class MotivationReminderServiceRankChangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_gets_notification_when_their_rank_improves(self):
        service = MotivationReminderService(SimpleNamespace())
        service.templates = SimpleNamespace(
            resolve=AsyncMock(return_value={"text": "ok", "media_type": "none", "media_path": None})
        )
        service._send = AsyncMock(return_value=True)
        local_day = date(2026, 6, 29)
        profile = SimpleNamespace(
            user_id=1,
            last_known_rank=3,
            motivation_overtaken_date=None,
            xp_total=120,
        )
        user = SimpleNamespace(full_name="Akbar", username=None)
        below_profile = SimpleNamespace(user_id=2, xp_total=100)
        below_user = SimpleNamespace(full_name="Opponent", username=None)
        members = [
            (profile, user, 155),
            (below_profile, below_user, 120),
        ]

        sent = await service._maybe_passed(
            SimpleNamespace(), profile, user, "uz", 1, members, local_day
        )

        self.assertTrue(sent)
        service.templates.resolve.assert_awaited_once_with(KEY_PASSED, "uz")
        self.assertIsNone(profile.motivation_overtaken_date)
        fields = service._send.await_args.args[4]
        self.assertEqual(fields["name"], "Opponent")
        self.assertEqual(fields["rank"], 1)
        self.assertEqual(fields["xp_gap"], 35)

    async def test_rank_improvement_needs_existing_baseline(self):
        service = MotivationReminderService(SimpleNamespace())
        service.templates = SimpleNamespace(resolve=AsyncMock())
        service._send = AsyncMock()
        profile = SimpleNamespace(last_known_rank=None, motivation_overtaken_date=None)

        sent = await service._maybe_passed(
            SimpleNamespace(), profile, SimpleNamespace(), "uz", 1, [], date(2026, 6, 29)
        )

        self.assertFalse(sent)
        service.templates.resolve.assert_not_called()
        service._send.assert_not_called()

    def test_rank_passed_default_text_exists(self):
        self.assertIn("{name}", default_text(KEY_PASSED, "uz"))
        self.assertIn("{rank}", default_text(KEY_PASSED, "ru"))


if __name__ == "__main__":
    unittest.main()
