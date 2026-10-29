"""Pure decisions and persisted canonical result/access contexts, no providers."""
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
import json
import unittest
from unittest.mock import patch

from sqlalchemy import delete, event, func, select, update

from app.db.models.course_miniapp_event import CLIENT_COURSE_MINIAPP_EVENT_NAMES, CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderConsent, SmartReminderPreference
from app.db.models.user import User
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.daily_plan_service import plan_key
from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import LimitConfigService
from app.services.smart_reminder_policy import HabitCalibration, PolicyContext, VerifiedStudy, evaluate
from app.services.smart_reminder_policy_context import SmartReminderPolicyContextService, TERMINAL_EVENTS
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError
from tests import test_smart_reminder_legacy_backfill as fixtures


UTC = timezone.utc
SIMULATION = HabitCalibration("test-simulation-only", 3)  # Not a product threshold.


def context(**changes):
    values = dict(
        observed_at=datetime(2026, 10, 28, tzinfo=UTC), level="hsk1", progress_level="hsk1",
        expected_level="hsk1", completed_parts=5, total_parts=100, target_allowed=True,
        foundation_required=False, revision=2, grant_epoch=1, master_enabled=True,
        permitted_channels=("telegram",), timezone_name="Etc/UTC", course_day="2026-10-28",
        daily_goal_xp=20, plan_completed=False, saved_time=time(14),
    )
    return PolicyContext(**(values | changes))


def samples(*, hour=2, minute=0, days=3):
    return tuple(VerifiedStudy(f"fixture-{n}", "lesson",
                              datetime(2026, 10, 27, hour, minute, tzinfo=UTC) - timedelta(days=n),
                              f"2026-10-{27-n:02}", 20) for n in range(days))


