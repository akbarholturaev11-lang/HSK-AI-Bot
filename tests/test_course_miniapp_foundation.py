import json
import unittest
from unittest import mock
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect

from app.db import models  # noqa: F401
from app.db.base import Base
from app.bot.utils.course_miniapp import (
    course_miniapp_url,
    course_stroke_order_url,
    course_study_miniapp_url,
    course_v3_miniapp_url,
)
from app.services.course_miniapp_access_service import (
    COURSE_AI_PRACTICE_FEATURES,
    COURSE_DAILY_FREE_LIMITS,
    CourseMiniAppAccessService,
    free_course_parts_for_level,
)
from app.services.course_access_policy_service import (
    COURSE_ACCESS_AD,
    COURSE_ACCESS_MODE_ADS,
    COURSE_ACCESS_MODE_FREE_UNTIL,
    COURSE_ACCESS_MODE_SUBSCRIPTION,
    COURSE_ACCESS_OPEN,
    COURSE_ACCESS_SUBSCRIPTION,
    CourseLessonAccessPolicy,
)
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
        self.assertIn("course_user_notifications", table_names)
        self.assertIn("subscription_entry_events", table_names)
        self.assertIn("course_ad_creatives", table_names)
        self.assertIn("course_ad_views", table_names)
        ad_columns = {
            column["name"]
            for column in inspect(engine).get_columns("course_ad_creatives")
        }
        self.assertIn("media_blob", ad_columns)
        self.assertIn("media_size", ad_columns)
        self.assertIn("media_checksum", ad_columns)


class CourseMiniAppUrlTests(unittest.TestCase):
    def test_desktop_profile_focus_flag_is_explicit_and_keeps_existing_query(self):
        with mock.patch(
            "app.bot.utils.course_miniapp.settings.MINI_APP_BASE_URL",
            "https://app.example.test/course-v3.html?channel=telegram",
        ):
            regular = course_v3_miniapp_url(lang="uz", tab="profile")
            desktop = course_v3_miniapp_url(
                lang="uz",
                tab="profile",
                focus_desktop_download=True,
            )

        self.assertIn("channel=telegram", regular)
        self.assertIn("tab=profile", regular)
        self.assertNotIn("desktop_download=", regular)
        self.assertIn("channel=telegram", desktop)
        self.assertIn("desktop_download=1", desktop)

    def test_legacy_course_links_point_to_existing_course_v3_surfaces(self):
        lesson = SimpleNamespace(level="hsk1", lesson_order=4)

        course_url = course_study_miniapp_url(
            lang="uz",
            level="hsk1",
            lesson=4,
            tab="training",
            source="motivation_reminder",
            autostart=True,
        )
        challenge_url = course_study_miniapp_url(lang="uz", level="hsk1", tab="rating", challenge_id=77)
        quiz_url = course_miniapp_url(lesson, "quiz", "uz", block_no=1)
        vocab_url = course_stroke_order_url(lesson, lang="uz", block_no=1)

        self.assertIn("course-v3.html", course_url)
        self.assertIn("tab=mashq", course_url)
        self.assertIn("lesson=4", course_url)
        self.assertIn("source=motivation_reminder", course_url)
        self.assertIn("autostart=1", course_url)
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

    def test_access_ref_is_opaque_bounded_and_index_safe(self):
        self.assertEqual(
            CourseMiniAppAccessService.normalize_access_ref("attempt-12345678"),
            "attempt-12345678",
        )
        for invalid in ("", "short", "has spaces 123", "x" * 49, "slash/value"):
            with self.assertRaises(ValueError):
                CourseMiniAppAccessService.normalize_access_ref(invalid)

    def test_blocked_user_is_not_free_eligible(self):
        self.assertFalse(CourseMiniAppAccessService.is_free_user(self._user(status="blocked")))

    def test_practice_ad_cap_only_on_ai_token_sections(self):
        # Reklama bilan ochish faqat AI token sarflaydigan bo'limda cheklanadi
        # (talaffuz). Boshqa bo'limlarda "<feature>_ad" kaliti YO'Q (cheksiz).
        self.assertEqual(COURSE_AI_PRACTICE_FEATURES, ("pronunciation",))
        self.assertEqual(COURSE_DAILY_FREE_LIMITS.get("pronunciation_ad"), 2)
        for feature in ("recognition", "memorize", "placement", "training_test"):
            self.assertNotIn(f"{feature}_ad", COURSE_DAILY_FREE_LIMITS)
        # Bepul asosiy bo'limlar hali 1 (umrbod, lifetime=True bilan ishlatiladi).
        self.assertEqual(COURSE_DAILY_FREE_LIMITS.get("recognition"), 1)

    def test_free_course_parts_are_level_aware(self):
        self.assertEqual(free_course_parts_for_level("beginner"), 3)
        self.assertEqual(free_course_parts_for_level("hsk1"), 3)
        for level in ("hsk2", "hsk3", "hsk4", "hsk4a", "hsk4b"):
            self.assertEqual(free_course_parts_for_level(level), 2)
        self.assertEqual(free_course_parts_for_level("unknown"), 2)

    def test_unpaid_course_lesson_policy_includes_hsk1_checkpoint(self):
        # HSK1 mini-parts 1-3 are fully free; part 4 is the first premium
        # preview. HSK2-HSK4 retain the existing two-part allowance.
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 1))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 2))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 3))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 4))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk2", 1))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk2", 2))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk2", 3))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk4", 4))


