"""Committed shadow reasons are observations, never real delivery metrics."""
import asyncio
from dataclasses import replace
from datetime import timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import insert, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.motivation_reminder_service import D1_RECOVERY_ASSIGNED_EVENT, D1_RECOVERY_EXPERIMENT
from app.services.smart_reminder_analysis import (
    EVENT, MONTHLY, RAW_RETENTION, SHADOW_CADENCE_REASONS, SHADOW_REFUSAL_REASONS,
    SmartReminderAnalysisObserver,
)
from app.services.smart_reminder_cadence import evaluate_cadence
from app.services.smart_reminder_policy import VerifiedStudy
from tests import test_smart_reminder_analysis as analysis_fixture
from tests import test_smart_reminder_cadence as cadence_fixture
from tests import test_smart_reminder_shadow_queue as queue_fixture


class ShadowAnalysisChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not analysis_fixture.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = queue_fixture.PostgreSQLQueueTests if self.postgres else queue_fixture.SQLiteQueueTests
        self.q = cls(methodName="test_reservation_commits_frozen_shadow_only_and_retry_never_extends_it")
        await self.q.asyncSetUp()
        self.observer = SmartReminderAnalysisObserver(SimpleNamespace(SMART_REMINDER_ANALYSIS_ENABLED=True),
            self.q.sessions, clock=lambda: self.q.tick, timeout=2)

    async def asyncTearDown(self):
        if hasattr(self, "q"):
            await self.q.asyncTearDown()

    async def rows(self, table):
        async with self.q.sessions() as session:
            return (await session.execute(select(table))).mappings().all()

    async def finish(self):
        reserved = await self.q.reserve()
        self.assertEqual(reserved.reason, "shadow_reserved")
        self.q.tick = self.q.tick.replace(hour=14)
        lease = await self.q.claim(reserved.job_id)
        self.assertEqual(lease.reason, "shadow_claimed")
        return await self.q.finish(lease)

    async def observe_reason(self, reason, stage="shadow_suppressed"):
        before = await self.rows(queue_fixture.JOB)
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 1)
        facts = await self.rows(EVENT)
        self.assertEqual([(r["stage"], r["reason_code"], r["channel"]) for r in facts], [(stage, reason, "none")])
        self.assertEqual(facts[0]["occurred_at"], before[0]["updated_at"])
        self.assertEqual(facts[0]["expires_at"] - facts[0]["occurred_at"], RAW_RETENTION)
        self.assertEqual(await self.rows(queue_fixture.JOB), before)
        self.assertEqual(await self.rows(queue_fixture.ATTEMPT), [])
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)

    async def test_real_queue_unconfigured_cadence_has_its_original_suppression_reason(self):
        result = await self.finish()
        self.assertEqual(result.policy_reason, "cadence_calibration_unconfigured")
        await self.observe_reason(result.policy_reason)

    async def test_candidate_is_explicit_shadow_under_qa_only_complete_source_and_calibration(self):
        def calibrated(context, **kwargs):
            # Deliberately synthetic positive coverage; never a production reader.
            now = context.policy.observed_at
            studies = tuple(VerifiedStudy(f"qa-verified-{n}", "lesson", now-timedelta(days=n),
                (now-timedelta(days=n)).date().isoformat(), 20) for n in range(3, 8))
            context = replace(context, policy=replace(context.policy, studies=studies, coverage_limits=()),
                learning_complete_since=context.history_since)
            return evaluate_cadence(context, calibration=cadence_fixture.QA, **kwargs)
        with patch("app.services.smart_reminder_shadow_queue.evaluate_cadence", side_effect=calibrated):
            result = await self.finish()
        self.assertEqual(result.policy_reason, "shadow_candidate")
        await self.observe_reason("shadow_candidate", "shadow_candidate")
        self.assertFalse(result.dispatch_allowed)

    async def test_actual_goal_completion_reason_is_not_a_delivery_or_nonresponse(self):
        await self.q.test_goal_completed_after_old_clock_uses_current_accepted_learning()
        await self.observe_reason("goal_completed")

    async def test_actual_access_loss_is_recorded_without_consuming_access(self):
        await self.q.test_current_lesson_access_is_rechecked_without_consuming()
        await self.observe_reason("target_inaccessible")

    async def test_actual_channel_off_is_not_overridden_by_analysis(self):
        await self.q.test_current_source_off_without_epoch_is_still_a_veto()
        await self.observe_reason("consent_or_permission_unavailable")

    async def test_admin_pause_is_shadow_suppression_without_delivery_or_negative_learning(self):
        from app.services.notification_template_service import KEY_SMART_STUDY, NotificationTemplateService
        reserved=await self.q.reserve()
        self.q.tick=self.q.tick.replace(hour=14)
        lease=await self.q.claim(reserved.job_id)
        async with self.q.sessions.begin() as session:
            await NotificationTemplateService(session).update_text(KEY_SMART_STUDY,enabled=False,
                text_uz='',text_ru='',text_tj='',updated_by=None)
        self.assertEqual((await self.q.finish(lease)).reason,'admin_study_disabled')
        await self.observe_reason('admin_study_disabled')

    async def test_actual_personal_quiet_is_observed(self):
        await self.q.test_current_quiet_hours_after_claim_suppress()
        await self.observe_reason("personal_quiet")

    async def test_d1_after_claim_records_terminal_holdout_without_delivery(self):
        reserved = await self.q.reserve()
        self.q.tick = self.q.tick.replace(hour=14)
        lease = await self.q.claim(reserved.job_id)
        async with self.q.sessions.begin() as session:
            session.add(CourseMiniAppEvent(user_id=1, event_name=D1_RECOVERY_ASSIGNED_EVENT,
                source=D1_RECOVERY_EXPERIMENT, payload_json=json.dumps({"arm": "control"}), created_at=self.q.tick))
        self.assertEqual((await self.q.finish(lease)).reason, "d1_holdout_active")
        await self.observe_reason("d1_holdout_active")

    async def test_expiry_is_shadow_suppression_and_initial_no_job_refusal_is_unobserved(self):
        await self.q.update_pref(master_enabled=False)
        self.assertEqual((await self.q.reserve()).reason, "master_off")
        self.assertEqual((await self.observer.reconcile_tick())["examined"], 0)
        self.assertEqual(await self.rows(EVENT), [])
        await self.q.update_pref(master_enabled=True)
        await self.q.reserve()
        self.q.tick = self.q.expiry
        await self.q.queue.expire_due(limit=1)
        await self.observe_reason("shadow_expired")

    async def test_pending_selected_attempted_unknown_or_impossible_source_is_refused(self):
        reserved = await self.q.reserve()
        self.assertEqual(await self.observer.service.capture_job(1, reserved.job_id), 0)
        for values in (
            {"state": "completed", "reason_code": "synthetic-private-proof"},
            {"state": "cancelled", "reason_code": "shadow_candidate"},
            {"state": "completed", "reason_code": "shadow_candidate", "selected_channel": "telegram"},
            {"state": "completed", "reason_code": "shadow_candidate", "policy_version": "unreviewed-v2"},
        ):
            async with self.q.sessions.begin() as session:
                await session.execute(update(queue_fixture.JOB).values(**(
                    dict(selected_channel=None, policy_version=queue_fixture.QUEUE_VERSION) | values)))
            self.assertEqual(await self.observer.service.capture_job(1, reserved.job_id), 0)
        async with self.q.sessions.begin() as session:
            await session.execute(update(queue_fixture.JOB).values(policy_version=queue_fixture.QUEUE_VERSION,
                state="completed", reason_code="shadow_candidate"))
            await session.execute(insert(queue_fixture.ATTEMPT).values(id="existing-attempt", job_id=reserved.job_id,
                attempt_key="x" * 64, channel="telegram", state="definite_failure", grant_epoch=1, expires_at=self.q.expiry))
        self.assertEqual(await self.observer.service.capture_job(1, reserved.job_id), 0)
        self.assertEqual(await self.rows(EVENT), [])

    async def test_foreign_pending_deletion_and_future_terminal_sources_are_refused(self):
        result = await self.finish()
        self.assertEqual(await self.observer.service.capture_job(2, result.job_id), 0)
        async with self.q.sessions.begin() as session:
            await session.execute(update(queue_fixture.JOB).values(updated_at=self.q.tick+timedelta(seconds=1)))
        self.assertEqual(await self.observer.service.capture_job(1, result.job_id), 0)
        self.q.tick += timedelta(seconds=1)
        await self.q._deletion()
        self.assertEqual(await self.observer.service.capture_job(1, result.job_id), 0)

    async def test_shadow_retention_preserves_anonymous_facts_and_source(self):
        await self.finish()
        await self.observer.reconcile_tick()
        self.q.tick += RAW_RETENTION
        await self.observer.service.retention(execute=True)
        self.assertEqual((await self.observer.reconcile_tick())["inserted_facts"], 0)
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)
        self.assertEqual(len(await self.rows(queue_fixture.JOB)), 1)

    async def test_real_account_purge_removes_unexpired_shadow_detail(self):
        await self.finish()
        await self.observer.reconcile_tick()
        self.assertEqual(len(await self.rows(EVENT)), 1)
        async with self.q.sessions.begin() as session:
            self.assertTrue(await UserRepository(session)._delete_account(await session.get(User, 1)))
        self.assertEqual(await self.rows(EVENT), [])
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)

    async def test_populated_shadow_detail_or_monthly_refuses_downgrade(self):
        await self.finish()
        await self.observer.reconcile_tick()
        def downgrade(connection):
            with Operations.context(MigrationContext.configure(connection)):
                analysis_fixture.shadow_migration.downgrade()
        for retained in ("raw", "anonymous_only"):
            if retained == "anonymous_only":
                self.q.tick += RAW_RETENTION
                await self.observer.service.retention(execute=True)
            with self.assertRaisesRegex(RuntimeError, "Refusing populated shadow"):
                async with self.q.engine.begin() as connection:
                    await connection.run_sync(downgrade)

    async def test_postgres_racing_reconciliation_counts_terminal_shadow_once(self):
        if not self.postgres:
            self.skipTest("PostgreSQL independent shadow capture transactions")
        await self.finish()
        other = SmartReminderAnalysisObserver(self.observer.settings, self.q.sessions, clock=lambda: self.q.tick)
        results = await asyncio.gather(self.observer.reconcile_tick(), other.reconcile_tick())
        self.assertEqual(sum(r["inserted_facts"] for r in results), 1)
        self.assertEqual(sum(r["fact_count"] for r in await self.rows(MONTHLY)), 1)


class SQLiteShadowAnalysisTests(ShadowAnalysisChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLShadowAnalysisTests(ShadowAnalysisChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
