"""Cadence simulations and real ledger readers; QA numbers are not defaults."""
from dataclasses import replace
from datetime import datetime, time, timedelta
from fractions import Fraction
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import event, update

from app.db.models.course_progress import CourseProgress
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderJob, SmartReminderPreference
from app.services.smart_reminder_cadence import (
    CadenceCalibration, CadenceContext, StudyIntent, evaluate_cadence,
)
from app.services.smart_reminder_policy import VerifiedStudy
from app.services.smart_reminder_policy_context import SmartReminderPolicyContextService
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError
from tests import test_smart_reminder_policy as policy_tests
from tests import test_smart_reminder_legacy_backfill as fixtures


# Deliberately explicit simulation configuration. No runtime caller/settings.
QA = CadenceCalibration("qa-only-not-approved", 4, Fraction(2), Fraction(1), 2, 3, 7)
NOW = policy_tests.context().observed_at


def history(days_ago=(3, 4, 5, 6, 7)):
    return tuple(VerifiedStudy(f"fixture:{n}", "lesson", NOW-timedelta(days=n)+timedelta(hours=2),
                              (NOW-timedelta(days=n)).date().isoformat(), 1) for n in days_ago)


def intent(days_ago, *, shown=False, external=False, state="shadow", owner=1):
    start = NOW-timedelta(days=days_ago)
    scheduled = start+timedelta(hours=2)
    return StudyIntent(f"job-{days_ago}", owner, start.date(), "Etc/UTC", start, start+timedelta(days=1),
                       scheduled, state, external or shown, scheduled if shown else None)


def context(*, studies=None, intents=(), complete=True, **changes):
    values = dict(user_id=1, policy=policy_tests.context(studies=history() if studies is None else studies),
                  history_since=NOW-timedelta(days=30), intents=intents, ledger_complete=True,
                  learning_complete_since=NOW-timedelta(days=30) if complete else None)
    return CadenceContext(**(values | changes))


