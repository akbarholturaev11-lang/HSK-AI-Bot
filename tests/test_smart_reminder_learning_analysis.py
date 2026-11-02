"""Partial original target learning is temporal evidence, never causal return."""
import asyncio
from datetime import timedelta
import unittest

from sqlalchemy import event, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.desktop_course_service import DesktopCourseService
from app.services.smart_reminder_analysis import SmartReminderAnalysisService
from app.services.smart_reminder_preferences import _utc
from tests import test_smart_reminder_analysis as fixture
from tests import test_smart_reminder_telegram as telegram_fixture


class TargetLearningChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = fixture.PostgreSQLAnalysisTests if self.postgres else fixture.SQLiteAnalysisTests
        self.fixture = cls(methodName="test_reserved_fact_replay_counts_once_and_source_is_unchanged")
        await self.fixture.asyncSetUp()
        self.case = self.fixture.case
        self.analysis = self.fixture.analysis
        self.started = self.case.tick
        self.learned = self.started + timedelta(seconds=20)
        self.fixture.moment = self.started + timedelta(seconds=60)

    async def asyncTearDown(self):
        if hasattr(self, "case"):
            await self.fixture.asyncTearDown()

    async def contact(self, outcome="client_posted_unverified"):
        grant = await self.case.claim()
        self.case.tick += timedelta(seconds=1)
        await self.case.receipt(grant, outcome)
        return grant

    async def result(self, *, order=5, at=None, arrived=None, duplicate=False, changes=None):
        """Existing authoritative XP/progress + native server result contract."""
        at = at or self.learned
        async with self.case.sessions.begin() as session:
            user = await session.get(User, 1)
            ref = f"v3-part:hsk1:{order}:complete"
            game = await CourseGamificationService(session).award(user, activity_type="lesson",
                activity_ref=ref, base_xp=20, level="hsk1")
            if duplicate:
                game = await CourseGamificationService(session).award(user, activity_type="lesson",
                    activity_ref=ref, base_xp=20, level="hsk1")
            result = DesktopCourseService._completion_payload(lesson_order=order, next_lesson=order+1,
                completed_lessons_count=order, gamification=game)
            payload = {"device_id": "device-1", "result": result} | (changes or {})
            await CourseMiniAppAnalyticsService(session).record_server_event(event_name="lesson_completed",
                user_id=1, telegram_id=user.telegram_id, source="android_course", level="hsk1",
                lesson_order=order, session_id=f"native-result-{order}", dedupe_key=f"native-result-{order}", payload=payload)
            await session.execute(update(CourseXpEvent).where(CourseXpEvent.user_id == 1,
                CourseXpEvent.activity_ref == ref).values(created_at=at, activity_date=at.date()))
            await session.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id == 1,
                CourseMiniAppEvent.source == "android_course", CourseMiniAppEvent.lesson_order == order)
                .values(created_at=arrived or at))
            await session.execute(update(CourseProgress).where(CourseProgress.user_id == 1)
                .values(completed_lessons_count=order))

    async def read(self, uid=1, job=None):
        return await self.analysis.target_learning(uid, job or self.case.job_id)

    async def test_original_target_after_real_native_receipt_is_read_only_and_replay_stable(self):
        await self.contact()
        await self.result()
        tables = (fixture.JOB, fixture.ATTEMPT, fixture.GRANT, fixture.EVENT, fixture.MONTHLY,
            CourseXpEvent.__table__, CourseMiniAppEvent.__table__, CourseProgress.__table__)
        before = [await self.fixture.rows(t) for t in tables]
        statements = []
        def inspect(c, cursor, statement, parameters, context, executemany):
            statements.append(statement)
            if statement.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
                raise AssertionError("Learning projection must not write")
        event.listen(self.case.engine.sync_engine, "before_cursor_execute", inspect)
        try:
            result = await self.read()
            self.assertEqual(result, await self.read())
        finally:
            event.remove(self.case.engine.sync_engine, "before_cursor_execute", inspect)
        self.assertEqual(result.reason, "verified_target_learning_after_attempt")
        self.assertEqual((result.boundary_at, result.learned_at), (self.started, self.learned))
        self.assertIn("causal_attribution_unavailable", result.coverage_limits)
        self.assertIn("independent_open_unavailable", result.coverage_limits)
        self.assertEqual(before, [await self.fixture.rows(t) for t in tables])
        if self.postgres:
            user_lock = next(i for i,s in enumerate(statements) if "users" in s and "FOR UPDATE" in s)
            source = next(i for i,s in enumerate(statements) if "course_xp_events" in s)
            self.assertLess(user_lock, source)

    async def test_late_receipt_keeps_original_learning_time(self):
        await self.contact()
        await self.result(arrived=self.learned+timedelta(seconds=25))
        self.assertEqual((await self.read()).learned_at, self.learned)

    async def test_old_result_replayed_after_contact_is_unavailable(self):
        await self.contact()
        await self.result(at=self.started-timedelta(seconds=20), arrived=self.learned)
        self.assertEqual((await self.read()).reason, "target_learning_unavailable")
        self.assertIsNone((await self.read()).learned_at)

    async def test_missing_open_only_bonus_and_other_target_are_not_zero_learning(self):
        await self.contact()
        async with self.case.sessions.begin() as session:
            user = await session.get(User, 1)
            await CourseGamificationService(session).award(user, activity_type="bonus",
                activity_ref="synthetic-bonus", base_xp=10, level="hsk1")
            await CourseMiniAppAnalyticsService(session).record_server_event(event_name="android_app_opened",
                user_id=1, telegram_id=user.telegram_id, source="android", level="hsk1")
        await self.result(order=6)
        result = await self.read()
        self.assertEqual(result.reason, "target_learning_unavailable")
        self.assertIsNone(result.learned_at)
        self.assertIn("negative_learning_coverage_unknown", result.coverage_limits)

    async def test_incomplete_duplicate_and_malformed_result_receipts_do_not_qualify(self):
        await self.contact()
        await self.result(duplicate=True)
        self.assertIsNone((await self.read()).learned_at)
        async with self.case.sessions.begin() as session:
            await session.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.source == "android_course")
                .values(payload_json='{"device_id":"device-1","result":{"ok":true}}'))
        self.assertIsNone((await self.read()).learned_at)

    async def test_unposted_declined_and_unknown_contacts_are_not_learning_links(self):
        self.assertEqual((await self.read()).reason, "learning_contact_unconfirmed")
        await self.contact("client_outcome_unknown")
        await self.result()
        self.assertIsNone((await self.read()).learned_at)
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.ATTEMPT).values(state="confirmed_not_displayed"))
            await session.execute(update(fixture.GRANT).values(receipt_outcome="client_declined_before_post"))
        self.assertEqual((await self.read()).reason, "learning_contact_unconfirmed")

    async def test_unpaired_receipt_and_wrong_epoch_cannot_prove_contact(self):
        await self.contact()
        await self.result()
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.GRANT).values(preference_revision=99))
        self.assertEqual((await self.read()).reason, "learning_contact_unconfirmed")
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.GRANT).values(preference_revision=2,
                expires_at=self.started+timedelta(seconds=2)))
        self.assertEqual((await self.read()).reason, "learning_contact_unconfirmed")

    async def test_foreign_missing_blocked_and_deleting_owners_have_no_result(self):
        await self.contact()
        await self.result()
        self.assertEqual((await self.read(uid=2)).reason, "learning_job_unavailable")
        self.assertEqual((await self.read(uid=999)).reason, "learning_owner_unavailable")
        async with self.case.sessions.begin() as session:
            await session.execute(update(User).where(User.id == 1).values(status="blocked"))
        self.assertEqual((await self.read()).reason, "learning_owner_unavailable")
        async with self.case.sessions.begin() as session:
            await session.execute(update(User).where(User.id == 1).values(status="active"))
        await self.case._deletion()
        self.assertEqual((await self.read()).reason, "learning_owner_unavailable")

    async def test_other_course_target_and_shadow_policy_are_unavailable(self):
        await self.contact()
        await self.result()
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(course_key="hsk2"))
        self.assertIsNone((await self.read()).learned_at)
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(policy_version="smart-queue-shadow-v1"))
        self.assertEqual((await self.read()).reason, "learning_source_unsupported")

    async def test_equal_future_and_next_day_results_do_not_enter_window(self):
        await self.contact()
        await self.result(at=self.started)
        self.assertIsNone((await self.read()).learned_at)
        async with self.case.sessions.begin() as session:
            await session.execute(update(CourseXpEvent).where(CourseXpEvent.activity_ref == "v3-part:hsk1:5:complete")
                .values(created_at=self.fixture.moment+timedelta(seconds=1)))
        self.assertIsNone((await self.read()).learned_at)
        job = (await self.fixture.rows(fixture.JOB))[0]
        end = _utc(job["day_end_utc"])
        self.fixture.moment = end + timedelta(seconds=10)
        async with self.case.sessions.begin() as session:
            await session.execute(update(CourseXpEvent).where(CourseXpEvent.activity_ref == "v3-part:hsk1:5:complete")
                .values(created_at=end))
            await session.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.source == "android_course")
                .values(created_at=end))
        self.assertIsNone((await self.read()).learned_at)

    async def test_bad_frozen_timezone_and_expired_sources_stay_unavailable(self):
        await self.contact()
        await self.result()
        self.fixture.moment += timedelta(days=91)
        self.assertEqual((await self.read()).reason, "learning_window_unavailable")
        self.fixture.moment = self.started+timedelta(seconds=60)
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(timezone_name="Unknown/Zone"))
        self.assertEqual((await self.read()).reason, "learning_window_unavailable")

    async def test_source_over_limit_is_unknown(self):
        await self.contact()
        await self.result()
        async with self.case.sessions.begin() as session:
            session.add_all([CourseMiniAppEvent(user_id=1, source="android_course", level="hsk1",
                event_name="lesson_completed", lesson_order=5, created_at=self.learned,
                payload_json="{}") for _ in range(513)])
        result = await self.read()
        self.assertIsNone(result.learned_at)
        self.assertIn("learning_history_over_limit", result.coverage_limits)

    async def test_native_result_can_follow_telegram_contact_without_same_device_or_causal_claim(self):
        await self.contact()
        # A stored Telegram provider outcome: no real provider is contacted.
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(selected_channel="telegram", selected_device_id=None,
                policy_version="smart-telegram-v1:synthetic"))
            await session.execute(update(fixture.ATTEMPT).values(channel="telegram", device_id=None,
                state="provider_accepted"))
        await self.result(changes={"device_id": "another-owned-lesson-device"})
        result = await self.read()
        self.assertEqual(result.reason, "verified_target_learning_after_attempt")
        self.assertNotIn("device", vars(result))
        self.assertIn("causal_attribution_unavailable", result.coverage_limits)

    async def test_invalid_identity_is_refused_before_sql(self):
        for uid, job in ((True, self.case.job_id), (0, self.case.job_id), (1, ""), (1, "x"*37)):
            with self.subTest(uid=uid), self.assertRaises(ValueError):
                await self.analysis.target_learning(uid, job)

    async def test_postgres_waiting_projection_rechecks_submitted_deletion_before_learning(self):
        if not self.postgres:
            self.skipTest("PostgreSQL canonical owner row lock")
        await self.contact()
        await self.result()
        # Hold the same canonical lock as deletion; the projection must wait
        # and see the committed guard before reading personal lesson sources.
        from app.db.models.account_deletion import AccountDeletionRequest
        async with self.case.sessions.begin() as session:
            await session.execute(select(User.id).where(User.id == 1).with_for_update())
            task = asyncio.create_task(self.read())
            try:
                await asyncio.sleep(.05)
                self.assertFalse(task.done())
                session.add(AccountDeletionRequest(id="learning-guard", user_id=1, active_user_id=1,
                    provider="telegram", status="submitted", secret_hash="a"*64, client_hash="b"*64,
                    created_at=self.started, expires_at=self.started+timedelta(hours=1)))
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
        self.assertEqual((await asyncio.wait_for(task, 2)).reason, "learning_owner_unavailable")