class CourseLessonAccessPolicyTests(unittest.TestCase):
    def test_subscription_policy_keeps_current_paid_gate(self):
        policy = CourseLessonAccessPolicy(mode=COURSE_ACCESS_MODE_SUBSCRIPTION)

        self.assertEqual(
            policy.requirement_for(lesson_order=2, is_paid=False, free_lessons=2),
            COURSE_ACCESS_OPEN,
        )
        self.assertEqual(
            policy.requirement_for(lesson_order=3, is_paid=False, free_lessons=2),
            COURSE_ACCESS_SUBSCRIPTION,
        )
        self.assertEqual(
            policy.requirement_for(lesson_order=3, is_paid=True, free_lessons=2),
            COURSE_ACCESS_OPEN,
        )

    def test_ads_policy_replaces_subscription_gate_with_ad_gate(self):
        policy = CourseLessonAccessPolicy(mode=COURSE_ACCESS_MODE_ADS)

        self.assertEqual(
            policy.requirement_for(lesson_order=1, is_paid=False, free_lessons=2),
            COURSE_ACCESS_OPEN,
        )
        self.assertEqual(
            policy.requirement_for(lesson_order=3, is_paid=False, free_lessons=2),
            COURSE_ACCESS_AD,
        )

    def test_free_until_policy_opens_lessons_only_until_expiry(self):
        active = CourseLessonAccessPolicy(
            mode=COURSE_ACCESS_MODE_FREE_UNTIL,
            free_until=datetime.now(timezone.utc) + timedelta(days=1),
        )
        expired = CourseLessonAccessPolicy(
            mode=COURSE_ACCESS_MODE_FREE_UNTIL,
            free_until=datetime.now(timezone.utc) - timedelta(seconds=1),
        )

        self.assertEqual(
            active.requirement_for(lesson_order=8, is_paid=False, free_lessons=2),
            COURSE_ACCESS_OPEN,
        )
        self.assertEqual(
            expired.requirement_for(lesson_order=8, is_paid=False, free_lessons=2),
            COURSE_ACCESS_SUBSCRIPTION,
        )


class CourseMiniAppAdAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    ATTEMPT_TOKEN = "A" * 32

    @staticmethod
    def _user():
        return SimpleNamespace(
            id=7,
            telegram_id=123,
            status="trial",
            payment_status="none",
            end_date=None,
        )

    @staticmethod
    def _session(*, scalar=None, scalars=None):
        session = _FakeSession()
        values = list(scalars) if scalars is not None else None

        async def execute(_query):
            value = values.pop(0) if values is not None else scalar
            return SimpleNamespace(scalar_one_or_none=lambda: value)

        session.execute = mock.AsyncMock(side_effect=execute)
        return session

    @classmethod
    def _attempt_event(cls, *, age_seconds=10, **overrides):
        payload = {
            "feature": "training_test",
            "access_ref": "attempt-12345678",
            "ad_id": 9,
            "placement": "start",
            "required_seconds": 7,
        }
        payload.update(overrides)
        return SimpleNamespace(
            created_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
            payload_json=json.dumps(payload),
        )

    async def test_start_attempt_issues_opaque_token_and_persists_exact_binding(self):
        session = self._session()
        result = await CourseMiniAppAccessService(session).start_ad_attempt(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
            ad_id=9,
            placement="start",
            required_seconds=7,
        )

        self.assertTrue(result["allowed"])
        self.assertRegex(result["attempt_token"], r"^[A-Za-z0-9_-]{24,64}$")
        self.assertEqual(len(session.added), 1)
        event = session.added[0]
        self.assertEqual(event.event_name, "course_ad_attempt_started")
        self.assertEqual(event.source, "course_v3_ad_attempt")
        self.assertNotIn(result["attempt_token"], event.session_id)
        self.assertEqual(
            json.loads(event.payload_json),
            {
                "feature": "training_test",
                "access_ref": "attempt-12345678",
                "ad_id": 9,
                "placement": "start",
                "required_seconds": 7,
            },
        )

    async def test_completed_start_ad_records_feature_bound_authorization(self):
        session = self._session(scalars=[self._attempt_event(), None])
        service = CourseMiniAppAccessService(session)

        result = await service.record_ad_authorization(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
            ad_id=9,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
        )

        self.assertTrue(result["allowed"])
        self.assertTrue(result["recorded"])
        self.assertEqual(len(session.added), 1)
        event = session.added[0]
        self.assertEqual(event.event_name, "course_ad_viewed")
        self.assertEqual(event.source, "course_v3_ad_auth")
        self.assertEqual(event.session_id, "training_test:attempt-12345678")
        self.assertEqual(json.loads(event.payload_json)["ad_id"], 9)
        self.assertIn("attempt_id", json.loads(event.payload_json))

    async def test_client_watched_seconds_cannot_replace_server_attempt(self):
        session = self._session()
        result = await CourseMiniAppAccessService(session).record_ad_authorization(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
            ad_id=9,
            placement="start",
            attempt_token="",
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["error"], "ad_attempt_required")
        self.assertEqual(session.added, [])

    async def test_attempt_must_reach_server_measured_duration(self):
        session = self._session(scalar=self._attempt_event(age_seconds=2))
        result = await CourseMiniAppAccessService(session).validate_ad_attempt(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
            ad_id=9,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["error"], "ad_attempt_incomplete")
        self.assertGreaterEqual(result["retry_after"], 1)

    async def test_attempt_is_bound_to_ad_feature_ref_and_placement(self):
        session = self._session(scalar=self._attempt_event())
        result = await CourseMiniAppAccessService(session).validate_ad_attempt(
            self._user(),
            feature_key="training_test",
            access_ref="different-12345678",
            ad_id=9,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["error"], "invalid_ad_attempt")

    async def test_expired_attempt_cannot_refresh_authorization(self):
        session = self._session(scalar=self._attempt_event(age_seconds=901))
        result = await CourseMiniAppAccessService(session).validate_ad_attempt(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
            ad_id=9,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["error"], "ad_attempt_expired")

    async def test_non_start_ad_cannot_authorize_a_new_session(self):
        session = self._session()
        result = await CourseMiniAppAccessService(session).record_ad_authorization(
            self._user(),
            feature_key="mistake_review",
            access_ref="review-12345678",
            ad_id=9,
            placement="middle",
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["error"], "ad_authorization_requires_start_view")
        self.assertEqual(session.added, [])

    async def test_completed_ad_refreshes_stale_authorization_for_same_access_ref(self):
        stale_at = datetime.now(timezone.utc) - timedelta(hours=1)
        stale_event = SimpleNamespace(
            id=44,
            created_at=stale_at,
            payload_json="{}",
        )
        session = self._session(scalars=[self._attempt_event(ad_id=11), stale_event])

        result = await CourseMiniAppAccessService(session).record_ad_authorization(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
            ad_id=11,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
        )

        self.assertTrue(result["allowed"])
        self.assertTrue(result["recorded"])
        self.assertTrue(result["refreshed"])
        self.assertFalse(result["idempotent"])
        self.assertGreater(stale_event.created_at, stale_at)
        self.assertEqual(json.loads(stale_event.payload_json)["ad_id"], 11)
        self.assertEqual(session.flush_count, 1)

    async def test_ad_authorization_is_required_and_checked_by_exact_binding(self):
        missing = self._session(scalar=None)
        denied = await CourseMiniAppAccessService(missing).verify_ad_authorization(
            self._user(),
            feature_key="mistake_review",
            access_ref="review-12345678",
        )
        self.assertEqual(denied["error"], "ad_authorization_required")

        found = self._session(scalar=44)
        allowed = await CourseMiniAppAccessService(found).verify_ad_authorization(
            self._user(),
            feature_key="training_test",
            access_ref="attempt-12345678",
        )
        self.assertTrue(allowed["allowed"])
        query = found.execute.await_args.args[0]
        self.assertIn(
            "training_test:attempt-12345678",
            query.compile().params.values(),
        )

    async def test_lesson_ad_authorization_is_bound_to_level_and_lesson_order(self):
        session = self._session()
        result = await CourseMiniAppAccessService(session).start_ad_attempt(
            self._user(),
            feature_key="lesson",
            access_ref="lesson-12345678",
            ad_id=9,
            placement="start",
            required_seconds=7,
            level="hsk1",
            lesson_order=3,
        )

        self.assertTrue(result["allowed"])
        payload = json.loads(session.added[0].payload_json)
        self.assertEqual(payload["feature"], "lesson")
        self.assertEqual(payload["level"], "hsk1")
        self.assertEqual(payload["lesson_order"], 3)

        wrong_attempt = self._session(
            scalar=self._attempt_event(
                feature="lesson",
                access_ref="lesson-12345678",
                level="hsk1",
                lesson_order=3,
            )
        )
        denied = await CourseMiniAppAccessService(wrong_attempt).validate_ad_attempt(
            self._user(),
            feature_key="lesson",
            access_ref="lesson-12345678",
            ad_id=9,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
            level="hsk1",
            lesson_order=4,
        )
        self.assertFalse(denied["allowed"])
        self.assertEqual(denied["error"], "invalid_ad_attempt")

        auth_session = self._session(
            scalars=[
                self._attempt_event(
                    feature="lesson",
                    access_ref="lesson-12345678",
                    level="hsk1",
                    lesson_order=3,
                ),
                None,
            ]
        )
        recorded = await CourseMiniAppAccessService(auth_session).record_ad_authorization(
            self._user(),
            feature_key="lesson",
            access_ref="lesson-12345678",
            ad_id=9,
            placement="start",
            attempt_token=self.ATTEMPT_TOKEN,
            level="hsk1",
            lesson_order=3,
        )
        self.assertTrue(recorded["allowed"])
        auth_payload = json.loads(auth_session.added[0].payload_json)
        self.assertEqual(auth_session.added[0].session_id, "lesson:lesson-12345678")
        self.assertEqual(auth_payload["level"], "hsk1")
        self.assertEqual(auth_payload["lesson_order"], 3)

        valid_event = SimpleNamespace(
            created_at=datetime.now(timezone.utc),
            payload_json=json.dumps(
                {
                    "feature": "lesson",
                    "access_ref": "lesson-12345678",
                    "level": "hsk1",
                    "lesson_order": 3,
                }
            ),
        )
        verified = await CourseMiniAppAccessService(self._session(scalar=valid_event)).verify_ad_authorization(
            self._user(),
            feature_key="lesson",
            access_ref="lesson-12345678",
            level="hsk1",
            lesson_order=3,
        )
        self.assertTrue(verified["allowed"])

        invalid = await CourseMiniAppAccessService(self._session(scalar=valid_event)).verify_ad_authorization(
            self._user(),
            feature_key="lesson",
            access_ref="lesson-12345678",
            level="hsk1",
            lesson_order=4,
        )
        self.assertFalse(invalid["allowed"])
        self.assertEqual(invalid["error"], "invalid_ad_authorization")


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

    def test_course_ad_duration_is_admin_controlled_within_bounds(self):
        # Admin panel boshqaradi: 5–120s oralig'iga clamp qilinadi.
        self.assertEqual(CourseAdService.normalize_duration(3), 5)
        self.assertEqual(CourseAdService.normalize_duration(999), 120)
        self.assertEqual(CourseAdService.normalize_duration(30), 30)
        self.assertEqual(CourseAdService.normalize_duration(None), 7)

    def test_course_ad_link_is_normalized(self):
        self.assertIsNone(CourseAdService.normalize_link(""))
        self.assertIsNone(CourseAdService.normalize_link(None))
        self.assertEqual(
            CourseAdService.normalize_link("example.uz"), "https://example.uz"
        )
        self.assertEqual(
            CourseAdService.normalize_link("https://t.me/foo"), "https://t.me/foo"
        )

    def test_course_ad_language_is_normalized(self):
        self.assertEqual(CourseAdService.normalize_language("uz"), "uz")
        self.assertEqual(CourseAdService.normalize_language("RU"), "ru")
        self.assertEqual(CourseAdService.normalize_language("tj"), "tj")
        # Noma'lum/bo'sh til "all" (barcha tillar) ga tushadi.
        self.assertEqual(CourseAdService.normalize_language(""), "all")
        self.assertEqual(CourseAdService.normalize_language(None), "all")
        self.assertEqual(CourseAdService.normalize_language("en"), "all")

    def test_course_ad_type_and_slot_are_normalized(self):
        for value in ("odiy", "hamkorlik", "bot", "dars_yakuni"):
            self.assertEqual(CourseAdService.normalize_ad_type(value), value)
        self.assertEqual(CourseAdService.normalize_ad_type("DARS_YAKUNI"), "dars_yakuni")
        # Noma'lum/bo'sh tur oddiy reklamaga tushadi.
        self.assertEqual(CourseAdService.normalize_ad_type("xyz"), "odiy")
        self.assertEqual(CourseAdService.normalize_ad_type(None), "odiy")
        self.assertEqual(CourseAdService.normalize_slot("lesson_end"), "lesson_end")
        self.assertEqual(CourseAdService.normalize_slot("practice"), "practice")
        # Noma'lum/bo'sh slot mashq bo'limlari slotiga tushadi.
        self.assertEqual(CourseAdService.normalize_slot(""), "practice")
        self.assertEqual(CourseAdService.normalize_slot("lesson"), "practice")

    async def test_lesson_end_ads_never_mix_with_other_placements(self):
        """Dars yakuni reklamasi ALOHIDA slot: mashq bo'limlarida chiqmaydi,
        dars oxirida esa faqat u chiqadi. Filtr haqiqiy SQL bilan tekshiriladi."""
        import os
        import tempfile

        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.db.base import Base
        from app.db.models.course_ad import CourseAdCreative
        from app.services import course_ad_service as svc

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(
                    Base.metadata.create_all, tables=[CourseAdCreative.__table__]
                )
            maker = async_sessionmaker(engine, expire_on_commit=False)
            rows = {
                "odiy": "ad_odiy.mp4",
                "hamkorlik": "ad_hamkorlik.mp4",
                "bot": "ad_bot.mp4",
                "dars_yakuni": "ad_dars_yakuni.mp4",
            }
            with tempfile.TemporaryDirectory() as tmp:
                for name in rows.values():
                    with open(os.path.join(tmp, name), "wb") as fh:
                        fh.write(b"mp4")
                async with maker() as session:
                    for ad_type, name in rows.items():
                        session.add(
                            CourseAdCreative(
                                title=ad_type,
                                media_path=name,
                                media_type="video",
                                ad_type=ad_type,
                                language="all",
                                duration_seconds=7,
                                is_active=True,
                            )
                        )
                    # Eski yozuv: `ad_type` NULL — mashq slotida qolishi kerak.
                    session.add(
                        CourseAdCreative(
                            title="legacy",
                            media_path=next(iter(rows.values())),
                            media_type="video",
                            ad_type=None,
                            language="all",
                            duration_seconds=7,
                            is_active=True,
                        )
                    )
                    await session.commit()

                with mock.patch.object(svc, "COURSE_AD_MEDIA_ROOT", tmp):
                    async with maker() as session:
                        service = CourseAdService(session)
                        practice = await service.list_active()
                        lesson_end = await service.list_active(slot="lesson_end")
                        one = await service.get_active_ad(slot="lesson_end")

                    self.assertEqual(
                        sorted(ad.title for ad in practice),
                        ["bot", "hamkorlik", "legacy", "odiy"],
                    )
                    self.assertEqual([ad.title for ad in lesson_end], ["dars_yakuni"])
                    self.assertIsNotNone(one)
                    self.assertEqual(one.title, "dars_yakuni")
        finally:
            await engine.dispose()

    def test_course_ad_payload_exposes_language(self):
        from app.db.models.course_ad import CourseAdCreative

        ad = CourseAdCreative(
            id=1, title="x", media_path="course_ad_1.mp4", media_type="video",
            language="uz", duration_seconds=7, is_active=True,
        )
        payload = CourseAdService.payload(ad)
        self.assertEqual(payload["language"], "uz")
        self.assertFalse(payload["media_available"])
        self.assertFalse(payload["media_backed_up"])

    def test_lesson_end_payload_keeps_optional_external_cta(self):
        from app.db.models.course_ad import CourseAdCreative

        ad = CourseAdCreative(
            id=2,
            title="lesson end",
            media_path="lesson_end.mp4",
            media_type="video",
            language="uz",
            ad_type="dars_yakuni",
            link_url="https://example.uz/offer",
            button_text="Batafsil ko'rish",
            duration_seconds=7,
            is_active=True,
        )
        payload = CourseAdService.payload(ad)
        self.assertEqual(payload["ad_type"], "dars_yakuni")
        self.assertEqual(payload["link_url"], "https://example.uz/offer")
        self.assertEqual(payload["button_text"], "Batafsil ko'rish")

    def test_media_available_reflects_file_on_disk(self):
        """Fayli diskda yo'q reklama (ephemeral disk restartda o'chgan) media_available=False
        qaytarishi kerak — u foydalanuvchiga ko'rsatilmasin va qora ekran bermasin."""
        import os
        import tempfile

        from app.db.models.course_ad import CourseAdCreative
        from app.services import course_ad_service as svc

        # Bo'sh/yo'q media_path — mavjud emas.
        self.assertFalse(
            CourseAdService.media_available(
                CourseAdCreative(title="x", media_path="", media_type="video")
            )
        )
        # DB'da yozuv bor, lekin fayl diskda yo'q — mavjud emas.
        self.assertFalse(
            CourseAdService.media_available(
                CourseAdCreative(title="x", media_path="missing_ad.mp4", media_type="video")
            )
        )
        # Fayl haqiqatan mavjud bo'lsa — True.
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(svc, "COURSE_AD_MEDIA_ROOT", tmp):
                name = "present_ad.mp4"
                with open(os.path.join(tmp, name), "wb") as fh:
                    fh.write(b"data")
                self.assertTrue(
                    CourseAdService.media_available(
                        CourseAdCreative(title="x", media_path=name, media_type="video")
                    )
                )

    def test_media_available_restores_missing_file_from_db_backup(self):
        import os
        import tempfile

        from app.db.models.course_ad import CourseAdCreative
        from app.services import course_ad_service as svc

        data = b"safe-mp4"
        name = "restore_ad.mp4"
        ad = CourseAdCreative(
            title="x",
            media_path=name,
            media_type="video",
            media_blob=data,
            media_size=len(data),
            media_checksum=CourseAdService.media_checksum(data),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(svc, "COURSE_AD_MEDIA_ROOT", tmp):
                self.assertTrue(CourseAdService.media_available(ad))
                with open(os.path.join(tmp, name), "rb") as fh:
                    self.assertEqual(fh.read(), data)

    async def test_list_active_backfills_existing_media_backup(self):
        import os
        import tempfile

        from app.db.models.course_ad import CourseAdCreative
        from app.services import course_ad_service as svc

        name = "existing_ad.mp4"
        data = b"existing-mp4"
        ad = CourseAdCreative(
            id=7,
            title="x",
            media_path=name,
            media_type="video",
            duration_seconds=7,
            is_active=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, name), "wb") as fh:
                fh.write(data)
            with mock.patch.object(svc, "COURSE_AD_MEDIA_ROOT", tmp):
                session = _QuerySession([_ScalarListResult([ad])])
                service = CourseAdService(session)
                ads = await service.list_active()
                self.assertEqual(ads, [ad])
                self.assertTrue(service.media_backup_changed)
                self.assertEqual(ad.media_blob, data)
                self.assertEqual(ad.media_size, len(data))
                self.assertEqual(ad.media_checksum, CourseAdService.media_checksum(data))

    async def test_delete_removes_ad_and_returns_media_path(self):
        from app.db.models.course_ad import CourseAdCreative

        ad = CourseAdCreative(
            title="x", media_path="course_ad_1.mp4", media_type="video",
            duration_seconds=7, is_active=True,
        )

        class _Found:
            def scalar_one_or_none(self_inner):
                return ad

        class _Missing:
            def scalar_one_or_none(self_inner):
                return None

        class _DelSession(_FakeSession):
            def __init__(self, result):
                super().__init__()
                self.result = result
                self.deleted = []

            async def execute(self, _query):
                return self.result

            async def delete(self, obj):
                self.deleted.append(obj)

        found = _DelSession(_Found())
        media = await CourseAdService(found).delete(5)
        self.assertEqual(media, "course_ad_1.mp4")
        self.assertIn(ad, found.deleted)

        missing = _DelSession(_Missing())
        self.assertIsNone(await CourseAdService(missing).delete(99))
        self.assertEqual(missing.deleted, [])


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


class CourseMiniAppFoundationStatusTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _session(*payloads):
        return SimpleNamespace(
            execute=mock.AsyncMock(
                return_value=_ScalarListResult(payloads)
            )
        )

    async def test_beginner_foundation_is_required_until_completed_event_exists(self):
        user = SimpleNamespace(level="beginner", telegram_id=123)

        pending = await CourseMiniAppProfileService(self._session()).foundation_status(user)
        completed = await CourseMiniAppProfileService(
            self._session(json.dumps({"foundation_version": 1}))
        ).foundation_status(user)

        self.assertEqual(
            pending,
            {
                "id": "starter0_hsk1",
                "version": 1,
                "required": True,
                "completed": False,
                "status": "required",
            },
        )
        self.assertEqual(
            completed,
            {
                "id": "starter0_hsk1",
                "version": 1,
                "required": True,
                "completed": True,
                "status": "completed",
            },
        )

    async def test_hsk1_foundation_is_optional(self):
        user = SimpleNamespace(level="hsk1", telegram_id=123)

        status = await CourseMiniAppProfileService(self._session()).foundation_status(user)

        self.assertEqual(
            status,
            {
                "id": "starter0_hsk1",
                "version": 1,
                "required": False,
                "completed": False,
                "status": "optional",
            },
        )

    async def test_other_foundation_version_does_not_complete_current_version(self):
        user = SimpleNamespace(level="beginner", telegram_id=123)

        status = await CourseMiniAppProfileService(
            self._session(
                json.dumps({"foundation_version": 2}),
                "not-json",
            )
        ).foundation_status(user)

        self.assertFalse(status["completed"])
        self.assertEqual(status["status"], "required")

    async def test_other_foundation_id_does_not_complete_starter_zero(self):
        user = SimpleNamespace(level="beginner", telegram_id=123)

        status = await CourseMiniAppProfileService(
            self._session(
                json.dumps(
                    {
                        "foundation_id": "some_future_foundation",
                        "foundation_version": 1,
                    }
                )
            )
        ).foundation_status(user)

        self.assertFalse(status["completed"])


class CourseMiniAppAnalyticsTests(unittest.IsolatedAsyncioTestCase):
    def test_server_lesson_jump_events_are_allowlisted(self):
        from app.db.models.course_miniapp_event import COURSE_MINIAPP_EVENT_NAMES

        self.assertIn("level_completed", COURSE_MINIAPP_EVENT_NAMES)
        self.assertIn("lesson_jump_selected", COURSE_MINIAPP_EVENT_NAMES)

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

    def test_client_entry_level_is_replaced_with_server_user_level(self):
        payload = {"entry_level": "hsk4", "card_id": "foundation-meaning-1"}

        trusted = CourseMiniAppAnalyticsService.trusted_client_payload(
            payload,
            SimpleNamespace(level="beginner"),
        )

        self.assertEqual(trusted["entry_level"], "beginner")
        self.assertEqual(trusted["card_id"], "foundation-meaning-1")
        self.assertEqual(payload["entry_level"], "hsk4")


if __name__ == "__main__":
    unittest.main()