class PureCadenceTests(unittest.TestCase):
    def check(self, expected, snapshot=None, *, calibration=QA):
        decision = evaluate_cadence(snapshot or context(), calibration=calibration)
        self.assertEqual(decision.reason, expected)
        self.assertFalse(decision.dispatch_allowed)
        self.assertEqual(decision.candidate, expected == "shadow_candidate")
        return decision

    def test_unconfigured_calibration_cannot_enable_adaptation(self):
        self.check("cadence_calibration_unconfigured", calibration=None)

    def test_same_gap_differs_for_daily_and_twice_weekly_learners(self):
        daily = self.check("shadow_candidate")
        twice = self.check("shadow_candidate", context(studies=history((3, 6, 10, 13, 17))))
        self.assertEqual((daily.observed_gap_days, daily.abnormal_inactivity), (Fraction(1), True))
        self.assertEqual((twice.observed_gap_days, twice.abnormal_inactivity), (Fraction(7, 2), False))

    def test_reactivation_uses_personal_gap_not_universal_delays(self):
        snapshot = context(studies=history((3, 13, 23, 33)), history_since=NOW-timedelta(days=40),
                           learning_complete_since=NOW-timedelta(days=40))
        d = self.check("personal_cadence_cooldown", snapshot)
        self.assertEqual((d.observed_gap_days, d.abnormal_inactivity), (Fraction(10), False))

    def test_same_day_ownership_survives_every_state_and_calibration(self):
        for state in ("shadow", "pending", "claimed", "provider_accepted", "unknown", "cancelled", "expired", "completed"):
            with self.subTest(state=state):
                self.check("account_day_already_owned", context(intents=(intent(0, state=state),)), calibration=None)

    def test_overlapping_frozen_day_blocks_travel_duplicate(self):
        job = replace(intent(1), day_end_utc=NOW+timedelta(hours=5))
        self.check("account_day_already_owned", context(intents=(job,)))

    def test_dst_day_ownership_uses_frozen_utc_overlap(self):
        for month, day in ((3, 8), (11, 1)):
            moment=datetime(2026, month, day, 5 if month==3 else 4, tzinfo=NOW.tzinfo)
            policy=policy_tests.context(observed_at=moment, course_day=moment.date().isoformat(),
                                       timezone_name="America/New_York")
            job=replace(intent(2), local_day=(moment-timedelta(days=1)).date(),
                        day_start_utc=moment-timedelta(days=1), day_end_utc=moment+timedelta(hours=1),
                        scheduled_at=moment-timedelta(hours=12), timezone_name="America/New_York")
            self.check("account_day_already_owned", context(policy=policy, intents=(job,),
                       history_since=moment-timedelta(days=30)), calibration=None)

    def test_ledger_owner_conflict_and_incomplete_window_refuse(self):
        self.check("cadence_owner_mismatch", context(intents=(intent(3, owner=2),)))
        job = intent(3)
        self.check("cadence_ledger_conflict", context(intents=(job, replace(job, state="expired"))))
        self.check("cadence_ledger_incomplete", context(ledger_complete=False))
        self.check("cadence_owner_unknown", context(user_id=0))
        self.check("cadence_window_invalid", context(history_since=NOW+timedelta(days=1)))
        self.check("cadence_ledger_invalid", context(intents=(replace(job, state="invented"),)))

    def test_weekly_count_is_per_intent_not_per_endpoint_or_attempt(self):
        job = intent(2, external=True, state="provider_accepted")
        d = self.check("weekly_study_budget", context(intents=(job, job)), calibration=replace(QA, weekly_maximum=1))
        self.assertEqual(d.weekly_intents, 1)

    def test_shadow_cancelled_and_expired_without_attempt_do_not_spend_week(self):
        jobs = (intent(2), intent(3, state="cancelled"), intent(4, state="expired"))
        self.assertEqual(self.check("shadow_candidate", context(intents=jobs)).weekly_intents, 0)

    def test_live_reservation_and_cancelled_external_attempt_do_spend_week(self):
        for job in (intent(2, state="pending"), intent(2, state="claimed"), intent(2, state="cancelled", external=True)):
            self.check("weekly_study_budget", context(intents=(job,)), calibration=replace(QA, weekly_maximum=1))

    def test_rolling_week_boundary_and_history_coverage(self):
        self.check("shadow_candidate", context(intents=(intent(7, state="pending"),)), calibration=replace(QA, weekly_maximum=1))
        self.check("weekly_study_budget", context(intents=(intent(6, state="pending"),)), calibration=replace(QA, weekly_maximum=1))
        self.check("weekly_budget_window_incomplete", context(history_since=NOW-timedelta(days=5)))

    def test_zone_change_does_not_reinterpret_the_ledger(self):
        self.check("cadence_timezone_changed", context(intents=(replace(intent(3), timezone_name="Asia/Tashkent"),)))

    def test_incomplete_learning_cannot_prove_inactivity_or_failure(self):
        d = self.check("learning_coverage_unknown", context(complete=False))
        self.assertEqual(d.observed_gap_days, 1)
        self.assertIsNone(d.abnormal_inactivity)
        self.assertIsNone(d.unsuccessful_count)
        self.check("learning_coverage_unknown", context(learning_complete_since=NOW-timedelta(days=10)))

    def test_sparse_duplicate_or_unverified_sources_do_not_establish_rhythm(self):
        self.check("sparse_learning_history", context(studies=history((3,))*20))
        self.check("sparse_learning_history", context(studies=()))
        snapshot=context()
        self.check("cadence_source_coverage_limited", replace(snapshot, policy=replace(snapshot.policy,
                    coverage_limits=("uncorroborated_study",))))

    def test_provider_acceptance_or_post_without_display_is_not_ignored(self):
        studies = history((10, 11, 12, 13))
        for state in ("provider_accepted", "unknown", "cancelled"):
            d = self.check("delivery_outcome_unknown", context(studies=studies,
                    intents=(intent(3, state=state, external=True),)))
            self.assertIsNone(d.unsuccessful_count)

    def test_new_learning_does_not_guess_when_an_unknown_job_was_displayed(self):
        snapshot=context(intents=(intent(12, external=True, state="unknown"),))
        self.check("delivery_outcome_unknown", snapshot)

    def test_definite_non_display_is_not_an_unsuccessful_user_response(self):
        job=replace(intent(3, external=True, state="cancelled"), definite_non_display=True)
        d=self.check("shadow_candidate", context(intents=(job,)))
        self.assertEqual(d.unsuccessful_count, 0)
        self.assertEqual(d.weekly_intents, 1)

    def test_late_verified_exposure_uses_shown_time_not_old_schedule(self):
        job=replace(intent(12, external=True), verified_shown_at=NOW-timedelta(days=1))
        d=self.check("personal_cadence_cooldown", context(intents=(job,)))
        self.assertEqual(d.unsuccessful_count, 1)

    def test_observation_window_must_finish_before_negative_outcome(self):
        studies=history((10, 11, 12, 13))
        job=intent(1, shown=True, state="completed")
        self.check("outcome_observation_pending", context(studies=studies, intents=(job,)))

    def test_intervals_widen_after_mature_verified_shown_without_learning(self):
        studies=history((10, 11, 12, 13))
        one=self.check("shadow_candidate", context(studies=studies, intents=(intent(3, shown=True),)))
        two=self.check("personal_cadence_cooldown", context(studies=studies, intents=(intent(6, shown=True), intent(3, shown=True))))
        self.assertEqual((one.unsuccessful_count, two.unsuccessful_count), (1, 2))
        self.assertEqual(one.next_eligible_at, intent(3).scheduled_at+timedelta(days=2))
        self.assertEqual(two.next_eligible_at, intent(3).scheduled_at+timedelta(days=4))

    def test_finite_series_stops_and_duplicate_job_does_not_speed_it(self):
        studies=history((20, 21, 22, 23))
        jobs=tuple(intent(n, shown=True) for n in (12, 10, 6))
        self.check("reactivation_stopped", context(studies=studies, intents=jobs))
        d=self.check("shadow_candidate", context(studies=studies, intents=(jobs[0],)*20))
        self.assertEqual(d.unsuccessful_count, 1)

    def test_original_verified_learning_restarts_after_stop_without_resetting_budget(self):
        studies=history((20, 21, 22, 23))
        jobs=tuple(intent(n, shown=True) for n in (12, 10, 6))
        self.check("reactivation_stopped", context(studies=studies, intents=jobs))
        fresh=VerifiedStudy("fresh-original", "training", NOW-timedelta(days=2), "old", 8)
        d=self.check("shadow_candidate", context(studies=studies+(fresh,), intents=jobs))
        self.assertEqual(d.unsuccessful_count, 0)
        self.assertEqual(d.weekly_intents, 1)
        self.check("weekly_study_budget", context(studies=studies+(fresh,), intents=jobs), calibration=replace(QA, weekly_maximum=1))

    def test_replay_reward_and_open_cannot_restart_stopped_series(self):
        studies=history((20, 21, 22, 23))
        jobs=tuple(intent(n, shown=True) for n in (12, 10, 6))
        reward=VerifiedStudy("chest", "reward_chest", NOW-timedelta(days=2), "old", 500)
        self.check("reactivation_stopped", context(studies=studies+studies+(reward,), intents=jobs))
        # Opens are not a field in the cadence input. A posted/accepted unknown
        # outcome cannot stand in for display or restart learning.

    def test_current_off_access_goal_quiet_and_manual_rules_win(self):
        for changes, reason in (({"master_enabled":False}, "master_off"),
                ({"target_allowed":False}, "target_inaccessible"),
                ({"plan_completed":True}, "plan_completed"),
                ({"quiet_start":time(22), "quiet_end":time(7)}, "personal_quiet"),
                ({"expected_level":"nhsk1"}, "course_context_changed")):
            snapshot=context()
            self.check(reason, replace(snapshot, policy=replace(snapshot.policy, **changes)))
        snapshot=context()
        snapshot=replace(snapshot, policy=replace(snapshot.policy, time_mode="manual_locked", manual_time=time(2)))
        self.assertEqual(self.check("shadow_candidate", snapshot).eligibility.time_local, time(2))

    def test_invalid_calibration_is_rejected(self):
        for changes in ({"weekly_maximum":8},{"weekly_maximum":True},{"backoff_factor":1},
                        {"maximum_unsuccessful":0},{"minimum_learning_days":1},
                        {"abnormal_gap_multiplier":Fraction(1)},{"observation_multiplier":0.5},{"version":" "}):
            with self.assertRaises(ValueError): replace(QA, **changes)

    def test_extreme_calibration_does_not_wrap_into_an_earlier_date(self):
        snapshot=context(studies=history((10, 11, 12, 13)), intents=(intent(3, shown=True),))
        self.check("cadence_time_out_of_range", snapshot, calibration=replace(QA, backoff_factor=10**20))