class PurePolicyTests(unittest.TestCase):
    def check(self, expected, **changes):
        decision = evaluate(context(**changes))
        self.assertEqual(decision.reason, expected)
        self.assertFalse(decision.dispatch_allowed)
        self.assertEqual(decision.candidate, expected == "shadow_candidate")
        return decision

    def test_saved_clock_remains_auto_without_calibration(self):
        d = self.check("shadow_candidate", studies=samples())
        self.assertEqual((d.time_local, d.time_source, d.time_reason),
                         (time(14), "saved", "habit_threshold_unconfigured"))
        self.assertEqual((d.target_lesson_order, d.revision, d.grant_epoch), (6, 2, 1))

    def test_no_saved_time_does_not_invent_default(self):
        self.check("personal_time_unknown", saved_time=None)

    def test_offset_cannot_invent_zone(self):
        d = self.check("timezone_unknown", timezone_name=None)
        self.assertEqual(d.time_local, time(14))
        self.check("timezone_unknown", timezone_name="not/a-zone")

    def test_confirmed_two_am_habit_has_no_global_night_blackout(self):
        d = evaluate(context(studies=samples()), calibration=SIMULATION)
        self.assertTrue(d.candidate)
        self.assertEqual((d.time_local, d.time_source), (time(2), "habit"))
        self.assertEqual(d.scheduled_at, datetime(2026, 10, 28, 2, tzinfo=UTC))
        self.assertFalse(d.dispatch_allowed)

    def test_jitter_around_an_hour_is_one_observed_interval(self):
        clocks = [(20,57),(21,2),(21,5),(20,59),(21,1)]
        studies = tuple(VerifiedStudy(f"jitter-{n}","lesson",
            (context().observed_at-timedelta(days=n+1)).replace(hour=h,minute=m),"old",20)
            for n,(h,m) in enumerate(clocks))
        decision = evaluate(context(studies=studies),calibration=SIMULATION)
        self.assertEqual((decision.time_local,decision.time_source),(time(21,1),"habit"))

    def test_widely_scattered_days_do_not_make_a_minor_exact_mode_a_habit(self):
        clocks = [(21,0)]*3+[(2,0),(5,0),(8,0),(11,0),(14,0),(17,0)]
        studies = tuple(VerifiedStudy(f"scattered-{n}","lesson",
            (context().observed_at-timedelta(days=n+1)).replace(hour=h,minute=m),"old",20)
            for n,(h,m) in enumerate(clocks))
        decision = evaluate(context(studies=studies),calibration=SIMULATION)
        self.assertEqual(decision.time_source,"saved")

    def test_sparse_days_and_duplicate_replays_keep_saved_time(self):
        for studies in (samples(days=1) * 40, samples(days=2)):
            d = evaluate(context(studies=studies), calibration=SIMULATION)
            self.assertEqual((d.time_local, d.time_reason), (time(14), "sparse_learning_days"))

    def test_multiple_sessions_in_one_day_get_one_vote(self):
        studies = samples() + tuple(VerifiedStudy(f"spam-{n}", "test",
                datetime(2026, 10, 27, 20, n, tzinfo=UTC), "2026-10-27", 8) for n in range(40))
        self.assertEqual(evaluate(context(studies=studies), calibration=SIMULATION).time_local, time(2))

    def test_midnight_cluster_does_not_become_noon(self):
        studies = tuple(VerifiedStudy(str(n), "lesson", datetime(2026, 10, 27-n,
                    23 if n % 2 else 0, 59 if n % 2 else 1, tzinfo=UTC), "old", 20) for n in range(6))
        d = evaluate(context(studies=studies), calibration=SIMULATION)
        self.assertEqual((d.time_local, d.time_reason), (time(0, 1), "observed_learning_interval_stable"))

    def test_coverage_limits_prevent_adaptation(self):
        for limit in ("uncorroborated_study", "unsupported_study_type", "observation_window_over_limit"):
            d = evaluate(context(studies=samples(), coverage_limits=(limit,)), calibration=SIMULATION)
            self.assertEqual((d.time_local, d.time_reason), (time(14), "history_coverage_limited"))

    def test_manual_time_wins_over_habit(self):
        d = evaluate(context(studies=samples(), time_mode="manual_locked", manual_time=time(3)), calibration=SIMULATION)
        self.assertEqual((d.time_local, d.time_source), (time(3), "manual"))
        self.check("personal_time_unknown", time_mode="manual_locked", manual_time=None)

    def test_off_and_channel_constraints(self):
        self.check("master_off", master_enabled=False)
        self.check("consent_or_permission_unavailable", permitted_channels=())
        self.check("manual_channel_unavailable", channel_mode="manual_locked", preferred_channel="android")
        self.check("shadow_candidate", master_enabled=None)

    def test_course_switch_access_foundation_and_completion(self):
        self.check("course_context_changed", progress_level="hsk2")
        self.check("course_context_changed", expected_level="nhsk1")
        self.check("course_context_changed", level="")
        self.check("target_inaccessible", target_allowed=False)
        self.check("foundation_required", foundation_required=True)
        self.check("course_completed", completed_parts=100)
        self.check("progress_unknown", completed_parts=101)

    def test_positive_xp_goal_and_plan_are_separate(self):
        study = VerifiedStudy("today", "test", datetime(2026, 10, 28, tzinfo=UTC), "2026-10-28", 20)
        d = self.check("goal_completed", studies=(study,), plan_completed=False)
        self.assertEqual((d.goal_state, d.verified_today_xp), ("met", 20))
        d = self.check("plan_completed", plan_completed=True)
        self.assertEqual((d.goal_state, d.verified_today_xp), ("not_proven", 0))
        self.check("shadow_candidate", studies=(replace(study, course_day="2026-10-27"),))

    def test_future_samples_are_not_learning(self):
        future = VerifiedStudy("future", "test", datetime(2026, 10, 29, tzinfo=UTC), "2026-10-28", 999)
        self.check("shadow_candidate", studies=(future,))

    def test_reward_type_cannot_enter_the_pure_learning_boundary(self):
        reward = VerifiedStudy("reward", "reward_chest", context().observed_at, "2026-10-28", 999)
        d = self.check("shadow_candidate", studies=(reward,))
        self.assertEqual(d.verified_today_xp, 0)

    def test_pause_and_personal_quiet_wrap_midnight(self):
        self.check("paused", pause_until=datetime(2026, 10, 29, tzinfo=UTC))
        self.check("personal_quiet", quiet_start=time(22), quiet_end=time(7))
        self.check("personal_quiet", quiet_start=time(13), quiet_end=time(15))
        self.check("shadow_candidate", quiet_start=time(3), quiet_end=time(7))
        self.check("personal_quiet", quiet_start=time(3))

    def test_mismatched_course_day_and_elapsed_time_are_not_shifted(self):
        self.check("course_day_mismatch", course_day="2026-10-27")
        self.check("personal_time_passed", observed_at=datetime(2026, 10, 28, 15, tzinfo=UTC))

    def test_dst_gap_and_fold_are_refused(self):
        self.check("local_time_nonexistent", observed_at=datetime(2026, 3, 8, 5, tzinfo=UTC),
                   course_day="2026-03-08", timezone_name="America/New_York", saved_time=time(2, 30))
        self.check("local_time_ambiguous", observed_at=datetime(2026, 11, 1, 4, tzinfo=UTC),
                   course_day="2026-11-01", timezone_name="America/New_York", saved_time=time(1, 30))

    def test_fractional_zone_and_non_utc_local_day(self):
        d = self.check("shadow_candidate", observed_at=datetime(2026, 10, 27, 23, tzinfo=UTC),
                       timezone_name="Asia/Kathmandu", course_day="2026-10-28")
        self.assertEqual(d.scheduled_at, datetime(2026, 10, 28, 8, 15, tzinfo=UTC))

    def test_invalid_time_and_calibration_fail_explicitly(self):
        with self.assertRaises(ValueError):
            evaluate(context(observed_at=datetime(2026, 10, 28)))
        for minimum in (0, 1, True):
            with self.assertRaises(ValueError): HabitCalibration("qa", minimum)
        with self.assertRaises(ValueError):
            evaluate(context(studies=(samples()[0], replace(samples()[0], xp=50))))


