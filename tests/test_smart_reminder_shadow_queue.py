"""Real SQL durable shadow ownership/races; synthetic IO, never real providers."""
import asyncio
from datetime import datetime, time, timedelta, timezone
import unittest
from uuid import uuid4

from sqlalchemy import event, func, insert, select, update
from sqlalchemy.orm import Session

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderConsent, SmartReminderCapability, SmartReminderPreference
from app.db.models.user import User
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError, SmartReminderPatch, SmartReminderPreferencesService
from app.services.smart_reminder_shadow_queue import JOB, ATTEMPT, QUEUE_VERSION, SmartReminderShadowQueue, day_window
from tests import test_smart_reminder_policy as fixtures


UTC = timezone.utc


class DayWindowTests(unittest.TestCase):
    def test_dst_days_and_fractional_offsets_are_real_iana_windows(self):
        cases = (("America/New_York", "2026-03-08", 23), ("America/New_York", "2026-11-01", 25),
                 ("Australia/Lord_Howe", "2026-10-04", 23.5), ("Asia/Kathmandu", "2026-10-29", 24))
        for zone, day, hours in cases:
            with self.subTest(zone=zone, day=day):
                start, end = day_window(zone, day)
                self.assertEqual((end-start).total_seconds(), hours*3600)
        self.assertEqual(day_window("Asia/Kathmandu", "2026-10-29")[0].hour, 18)
        self.assertEqual(day_window("Asia/Kathmandu", "2026-10-29")[0].minute, 15)

    def test_skipped_date_refuses_and_date_line_day_labels_can_overlap(self):
        with self.assertRaises(ValueError): day_window("Pacific/Apia", "2011-12-30")
        self.assertEqual(day_window("Pacific/Honolulu", "2026-10-29"),
                         day_window("Pacific/Kiritimati", "2026-10-30"))


