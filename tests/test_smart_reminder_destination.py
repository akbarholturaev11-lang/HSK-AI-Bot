"""D06: real current-device eligibility, original learning votes, no authority."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy import delete, event, insert, select, update

from app.db.models.android_push import AndroidPushToken
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.learner_pwa_push import LearnerPwaPushSubscription
from app.db.models.smart_reminder import SmartReminderCapability, SmartReminderConsent, SmartReminderPreference
from app.db.models.user import User
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.desktop_course_service import DesktopCourseService
from app.services.smart_reminder_destination import (
    Destination, DestinationChoice, DestinationEvidence, DestinationStudy,
    SmartReminderDestinationService, choose_destination,
)
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError
from app.services.smart_reminder_shadow_queue import QUEUE_VERSION
from tests import test_smart_reminder_android as fixture

NOW = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)


class DestinationPolicyTests(unittest.TestCase):
    def phone(self, name, **changes):
        return replace(Destination(1, "android", name, NOW + timedelta(hours=1), NOW), **changes)

    def pwa(self, name, **changes):
        return replace(Destination(1, "pwa", name, NOW + timedelta(hours=1), NOW), **changes)

    def choose(self, endpoints, studies=(), **changes):
        return choose_destination(**(dict(user_id=1, destinations=endpoints,
            evidence=DestinationEvidence(tuple(studies)), observed_at=NOW,
            history_since=NOW-timedelta(days=30)) | changes))

    def study(self, name, ref, **changes):
        return replace(DestinationStudy(1, ref, "android", name, NOW-timedelta(days=1)), **changes)

    def test_one_phone_needs_no_history_and_never_grants_dispatch(self):
        result = self.choose((self.phone("only"),))
        self.assertEqual((result.reason, result.channel, result.device_id), ("single_eligible_destination", "android", "only"))
        self.assertIsNone(result.observed_results)
        self.assertFalse(result.dispatch_allowed)
        with self.assertRaises(ValueError):
            replace(result, dispatch_allowed=True)

    def test_pwa_is_a_single_selected_destination_and_manual_native_lock_excludes_it(self):
        pwa = self.pwa("pwa-device")
        result = self.choose((pwa,), master_enabled=True)
        self.assertEqual((result.channel, result.device_id), ("pwa", "pwa-device"))
        self.assertFalse(result.dispatch_allowed)
        self.assertEqual(self.choose((pwa,), master_enabled=True,
            channel_mode="manual_locked", preferred_channel="telegram").channel, None)

    def test_more_original_study_results_win_over_recent_app_activity(self):
        endpoints = (self.phone("a"), self.phone("b", last_active_at=NOW-timedelta(days=1)))
        result = self.choose(endpoints, (self.study("a", "a1"), self.study("b", "b1"), self.study("b", "b2")))
        self.assertEqual((result.device_id, result.reason, result.observed_results), ("b", "observed_study_preference", 2))

    def test_duplicate_reward_foreign_future_and_outside_window_do_not_add_votes(self):
        b = self.study("b", "b1")
        invalid = (self.study("a", "reward", activity_type="reward"), self.study("a", "foreign", user_id=2),
            self.study("a", "future", accepted_at=NOW+timedelta(seconds=1)),
            self.study("a", "old", accepted_at=NOW-timedelta(days=31)))
        result = self.choose((self.phone("a"), self.phone("b")), (b, b, *invalid))
        self.assertEqual((result.device_id, result.observed_results), ("b", 1))

    def test_conflicting_attribution_is_not_counted_for_either_device(self):
        result = self.choose((self.phone("a"), self.phone("b")), (
            self.study("a", "same"), self.study("b", "same"), self.study("b", "proven")))
        self.assertEqual((result.device_id, result.observed_results), ("b", 1))
        self.assertIn("destination_attribution_conflict", result.coverage_limits)

    def test_verified_recency_then_stable_reachability_break_ties(self):
        result = self.choose((self.phone("a"), self.phone("b")), (
            self.study("a", "a1"), self.study("b", "b1", accepted_at=NOW)))
        self.assertEqual(result.device_id, "b")
        for endpoints in ((self.phone("b"), self.phone("a")), (self.phone("a"), self.phone("b"))):
            result = self.choose(endpoints)
            self.assertEqual(result.device_id, "a")
            self.assertEqual(result.reason, "recent_reachable_destination_fallback")
            self.assertIsNone(result.observed_results)

    def test_manual_channel_and_off_override_learning_preference(self):
        tg = Destination(1, "telegram")
        history = (self.study("a", "a1"),)
        self.assertEqual(self.choose((tg, self.phone("a")), history, channel_mode="manual_locked",
            preferred_channel="telegram").channel, "telegram")
        self.assertIsNone(self.choose((self.phone("a"),), history, channel_mode="manual_locked",
            preferred_channel="telegram").channel)
        self.assertIsNone(self.choose((tg, self.phone("a")), history, master_enabled=False).channel)

    def test_expired_foreign_unsupported_and_conflicting_frames_are_refused(self):
        result = self.choose((self.phone("a", valid_until=NOW), self.phone("b", user_id=2),
            Destination(1, "ios", "future-host")))
        self.assertIsNone(result.channel)
        self.assertEqual(self.choose((self.phone("a"), self.phone("a", last_active_at=None))).reason,
            "destination_snapshot_conflict")

    def test_privileged_cross_channel_evidence_uses_same_single_choice_core(self):
        tg = Destination(1, "telegram")
        studies = (DestinationStudy(1, "tg1", "telegram", None, NOW),
            DestinationStudy(1, "tg2", "telegram", None, NOW), self.study("a", "a1"))
        self.assertEqual(self.choose((self.phone("a"), tg), studies).channel, "telegram")


class DestinationSourceChecks:
    postgres = False

    async def asyncSetUp(self):
        if self.postgres and not fixture.PG_URL:
            self.skipTest("Owned loopback PostgreSQL required")
        cls = fixture.PostgreSQLAndroidProtocolTests if self.postgres else fixture.SQLiteAndroidProtocolTests
        self.case = cls(methodName="test_due_is_non_persisting_and_claim_commits_once_before_response")
        await self.case.asyncSetUp()
        self.tick = self.case.tick
        self.actor = SmartReminderActor(1, "android", device_id="device-1", session_id="session-1")
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(state="shadow", policy_version=QUEUE_VERSION,
                selected_channel=None, selected_device_id=None))
            await session.execute(update(SmartReminderConsent).where(SmartReminderConsent.channel == "telegram").values(state="off"))

    async def asyncTearDown(self):
        if hasattr(self, "case") and hasattr(self.case, "engine"):
            await self.case.asyncTearDown()

    async def choose(self, *, actor=None, job=None, reader=None):
        async with self.case.sessions.begin() as session:
            options = {"study_reader": reader} if reader is not None else {}
            return await SmartReminderDestinationService(session, clock=lambda: self.tick, **options).select(
                actor or self.actor, job_id=job or self.case.job_id, history_since=self.tick-timedelta(days=30))

    async def add_pwa_install(self):
        async with self.case.sessions.begin() as session:
            session.add(DesktopDevice(id="pwa-device", user_id=1, platform="pwa",
                installation_key_hash="p"*64, app_version="synthetic", last_seen_at=self.tick))
            session.add(DesktopSession(id="pwa-session", device_id="pwa-device",
                refresh_token_hash="r"*64, expires_at=self.tick+timedelta(days=1)))
            session.add(LearnerPwaPushSubscription(id=str(uuid4()), device_id="pwa-device",
                endpoint_hash="e"*64, encrypted_payload="synthetic-only",
                created_at=self.tick, updated_at=self.tick))
            await session.execute(update(SmartReminderConsent).where(
                SmartReminderConsent.channel == "android").values(state="off"))

    async def choose_with_pwa(self):
        async with self.case.sessions.begin() as session:
            return await SmartReminderDestinationService(session, clock=lambda: self.tick,
                pwa_push_ready=True).select(self.actor, job_id=self.case.job_id,
                    history_since=self.tick-timedelta(days=30))

    async def test_current_push_subscription_needs_existing_smart_master_opt_in(self):
        await self.add_pwa_install()
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(
                SmartReminderPreference.user_id == 1).values(master_enabled=None))
        choice = await self.choose_with_pwa()
        self.assertIsNone(choice.channel)
        self.assertIn(choice.reason, {"no_eligible_destination", "manual_channel_unavailable"})

    async def test_current_pwa_endpoint_can_be_selected_when_smart_is_on_and_other_channels_are_off(self):
        await self.add_pwa_install()
        choice = await self.choose_with_pwa()
        self.assertEqual((choice.channel, choice.device_id), ("pwa", "pwa-device"))

    async def test_manual_android_channel_lock_blocks_pwa_destination(self):
        await self.add_pwa_install()
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(
                SmartReminderPreference.user_id == 1).values(
                    channel_mode="manual_locked", preferred_channel="android"))
        choice = await self.choose_with_pwa()
        self.assertIsNone(choice.channel)

    async def second_phone(self):
        await self.case.second_installation()
        async with self.case.sessions.begin() as session:
            session.add(SmartReminderConsent(user_id=1, device_id="device-2", channel="android",
                source_key="intent:android:device-2", state="on", source="user_intent"))

    async def native_lesson(self, device, order, *, days_ago=1, duplicate=False, changes=None):
        ref = f"v3-part:hsk1:{order}:complete"
        async with self.case.sessions.begin() as session:
            user = await session.get(User, 1)
            game = await CourseGamificationService(session).award(user, activity_type="lesson", activity_ref=ref,
                base_xp=20, level="hsk1")
            if duplicate:
                game = await CourseGamificationService(session).award(user, activity_type="lesson", activity_ref=ref,
                    base_xp=20, level="hsk1")
            result = DesktopCourseService._completion_payload(lesson_order=order, next_lesson=order+1,
                completed_lessons_count=order, gamification=game)
            payload = {"device_id": device, "result": result} | (changes or {})
            await CourseMiniAppAnalyticsService(session).record_server_event(event_name="lesson_completed", user_id=1,
                telegram_id=user.telegram_id, source="android_course", level="hsk1", lesson_order=order,
                session_id=f"native-lesson-{order}", dedupe_key=f"native-lesson-{order}", payload=payload)
            at = self.tick-timedelta(days=days_ago)
            await session.execute(update(CourseXpEvent).where(CourseXpEvent.user_id == 1,
                CourseXpEvent.activity_ref == ref).values(created_at=at, activity_date=at.date()))
            await session.execute(update(CourseMiniAppEvent).where(CourseMiniAppEvent.user_id == 1,
                CourseMiniAppEvent.source == "android_course", CourseMiniAppEvent.lesson_order == order).values(created_at=at))
            await session.execute(update(CourseProgress).where(CourseProgress.user_id == 1).values(completed_lessons_count=order))

    async def test_single_native_only_phone_selects_immediately_without_learning_query(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(User).where(User.id == 1).values(telegram_id=None))
        reader = AsyncMock(side_effect=AssertionError("one phone needs no history"))
        result = await self.choose(reader=reader)
        self.assertEqual((result.channel, result.device_id, result.reason), ("android", "device-1", "single_eligible_destination"))
        reader.assert_not_awaited()
        self.assertFalse(result.dispatch_allowed)
        self.assertEqual((result.preference_revision, result.grant_epoch), (2, 1))

    async def test_multiple_sessions_on_same_phone_remain_one_destination(self):
        async with self.case.sessions.begin() as session:
            session.add(DesktopSession(id="extra-login", device_id="device-1", refresh_token_hash="extra-synthetic",
                expires_at=self.tick+timedelta(days=2)))
        result = await self.choose(reader=AsyncMock(side_effect=AssertionError("still one phone")))
        self.assertEqual((result.device_id, result.reason), ("device-1", "single_eligible_destination"))

    async def test_existing_native_history_prefers_more_studied_phone_on_first_day(self):
        await self.second_phone()
        await self.native_lesson("device-1", 5, days_ago=3)
        await self.native_lesson("device-2", 6, days_ago=2)
        await self.native_lesson("device-2", 7, days_ago=1)
        result = await self.choose()
        self.assertEqual((result.device_id, result.reason, result.observed_results), ("device-2", "observed_study_preference", 2))
        self.assertIn("native_android_lesson_attribution_only", result.coverage_limits)
        self.assertFalse(result.dispatch_allowed)

    async def test_duplicate_xp_unbound_or_foreign_payload_does_not_steal_preference(self):
        await self.second_phone()
        await self.native_lesson("device-2", 5)
        await self.native_lesson("device-1", 6, duplicate=True)
        await self.native_lesson("device-1", 7, changes={"device_id": "not-an-owned-phone"})
        await self.native_lesson("device-1", 8, changes={"result": {"ok": True}})
        self.assertEqual((await self.choose()).device_id, "device-2")

    async def test_conflicting_server_receipts_do_not_invent_a_preferred_phone(self):
        await self.second_phone()
        await self.native_lesson("device-2", 5)
        async with self.case.sessions.begin() as session:
            original = (await session.execute(select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.source == "android_course", CourseMiniAppEvent.lesson_order == 5))).scalar_one()
            payload = json.loads(original.payload_json)
            payload["device_id"] = "device-1"
            session.add(CourseMiniAppEvent(user_id=1, level="hsk1", source="android_course",
                event_name="lesson_completed", lesson_order=5, created_at=original.created_at,
                payload_json=json.dumps(payload)))
        result = await self.choose()
        self.assertEqual(result.reason, "recent_reachable_destination_fallback")
        self.assertIsNone(result.observed_results)
        self.assertIn("destination_attribution_conflict", result.coverage_limits)

    async def test_only_telegram_and_manual_android_use_current_consent_without_history(self):
        reader = AsyncMock(side_effect=AssertionError("one permitted destination needs no history"))
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderConsent).where(SmartReminderConsent.channel == "telegram").values(state="on"))
            await session.execute(update(SmartReminderCapability).values(study_notifications_allowed=False))
        result = await self.choose(reader=reader)
        self.assertEqual((result.channel, result.device_id), ("telegram", None))
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderCapability).values(study_notifications_allowed=True))
            await session.execute(update(SmartReminderPreference).values(channel_mode="manual_locked", preferred_channel="android"))
        result = await self.choose(reader=reader)
        self.assertEqual((result.channel, result.device_id), ("android", "device-1"))
        reader.assert_not_awaited()

    async def test_opens_reward_xp_and_unsupported_practice_are_not_learning_votes(self):
        await self.second_phone()
        await self.native_lesson("device-2", 5)
        async with self.case.sessions.begin() as session:
            for i in range(10):
                session.add(CourseMiniAppEvent(user_id=1, level="hsk1", source="android_course",
                    event_name="miniapp_opened", created_at=self.tick, payload_json=json.dumps({"device_id": "device-1"})))
            session.add(CourseXpEvent(user_id=1, activity_type="reward", activity_ref="reward-only", xp=10000,
                activity_date=self.tick.date(), week_start=self.tick.date(), created_at=self.tick))
        self.assertEqual((await self.choose()).device_id, "device-2")

    async def test_notice_permission_is_independent_and_legacy_mirror_cannot_create_study_consent(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(AndroidPushToken).where(AndroidPushToken.device_id == "device-1").values(
                notifications_allowed=False, study_reminders_enabled=False))
        self.assertEqual((await self.choose()).device_id, "device-1")
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderConsent).where(SmartReminderConsent.channel == "android").values(state="off"))
            await session.execute(update(AndroidPushToken).values(notifications_allowed=True, study_reminders_enabled=True))
        self.assertIsNone((await self.choose()).channel)

    async def test_denied_stale_unsupported_or_unreachable_phone_is_not_selected(self):
        await self.second_phone()
        for changes in ({"study_notifications_allowed": False}, {"protocol_version": 0},
                        {"autonomous_study_disabled": False}, {"expires_at": self.tick}):
            async with self.case.sessions.begin() as session:
                await session.execute(update(SmartReminderCapability).where(SmartReminderCapability.device_id == "device-2").values(**(
                    dict(study_notifications_allowed=True, protocol_version=1, autonomous_study_disabled=True,
                    expires_at=self.case.expiry) | changes)))
            self.assertEqual((await self.choose()).device_id, "device-1")

    async def test_missing_transport_login_and_wrong_frozen_zone_are_excluded(self):
        await self.second_phone()
        async with self.case.sessions.begin() as session:
            await session.execute(update(AndroidPushToken).where(AndroidPushToken.device_id == "device-2").values(token=""))
        self.assertEqual((await self.choose()).device_id, "device-1")
        async with self.case.sessions.begin() as session:
            await session.execute(update(AndroidPushToken).where(AndroidPushToken.device_id == "device-2").values(token="synthetic-other-no-provider"))
            await session.execute(update(DesktopSession).where(DesktopSession.device_id == "device-2").values(revoked_at=self.tick))
        self.assertEqual((await self.choose()).device_id, "device-1")
        async with self.case.sessions.begin() as session:
            await session.execute(update(DesktopSession).where(DesktopSession.device_id == "device-2").values(revoked_at=None))
            await session.execute(update(AndroidPushToken).where(AndroidPushToken.device_id == "device-2").values(timezone_name="Asia/Tashkent"))
        self.assertEqual((await self.choose()).device_id, "device-1")

    async def test_revoked_or_other_owner_device_is_ignored(self):
        await self.second_phone()
        await self.native_lesson("device-2", 5)
        async with self.case.sessions.begin() as session:
            await session.execute(update(DesktopDevice).where(DesktopDevice.id == "device-2").values(revoked_at=self.tick))
        self.assertEqual((await self.choose()).device_id, "device-1")

    async def test_manual_unavailable_channel_never_falls_back_to_android(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1).values(
                channel_mode="manual_locked", preferred_channel="telegram"))
        result = await self.choose()
        self.assertEqual((result.channel, result.reason), (None, "manual_channel_unavailable"))

    async def test_master_off_and_stale_epoch_suppress_planning(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1).values(master_enabled=False))
        self.assertIsNone((await self.choose()).channel)
        async with self.case.sessions.begin() as session:
            await session.execute(update(SmartReminderPreference).where(SmartReminderPreference.user_id == 1).values(
                master_enabled=True, grant_epoch=2))
        self.assertEqual((await self.choose()).reason, "destination_context_changed")

    async def test_selected_or_attempted_intent_never_moves_to_another_phone(self):
        await self.second_phone()
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(selected_channel="android", selected_device_id="device-1"))
        self.assertEqual((await self.choose()).reason, "destination_intent_frozen")
        async with self.case.sessions.begin() as session:
            await session.execute(update(fixture.JOB).values(selected_channel=None, selected_device_id=None))
            await session.execute(insert(fixture.ATTEMPT).values(id="existing-attempt", job_id=self.case.job_id,
                attempt_key="x"*64, channel="android", state="unknown", grant_epoch=1, expires_at=self.case.expiry))
        self.assertEqual((await self.choose()).reason, "destination_intent_already_attempted")

    async def test_reader_is_read_only_and_proposal_cannot_authorize_a_claim(self):
        statements = []
        def capture(c, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(self.case.engine.sync_engine, "before_cursor_execute", capture)
        try:
            result = await self.choose()
        finally:
            event.remove(self.case.engine.sync_engine, "before_cursor_execute", capture)
        self.assertFalse(any(s.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"} for s in statements))
        self.assertFalse(result.dispatch_allowed)
        self.assertNotIn("synthetic-no-provider", repr(result))
        await self.case.claim(status=404)
        await self.case.no_grant()

    async def test_pending_deletion_block_and_foreign_job_cannot_select(self):
        with self.assertRaises(SmartReminderError):
            await self.choose(job="not-owned")
        await self.case._deletion()
        with self.assertRaises(SmartReminderError):
            await self.choose()

    async def test_clock_expiry_during_history_read_withholds_selection(self):
        await self.second_phone()
        async def slow_reader(*args, **kwargs):
            self.tick = self.case.expiry+timedelta(microseconds=1)
            return DestinationEvidence()
        self.assertIsNone((await self.choose(reader=slow_reader)).channel)


class SQLiteDestinationTests(DestinationSourceChecks, unittest.IsolatedAsyncioTestCase):
    pass


class PostgreSQLDestinationTests(DestinationSourceChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True