class PolicyContextChecks:
    postgres = False
    _progress = fixtures.BackfillChecks._progress
    _deletion = fixtures.BackfillChecks._deletion

    async def asyncSetUp(self):
        await fixtures.BackfillChecks.asyncSetUp(self)
        self.moment = self.now.replace(hour=12, minute=0, second=0, microsecond=0)
        self.actor = SmartReminderActor(1, "telegram", telegram_id=3001)
        await self._progress(offset=0)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(level="hsk1"))
            s.add(CourseMiniAppProfile(user_id=1, daily_goal_xp=20, timezone_offset_minutes=0))
            s.add(SmartReminderPreference(user_id=1, revision=2, grant_epoch=1, master_enabled=True,
                      migration_version=1, legacy_time_local=time(14), timezone_name="Etc/UTC"))
            s.add(SmartReminderConsent(user_id=1, channel="telegram", source_key="legacy:telegram",
                      state="on", source="legacy_course_snapshot"))

    async def asyncTearDown(self):
        await fixtures.BackfillChecks.asyncTearDown(self)

    async def load(self, **kwargs):
        async with self.sessions.begin() as s:
            return await SmartReminderPolicyContextService(s).load(
                kwargs.pop("actor", self.actor), observed_at=self.moment,
                history_since=self.moment-timedelta(days=7), expected_level=kwargs.pop("expected_level", "hsk1"), **kwargs)

    async def study(self, *, kind="lesson", days_ago=0, order=1, uid=1, xp=20,
                    level="hsk1", receipt=True, source="course_v3", session="practice-fixture"):
        moment = (self.moment - timedelta(days=days_ago)).replace(hour=2)
        ref = f"v3-part:{level}:{order}:complete" if kind == "lesson" else session+":completed"
        async with self.sessions.begin() as s:
            s.add(CourseXpEvent(user_id=uid, activity_type=kind, activity_ref=ref, xp=xp,
                               activity_date=moment.date(), week_start=moment.date(), created_at=moment))
            if kind == "lesson" and uid == 1:
                await s.execute(update(CourseProgress).where(CourseProgress.user_id == uid).values(completed_lessons_count=order))
            if receipt:
                # Same accepted terminal event shapes as Mini App/native server
                # completion services; ingress prohibition is separately pinned.
                s.add(CourseMiniAppEvent(user_id=uid, level=level, source=source,
                    event_name=kind+"_completed", lesson_order=order if kind == "lesson" else None,
                    session_id=session, created_at=moment, payload_json=json.dumps({"total": 10, "score": 8})))
        return ref

    async def test_reader_is_zero_write_and_does_not_create_missing_plan(self):
        statements = []
        def capture(c, cursor, statement, parameters, ctx, many): statements.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            view = await self.load()
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        self.assertTrue(evaluate(view).candidate)
        self.assertIsNone(view.plan_completed)
        self.assertFalse(any(q.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for q in statements))

    async def test_reader_neither_flushes_pending_changes_nor_uses_stale_orm(self):
        async with self.sessions() as s:
            user = await s.get(User, 1)
            profile = await s.scalar(select(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1))
            await s.execute(update(User).where(User.id == 1).values(level="hsk2").execution_options(synchronize_session=False))
            self.assertEqual(user.level, "hsk1")
            profile.daily_goal_xp = 999
            view = await SmartReminderPolicyContextService(s).load(self.actor, observed_at=self.moment,
                history_since=self.moment-timedelta(days=7), expected_level="hsk1")
            self.assertEqual((view.level, view.daily_goal_xp), ("hsk2", 20))
            self.assertEqual(evaluate(view).reason, "course_context_changed")
            self.assertTrue(s.in_transaction())
            self.assertIn(profile, s.dirty)
            await s.rollback()

    async def test_terminal_names_cannot_be_client_submitted_learning(self):
        self.assertFalse(set(TERMINAL_EVENTS) & set(CLIENT_COURSE_MINIAPP_EVENT_NAMES))
        async with self.sessions.begin() as s:
            for name in TERMINAL_EVENTS:
                result = await CourseMiniAppAnalyticsService(s).record_client_event(event_name=name, user_id=1)
                self.assertFalse(result["ok"])

    async def test_accepted_lesson_and_cross_client_replay_count_once(self):
        ref = await self.study()
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1, level="hsk1", source="android_course", event_name="lesson_completed",
                                    lesson_order=1, session_id="native-replay", created_at=self.moment))
        view = await self.load()
        self.assertEqual([x.reference for x in view.studies], [ref])
        self.assertEqual(evaluate(view).reason, "goal_completed")

    async def test_practice_replay_uses_original_day_not_new_terminal_time(self):
        await self.study(kind="training", days_ago=1, xp=8)
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1, level="hsk1", source="desktop_course", event_name="training_completed",
                session_id="practice-fixture", created_at=self.moment, payload_json='{"total":10,"score":8}'))
        view = await self.load()
        self.assertEqual(len(view.studies), 1)
        self.assertEqual(evaluate(view).verified_today_xp, 0)
        self.assertTrue(evaluate(view).candidate)

    async def test_reward_only_and_open_events_do_not_complete_goal(self):
        await self.study(kind="reward_chest", xp=500, receipt=False)
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1, level="hsk1", source="android", event_name="miniapp_opened", created_at=self.moment))
        view = await self.load()
        self.assertEqual((view.studies, view.coverage_limits), ((), ()))
        self.assertEqual(evaluate(view).goal_state, "not_proven")
        self.assertTrue(evaluate(view).candidate)

    async def test_unpaired_xp_unsupported_type_and_missing_progress_are_not_proof(self):
        await self.study(receipt=False)
        await self.study(kind="voice", receipt=False, session="voice-qa")
        view = await self.load()
        self.assertEqual(view.studies, ())
        self.assertIn("uncorroborated_study", view.coverage_limits)
        self.assertIn("unsupported_study_type", view.coverage_limits)

    async def test_receipt_without_accepted_progress_and_invalid_practice_are_not_proof(self):
        await self.study()
        await self.study(kind="test", session="bad-practice")
        async with self.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id == 1).values(completed_lessons_count=0))
            await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name == "test_completed").values(
                payload_json='{"total":0,"score":0}'))
        self.assertEqual((await self.load()).studies, ())

    async def test_foreign_native_owner_and_wrong_level_are_not_learning(self):
        await self.study(uid=2)
        await self.study(level="nhsk1")
        view = await self.load()
        self.assertEqual(view.studies, ())
        self.assertTrue(evaluate(view).candidate)

    async def test_real_persisted_two_am_history_supports_simulation_only(self):
        for n in (3, 2, 1): await self.study(days_ago=n, order=4-n)
        view = await self.load()
        self.assertEqual(evaluate(view).time_local, time(14))
        d = evaluate(replace(view, observed_at=self.moment.replace(hour=0)), calibration=SIMULATION)
        self.assertEqual((d.time_local, d.reason), (time(2), "shadow_candidate"))
        self.assertFalse(d.dispatch_allowed)

    async def test_stored_plan_complete_is_not_xp_goal_or_new_plan(self):
        async with self.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id == 1).values(completed_lessons_count=1))
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1).values(
                daily_plan_key=plan_key(level="hsk1", local_day=self.moment.date().isoformat()),
                daily_plan_json='[{"t":"continue_lesson","ref":"part:1"}]'))
        d = evaluate(await self.load())
        self.assertEqual((d.reason, d.goal_state), ("plan_completed", "not_proven"))
        async with self.sessions.begin() as s:
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1).values(
                daily_plan_json='[{"t":"continue_lesson","ref":"part:1"},{"t":"bogus"}]'))
        self.assertIsNone((await self.load()).plan_completed)
        async with self.sessions.begin() as s:
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1).values(
                daily_plan_json='[{"t":"continue_lesson","ref":"part:-1"}]'))
        self.assertIsNone((await self.load()).plan_completed)

    async def test_old_course_plan_and_missing_profile_are_not_recreated(self):
        async with self.sessions.begin() as s:
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1).values(
                daily_plan_key="v1:nhsk1:"+self.moment.date().isoformat(),
                daily_plan_json='[{"t":"continue_lesson","ref":"part:1"}]'))
        self.assertIsNone((await self.load()).plan_completed)
        async with self.sessions.begin() as s:
            await s.execute(delete(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == 1))
        view = await self.load()
        self.assertIsNone(view.daily_goal_xp)
        self.assertIsNone(view.course_day)
        self.assertEqual(evaluate(view).reason, "course_day_mismatch")
        async with self.sessions() as s:
            self.assertEqual(await s.scalar(select(func.count()).select_from(CourseMiniAppProfile)), 0)

    async def test_course_switch_and_beginner_foundation_are_not_bypassed(self):
        self.assertEqual(evaluate(await self.load(expected_level="nhsk1")).reason, "course_context_changed")
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(level="beginner"))
        self.assertEqual(evaluate(await self.load()).reason, "foundation_required")
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 1).values(level="hsk2"))
        self.assertEqual(evaluate(await self.load()).reason, "course_context_changed")

    async def test_actual_access_service_refuses_spent_free_limit_without_consumption(self):
        async with self.sessions.begin() as s:
            service = LimitConfigService(s)
            payload = await service.get_payload()
            payload["plans"]["FREE"][A.LESSON_START] = {"limit": 0, "window": "daily"}
            await service.save_config(payload)
        view = await self.load()
        self.assertFalse(view.target_allowed)
        self.assertEqual(evaluate(view).reason, "target_inaccessible")
        async with self.sessions() as s:
            self.assertEqual(await s.scalar(select(func.count()).select_from(CourseMiniAppEvent)), 0)

    async def test_global_off_epoch_and_deletion_use_current_p1_guards(self):
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1).values(
                master_enabled=False, revision=3, grant_epoch=2))
        d = evaluate(await self.load())
        self.assertEqual((d.reason, d.revision, d.grant_epoch), ("master_off", 3, 2))
        await self._deletion()
        with self.assertRaises(SmartReminderError) as exc: await self.load()
        self.assertEqual(exc.exception.code, "smart_account_deletion_pending")

    async def test_native_os_denial_does_not_fall_back_from_manual_android(self):
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id="android-qa", user_id=1, installation_key_hash="synthetic-policy", platform="android", app_version="qa"))
            await s.flush()
            s.add(DesktopSession(id="session-qa", device_id="android-qa", refresh_token_hash="synthetic-policy",
                                 expires_at=self.now+timedelta(days=1)))
            s.add(SmartReminderConsent(user_id=1, device_id="android-qa", channel="android", state="on",
                                      source="user_intent", source_key="intent:android:android-qa"))
            s.add(SmartReminderCapability(device_id="android-qa", user_id=1, study_notifications_allowed=False))
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1).values(
                channel_mode="manual_locked", preferred_channel="android"))
        actor = SmartReminderActor(1, "android", device_id="android-qa", session_id="session-qa")
        self.assertEqual(evaluate(await self.load(actor=actor)).reason, "manual_channel_unavailable")
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopSession).where(DesktopSession.id == "session-qa").values(revoked_at=self.now))
        with self.assertRaises(SmartReminderError): await self.load(actor=actor)

    async def test_native_only_canonical_owner_never_enrolls_telegram(self):
        await self._progress(user_id=2, offset=0)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 2).values(level="hsk1"))
            s.add(CourseMiniAppProfile(user_id=2, timezone_offset_minutes=0))
            s.add(SmartReminderPreference(user_id=2, master_enabled=True, legacy_time_local=time(14), timezone_name="Etc/UTC"))
            s.add(DesktopDevice(id="native-only", user_id=2, installation_key_hash="synthetic-native-only", platform="android", app_version="qa"))
            await s.flush()
            s.add(DesktopSession(id="native-session", device_id="native-only", refresh_token_hash="synthetic-native-only",
                                 expires_at=self.now+timedelta(days=1)))
            s.add(SmartReminderConsent(user_id=2, device_id="native-only", channel="android", state="on",
                                      source="user_intent", source_key="intent:android:native-only"))
            s.add(SmartReminderCapability(device_id="native-only", user_id=2, study_notifications_allowed=True,
                      observed_at=self.now-timedelta(minutes=1), expires_at=self.now+timedelta(hours=1)))
        actor = SmartReminderActor(2, "android", device_id="native-only", session_id="native-session")
        view = await self.load(actor=actor)
        self.assertEqual(view.permitted_channels, ("android",))
        self.assertTrue(evaluate(view).candidate)
        self.assertFalse(evaluate(view).dispatch_allowed)
        async with self.sessions() as s:
            self.assertIsNone(await s.scalar(select(User.telegram_id).where(User.id == 2)))
            self.assertEqual(await s.scalar(select(func.count()).select_from(SmartReminderConsent).where(
                SmartReminderConsent.user_id == 2, SmartReminderConsent.channel == "telegram")), 0)

    async def test_truncated_window_is_explicit_and_disables_habit(self):
        for n in (3, 2, 1): await self.study(days_ago=n, order=4-n)
        with patch("app.services.smart_reminder_policy_context.MAX_POLICY_ROWS", 2):
            view = await self.load()
        self.assertIn("observation_window_over_limit", view.coverage_limits)
        self.assertEqual(evaluate(view, calibration=SIMULATION).time_source, "saved")


class SQLitePolicyContextTests(PolicyContextChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.PG_URL, "Disposable loopback PostgreSQL not configured")
class PostgreSQLPolicyContextTests(PolicyContextChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
