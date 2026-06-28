import json
import unittest
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine

from app.db import models  # noqa: F401
from app.db.base import Base
from app.bot.utils.course_miniapp import (
    course_miniapp_url,
    course_stroke_order_url,
    course_study_miniapp_url,
)
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_ad_service import CourseAdService
from app.services.course_miniapp_analytics_service import (
    MAX_EVENT_PAYLOAD_CHARS,
    CourseMiniAppAnalyticsService,
)
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService


class _NestedTransaction(AbstractAsyncContextManager):
    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _FakeSession:
    def __init__(self):
        self.added = []
        self.flush_count = 0

    def begin_nested(self):
        return _NestedTransaction()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flush_count += 1


class _Result:
    def __init__(self, *, rows=None, scalar=0):
        self._rows = rows or []
        self._scalar = scalar

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class _ScalarListResult:
    def __init__(self, values):
        self.values = list(values)

    def scalars(self):
        return self

    def all(self):
        return self.values


class _QuerySession(_FakeSession):
    def __init__(self, results):
        super().__init__()
        self.results = list(results)

    async def execute(self, _query):
        return self.results.pop(0)


class _FailingSession(_FakeSession):
    def __init__(self):
        super().__init__()
        self.rolled_back = False

    async def flush(self):
        raise RuntimeError("database unavailable")

    async def rollback(self):
        self.rolled_back = True


class CourseMiniAppModelTests(unittest.TestCase):
    def test_foundation_tables_create_on_sqlite(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        table_names = set(Base.metadata.tables)
        self.assertIn("course_miniapp_profiles", table_names)
        self.assertIn("course_feature_usages", table_names)
        self.assertIn("course_miniapp_events", table_names)
        self.assertIn("course_mistakes", table_names)
        self.assertIn("course_xp_events", table_names)
        self.assertIn("subscription_entry_events", table_names)
        self.assertIn("course_ad_creatives", table_names)
        self.assertIn("course_ad_views", table_names)


class CourseMiniAppUrlTests(unittest.TestCase):
    def test_legacy_course_links_point_to_existing_course_v3_surfaces(self):
        lesson = SimpleNamespace(level="hsk1", lesson_order=4)

        course_url = course_study_miniapp_url(lang="uz", level="hsk1", lesson=4, tab="training")
        challenge_url = course_study_miniapp_url(lang="uz", level="hsk1", tab="rating", challenge_id=77)
        quiz_url = course_miniapp_url(lesson, "quiz", "uz", block_no=1)
        vocab_url = course_stroke_order_url(lesson, lang="uz", block_no=1)

        self.assertIn("course-v3.html", course_url)
        self.assertIn("tab=mashq", course_url)
        self.assertIn("lesson=4", course_url)
        self.assertIn("tab=rating", challenge_url)
        self.assertIn("challenge_id=77", challenge_url)
        self.assertIn("course-v3.html", quiz_url)
        self.assertIn("tab=mashq", quiz_url)
        self.assertIn("lesson=4", quiz_url)
        self.assertIn("hsk-lugat.html", vocab_url)
        for url in (course_url, quiz_url, vocab_url):
            self.assertNotIn("study.html", url)
            self.assertNotIn("stroke-order.html", url)
            self.assertNotIn("duo-lesson.html", url)


class CourseMiniAppAccessTests(unittest.TestCase):
    @staticmethod
    def _user(**overrides):
        values = {
            "status": "trial",
            "payment_status": "none",
            "end_date": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_paid_access_requires_current_approved_subscription(self):
        active = self._user(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) + timedelta(days=1),
        )
        expired = self._user(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        no_end_date = self._user(status="active", payment_status="approved")

        self.assertTrue(CourseMiniAppAccessService.is_paid_user(active))
        self.assertFalse(CourseMiniAppAccessService.is_paid_user(expired))
        self.assertFalse(CourseMiniAppAccessService.is_paid_user(no_end_date))

    def test_unknown_feature_is_rejected(self):
        with self.assertRaises(ValueError):
            CourseMiniAppAccessService._normalize_feature_key("payments")

    def test_blocked_user_is_not_free_eligible(self):
        self.assertFalse(CourseMiniAppAccessService.is_free_user(self._user(status="blocked")))

    def test_unpaid_course_lesson_policy_keeps_three_free_previews_per_level(self):
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 3))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 4))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk2", 1))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk4", 4))


class CourseMiniAppEntitlementTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_trial_usage_closes_free_lesson_and_voice(self):
        session = _QuerySession(
            [
                _Result(rows=[]),
                _Result(scalar=1),
            ]
        )
        user = SimpleNamespace(
            id=4,
            telegram_id=123,
            status="trial",
            payment_status="none",
            end_date=None,
            trial_course_completed_at=datetime.now(timezone.utc),
            trial_voice_used_at=None,
        )
        entitlements = await CourseMiniAppAccessService(session).get_entitlements(user)
        self.assertFalse(entitlements["lesson"]["allowed"])
        self.assertFalse(entitlements["voice"]["allowed"])
        self.assertTrue(entitlements["placement"]["allowed"])
        self.assertTrue(entitlements["training_test"]["allowed"])


class CourseAdServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_ad_supported_lesson_requires_all_three_views(self):
        missing_end = _QuerySession([_ScalarListResult(["start", "middle"])])
        complete = _QuerySession([_ScalarListResult(["start", "middle", "end"])])

        self.assertFalse(
            await CourseAdService(missing_end).has_completed_required_views(
                user_telegram_id=123,
                level="hsk1",
                lesson_order=4,
            )
        )
        self.assertTrue(
            await CourseAdService(complete).has_completed_required_views(
                user_telegram_id=123,
                level="hsk1",
                lesson_order=4,
            )
        )

    def test_course_ad_duration_is_clamped_to_six_or_seven_seconds(self):
        self.assertEqual(CourseAdService.normalize_duration(4), 6)
        self.assertEqual(CourseAdService.normalize_duration(99), 7)
        self.assertEqual(CourseAdService.normalize_duration(6), 6)


class CourseMiniAppProfileTests(unittest.TestCase):
    def test_onboarding_preferences_are_strict(self):
        self.assertEqual(
            CourseMiniAppProfileService.validate_preferences(
                goal="hsk_exam",
                daily_minutes=30,
                start_mode="continue",
            ),
            ("hsk_exam", 30, "continue"),
        )
        with self.assertRaises(ValueError):
            CourseMiniAppProfileService.validate_preferences(
                goal="hsk_exam",
                daily_minutes=25,
                start_mode="continue",
            )


class CourseMiniAppAnalyticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_cannot_write_server_completion_event(self):
        service = CourseMiniAppAnalyticsService(_FakeSession())
        result = await service.record_client_event(
            event_name="lesson_completed",
            telegram_id=123,
        )
        self.assertEqual(result, {"ok": False, "error": "course_client_event_not_allowed"})

    async def test_allowed_client_event_is_buffered(self):
        session = _FakeSession()
        service = CourseMiniAppAnalyticsService(session)
        result = await service.record_client_event(
            event_name="lesson_started",
            telegram_id=123,
            user_id=4,
            level="hsk1",
            lesson_order=1,
            payload={"source": "path"},
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["recorded"])
        self.assertEqual(len(session.added), 1)
        self.assertEqual(session.added[0].event_name, "lesson_started")

    async def test_analytics_failure_rolls_back_without_raising(self):
        session = _FailingSession()
        with self.assertLogs("app.services.course_miniapp_analytics_service", level="ERROR"):
            result = await CourseMiniAppAnalyticsService(session).record_server_event(
                event_name="miniapp_opened",
                telegram_id=123,
            )
        self.assertFalse(result["ok"])
        self.assertTrue(session.rolled_back)

    def test_large_payload_is_stored_as_valid_truncated_json(self):
        payload_json = CourseMiniAppAnalyticsService._payload_json({"value": "x" * 9000})
        parsed = json.loads(payload_json)
        self.assertTrue(parsed["truncated"])
        self.assertLessEqual(len(payload_json), MAX_EVENT_PAYLOAD_CHARS)


if __name__ == "__main__":
    unittest.main()
