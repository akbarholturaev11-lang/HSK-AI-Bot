"""Synthetic reviewed cohorts/learning feed; real SQL, fake Telegram only."""
import asyncio
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import event, func, insert, inspect, select, update

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.android_push import AndroidPushToken
from app.db.models.smart_reminder import SmartReminderRouting, SmartReminderPreference, SmartReminderCapability
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_reminder_service import CourseReminderService
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError, SmartReminderPatch, SmartReminderPreferencesService
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from app.services.android_push_service import AndroidPushService
from app.services.smart_reminder_telegram import (
    LearningCoverage, RoutingReview, SmartReminderRoutingService, SmartReminderTelegramService,
)
from tests import test_smart_reminder_policy as fixtures
from tests.test_smart_reminder_cadence import QA


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("routing_0135", ROOT/"alembic/versions/0135_smart_reminder_routing.py")
MIGRATION = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MIGRATION)
UTC = timezone.utc


class DisabledAndReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_reviewed_initializer_defers_routing_to_0135(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from scripts import qa_standalone_bootstrap as qa
        self.assertEqual(ScriptDirectory.from_config(Config(str(ROOT/"alembic.ini"))).get_heads(),[qa.EXPECTED_HEAD])
        self.assertEqual(qa.EXPECTED_HEAD,MIGRATION.revision)
        self.assertIn("smart_reminder_routing",qa.MIGRATION_CREATED_TABLES)
        self.assertNotIn("smart_reminder_routing",{t.name for t in qa._initial_schema_tables(qa._registered_model_metadata())})

    async def test_default_off_and_missing_calibration_or_coverage_are_zero_sql_and_io(self):
        factory=Mock(side_effect=AssertionError("disabled SQL")); sender=AsyncMock()
        for settings,calibration,coverage,expected in (
            (SimpleNamespace(),None,None,"telegram_dispatch_disabled"),
            (SimpleNamespace(SMART_REMINDER_TELEGRAM_ENABLED=1),QA,AsyncMock(),"telegram_dispatch_disabled"),
            (SimpleNamespace(SMART_REMINDER_TELEGRAM_ENABLED=True),None,None,"cadence_calibration_unconfigured"),
            (SimpleNamespace(SMART_REMINDER_TELEGRAM_ENABLED=True),QA,None,"learning_coverage_unavailable"),
        ):
            service=SmartReminderTelegramService(settings,factory,calibration=calibration,coverage_reader=coverage)
            self.assertEqual((await service.prepare(None,expires_at=None,history_since=None,expected_level="hsk1")).reason,expected)
            self.assertEqual((await service.claim(None,None,history_since=None,lease_for=None)).reason,expected)
            self.assertEqual((await service.dispatch(None,None,sender,history_since=None)).reason,expected)
        factory.assert_not_called();sender.assert_not_called()
        from app.config import Settings
        self.assertFalse(Settings.model_fields["SMART_REMINDER_TELEGRAM_ENABLED"].default)

    async def test_review_flags_are_explicit_and_typed_not_inventory_inferences(self):
        now=datetime.now(UTC)
        values=dict(user_id=1,generation=1,verified_at=now,verified_until=now+timedelta(hours=1),
                    evidence_sha256="a"*64,legacy_quiesced=True,legacy_outcomes_reconciled=True,other_study_fenced=True)
        for changes in ({"legacy_quiesced":False},{"legacy_outcomes_reconciled":False},{"other_study_fenced":1},{"user_id":True},
                        {"generation":0},{"version":True},{"evidence_sha256":"unknown"},
                        {"verified_until":now}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): RoutingReview(**(values|changes))


class TelegramChecks:
    postgres=False
    asyncTearDown=fixtures.PolicyContextChecks.asyncTearDown
    _progress=fixtures.PolicyContextChecks._progress
    _deletion=fixtures.PolicyContextChecks._deletion
    study=fixtures.PolicyContextChecks.study

    async def asyncSetUp(self):
        await fixtures.PolicyContextChecks.asyncSetUp(self)
        self.tick=self.moment
        self.since=self.tick-timedelta(days=30)  # Explicit QA read window, not policy.
        self.expiry=self.tick.replace(hour=18)
        self.settings=SimpleNamespace(SMART_REMINDER_TELEGRAM_ENABLED=True)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(
                status="active",payment_status="approved",end_date=self.now+timedelta(days=2)))
        for n in range(1,5): await self.study(order=n,days_ago=5-n,xp=1)
        self.routing=SmartReminderRoutingService(self.sessions,clock=lambda:self.tick)
        async def complete_fixture_feed(session,actor,since,now):
            # Every learning write in this synthetic fixture is known. This is
            # explicitly NOT the incomplete legacy/production outcome reader.
            return LearningCoverage(actor.user_id,since,now,"synthetic-complete-fixture-v1")
        self.service=SmartReminderTelegramService(self.settings,self.sessions,calibration=QA,
            coverage_reader=complete_fixture_feed,clock=lambda:self.tick)
        self.bot=AsyncMock();self.bot.send_message.return_value=SimpleNamespace(message_id=77)

    def review(self,generation=1,**changes):
        values=dict(user_id=1,generation=generation,verified_at=self.tick,verified_until=self.expiry,
            evidence_sha256="a"*64,legacy_quiesced=True,legacy_outcomes_reconciled=True,other_study_fenced=True)
        return RoutingReview(**(values|changes))

    async def active(self):
        generation=await self.routing.hold(self.actor,expected_generation=0)
        await self.routing.activate(self.actor,self.review(generation))
        return generation

    async def prepare(self,**changes):
        return await self.service.prepare(self.actor,**(dict(expires_at=self.expiry,
            history_since=self.since,expected_level="hsk1")|changes))

    async def claim(self,job_id,**changes):
        return await self.service.claim(self.actor,job_id,**(dict(history_since=self.since,
            lease_for=timedelta(seconds=30))|changes))

    async def send(self,envelope):
        # Acquiring User from another transaction proves the provider callback
        # runs after the authorization transaction committed/released locks.
        async with self.sessions.begin() as s:
            await s.execute(select(User.id).where(User.id==envelope.user_id).with_for_update())
            self.assertEqual(await s.scalar(select(ATTEMPT.c.state).where(
                ATTEMPT.c.job_id==envelope.job_id)),"in_flight")
        return await self.bot.send_message(chat_id=envelope.telegram_id,text="Synthetic authorized study")

    async def dispatch(self,lease,send=None):
        return await self.service.dispatch(self.actor,lease,send or self.send,history_since=self.since)

    async def rows(self,table):
        async with self.sessions() as s: return (await s.execute(select(table))).mappings().all()

    async def off(self):
        async with self.sessions.begin() as s:
            await SmartReminderPreferencesService(s).patch(self.actor,SmartReminderPatch(
                request_id=str(uuid4()),expected_revision=2,master_enabled=False))

    async def test_hold_is_sticky_for_both_server_study_paths_but_changes_no_consent(self):
        before=await self.rows(SmartReminderPreference.__table__)
        self.assertEqual(await self.routing.hold(self.actor,expected_generation=0),1)
        async with self.sessions.begin() as s:
            self.assertFalse(await SmartReminderLifecycleService(s).legacy_veto(1,"telegram"))
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_send_veto(1,"telegram"))
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_send_veto(1,"android",device_id="absent"))
        self.assertEqual(await self.rows(SmartReminderPreference.__table__),before)
        self.assertEqual(await self.rows(JOB),[]);self.assertEqual(await self.rows(ATTEMPT),[])
        with self.assertRaisesRegex(SmartReminderError,"routing_generation_conflict"):
            await self.routing.hold(self.actor,expected_generation=0)

    async def test_review_must_follow_hold_and_bind_current_account_generation_and_revision(self):
        await self.routing.hold(self.actor,expected_generation=0)
        for review in (self.review(user_id=2),self.review(generation=2),
                       self.review(verified_at=self.tick-timedelta(seconds=1)),
                       self.review(verified_at=self.tick+timedelta(seconds=1)),
                       self.review(verified_at=self.tick-timedelta(seconds=2),verified_until=self.tick)):
            with self.subTest(review=review), self.assertRaisesRegex(SmartReminderError,"routing_review_stale"):
                await self.routing.activate(self.actor,review)
        await self.off()
        with self.assertRaisesRegex(SmartReminderError,"routing_review_stale"):
            await self.routing.activate(self.actor,self.review())

    async def test_admission_cannot_invent_native_only_telegram_or_relink_transport(self):
        with self.assertRaises(SmartReminderError):
            await self.routing.hold(SmartReminderActor(2,"telegram",telegram_id=3001),expected_generation=0)
        with self.assertRaises(SmartReminderError):
            await self.routing.hold(SmartReminderActor(2,"android"),expected_generation=0)
        await self.routing.hold(self.actor,expected_generation=0)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(telegram_id=3999))
        with self.assertRaisesRegex(SmartReminderError,"routing_review_stale"):
            await self.routing.activate(replace(self.actor,telegram_id=3999),self.review())

    async def test_existing_legacy_sender_skips_owned_accounts_and_keeps_other_categories(self):
        await self.active();self.tick=self.tick.replace(hour=14)
        async with self.sessions() as s:
            with patch("app.services.course_reminder_service.datetime",wraps=datetime) as clock:
                clock.now.return_value=self.tick
                with patch.object(CourseReminderService,"_build_reminder_text",AsyncMock(return_value=("Synthetic",{}))):
                    await CourseReminderService(s).send_due_reminders(self.bot)
        self.bot.send_message.assert_not_awaited()

    async def test_current_time_intent_is_preserved_while_legacy_delivery_stays_owned(self):
        from app.bot.handlers.course import course_set_reminder_time_handler
        from app.bot.utils.smart_reminder import INTERACTION_KEY, smart_reminder_time_keyboard
        from tests.test_smart_reminder_preferences import State
        await self.active();state=State()
        async with self.sessions() as s:
            await smart_reminder_time_keyboard(s,state,1,"uz")
        nonce=state.data[INTERACTION_KEY]["nonce"]
        callback=SimpleNamespace(from_user=SimpleNamespace(id=3001),answer=AsyncMock(),message=SimpleNamespace(),
            data="course:reminder_time:15:00:"+nonce)
        with patch("app.bot.handlers.course.edit_callback_workflow_message",new=AsyncMock()):
            async with self.sessions() as s:
                await course_set_reminder_time_handler(callback,state,s)
        async with self.sessions.begin() as s:
            self.assertEqual(await s.scalar(select(CourseProgress.reminder_time).where(CourseProgress.user_id==1)),time(15))
            self.assertTrue(await s.scalar(select(CourseProgress.reminder_enabled).where(CourseProgress.user_id==1)))
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_send_veto(1,"telegram"))

    async def test_new_android_inventory_after_review_invalidates_pending_authority(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id="new-unknown-android",user_id=1,platform="android",app_version="qa",
                installation_key_hash="new-android-fixture"))
        with self.assertRaisesRegex(SmartReminderError,"telegram_cohort_unavailable"):
            await self.dispatch(lease)
        self.bot.send_message.assert_not_awaited()
        async with self.sessions.begin() as s:
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_send_veto(1,"telegram"))

    async def test_present_android_without_fresh_fencing_cannot_enter_telegram_cohort(self):
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id="unknown-android",user_id=1,platform="android",app_version="qa",
                installation_key_hash="unknown-android-fixture"))
        await self.routing.hold(self.actor,expected_generation=0)
        with self.assertRaisesRegex(SmartReminderError,"routing_review_stale"):
            await self.routing.activate(self.actor,self.review())

    async def fenced_phone(self,until=None):
        async with self.sessions.begin() as s:
            s.add(DesktopDevice(id="fenced-phone",user_id=1,platform="android",app_version="qa",
                installation_key_hash="fenced-android-fixture"))
            await s.flush()
            s.add(DesktopSession(id="fenced-phone-session",device_id="fenced-phone",
                refresh_token_hash="synthetic-fenced-session",expires_at=self.now+timedelta(days=1)))
            s.add(SmartReminderCapability(user_id=1,device_id="fenced-phone",protocol_version=1,generation=1,
                autonomous_study_disabled=True,observed_at=self.tick-timedelta(minutes=1),expires_at=until or self.expiry))
            s.add(AndroidPushToken(device_id="fenced-phone",token="synthetic-never-real-fcm",
                study_reminders_enabled=False,notifications_allowed=True,timezone_name="Etc/UTC"))

    async def test_proof_validity_cannot_outlive_present_android_fencing(self):
        until=self.tick+timedelta(hours=3)
        await self.fenced_phone(until)
        await self.routing.hold(self.actor,expected_generation=0)
        with self.assertRaisesRegex(SmartReminderError,"routing_review_stale"):
            await self.routing.activate(self.actor,self.review())
        await self.routing.activate(self.actor,self.review(verified_until=until))

    async def test_study_mirror_intent_is_not_rewritten_and_account_notices_do_not_change_cohort(self):
        await self.fenced_phone();await self.active()
        async def preferences(enabled):
            async with self.sessions() as s:
                await AndroidPushService(s,self.settings).update_preferences(device=await s.get(DesktopDevice,"fenced-phone"),
                    study_reminders_enabled=enabled,timezone_name="Etc/UTC",notifications_allowed=False)
        await preferences(False)
        planned=await self.prepare()
        self.assertEqual(planned.reason,"telegram_planned")
        await preferences(True)
        async with self.sessions() as s:
            phone=await s.get(AndroidPushToken,"fenced-phone")
            self.assertTrue(phone.study_reminders_enabled)
            self.assertFalse(phone.notifications_allowed)
        self.tick=self.tick.replace(hour=14)
        with self.assertRaisesRegex(SmartReminderError,"telegram_cohort_unavailable"):
            await self.claim(planned.job_id)
        self.bot.send_message.assert_not_awaited()

    async def test_weekly_report_remains_independent_for_owned_cohort(self):
        self.tick=(self.tick-timedelta(days=self.tick.weekday())).replace(hour=9)
        self.expiry=self.tick.replace(hour=18)
        await self.active()
        async with self.sessions() as s:
            with patch("app.services.course_reminder_service.datetime",wraps=datetime) as clock:
                clock.now.return_value=self.tick
                with patch("app.services.course_reminder_service.CourseProgressSummaryService") as summaries:
                    summaries.return_value.summarize_completed_range=AsyncMock(return_value={"lessons":4,"vocab":3,"dialogues":1})
                    await CourseReminderService(s).send_weekly_progress_reports(self.bot)
        self.assertEqual(self.bot.send_message.await_count,1)
        self.assertEqual(await self.rows(JOB),[])

    async def test_known_legacy_send_before_cutover_still_owns_its_day(self):
        self.tick=self.tick.replace(hour=14)
        async with self.sessions.begin() as s:
            await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(last_reminder_sent_at=self.tick))
        await self.active()
        self.assertEqual((await self.prepare()).reason,"legacy_study_already_attempted")
        self.assertEqual(await self.rows(ATTEMPT),[])
        self.bot.send_message.assert_not_awaited()

    async def test_d1_both_existing_arms_suppress_before_creating_an_intent(self):
        await self.active()
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1,event_name="d1_recovery_assigned",source="d1_recovery_v1",
                payload_json='{"arm":"control"}',created_at=self.tick))
        for arm in ("control","treatment"):
            async with self.sessions.begin() as s:
                await s.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.event_name=="d1_recovery_assigned").values(
                    payload_json='{"arm":"'+arm+'"}'))
            self.assertEqual((await self.prepare()).reason,"d1_holdout_active")
        self.assertEqual(await self.rows(JOB),[])

    async def test_one_committed_telegram_attempt_accepts_provider_not_display(self):
        await self.active();planned=await self.prepare()
        self.assertEqual(planned.reason,"telegram_planned")
        self.assertEqual((await self.prepare()).job_id,planned.job_id)
        self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        self.assertEqual(lease.reason,"telegram_claimed")
        result=await self.dispatch(lease)
        self.assertEqual(result.reason,"telegram_provider_accepted")
        self.assertEqual((await self.rows(JOB))[0]["selected_channel"],"telegram")
        attempts=await self.rows(ATTEMPT);self.assertEqual(len(attempts),1)
        self.assertEqual(attempts[0]["state"],"provider_accepted")
        self.assertIsNone(attempts[0]["device_id"])
        self.assertEqual((await self.dispatch(lease)).reason,"telegram_lease_lost")
        self.assertEqual((await self.claim(planned.job_id)).reason,"telegram_attempt_not_replayable")
        self.assertEqual(self.bot.send_message.await_count,1)

    async def test_prepared_lease_recovers_but_old_token_and_new_policy_cannot_send(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        first=await self.claim(planned.job_id)
        self.tick+=timedelta(seconds=31)
        second=await self.claim(planned.job_id)
        self.assertNotEqual(first.token,second.token)
        self.assertEqual((await self.dispatch(first)).reason,"telegram_lease_lost")
        self.assertEqual(len(await self.rows(ATTEMPT)),1)
        self.assertEqual((await self.dispatch(second)).reason,"telegram_provider_accepted")
        changed=SmartReminderTelegramService(self.settings,self.sessions,calibration=replace(QA,version="other-qa"),
            coverage_reader=self.service.coverage_reader,clock=lambda:self.tick)
        self.assertEqual((await changed.claim(self.actor,planned.job_id,history_since=self.since,
            lease_for=timedelta(seconds=30))).reason,"foreign_job_policy")

    async def test_off_after_claim_and_stale_bot_time_never_revive_old_job(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id);nonce=uuid4().hex
        binding=dict(user_id=1,revision=2,nonce=nonce)
        await self.off()
        async with self.sessions.begin() as s:
            with self.assertRaisesRegex(SmartReminderError,"smart_master_off"):
                await SmartReminderPreferencesService(s).bot_time(self.actor,nonce=nonce,binding=binding,selected=time(15))
        with self.assertRaises(SmartReminderError): await self.dispatch(lease)
        self.assertEqual((await self.rows(JOB))[0]["state"],"cancelled")
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"],"cancelled")
        self.bot.send_message.assert_not_awaited()

    async def test_hold_after_claim_removes_grant_and_new_generation_cannot_reuse_lease(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        generation=await self.routing.hold(self.actor,expected_generation=1)
        await self.routing.activate(self.actor,self.review(generation))
        self.assertEqual((await self.dispatch(lease)).reason,"telegram_lease_lost")
        self.assertEqual((await self.prepare()).job_id,planned.job_id)
        self.bot.send_message.assert_not_awaited()

    async def test_d1_assignment_after_claim_cancels_prepared_attempt(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        async with self.sessions.begin() as s:
            s.add(CourseMiniAppEvent(user_id=1,event_name="d1_recovery_assigned",source="d1_recovery_v1",
                payload_json='{"arm":"control"}',created_at=self.tick))
        self.assertEqual((await self.dispatch(lease)).reason,"d1_holdout_active")
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"],"cancelled")
        self.bot.send_message.assert_not_awaited()

    async def test_new_learning_after_claim_wins_and_no_second_day_identity_is_created(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        # The existing server receipt/XP/progress shape, within the current day.
        self.moment=self.tick
        await self.study(order=5,xp=20)
        self.assertEqual((await self.dispatch(lease)).reason,"goal_completed")
        self.assertEqual(len(await self.rows(JOB)),1)
        self.bot.send_message.assert_not_awaited()

    async def test_expired_job_and_expired_review_never_restore_legacy(self):
        await self.active();planned=await self.prepare(expires_at=self.tick.replace(hour=16))
        self.tick=self.tick.replace(hour=17)
        self.assertEqual((await self.claim(planned.job_id)).reason,"telegram_expired")
        self.tick=self.expiry
        with self.assertRaisesRegex(SmartReminderError,"telegram_cohort_unavailable"):
            await self.claim(planned.job_id)
        async with self.sessions.begin() as s:
            self.assertTrue(await SmartReminderLifecycleService(s).legacy_send_veto(1,"telegram"))

    async def test_bot_block_and_deletion_win_over_existing_cohort(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(bot_blocked_at=self.now))
        with self.assertRaises(SmartReminderError): await self.claim(planned.job_id)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(bot_blocked_at=None))
        await self._deletion()
        with self.assertRaisesRegex(SmartReminderError,"smart_account_deletion_pending"):
            await self.claim(planned.job_id)
        self.bot.send_message.assert_not_awaited()

    async def test_provider_error_or_crash_never_replays_an_externalized_attempt(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        async def fail(envelope):
            await self.send(envelope)
            raise RuntimeError("synthetic uncertain transport return")
        self.assertEqual((await self.dispatch(lease,fail)).reason,"telegram_unknown")
        self.tick+=timedelta(minutes=1)
        self.assertEqual((await self.claim(planned.job_id)).reason,"telegram_attempt_not_replayable")
        self.assertEqual(self.bot.send_message.await_count,1)

    async def test_acceptance_update_rollback_preserves_inflight_and_no_second_provider_call(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        def fail(c,cursor,sql,parameters,ctx,many):
            if sql.startswith("UPDATE smart_reminder_attempts") and "provider_accepted" in parameters:
                raise RuntimeError("synthetic acceptance persistence failure")
        event.listen(self.engine.sync_engine,"after_cursor_execute",fail)
        try:
            with self.assertRaisesRegex(RuntimeError,"synthetic acceptance"):
                await self.dispatch(lease)
        finally: event.remove(self.engine.sync_engine,"after_cursor_execute",fail)
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"],"in_flight")
        self.assertEqual((await self.dispatch(lease)).reason,"telegram_attempt_not_replayable")
        self.assertEqual(self.bot.send_message.await_count,1)

    async def test_start_update_rollback_returns_no_transport_authority(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        def fail(c,cursor,sql,parameters,ctx,many):
            if sql.startswith("UPDATE smart_reminder_attempts") and "in_flight" in parameters:
                raise RuntimeError("synthetic start persistence failure")
        event.listen(self.engine.sync_engine,"after_cursor_execute",fail)
        try:
            with self.assertRaisesRegex(RuntimeError,"synthetic start"):
                await self.dispatch(lease)
        finally: event.remove(self.engine.sync_engine,"after_cursor_execute",fail)
        self.bot.send_message.assert_not_awaited()
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"],"prepared")
        self.assertEqual((await self.dispatch(lease)).reason,"telegram_provider_accepted")

    async def test_off_during_already_authorized_io_records_acceptance_without_new_permission(self):
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        async def send_then_off(envelope):
            result=await self.send(envelope)
            await self.off()
            return result
        self.assertEqual((await self.dispatch(lease,send_then_off)).reason,"telegram_provider_accepted")
        self.assertFalse((await self.rows(SmartReminderPreference.__table__))[0]["master_enabled"])
        self.assertEqual((await self.rows(ATTEMPT))[0]["state"],"provider_accepted")
        self.assertEqual(self.bot.send_message.await_count,1)

    async def test_missing_or_wrong_owner_authoritative_coverage_cannot_be_fabricated_from_legacy(self):
        await self.active()
        self.service.coverage_reader=AsyncMock(return_value=None)
        self.assertEqual((await self.prepare()).reason,"learning_coverage_unknown")
        self.assertEqual(await self.rows(ATTEMPT),[])

    async def test_wrong_owner_authoritative_feed_is_not_accepted(self):
        await self.active()
        self.service.coverage_reader=AsyncMock(return_value=LearningCoverage(2,self.since,self.tick,"other-owner-fixture"))
        with self.assertRaisesRegex(SmartReminderError,"learning_coverage_invalid"):
            await self.prepare()
        self.assertEqual(await self.rows(ATTEMPT),[])

    async def test_real_routing_migration_empty_roundtrip_populated_refusal_and_owner_purge(self):
        def migrate(sync,direction):
            with Operations.context(MigrationContext.configure(sync)): getattr(MIGRATION,direction)()
        async with self.engine.begin() as c:
            await c.run_sync(lambda s:SmartReminderRouting.__table__.drop(s))
            await c.run_sync(migrate,"upgrade")
            cols=await c.run_sync(lambda s:{v['name'] for v in inspect(s).get_columns(SmartReminderRouting.__tablename__)})
            self.assertEqual(cols,set(SmartReminderRouting.__table__.columns.keys()))
            await c.run_sync(migrate,"downgrade")
            await c.run_sync(migrate,"upgrade")
        await self.active()
        async with self.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError,"Retain routing ownership"):
                await c.run_sync(migrate,"downgrade")
        async with self.sessions.begin() as s:
            row=dict((await self.rows(SmartReminderRouting.__table__))[0]);row['user_id']=2
            await s.execute(insert(SmartReminderRouting.__table__).values(**row))
            self.assertTrue(await UserRepository(s).delete_by_user_id(1))
        self.assertEqual([r['user_id'] for r in await self.rows(SmartReminderRouting.__table__)],[2])

    async def test_postgres_two_schedulers_and_legacy_yield_one_telegram_provider_call(self):
        if not self.postgres: self.skipTest("PostgreSQL User row-lock race")
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        entered=asyncio.Event();release=asyncio.Event()
        async def slow_send(envelope):
            async with self.sessions.begin() as s:
                await s.execute(select(User.id).where(User.id==1).with_for_update())
                self.assertEqual(await s.scalar(select(ATTEMPT.c.state).where(ATTEMPT.c.job_id==planned.job_id)),"in_flight")
            entered.set();await release.wait()
            return await self.send(envelope)
        async def worker():
            lease=await self.claim(planned.job_id)
            return await self.dispatch(lease,slow_send) if lease.reason=="telegram_claimed" else lease
        tasks=[asyncio.create_task(worker()) for _ in range(2)]
        try:
            await asyncio.wait_for(entered.wait(),10)
            async with self.sessions() as s:
                with patch("app.services.course_reminder_service.datetime",wraps=datetime) as clock:
                    clock.now.return_value=self.tick
                    with patch.object(CourseReminderService,"_build_reminder_text",AsyncMock(return_value=("Synthetic",{}))):
                        await CourseReminderService(s).send_due_reminders(self.bot)
            release.set();results=await asyncio.wait_for(asyncio.gather(*tasks),10)
            self.assertEqual(sum(r.reason=="telegram_provider_accepted" for r in results),1)
            self.assertEqual(self.bot.send_message.await_count,1)
            self.assertEqual(len(await self.rows(ATTEMPT)),1)
        finally:
            release.set()
            for task in tasks:
                if not task.done(): task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)

    async def waiting_dispatch(self,change):
        if not self.postgres: self.skipTest("PostgreSQL waiting User-lock boundary")
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id,lease_for=timedelta(minutes=5))
        entered=asyncio.Event()
        def capture(c,cursor,sql,parameters,ctx,many):
            if sql.startswith("SELECT users.id") and "FOR UPDATE" in sql: entered.set()
        async with self.sessions.begin() as holder:
            await holder.execute(select(User.id).where(User.id==1).with_for_update())
            event.listen(self.engine.sync_engine,"before_cursor_execute",capture)
            task=asyncio.create_task(self.dispatch(lease))
            try:
                await asyncio.wait_for(entered.wait(),5);await asyncio.sleep(0.03)
                self.assertFalse(task.done())
                if change=="off":
                    await SmartReminderPreferencesService(holder).patch(self.actor,SmartReminderPatch(
                        request_id=str(uuid4()),expected_revision=2,master_enabled=False))
                else:
                    self.tick+=timedelta(minutes=1)
                    await holder.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(completed_lessons_count=5))
                    holder.add(CourseXpEvent(user_id=1,activity_type="lesson",activity_ref="v3-part:hsk1:5:complete",xp=20,
                        activity_date=self.tick.date(),week_start=self.tick.date(),created_at=self.tick))
                    holder.add(CourseMiniAppEvent(user_id=1,level="hsk1",event_name="lesson_completed",lesson_order=5,
                        source="android_course",created_at=self.tick))
                await holder.commit()
                if change=="off":
                    with self.assertRaises(SmartReminderError): await asyncio.wait_for(task,10)
                else:
                    self.assertEqual((await asyncio.wait_for(task,10)).reason,"goal_completed")
                self.bot.send_message.assert_not_awaited()
            finally:
                event.remove(self.engine.sync_engine,"before_cursor_execute",capture)
                if not task.done(): task.cancel()
                await asyncio.gather(task,return_exceptions=True)

    async def test_postgres_off_commit_wins_over_waiting_dispatch(self):
        await self.waiting_dispatch("off")

    async def test_postgres_learning_commit_and_postlock_clock_win_over_waiting_dispatch(self):
        await self.waiting_dispatch("learning")

    async def test_postgres_hold_queued_first_wins_over_waiting_dispatch(self):
        if not self.postgres: self.skipTest("PostgreSQL routing hold/waiting dispatcher")
        await self.active();planned=await self.prepare();self.tick=self.tick.replace(hour=14)
        lease=await self.claim(planned.job_id)
        first=asyncio.Event();second=asyncio.Event();seen=[]
        def capture(c,cursor,sql,parameters,ctx,many):
            if sql.startswith("SELECT users.id") and "FOR UPDATE" in sql:
                seen.append(True)
                (first if len(seen)==1 else second).set()
        tasks=[]
        async with self.sessions.begin() as holder:
            await holder.execute(select(User.id).where(User.id==1).with_for_update())
            event.listen(self.engine.sync_engine,"before_cursor_execute",capture)
            try:
                hold=asyncio.create_task(self.routing.hold(self.actor,expected_generation=1));tasks.append(hold)
                await asyncio.wait_for(first.wait(),5);await asyncio.sleep(0.03)
                dispatch=asyncio.create_task(self.dispatch(lease));tasks.append(dispatch)
                await asyncio.wait_for(second.wait(),5);await asyncio.sleep(0.03)
                self.assertFalse(hold.done());self.assertFalse(dispatch.done())
                await holder.commit()
                self.assertEqual(await asyncio.wait_for(hold,10),2)
                with self.assertRaisesRegex(SmartReminderError,"telegram_cohort_unavailable"):
                    await asyncio.wait_for(dispatch,10)
                self.bot.send_message.assert_not_awaited()
            finally:
                event.remove(self.engine.sync_engine,"before_cursor_execute",capture)
                for task in tasks:
                    if not task.done(): task.cancel()
                await asyncio.gather(*tasks,return_exceptions=True)


class SQLiteTelegramTests(TelegramChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.fixtures.PG_URL,"Disposable loopback PostgreSQL not configured")
class PostgreSQLTelegramTests(TelegramChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
