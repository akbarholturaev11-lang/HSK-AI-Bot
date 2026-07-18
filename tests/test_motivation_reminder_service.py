import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.bot.keyboards.course import course_intro_keyboard
from app.db.models.course_miniapp_event import (
    CLIENT_COURSE_MINIAPP_EVENT_NAMES,
    COURSE_MINIAPP_EVENT_NAMES,
    CourseMiniAppEvent,
)
from app.services.motivation_reminder_service import (
    D1_RECOVERY_ASSIGNED_EVENT,
    D1_RECOVERY_EXPERIMENT,
    D1_RECOVERY_FAILED_EVENT,
    D1_RECOVERY_SENT_EVENT,
    MotivationReminderService,
    _button,
    _d1_recovery_arm,
    _d1_recovery_states,
)
from app.services.notification_template_service import (
    KEY_D1_RECOVERY,
    KEY_LESSON_UNFINISHED,
    MOTIVATION_KEYS,
    default_text,
)


class _EmptyRows:
    def all(self):
        return []

    def scalars(self):
        return self


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def scalars(self):
        return self


class _SequenceSession:
    def __init__(self, results):
        self.results = list(results)
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        return self.results.pop(0)


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

    def test_lesson_unfinished_template_is_registered(self):
        self.assertIn(KEY_LESSON_UNFINISHED, MOTIVATION_KEYS)
        self.assertIn("{lesson}", default_text(KEY_LESSON_UNFINISHED, "uz"))

    def test_d1_recovery_template_and_server_only_events_are_registered(self):
        self.assertIn(KEY_D1_RECOVERY, MOTIVATION_KEYS)
        self.assertIn("{lesson}", default_text(KEY_D1_RECOVERY, "uz"))
        for event_name in (
            D1_RECOVERY_ASSIGNED_EVENT,
            D1_RECOVERY_SENT_EVENT,
            D1_RECOVERY_FAILED_EVENT,
        ):
            self.assertIn(event_name, COURSE_MINIAPP_EVENT_NAMES)
            self.assertNotIn(event_name, CLIENT_COURSE_MINIAPP_EVENT_NAMES)

    def test_lesson_label_uses_level_and_order(self):
        event = CourseMiniAppEvent(
            telegram_id=1001,
            event_name="lesson_started",
            level="hsk2",
            lesson_order=4,
        )
        self.assertEqual(
            MotivationReminderService._lesson_label(event, "uz"),
            "HSK2 4-dars",
        )

    def test_local_day_bounds_respect_offset(self):
        start, end = MotivationReminderService._local_day_bounds_utc(
            date(2026, 6, 29),
            300,
        )
        self.assertEqual(start, datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 6, 29, 19, 0, tzinfo=timezone.utc))

    def test_reminder_button_opens_miniapp(self):
        markup = _button("uz")
        self.assertIsNotNone(markup.inline_keyboard[0][0].web_app)
        self.assertIn("source=motivation_reminder", markup.inline_keyboard[0][0].web_app.url)

    def test_d1_button_opens_exact_lesson_with_autostart(self):
        markup = _button(
            "uz",
            level="hsk2",
            lesson=1,
            source=D1_RECOVERY_EXPERIMENT,
            autostart=True,
        )
        button = markup.inline_keyboard[0][0]
        self.assertEqual(button.text, "▶️ Darsga qaytish")
        self.assertIn("level=hsk2", button.web_app.url)
        self.assertIn("lesson=1", button.web_app.url)
        self.assertIn("source=d1_recovery_v1", button.web_app.url)
        self.assertIn("autostart=1", button.web_app.url)

    def test_d1_arm_is_stable_and_balanced(self):
        self.assertEqual(_d1_recovery_arm(12345), _d1_recovery_arm(12345))
        treatment = sum(_d1_recovery_arm(value)[0] == "treatment" for value in range(1, 1001))
        self.assertGreater(treatment, 440)
        self.assertLess(treatment, 560)

    def test_d1_state_requires_first_lesson_without_return_or_completion(self):
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        onboarding_at = now - timedelta(hours=30)
        started_at = now - timedelta(hours=29)
        base = [
            CourseMiniAppEvent(
                telegram_id=1,
                event_name="onboarding_completed",
                source="course_onboarding",
                created_at=onboarding_at,
            ),
            CourseMiniAppEvent(
                telegram_id=1,
                event_name="lesson_started",
                source="course_v3",
                level="hsk1",
                lesson_id=10,
                lesson_order=1,
                session_id="first-session",
                created_at=started_at,
            ),
            CourseMiniAppEvent(
                telegram_id=1,
                event_name="card_seen",
                source="course_v3",
                level="hsk1",
                lesson_order=1,
                session_id="first-session",
                created_at=started_at + timedelta(minutes=10),
            ),
        ]

        state = _d1_recovery_states(base, now=now)[1]

        self.assertEqual(state["started"].lesson_order, 1)
        self.assertEqual(state["last_activity_at"], started_at + timedelta(minutes=10))

        returned = base + [
            CourseMiniAppEvent(
                telegram_id=1,
                event_name="miniapp_opened",
                source="course_v3",
                session_id="return-session",
                created_at=now - timedelta(hours=20),
            )
        ]
        self.assertNotIn(1, _d1_recovery_states(returned, now=now))

        completed = base + [
            CourseMiniAppEvent(
                telegram_id=1,
                event_name="lesson_completed",
                source="course_v3",
                level="hsk1",
                lesson_id=10,
                lesson_order=1,
                created_at=now - timedelta(hours=20),
            )
        ]
        self.assertNotIn(1, _d1_recovery_states(completed, now=now))

        completed_without_lesson_id = base + [
            CourseMiniAppEvent(
                telegram_id=1,
                event_name="book_lesson_completed",
                source="course_v3",
                level="HSK1",
                lesson_id=None,
                lesson_order=1,
                created_at=now - timedelta(hours=20),
            )
        ]
        self.assertNotIn(1, _d1_recovery_states(completed_without_lesson_id, now=now))

    def test_course_block_keyboard_has_miniapp_button(self):
        markup = course_intro_keyboard("uz")
        self.assertIsNotNone(markup.inline_keyboard[-1][0].web_app)


class MotivationReminderServiceQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_reminders_are_not_limited_to_paid_active_users(self):
        session = _CaptureSession()

        await MotivationReminderService(session).send_due_reminders(SimpleNamespace())

        compiled = str(session.queries[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("blocked", compiled)
        self.assertIn("last_active_at", compiled)
        self.assertIn("bot_blocked_at", compiled)
        self.assertNotIn("users.status = 'active'", compiled)

    async def test_d1_loader_prefilters_candidates_and_aggregates_high_volume_activity(self):
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        onboarding = CourseMiniAppEvent(
            telegram_id=1,
            event_name="onboarding_completed",
            created_at=now - timedelta(hours=26),
        )
        started = CourseMiniAppEvent(
            telegram_id=1,
            event_name="lesson_started",
            level="hsk1",
            lesson_order=1,
            session_id="first-session",
            created_at=now - timedelta(hours=25),
        )
        aggregated_activity = now - timedelta(hours=24, minutes=30)
        session = _SequenceSession(
            [
                _Rows([SimpleNamespace(telegram_id=1)]),
                _Rows([onboarding, started]),
                _Rows(
                    [
                        SimpleNamespace(
                            telegram_id=1,
                            last_activity_at=aggregated_activity,
                        )
                    ]
                ),
            ]
        )

        states = await MotivationReminderService(session)._load_d1_recovery_states(
            [1, 2],
            now,
        )

        self.assertEqual(states[1]["last_activity_at"], aggregated_activity)
        self.assertEqual(len(session.queries), 3)
        lifecycle_query = str(
            session.queries[1].compile(compile_kwargs={"literal_binds": True})
        )
        activity_query = str(
            session.queries[2].compile(compile_kwargs={"literal_binds": True})
        )
        self.assertIn("onboarding_completed", lifecycle_query)
        self.assertNotIn("card_seen", lifecycle_query)
        self.assertNotIn("interaction_completed", lifecycle_query)
        self.assertIn("max(course_miniapp_events.created_at)", activity_query.lower())


class D1RecoveryDeliveryTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _state(now):
        started = CourseMiniAppEvent(
            telegram_id=10,
            event_name="lesson_started",
            source="course_v3",
            level="hsk1",
            lesson_id=5,
            lesson_order=1,
            session_id="lesson-session",
            created_at=now - timedelta(hours=25),
        )
        return {
            "assignment": None,
            "assigned_at": None,
            "arm": None,
            "started": started,
            "last_activity_at": now - timedelta(hours=25),
        }

    async def test_control_is_reserved_without_sending(self):
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        telegram_id = next(
            value for value in range(1, 1000) if _d1_recovery_arm(value)[0] == "control"
        )
        session = SimpleNamespace()
        service = MotivationReminderService(session)
        service._reserve_d1_assignment = AsyncMock(return_value=True)
        service.templates = SimpleNamespace(resolve=AsyncMock(return_value={"text": "x"}))
        service._send = AsyncMock(return_value=True)
        user = SimpleNamespace(id=2, telegram_id=telegram_id)

        status = await service._handle_d1_recovery(
            bot=SimpleNamespace(),
            user=user,
            lang="uz",
            local_now=now,
            now=now,
            state=self._state(now),
        )

        self.assertEqual(status, "d1_control_assigned")
        service._send.assert_not_awaited()

    async def test_disabled_template_does_not_assign_or_start_holdout(self):
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        service = MotivationReminderService(SimpleNamespace())
        service.templates = SimpleNamespace(resolve=AsyncMock(return_value=None))
        service._reserve_d1_assignment = AsyncMock(return_value=True)

        status = await service._handle_d1_recovery(
            bot=SimpleNamespace(),
            user=SimpleNamespace(id=2, telegram_id=10),
            lang="uz",
            local_now=now,
            now=now,
            state=self._state(now),
        )

        self.assertIsNone(status)
        service._reserve_d1_assignment.assert_not_awaited()

    async def test_treatment_uses_exact_deeplink_and_records_sent(self):
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        telegram_id = next(
            value for value in range(1, 1000) if _d1_recovery_arm(value)[0] == "treatment"
        )
        session = SimpleNamespace(add=Mock(), commit=AsyncMock(), rollback=AsyncMock())
        service = MotivationReminderService(session)
        service._reserve_d1_assignment = AsyncMock(return_value=True)
        service.templates = SimpleNamespace(
            resolve=AsyncMock(return_value={"text": "{lesson}", "media_type": "none", "media_path": None})
        )
        service._send = AsyncMock(return_value=True)
        user = SimpleNamespace(id=2, telegram_id=telegram_id)

        status = await service._handle_d1_recovery(
            bot=SimpleNamespace(),
            user=user,
            lang="uz",
            local_now=now,
            now=now,
            state=self._state(now),
        )

        self.assertEqual(status, "d1_treatment_sent")
        kwargs = service._send.await_args.kwargs
        self.assertEqual(kwargs["target_level"], "hsk1")
        self.assertEqual(kwargs["target_lesson"], 1)
        self.assertEqual(kwargs["source"], D1_RECOVERY_EXPERIMENT)
        self.assertTrue(kwargs["autostart"])
        self.assertEqual(session.add.call_args.args[0].event_name, D1_RECOVERY_SENT_EVENT)
        session.commit.assert_awaited_once()

    async def test_active_assignment_suppresses_other_motivation_messages(self):
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        state = self._state(now)
        state["assigned_at"] = now - timedelta(hours=10)
        service = MotivationReminderService(SimpleNamespace())
        service._reserve_d1_assignment = AsyncMock(return_value=True)

        status = await service._handle_d1_recovery(
            bot=SimpleNamespace(),
            user=SimpleNamespace(id=2, telegram_id=10),
            lang="uz",
            local_now=now,
            now=now,
            state=state,
        )

        self.assertEqual(status, "d1_holdout_active")
        service._reserve_d1_assignment.assert_not_awaited()


class MotivationReminderServiceRankChangeTests(unittest.TestCase):
    def test_rank_passed_is_not_a_chat_notification_template(self):
        self.assertNotIn("rating_passed", MOTIVATION_KEYS)


if __name__ == "__main__":
    unittest.main()