class QueueChecks:
    postgres = False
    asyncTearDown = fixtures.PolicyContextChecks.asyncTearDown
    _progress = fixtures.PolicyContextChecks._progress
    _deletion = fixtures.PolicyContextChecks._deletion

    async def asyncSetUp(self):
        await fixtures.PolicyContextChecks.asyncSetUp(self)
        self.tick = self.moment
        self.since = self.tick-timedelta(days=30)  # QA window, not product policy.
        self.expiry = self.tick.replace(hour=18)
        self.queue = SmartReminderShadowQueue(self.sessions, clock=lambda: self.tick)

    async def reserve(self, actor=None, **changes):
        return await self.queue.reserve(actor or self.actor, **(dict(history_since=self.since,
            expected_level="hsk1", expires_at=self.expiry) | changes))

    async def claim(self, job_id, actor=None, **changes):
        return await self.queue.claim(actor or self.actor, job_id, **(dict(history_since=self.since,
            lease_for=timedelta(minutes=5)) | changes))

    async def finish(self, result, actor=None):
        return await self.queue.finish(actor or self.actor, result.job_id, result.lease_token, history_since=self.since)

    async def row(self, job_id):
        async with self.sessions() as s:
            return dict((await s.execute(select(JOB).where(JOB.c.id==job_id))).mappings().one())

    async def counts(self):
        async with self.sessions() as s:
            return (await s.scalar(select(func.count()).select_from(JOB)),
                    await s.scalar(select(func.count()).select_from(ATTEMPT)))

    async def update_pref(self, **values):
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id==1).values(**values))

    async def accepted_lesson(self, s):
        await s.execute(insert(CourseXpEvent).values(user_id=1, activity_type="lesson",
            activity_ref="v3-part:hsk1:1:complete", xp=20, activity_date=self.tick.date(),
            week_start=self.tick.date(), created_at=self.tick))
        await s.execute(insert(CourseMiniAppEvent).values(user_id=1, event_name="lesson_completed", source="course_v3",
            level="hsk1", lesson_order=1, created_at=self.tick))
        await s.execute(update(CourseProgress).where(CourseProgress.user_id==1).values(completed_lessons_count=1))

    async def test_reservation_commits_frozen_shadow_only_and_retry_never_extends_it(self):
        first = await self.reserve()
        self.assertEqual(first.reason, "shadow_reserved")
        self.assertFalse(first.dispatch_allowed)
        before = await self.row(first.job_id)
        retry = await self.reserve(expires_at=self.expiry+timedelta(hours=1))
        self.assertEqual((retry.reason,retry.job_id), ("account_day_already_owned",first.job_id))
        self.assertEqual(await self.row(first.job_id), before)
        self.assertEqual((before["state"],before["reason_code"]), ("shadow","cadence_calibration_unconfigured"))
        self.assertEqual(before["policy_version"], QUEUE_VERSION)
        self.assertIsNone(before["selected_channel"])
        self.assertIsNone(before["selected_device_id"])
        self.assertEqual(await self.counts(), (1,0))

    async def test_no_implicit_expiry_or_zone_or_cold_start_time_is_invented(self):
        self.assertEqual((await self.reserve(expires_at=self.tick.replace(hour=14))).reason, "queue_expiry_outside_day")
        self.assertEqual((await self.reserve(expires_at=self.tick+timedelta(days=1))).reason, "queue_expiry_outside_day")
        await self.update_pref(timezone_name=None)
        self.assertEqual((await self.reserve()).reason, "timezone_unknown")
        self.assertEqual(await self.counts(), (0,0))

    async def test_partial_same_day_history_is_refused(self):
        self.assertEqual((await self.reserve(history_since=self.tick-timedelta(hours=1))).reason, "queue_history_incomplete")
        self.assertEqual(await self.counts(), (0,0))

    async def test_future_is_not_due_missed_tick_inside_expiry_remains_processable(self):
        reserved=await self.reserve()
        self.assertEqual(await self.queue.due(limit=5), ())
        self.assertEqual((await self.claim(reserved.job_id)).reason, "shadow_not_due")
        self.tick=self.tick.replace(hour=14, minute=30)
        self.assertEqual([h.job_id for h in await self.queue.due(limit=5)], [reserved.job_id])
        lease=await self.claim(reserved.job_id)
        self.assertEqual(lease.reason, "shadow_claimed")
        finished=await self.finish(lease)
        self.assertEqual((finished.reason,finished.policy_reason), ("shadow_evaluated","cadence_calibration_unconfigured"))
        self.assertEqual(await self.queue.due(limit=5), ())
        self.assertEqual(await self.counts(), (1,0))

    async def test_expired_jobs_are_cleaned_without_a_client_or_lease_recall(self):
        reserved=await self.reserve()
        self.tick=self.expiry
        self.assertEqual(await self.queue.due(limit=5), ())
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(status="blocked"))
        expired=await self.queue.expire_due(limit=5)
        self.assertEqual([r.reason for r in expired], ["shadow_expired"])
        self.assertEqual((await self.row(reserved.job_id))["state"], "expired")

    async def test_lease_restart_rotates_token_and_old_worker_cannot_finish(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        first=await self.claim(reserved.job_id)
        self.assertEqual((await self.claim(reserved.job_id)).reason, "shadow_lease_busy")
        self.tick+=timedelta(minutes=5)
        restarted=SmartReminderShadowQueue(self.sessions, clock=lambda:self.tick)
        second=await restarted.claim(self.actor,reserved.job_id,history_since=self.since,lease_for=timedelta(minutes=5))
        self.assertEqual(second.reason,"shadow_claimed")
        self.assertNotEqual(first.lease_token,second.lease_token)
        self.assertEqual((await self.finish(first)).reason,"shadow_lease_lost")
        self.assertEqual((await self.finish(second)).reason,"shadow_evaluated")

    async def test_lease_is_bounded_by_expiry_and_stale_finish_does_not_reopen(self):
        reserved=await self.reserve(); self.tick=self.expiry-timedelta(minutes=1)
        lease=await self.claim(reserved.job_id)
        self.assertEqual(lease.lease_expires_at,self.expiry)
        self.tick=self.expiry
        self.assertEqual((await self.finish(lease)).reason,"shadow_expired")
        self.assertEqual((await self.finish(lease)).reason,"shadow_lease_lost")
        self.assertEqual(await self.counts(),(1,0))

    async def test_validation_delay_cannot_admit_an_expired_claim(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        readings=iter((self.tick,self.expiry+timedelta(seconds=1)))
        self.queue.clock=lambda:next(readings)
        self.assertEqual((await self.claim(reserved.job_id)).reason,"shadow_expired")
        self.assertIsNone((await self.row(reserved.job_id))["lease_token"])

    async def test_validation_delay_cannot_complete_an_expired_lease(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        readings=iter((self.tick,self.expiry+timedelta(seconds=1)))
        self.queue.clock=lambda:next(readings)
        self.assertEqual((await self.finish(lease)).reason,"shadow_expired")

    async def test_goal_completed_after_old_clock_uses_current_accepted_learning(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        self.tick+=timedelta(minutes=1)
        async with self.sessions.begin() as s: await self.accepted_lesson(s)
        self.tick+=timedelta(minutes=1)
        done=await self.finish(lease)
        self.assertEqual(done.reason,"goal_completed")
        self.assertEqual((await self.row(reserved.job_id))["state"],"cancelled")

    async def test_current_quiet_hours_after_claim_suppress(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        await self.update_pref(quiet_start=time(13),quiet_end=time(15))
        self.assertEqual((await self.finish(lease)).reason,"personal_quiet")
        self.assertEqual((await self.row(reserved.job_id))["state"],"cancelled")

    async def test_course_switch_after_claim_suppresses(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==1).values(level="hsk2"))
        self.assertEqual((await self.finish(lease)).reason,"course_context_changed")

    async def test_changed_zone_or_manual_clock_cannot_move_a_frozen_job(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id); before=await self.row(reserved.job_id)
        await self.update_pref(timezone_name="Asia/Tashkent",time_mode="manual_locked",manual_time_local=time(15))
        self.assertEqual((await self.finish(lease)).reason,"shadow_context_changed")
        after=await self.row(reserved.job_id)
        for key in ("local_day","timezone_name","day_start_utc","day_end_utc","scheduled_at","expires_at"):
            self.assertEqual(after[key],before[key])

    async def test_current_source_off_without_epoch_is_still_a_veto(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        async with self.sessions.begin() as s:
            await s.execute(update(SmartReminderConsent).where(SmartReminderConsent.user_id==1).values(state="off"))
        self.assertEqual((await self.finish(lease)).reason,"consent_or_permission_unavailable")

    async def test_current_lesson_access_is_rechecked_without_consuming(self):
        from app.services.entitlements.limits_config import LimitConfigService
        from app.services.entitlements import actions as A
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        async with self.sessions.begin() as s:
            config=LimitConfigService(s); payload=await config.get_payload()
            payload["plans"]["FREE"][A.LESSON_START]={"limit":0,"window":"daily"}
            await config.save_config(payload)
        self.assertEqual((await self.finish(lease)).reason,"target_inaccessible")

    async def test_revision_epoch_change_and_off_invalidate_the_old_lease(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        async with self.sessions.begin() as s:
            await SmartReminderPreferencesService(s).patch(self.actor, SmartReminderPatch(
                request_id=str(uuid4()),expected_revision=2,master_enabled=False))
        self.assertEqual((await self.finish(lease)).reason,"shadow_lease_lost")
        row=await self.row(reserved.job_id)
        self.assertEqual(row["state"],"cancelled")
        self.assertIsNone(row["lease_token"])
        self.assertEqual(await self.counts(),(1,0))

    async def test_epoch_change_without_lifecycle_cannot_be_ignored(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        await self.update_pref(grant_epoch=5)
        self.assertEqual((await self.finish(lease)).reason,"shadow_preference_changed")

    async def test_observer_runs_only_after_committed_closed_sql_and_is_not_retried(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        live=[0]; calls=[]
        def checkout(*args): live[0]+=1
        def checkin(*args): live[0]-=1
        event.listen(self.engine.sync_engine,"checkout",checkout)
        event.listen(self.engine.sync_engine,"checkin",checkin)
        async def observe(report):
            self.assertEqual(live[0],0)
            self.assertFalse(report.dispatch_allowed)
            self.assertEqual((await self.row(report.job_id))["state"],"completed")
            calls.append(report.job_id)
            raise RuntimeError("synthetic observer crash after receiving committed report")
        try:
            with self.assertRaises(RuntimeError):
                await self.queue.run_one(self.actor,reserved.job_id,history_since=self.since,
                                         lease_for=timedelta(minutes=5),observe=observe)
            replay=await self.queue.run_one(self.actor,reserved.job_id,history_since=self.since,
                                            lease_for=timedelta(minutes=5),observe=observe)
        finally:
            event.remove(self.engine.sync_engine,"checkout",checkout)
            event.remove(self.engine.sync_engine,"checkin",checkin)
        self.assertEqual(replay.reason,"shadow_job_terminal")
        self.assertEqual(calls,[reserved.job_id])

    async def test_claim_commit_failure_rolls_back_before_any_observer(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        def fail_commit(session): raise RuntimeError("synthetic commit failure")
        event.listen(Session,"before_commit",fail_commit)
        try:
            with self.assertRaises(RuntimeError): await self.claim(reserved.job_id)
        finally:
            event.remove(Session,"before_commit",fail_commit)
        self.assertIsNone((await self.row(reserved.job_id))["lease_token"])
        self.assertEqual((await self.claim(reserved.job_id)).reason,"shadow_claimed")

    async def test_reservation_outer_commit_failure_leaves_no_released_savepoint_row(self):
        def fail_commit(session): raise RuntimeError("synthetic reservation commit failure")
        event.listen(Session,"before_commit",fail_commit)
        try:
            with self.assertRaises(RuntimeError): await self.reserve()
        finally:
            event.remove(Session,"before_commit",fail_commit)
        self.assertEqual(await self.counts(),(0,0))
        self.assertEqual((await self.reserve()).reason,"shadow_reserved")

    async def test_accepted_before_commit_crash_preserves_uncertainty_without_second_io(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        attempt_id=str(uuid4())
        # Fault-injection model of future transport protocol, not an enabled
        # provider adapter: persist in-flight BEFORE the synthetic external IO.
        async with self.sessions.begin() as s:
            await s.execute(insert(ATTEMPT).values(id=attempt_id,job_id=reserved.job_id,attempt_key=str(uuid4()),
                channel="telegram",state="in_flight",prepared_at=self.tick,started_at=self.tick,expires_at=self.expiry))
        calls=[]
        async def synthetic_provider():
            calls.append("accepted")
            return "accepted"
        accepted=await synthetic_provider()
        with self.assertRaises(RuntimeError):
            async with self.sessions.begin() as s:
                await s.execute(update(ATTEMPT).where(ATTEMPT.c.id==attempt_id).values(state="provider_accepted"))
                self.assertEqual(accepted,"accepted")
                raise RuntimeError("crash before acceptance commit")
        self.tick+=timedelta(minutes=6)
        recovered=await self.claim(reserved.job_id)
        self.assertEqual(recovered.reason,"external_outcome_preserved")
        self.assertEqual((await self.row(reserved.job_id))["state"],"unknown")
        async with self.sessions() as s:
            self.assertEqual(await s.scalar(select(ATTEMPT.c.state).where(ATTEMPT.c.id==attempt_id)),"in_flight")
        self.assertEqual(await self.queue.due(limit=5),())
        self.assertEqual((await self.finish(lease)).reason,"external_outcome_preserved")
        self.assertEqual(calls,["accepted"])
        self.assertEqual(await self.counts(),(1,1))

    async def test_expiry_never_reclassifies_external_outcomes_as_unsent(self):
        for state in ("in_flight","provider_accepted","client_posted_unverified","unknown"):
            with self.subTest(state=state):
                reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
                async with self.sessions.begin() as s:
                    await s.execute(insert(ATTEMPT).values(id=str(uuid4()),job_id=reserved.job_id,attempt_key=str(uuid4()),
                        channel="telegram",state=state,prepared_at=self.tick,started_at=self.tick,expires_at=self.expiry))
                self.tick=self.expiry
                result=await self.queue.expire_due(limit=10)
                self.assertEqual([r.reason for r in result],["external_outcome_preserved"])
                self.assertEqual((await self.row(reserved.job_id))["state"],"unknown")
                async with self.sessions() as s:
                    self.assertEqual(await s.scalar(select(ATTEMPT.c.state).where(ATTEMPT.c.job_id==reserved.job_id)),state)
                self.tick=(self.tick+timedelta(days=1)).replace(hour=12)
                self.expiry=self.tick.replace(hour=18)

    async def test_unexpected_prepared_attempt_is_cancelled_without_any_io(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        async with self.sessions.begin() as s:
            await s.execute(insert(ATTEMPT).values(id=str(uuid4()),job_id=reserved.job_id,attempt_key=str(uuid4()),
                channel="telegram",state="prepared",prepared_at=self.tick,expires_at=self.expiry))
        self.assertEqual((await self.claim(reserved.job_id)).reason,"shadow_attempt_present")
        async with self.sessions() as s:
            self.assertEqual(await s.scalar(select(ATTEMPT.c.state).where(ATTEMPT.c.job_id==reserved.job_id)),"cancelled")

    async def test_foreign_policy_canonical_owner_and_deletion_are_not_bypassed(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        async with self.sessions.begin() as s:
            await s.execute(update(JOB).where(JOB.c.id==reserved.job_id).values(policy_version="other-policy"))
        before=await self.row(reserved.job_id)
        self.assertEqual((await self.claim(reserved.job_id)).reason,"foreign_job_policy")
        self.assertEqual(await self.row(reserved.job_id),before)
        with self.assertRaises(SmartReminderError):
            await self.claim(reserved.job_id,actor=SmartReminderActor(2,"telegram",telegram_id=3001))
        await self._deletion()
        with self.assertRaises(SmartReminderError): await self.claim(reserved.job_id)

    async def test_date_line_travel_does_not_create_an_overlapping_new_day(self):
        self.tick=datetime(2026,10,29,12,tzinfo=UTC); self.since=self.tick-timedelta(days=30)
        self.expiry=datetime(2026,10,30,4,tzinfo=UTC)
        await self.update_pref(timezone_name="Pacific/Honolulu")
        async with self.sessions.begin() as s:
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id==1).values(timezone_offset_minutes=-600))
        reserved=await self.reserve(); before=await self.row(reserved.job_id)
        await self.update_pref(timezone_name="Pacific/Kiritimati",revision=3)
        async with self.sessions.begin() as s:
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id==1).values(timezone_offset_minutes=840))
        retry=await self.reserve()
        self.assertEqual((retry.reason,retry.job_id),("account_day_already_owned",reserved.job_id))
        self.assertEqual(await self.row(reserved.job_id),before)
        self.assertEqual(await self.counts(),(1,0))

    async def test_real_reservations_freeze_dst_and_fractional_zone_boundaries(self):
        self.tick=datetime(2026,3,8,5,tzinfo=UTC); self.since=self.tick-timedelta(days=30)
        self.expiry=datetime(2026,3,9,3,tzinfo=UTC)
        await self.update_pref(timezone_name="America/New_York")
        async with self.sessions.begin() as s:
            await s.execute(update(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id==1).values(timezone_offset_minutes=-300))
        reserved=await self.reserve(); row=await self.row(reserved.job_id)
        self.assertEqual(row["day_end_utc"]-row["day_start_utc"],timedelta(hours=23))
        self.assertEqual(row["timezone_name"],"America/New_York")

    async def test_invalid_batch_and_lease_have_no_implicit_defaults(self):
        for limit in (0,129,True):
            with self.assertRaises(ValueError): await self.queue.due(limit=limit)
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        with self.assertRaises(ValueError): await self.claim(reserved.job_id,lease_for=timedelta(0))
        lease=await self.claim(reserved.job_id,lease_for=timedelta(days=999999999))
        self.assertEqual(lease.lease_expires_at,self.expiry)

    async def test_drain_resolves_actor_outside_sql_and_never_sends(self):
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        observations=[]
        async def actor_for(uid): self.assertEqual(uid,1); return self.actor
        async def observe(report): observations.append(report)
        results=await self.queue.drain(actor_for,history_since=self.since,lease_for=timedelta(minutes=5),limit=5,observe=observe)
        self.assertEqual([r.reason for r in results],["shadow_evaluated"])
        self.assertEqual([r.job_id for r in observations],[reserved.job_id])
        self.assertTrue(all(not r.dispatch_allowed for r in observations))
        self.assertEqual(await self.counts(),(1,0))

    async def test_one_actor_resolution_failure_does_not_stop_the_due_batch(self):
        await self.reserve()
        await self._progress(user_id=3,offset=0)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==3).values(telegram_id=3003,level="hsk1"))
            s.add(CourseMiniAppProfile(user_id=3,timezone_offset_minutes=0))
            s.add(SmartReminderPreference(user_id=3,master_enabled=True,legacy_time_local=time(14),timezone_name="Etc/UTC"))
            s.add(SmartReminderConsent(user_id=3,channel="telegram",state="on",source="user_intent",source_key="intent:telegram"))
        other=SmartReminderActor(3,"telegram",telegram_id=3003)
        second=await self.reserve(actor=other); self.tick=self.tick.replace(hour=14)
        async def actor_for(uid):
            if uid==1: raise RuntimeError("synthetic unavailable actor resolver")
            return other
        results=await self.queue.drain(actor_for,history_since=self.since,lease_for=timedelta(minutes=5),limit=5)
        self.assertEqual(sorted(r.reason for r in results),["shadow_evaluated","shadow_worker_failed"])
        self.assertEqual((await self.row(second.job_id))["state"],"completed")

    async def native_actor(self):
        await self._progress(user_id=2,offset=0)
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id==2).values(level="hsk1"))
            s.add(CourseMiniAppProfile(user_id=2,timezone_offset_minutes=0))
            s.add(SmartReminderPreference(user_id=2,master_enabled=True,legacy_time_local=time(14),timezone_name="Etc/UTC"))
            s.add(DesktopDevice(id="native-queue",user_id=2,installation_key_hash="synthetic-queue",platform="android",app_version="qa"))
            await s.flush()
            s.add(DesktopSession(id="native-queue-session",device_id="native-queue",refresh_token_hash="synthetic-queue",expires_at=self.now+timedelta(days=1)))
            s.add(SmartReminderConsent(user_id=2,device_id="native-queue",channel="android",state="on",source="user_intent",source_key="intent:android:native-queue"))
            s.add(SmartReminderCapability(device_id="native-queue",user_id=2,study_notifications_allowed=True,
                observed_at=self.now-timedelta(minutes=1),expires_at=self.now+timedelta(hours=1)))
        return SmartReminderActor(2,"android",device_id="native-queue",session_id="native-queue-session")

    async def test_native_only_account_uses_real_actor_without_fake_telegram(self):
        actor=await self.native_actor()
        reserved=await self.reserve(actor=actor); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id,actor=actor)
        self.assertEqual((await self.finish(lease,actor=actor)).reason,"shadow_evaluated")
        async with self.sessions() as s:
            self.assertIsNone(await s.scalar(select(User.telegram_id).where(User.id==2)))
        self.assertEqual(await self.counts(),(1,0))

    async def test_native_revoked_session_cannot_finish_an_existing_lease(self):
        actor=await self.native_actor()
        reserved=await self.reserve(actor=actor); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id,actor=actor)
        async with self.sessions.begin() as s:
            await s.execute(update(DesktopSession).where(DesktopSession.id==actor.session_id).values(revoked_at=self.now))
        with self.assertRaises(SmartReminderError) as exc: await self.finish(lease,actor=actor)
        self.assertEqual(exc.exception.code,"smart_session_revoked")
        self.assertEqual(await self.counts(),(1,0))

    @unittest.skipUnless(fixtures.fixtures.PG_URL,"PostgreSQL row locks required")
    async def test_two_reservers_and_two_claimers_have_one_durable_owner(self):
        if not self.postgres: self.skipTest("SQLite does not implement row locks")
        results=await asyncio.wait_for(asyncio.gather(self.reserve(),self.reserve()),10)
        self.assertEqual(sorted(r.reason for r in results),["account_day_already_owned","shadow_reserved"])
        self.assertEqual(len({r.job_id for r in results}),1)
        self.tick=self.tick.replace(hour=14)
        claims=await asyncio.wait_for(asyncio.gather(self.claim(results[0].job_id),self.claim(results[0].job_id)),10)
        self.assertEqual(sorted(r.reason for r in claims),["shadow_claimed","shadow_lease_busy"])
        self.assertEqual(await self.counts(),(1,0))

    async def blocked_finish(self, lease, mutate):
        started=asyncio.Event()
        def lock_started(c,cursor,statement,parameters,ctx,many):
            if "FOR UPDATE" in statement and "FROM users" in statement: started.set()
        async with self.sessions.begin() as s:
            await s.execute(select(User.id).where(User.id==1).with_for_update())
            await mutate(s)
            event.listen(self.engine.sync_engine,"before_cursor_execute",lock_started)
            task=asyncio.create_task(self.finish(lease))
            try:
                await asyncio.wait_for(started.wait(),5)
                self.assertFalse(task.done())
            finally:
                event.remove(self.engine.sync_engine,"before_cursor_execute",lock_started)
        return await asyncio.wait_for(task,10)

    @unittest.skipUnless(fixtures.fixtures.PG_URL,"PostgreSQL row locks required")
    async def test_off_commit_wins_over_waiting_stale_worker(self):
        if not self.postgres: self.skipTest("SQLite does not implement row locks")
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        async def off(s):
            await SmartReminderPreferencesService(s).patch(self.actor,SmartReminderPatch(request_id=str(uuid4()),expected_revision=2,master_enabled=False))
        result=await self.blocked_finish(lease,off)
        self.assertEqual(result.reason,"shadow_lease_lost")
        self.assertEqual((await self.row(reserved.job_id))["state"],"cancelled")

    @unittest.skipUnless(fixtures.fixtures.PG_URL,"PostgreSQL row locks required")
    async def test_new_learning_commit_is_seen_by_waiting_worker(self):
        if not self.postgres: self.skipTest("SQLite does not implement row locks")
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id); self.tick+=timedelta(minutes=1)
        result=await self.blocked_finish(lease,self.accepted_lesson)
        self.assertEqual(result.reason,"goal_completed")

    async def waiting_operation(self, operation, mutate_after_wait):
        started=asyncio.Event()
        def lock_started(c,cursor,statement,parameters,ctx,many):
            if "FOR UPDATE" in statement and "FROM users" in statement: started.set()
        async with self.sessions.begin() as s:
            await s.execute(select(User.id).where(User.id==1).with_for_update())
            event.listen(self.engine.sync_engine,"before_cursor_execute",lock_started)
            task=asyncio.create_task(operation())
            try:
                await asyncio.wait_for(started.wait(),5)
                self.assertFalse(task.done())
                await mutate_after_wait(s)
            finally:
                event.remove(self.engine.sync_engine,"before_cursor_execute",lock_started)
        return await asyncio.wait_for(task,10)

    @unittest.skipUnless(fixtures.fixtures.PG_URL,"PostgreSQL row locks required")
    async def test_claim_samples_clock_after_waiting_past_expiry(self):
        if not self.postgres: self.skipTest("SQLite does not implement row locks")
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        async def expire_while_waiting(s): self.tick=self.expiry+timedelta(seconds=1)
        result=await self.waiting_operation(lambda:self.claim(reserved.job_id),expire_while_waiting)
        self.assertEqual(result.reason,"shadow_expired")
        self.assertIsNone((await self.row(reserved.job_id))["lease_token"])

    @unittest.skipUnless(fixtures.fixtures.PG_URL,"PostgreSQL row locks required")
    async def test_finish_keeps_learning_that_committed_after_the_prelock_clock(self):
        if not self.postgres: self.skipTest("SQLite does not implement row locks")
        reserved=await self.reserve(); self.tick=self.tick.replace(hour=14)
        lease=await self.claim(reserved.job_id)
        async def learn_while_waiting(s):
            self.tick+=timedelta(minutes=1)
            await self.accepted_lesson(s)
        result=await self.waiting_operation(lambda:self.finish(lease),learn_while_waiting)
        self.assertEqual(result.reason,"goal_completed")


class SQLiteQueueTests(QueueChecks,unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(fixtures.fixtures.PG_URL,"Disposable loopback PostgreSQL not configured")
class PostgreSQLQueueTests(QueueChecks,unittest.IsolatedAsyncioTestCase):
    postgres=True