class TelegramTargetLearningChecks:
    postgres = False
    result = TargetLearningChecks.result

    async def asyncSetUp(self):
        cls = telegram_fixture.PostgreSQLTelegramTests if self.postgres else telegram_fixture.SQLiteTelegramTests
        self.case = cls(methodName="test_one_committed_telegram_attempt_accepts_provider_not_display")
        await self.case.asyncSetUp()
        self.started = self.case.tick
        self.learned = self.started + timedelta(seconds=20)
        self.observed = self.started + timedelta(seconds=60)
        self.analysis = SmartReminderAnalysisService(self.case.sessions, clock=lambda: self.observed)

    async def asyncTearDown(self):
        if hasattr(self, "case"):
            await self.case.asyncTearDown()

    async def test_actual_telegram_acceptance_then_original_native_target_result(self):
        await self.case.active()
        job = await self.case.prepare()
        self.case.tick = self.case.tick.replace(hour=14)
        self.started = self.case.tick
        self.learned = self.started + timedelta(seconds=20)
        self.observed = self.started + timedelta(seconds=60)
        lease = await self.case.claim(job.job_id)
        outcome = await self.case.dispatch(lease)
        self.assertEqual(outcome.reason, "telegram_provider_accepted")
        await self.result(changes={"device_id": "native-lesson-device"})
        result = await self.analysis.target_learning(1, job.job_id)
        self.assertEqual(result.reason, "verified_target_learning_after_attempt")
        self.assertEqual(result.learned_at, self.learned)
        self.case.bot.send_message.assert_awaited_once()


class SQLiteTargetLearningTests(TargetLearningChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixture.PG_URL, "Owned loopback PostgreSQL required")
class PostgreSQLTargetLearningTests(TargetLearningChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class SQLiteTelegramLearningTests(TelegramTargetLearningChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixture.PG_URL, "Owned loopback PostgreSQL required")
class PostgreSQLTelegramLearningTests(TelegramTargetLearningChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
