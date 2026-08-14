import json
import unittest
from datetime import datetime, timedelta, timezone

from app.db.models.course_miniapp_event import (
    CLIENT_COURSE_MINIAPP_EVENT_NAMES,
    COURSE_MINIAPP_EVENT_NAMES,
)
from app.services.admin_miniapp_service import AdminMiniAppService
from app.services.course_miniapp_admin_analytics_service import (
    CourseMiniAppAdminAnalyticsService,
    LessonDropoffRow,
    build_foundation_metrics,
)


class CourseMiniAppAdminAnalyticsServiceTests(unittest.TestCase):
    def test_pct_handles_zero_denominator(self):
        self.assertEqual(CourseMiniAppAdminAnalyticsService._pct(3, 0), 0.0)
        self.assertEqual(CourseMiniAppAdminAnalyticsService._pct(3, 4), 75.0)

    def test_format_lesson_dropoff_orders_largest_gap_first(self):
        rows = [
            LessonDropoffRow(level="hsk1", lesson_order=1, started=10, completed=9),
            LessonDropoffRow(level="hsk2", lesson_order=3, started=15, completed=5),
        ]

        text = CourseMiniAppAdminAnalyticsService.format_lesson_dropoff(rows)

        self.assertTrue(text.startswith("HSK2-3"))
        self.assertIn("15", text)
        self.assertIn("5", text)

    def test_format_lesson_dropoff_empty(self):
        self.assertEqual(CourseMiniAppAdminAnalyticsService.format_lesson_dropoff([]), "hali yo'q")

    def test_foundation_events_are_server_and_client_allowlisted(self):
        for event_name in ("foundation_started", "foundation_completed"):
            self.assertIn(event_name, COURSE_MINIAPP_EVENT_NAMES)
            self.assertIn(event_name, CLIENT_COURSE_MINIAPP_EVENT_NAMES)

    def test_foundation_metrics_follow_versioned_chronological_cohort(self):
        now = datetime(2026, 8, 13, 12, tzinfo=timezone.utc)
        started_at = now - timedelta(days=5)

        def row(
            event_name,
            user,
            at,
            *,
            payload=None,
            source="course_v3",
            level=None,
            lesson_order=None,
        ):
            return (
                event_name,
                user,
                source,
                level,
                lesson_order,
                json.dumps(payload or {}),
                at,
            )

        foundation = {"foundation_version": "starter-0-v1", "entry_level": "beginner"}
        user1_completed = started_at + timedelta(minutes=10)
        user2_started = started_at + timedelta(hours=1)
        user2_completed = user2_started + timedelta(minutes=10)
        rows = [
            row("foundation_started", 1, started_at, payload=foundation),
            row(
                "interaction_completed",
                1,
                started_at + timedelta(minutes=2),
                payload={
                    **foundation,
                    "card_id": "meaning-choice",
                    "objective_id": "meaning",
                    "attempt": 1,
                    "guided": False,
                    "correct": True,
                },
            ),
            # Duplicate first-attempt telemetry cannot overwrite the earliest objective result.
            row(
                "interaction_completed",
                1,
                started_at + timedelta(minutes=3),
                payload={
                    **foundation,
                    "card_id": "meaning-choice",
                    "objective_id": "meaning",
                    "attempt": 1,
                    "guided": False,
                    "correct": False,
                },
            ),
            row("foundation_completed", 1, user1_completed, payload=foundation),
            row(
                "section_completed",
                1,
                user1_completed + timedelta(minutes=10),
                payload={"section_no": 1},
                level="hsk1",
                lesson_order=1,
            ),
            row(
                "section_completed",
                1,
                user1_completed + timedelta(minutes=20),
                payload={"section_no": 2},
                level="hsk1",
                lesson_order=1,
            ),
            row(
                "section_completed",
                1,
                user1_completed + timedelta(minutes=30),
                payload={"section_no": 3},
                level="hsk1",
                lesson_order=1,
            ),
            row(
                "paywall_seen",
                1,
                user1_completed + timedelta(hours=1),
                source="v3_locked_lesson",
            ),
            row(
                "section_completed",
                1,
                user1_completed + timedelta(hours=25),
                payload={"section_no": 1},
                level="hsk1",
                lesson_order=1,
            ),
            row("foundation_started", 2, user2_started, payload=foundation),
            row(
                "interaction_completed",
                2,
                user2_started + timedelta(minutes=2),
                payload={
                    **foundation,
                    "card_id": "meaning-choice",
                    "objective_id": "meaning",
                    "attempt": 1,
                    "guided": False,
                    "correct": False,
                },
            ),
            # Guided retries are mastery repair, not first-attempt accuracy.
            row(
                "interaction_completed",
                2,
                user2_started + timedelta(minutes=4),
                payload={
                    **foundation,
                    "card_id": "meaning-choice-guided",
                    "objective_id": "meaning",
                    "attempt": 2,
                    "guided": True,
                    "correct": True,
                },
            ),
            row("foundation_completed", 2, user2_completed, payload=foundation),
            row(
                "section_completed",
                2,
                user2_completed + timedelta(minutes=10),
                payload={"section_no": 1},
                level="hsk1",
                lesson_order=1,
            ),
            row(
                "foundation_started",
                3,
                started_at,
                payload={"foundation_version": "starter-0-v1", "entry_level": "hsk1"},
            ),
            # A completion without a matching start/version is not a conversion.
            row("foundation_completed", 4, started_at, payload=foundation),
        ]

        metrics = build_foundation_metrics(rows, now=now)

        self.assertEqual(metrics["started_users"], 3)
        self.assertEqual(metrics["completed_users"], 2)
        self.assertEqual(metrics["completion_rate"], 66.7)
        self.assertEqual(metrics["first_attempt"], {"objectives": 2, "correct": 1, "accuracy": 50.0})
        self.assertEqual(
            [(part["completed_users"], part["rate_from_foundation"]) for part in metrics["parts"]],
            [(2, 100.0), (1, 50.0), (1, 50.0)],
        )
        self.assertEqual(
            metrics["checkpoint_to_paywall"],
            {"checkpoint_users": 1, "paywall_users": 1, "rate": 100.0, "attribution_hours": 24},
        )
        self.assertEqual(
            metrics["d1_meaningful_return"],
            {"eligible": 2, "returned": 1, "rate": 50.0, "window_hours": [24, 48]},
        )

    def test_admin_advanced_text_exposes_foundation_metrics(self):
        text = AdminMiniAppService._advanced_report_text(
            {
                "foundation": {
                    "started_users": 10,
                    "completed_users": 8,
                    "completion_rate": 80.0,
                    "first_attempt": {"objectives": 20, "correct": 15, "accuracy": 75.0},
                    "parts": [
                        {"part": 1, "completed_users": 7, "rate_from_foundation": 87.5},
                        {"part": 2, "completed_users": 6, "rate_from_foundation": 75.0},
                        {"part": 3, "completed_users": 5, "rate_from_foundation": 62.5},
                    ],
                    "checkpoint_to_paywall": {"checkpoint_users": 5, "paywall_users": 4, "rate": 80.0},
                    "d1_meaningful_return": {"eligible": 4, "returned": 2, "rate": 50.0},
                }
            }
        )

        self.assertIn("Starter start → complete: 80.0%", text)
        self.assertIn("Starter first-attempt: 75.0%", text)
        self.assertIn("Starter → HSK1 P1/P2/P3: 87.5% / 75.0% / 62.5%", text)
        self.assertIn("Checkpoint → paywall ≤24h: 80.0%", text)
        self.assertIn("Starter D1 meaningful learning: 50.0%", text)


if __name__ == "__main__":
    unittest.main()