class CadenceReaderChecks:
    postgres=False
    asyncSetUp=policy_tests.PolicyContextChecks.asyncSetUp
    asyncTearDown=policy_tests.PolicyContextChecks.asyncTearDown
    _progress=policy_tests.PolicyContextChecks._progress
    _deletion=policy_tests.PolicyContextChecks._deletion
    study=policy_tests.PolicyContextChecks.study

    async def load(self, *, actor=None):
        async with self.sessions.begin() as s:
            return await SmartReminderPolicyContextService(s).load_cadence(
                actor or self.actor, observed_at=self.moment,
                history_since=self.moment-timedelta(days=30), expected_level="hsk1")

    async def job(self, days_ago=2, *, state="shadow", uid=1, attempts=()):
        start=(self.moment-timedelta(days=days_ago)).replace(hour=0)
        job=SmartReminderJob(id=str(uuid4()), user_id=uid, local_day=start.date(), timezone_name="Etc/UTC",
            day_start_utc=start, day_end_utc=start+timedelta(days=1), scheduled_at=start+timedelta(hours=2),
            expires_at=start+timedelta(hours=23), state=state, policy_version="qa-only")
        async with self.sessions.begin() as s:
            s.add(job)
            await s.flush()
            for outcome in attempts:
                started=job.scheduled_at if outcome != "prepared" else None
                s.add(SmartReminderAttempt(job_id=job.id, attempt_key=uuid4().hex, channel="telegram", state=outcome,
                    prepared_at=job.scheduled_at-timedelta(minutes=1), started_at=started,
                    resolved_at=started+timedelta(minutes=1) if started else None, expires_at=job.expires_at))
        return job

    async def test_legacy_reader_never_claims_complete_negative_coverage(self):
        for n in (8, 7, 6, 5, 4): await self.study(days_ago=n, order=9-n)
        snapshot=await self.load()
        self.assertIsNone(snapshot.learning_complete_since)
        d=evaluate_cadence(snapshot, calibration=QA)
        self.assertEqual(d.reason, "learning_coverage_unknown")
        self.assertEqual(d.observed_gap_days, 1)
        self.assertIsNone(d.abnormal_inactivity)

    async def test_real_attempt_rollup_counts_one_logical_job_across_attempts(self):
        await self.job(attempts=("provider_accepted", "verified_shown"))
        snapshot=await self.load()
        self.assertEqual(len(snapshot.intents), 1)
        self.assertTrue(snapshot.intents[0].externally_attempted)
        self.assertIsNotNone(snapshot.intents[0].verified_shown_at)
        d=evaluate_cadence(snapshot, calibration=replace(QA, weekly_maximum=1))
        self.assertEqual((d.reason, d.weekly_intents), ("weekly_study_budget", 1))

    async def test_accepted_and_posted_are_unknown_without_independent_display(self):
        await self.job(2, state="provider_accepted", attempts=("provider_accepted",))
        await self.job(3, attempts=("client_posted_unverified", "unknown"))
        snapshot=await self.load()
        self.assertTrue(all(j.externally_attempted for j in snapshot.intents))
        self.assertTrue(all(j.verified_shown_at is None for j in snapshot.intents))

    async def test_definite_rejections_are_separate_from_unknown_and_shown(self):
        await self.job(2, state="cancelled", attempts=("definite_failure", "confirmed_not_displayed"))
        await self.job(3, state="cancelled", attempts=("definite_failure", "unknown"))
        by_day={j.local_day:j for j in (await self.load()).intents}
        self.assertTrue(by_day[(self.moment-timedelta(days=2)).date()].definite_non_display)
        self.assertFalse(by_day[(self.moment-timedelta(days=3)).date()].definite_non_display)

    async def test_prepared_attempt_and_legacy_sent_time_are_not_exposure(self):
        await self.job(attempts=("prepared",))
        async with self.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(last_reminder_sent_at=self.moment))
        snapshot=await self.load()
        self.assertEqual(len(snapshot.intents), 1)
        self.assertFalse(snapshot.intents[0].externally_attempted)
        self.assertIsNone(snapshot.intents[0].verified_shown_at)
        self.assertIsNone(snapshot.learning_complete_since)

    async def test_same_day_cancelled_ownership_is_not_recreated_after_off_on(self):
        await self.job(0, state="cancelled")
        snapshot=await self.load()
        self.assertEqual(evaluate_cadence(snapshot).reason, "account_day_already_owned")
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1).values(
                revision=10, grant_epoch=4))
        d=evaluate_cadence(await self.load())
        self.assertEqual(d.reason, "account_day_already_owned")
        self.assertEqual((d.eligibility.revision, d.eligibility.grant_epoch), (10, 4))

    async def test_owner_scoped_ledger_and_forged_actor(self):
        await self.job(uid=2)
        self.assertEqual((await self.load()).intents, ())
        with self.assertRaises(SmartReminderError):
            await self.load(actor=SmartReminderActor(2, "telegram", telegram_id=3001))

    async def test_reader_has_no_writes_and_does_not_flush_or_commit(self):
        await self.job()
        statements=[]
        def capture(c, cursor, sql, parameters, ctx, many): statements.append(sql)
        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            async with self.sessions() as s:
                progress=await s.get(CourseProgress, 1)
                progress.completed_lessons_count=99
                snapshot=await SmartReminderPolicyContextService(s).load_cadence(self.actor, observed_at=self.moment,
                    history_since=self.moment-timedelta(days=30), expected_level="hsk1")
                self.assertEqual(snapshot.policy.completed_parts, 0)
                self.assertIn(progress, s.dirty)
                self.assertTrue(s.in_transaction())
                await s.rollback()
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        self.assertFalse(any(q.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for q in statements))

    async def test_overflow_is_explicit_and_never_treated_as_empty_history(self):
        await self.job(2)
        await self.job(3)
        with patch("app.services.smart_reminder_policy_context.MAX_POLICY_ROWS", 1):
            snapshot=await self.load()
        self.assertFalse(snapshot.ledger_complete)
        self.assertEqual(evaluate_cadence(snapshot, calibration=QA).reason, "cadence_ledger_incomplete")

    async def test_block_deletion_and_off_guard_precede_cadence(self):
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1).values(master_enabled=False))
        self.assertEqual(evaluate_cadence(await self.load()).reason, "master_off")
        await self._deletion()
        with self.assertRaises(SmartReminderError) as exc: await self.load()
        self.assertEqual(exc.exception.code, "smart_account_deletion_pending")


class SQLiteCadenceReaderTests(CadenceReaderChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.PG_URL, "Disposable loopback PostgreSQL not configured")
class PostgreSQLCadenceReaderTests(CadenceReaderChecks, unittest.IsolatedAsyncioTestCase):
    postgres=True
