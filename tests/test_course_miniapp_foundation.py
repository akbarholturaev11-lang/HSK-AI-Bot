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
)
from app.services.course_miniapp_access_service import (
    COURSE_AI_PRACTICE_FEATURES,
    COURSE_DAILY_FREE_LIMITS,
    CourseMiniAppAccessService,
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

    def test_unpaid_course_lesson_policy_keeps_only_first_lesson_free(self):
        # Bepul trial (mini-qismlar): 1-2-qism to'liq bepul; 3-qism (yarim
        # preview) va keyingilari premium. Reklama mashq bo'limlarida.
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 1))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 2))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 3))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk1", 4))
        self.assertFalse(CourseMiniAppAccessService.lesson_requires_premium("hsk2", 1))
        self.assertTrue(CourseMiniAppAccessService.lesson_requires_premium("hsk4", 4))


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


if __name__ == "__main__":
    unittest.main()
