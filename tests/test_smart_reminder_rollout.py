"""Automatic four-stage rollout and admission over the real Smart SQL paths."""
import asyncio
from datetime import timedelta
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import importlib.util
from pathlib import Path

from aiogram.exceptions import TelegramForbiddenError
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, insert, inspect, select, update

from app.db.base import Base

from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.learner_pwa_push import LearnerPwaPushSubscription
from app.db.models.course_progress import CourseProgress
from app.db.models.smart_reminder import (
    SmartReminderCapability, SmartReminderConsent, SmartReminderMutation, SmartReminderPreference,
    SmartReminderRollout, SmartReminderRouting,
)
from app.db.models.user import User
from app.services.notification_template_service import KEY_SMART_STUDY, NotificationTemplateService
from app.services.smart_reminder_lifecycle import SmartReminderLifecycleService
from app.services.smart_reminder_android import SmartReminderAndroidService, read_android_admission
from app.services.smart_reminder_policy import day_window
from app.services.smart_reminder_preferences import (
    SmartReminderActor, SmartReminderError, automatic_timezone_initialization_allowed, pwa_study_consent,
)
from app.services.smart_reminder_rollout import (
    COHORT_COUNT, LEGACY_DRAIN, REVIEW_TTL, STAGE_DURATION, SmartReminderAdmissionService,
    SmartReminderRolloutService, _utc, cohort_for_user, cohort_open,
)
from app.services.smart_reminder_runtime import SmartReminderRuntime
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from tests import test_smart_reminder_android as native
from tests import test_smart_reminder_telegram as telegram
from tests.test_smart_reminder_cadence import QA
from tests.test_smart_reminder_legacy_backfill import PG_URL
from tests.test_smart_reminder_runtime import open_rollout


ROUTING = SmartReminderRouting.__table__
ROLLOUT = SmartReminderRollout.__table__
_SPEC = importlib.util.spec_from_file_location("smart_rollout_migration",
    Path(__file__).resolve().parents[1] / "alembic/versions/0150_smart_reminder_rollout.py")
MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MIGRATION)


class CohortTests(unittest.TestCase):
    def test_cohorts_are_stable_cumulative_and_balanced(self):
        values = [cohort_for_user(user_id) for user_id in range(1, 4001)]
        self.assertEqual(values, [cohort_for_user(user_id) for user_id in range(1, 4001)])
        counts = [values.count(cohort) for cohort in range(COHORT_COUNT)]
        self.assertTrue(all(800 < count < 1200 for count in counts), counts)
        for user_id in range(1, 200):
            opened = [cohort_open(user_id, stage) for stage in range(COHORT_COUNT + 1)]
            self.assertEqual(opened, sorted(opened))  # An opened cohort stays open.
            self.assertFalse(opened[0])
            self.assertTrue(opened[COHORT_COUNT])
            self.assertTrue(cohort_open(user_id, 0, "complete"))
        for invalid in (0, -1, True, "1", 1.0):
            with self.assertRaises(ValueError):
                cohort_for_user(invalid)


class EarlyAccountTests(unittest.TestCase):
    def test_listed_owner_accounts_join_stage_one_and_invalid_entries_are_ignored(self):
        from app.services import smart_reminder_rollout as rollout
        self.assertEqual(cohort_for_user(3283), 3)
        with patch("app.config.settings.SMART_REMINDER_EARLY_USER_IDS", " 3283, x, -4, 0, 3471 ,"):
            self.assertEqual(rollout.early_accounts(), frozenset({3283, 3471}))
            self.assertEqual(rollout.rollout_cohort(3283), 0)
            self.assertTrue(cohort_open(3283, 1))
            self.assertEqual(cohort_for_user(3283), 3)  # The stable bucket itself is unchanged.
        with patch("app.config.settings.SMART_REMINDER_EARLY_USER_IDS", ""):
            self.assertFalse(cohort_open(3283, 1))


class PwaStudyConsentTests(unittest.TestCase):
    def test_pwa_needs_existing_study_consent_and_smart_off_always_wins(self):
        def pref(master, telegram):
            return {"master_enabled": master, "channels": {"telegram": {"consent": telegram}}}
        self.assertTrue(pwa_study_consent(pref(True, "off")))      # Explicit Smart ON.
        self.assertTrue(pwa_study_consent(pref(None, "on")))       # Existing study consent.
        self.assertFalse(pwa_study_consent(pref(None, "unknown"))) # A subscription alone is not consent.
        self.assertFalse(pwa_study_consent(pref(None, "off")))
        self.assertFalse(pwa_study_consent(pref(False, "on")))     # Smart OFF wins.


class FixtureChecks:
    postgres = False

    async def asyncSetUp(self):
        cls = telegram.PostgreSQLTelegramTests if self.postgres else telegram.SQLiteTelegramTests
        self.q = cls(methodName="test_admin_pause_after_prepare_stops_provider")
        await self.q.asyncSetUp()
        self.rollout = SmartReminderRolloutService(self.q.sessions, clock=lambda: self.q.tick)

    async def asyncTearDown(self):
        await self.q.asyncTearDown()

    async def state(self):
        return (await self.q.rows(ROLLOUT))[0]

    async def change_state(self, **values):
        async with self.q.sessions.begin() as s:
            await s.execute(update(ROLLOUT).where(ROLLOUT.c.id == 1).values(**values))

    async def template(self, enabled):
        async with self.q.sessions.begin() as s:
            await NotificationTemplateService(s).update_text(KEY_SMART_STUDY, enabled=enabled,
                text_uz="", text_ru="", text_tj="", updated_by=None)

    async def enabled(self):
        async with self.q.sessions() as s:
            return await NotificationTemplateService(s).is_enabled(KEY_SMART_STUDY)

    async def allowed(self, user_id):
        async with self.q.sessions() as s:
            return await self.rollout.allowed(s, user_id)

    async def attempts(self, outcomes, *, user_id=3, channel="telegram"):
        """Synthetic started attempts on distinct past days; never a delivery."""
        start = self.q.tick.replace(hour=0, minute=0, second=0, microsecond=0)
        first = getattr(self, "_days", 0) + 1
        self._days = first + len(outcomes)
        async with self.q.sessions.begin() as s:
            if channel == "android" and await s.get(DesktopDevice, "device-1") is None:
                s.add(DesktopDevice(id="device-1", user_id=user_id, platform="android", app_version="qa",
                    installation_key_hash="health-fixture"))
                await s.flush()
            for offset, state in enumerate(outcomes, start=first):
                day = start - timedelta(days=offset)
                job_id = str(uuid4())
                await s.execute(insert(JOB).values(id=job_id, user_id=user_id, local_day=day.date(),
                    timezone_name="Etc/UTC", day_start_utc=day, day_end_utc=day + timedelta(days=1),
                    scheduled_at=day + timedelta(hours=14), expires_at=day + timedelta(days=1),
                    state="unknown", policy_version="synthetic-health", preference_revision=1, grant_epoch=1,
                    course_key="hsk1", lesson_order=1, selected_channel=channel,
                    selected_device_id="device-1" if channel == "android" else None))
                await s.execute(insert(ATTEMPT).values(id=str(uuid4()), job_id=job_id, attempt_key=uuid4().hex,
                    channel=channel, device_id="device-1" if channel == "android" else None, grant_epoch=1,
                    state=state, prepared_at=self.q.tick, started_at=self.q.tick, expires_at=self.q.tick + timedelta(hours=1)))


class RolloutChecks(FixtureChecks):
    async def test_first_heartbeat_starts_stage_one_with_only_the_first_cohort(self):
        self.assertEqual([cohort_for_user(user_id) for user_id in (1, 2, 3)], [3, 2, 0])
        self.assertFalse(await self.allowed(3))
        self.assertEqual(await self.rollout.heartbeat(), 1)
        state = await self.state()
        self.assertEqual((state["generation"], state["stage"], state["status"]), (1, 1, "active"))
        self.assertEqual([await self.allowed(user_id) for user_id in (1, 2, 3)], [False, False, True])

    async def test_stages_open_cumulatively_after_observed_48_hours_then_complete(self):
        await self.rollout.heartbeat()
        await self.change_state(stage_started_at=self.q.tick - STAGE_DURATION + timedelta(minutes=1))
        self.assertEqual(await self.rollout.heartbeat(), 1)  # 47h59m is not enough.
        for stage in (2, 3, 4):
            await self.change_state(stage_started_at=self.q.tick - STAGE_DURATION)
            self.assertEqual(await self.rollout.heartbeat(), stage)
        self.assertEqual([await self.allowed(user_id) for user_id in (1, 2, 3)], [True, True, True])
        await self.change_state(stage_started_at=self.q.tick - STAGE_DURATION)
        self.assertEqual(await self.rollout.heartbeat(), 4)
        self.assertEqual((await self.state())["status"], "complete")
        snapshot = await self.snapshot()
        self.assertEqual((snapshot["status"], snapshot["next_stage_at"]), ("complete", None))

    async def test_unobserved_time_never_counts_and_stale_monitor_fails_closed(self):
        await self.rollout.heartbeat()
        self.q.tick += timedelta(hours=47)
        self.assertFalse(await self.allowed(3))  # No live monitor, no send authority.
        self.assertEqual((await self.snapshot())["status"], "paused")
        self.assertEqual(await self.rollout.heartbeat(), 1)
        state = await self.state()
        self.assertEqual(_utc(state["stage_started_at"]), self.q.tick)
        self.assertIsNone(state["error_code"])
        self.assertTrue(await self.enabled())
        self.assertTrue(await self.allowed(3))

    async def test_admin_off_pauses_and_on_restarts_at_stage_one_with_a_new_generation(self):
        await self.rollout.heartbeat()
        await self.change_state(stage=3)
        await self.template(False)
        self.assertEqual(await self.rollout.heartbeat(), 0)
        self.assertEqual((await self.state())["status"], "paused")
        self.assertFalse(await self.allowed(3))
        await self.template(True)
        self.assertEqual(await self.rollout.heartbeat(), 1)
        state = await self.state()
        self.assertEqual((state["generation"], state["stage"], state["status"]), (2, 1, "active"))
        self.assertEqual([await self.allowed(user_id) for user_id in (1, 2, 3)], [False, False, True])

    async def test_systemic_unknown_share_pauses_and_turns_the_template_off(self):
        await self.rollout.heartbeat()
        await self.attempts(["provider_accepted"] * 9 + ["unknown"] * 4)
        self.rollout._health_at = None
        self.assertEqual(await self.rollout.heartbeat(), 1)  # 4 unknown is below the minimum.
        await self.attempts(["unknown"] * 2)
        self.rollout._health_at = None
        self.assertEqual(await self.rollout.heartbeat(), 0)
        state = await self.state()
        self.assertEqual((state["status"], state["error_code"]), ("paused", "provider_unknown"))
        self.assertFalse(await self.enabled())
        self.assertFalse(await self.allowed(3))
        self.assertEqual(await self.rollout.heartbeat(), 0)

    async def test_learner_refusals_and_pending_android_receipts_are_not_systemic(self):
        await self.rollout.heartbeat()
        async with self.q.sessions.begin() as s:
            await s.execute(update(User).where(User.id == 2).values(bot_blocked_at=self.q.tick))
        await self.attempts(["unknown"] * 6, user_id=2)
        await self.attempts(["definite_failure"] * 6, user_id=3, channel="pwa")
        await self.attempts(["in_flight"] * 6, user_id=1, channel="android")
        self.rollout._health_at = None
        self.assertEqual(await self.rollout.heartbeat(), 1)
        self.assertTrue(await self.enabled())

    async def test_repeated_exceptions_or_consecutive_timeouts_pause_once(self):
        await self.rollout.heartbeat()
        for _ in range(2):
            await self.rollout.account_failed()
        self.assertEqual((await self.state())["status"], "active")
        await self.rollout.account_failed()
        self.assertEqual(((await self.state())["status"], (await self.state())["error_code"]),
                         ("paused", "runtime_exception"))
        self.assertFalse(await self.enabled())
        await self.template(True)
        self.assertEqual(await self.rollout.heartbeat(), 1)
        for timed_out in (True, True, False, True, True):
            await self.rollout.tick_finished(timed_out=timed_out)
        self.assertEqual((await self.state())["status"], "active")
        await self.rollout.tick_finished(timed_out=True)
        self.assertEqual((await self.state())["error_code"], "tick_timeout")
        with self.assertRaises(ValueError):
            await self.rollout.fail_stop("private provider text")

    async def test_snapshot_is_anonymous_and_read_only(self):
        self.assertEqual((await self.snapshot())["status"], "waiting")
        self.assertEqual(await self.q.rows(ROLLOUT), [])
        await self.rollout.heartbeat()
        snapshot = await self.snapshot()
        self.assertEqual(set(snapshot), {"generation", "stage", "cohort_count", "status", "next_stage_at",
                                         "heartbeat_at", "error_at", "error_code"})
        self.assertEqual(snapshot["next_stage_at"], (self.q.tick + STAGE_DURATION).isoformat())

    async def snapshot(self):
        async with self.q.sessions() as s:
            return await self.rollout.snapshot(s)

    async def test_real_migration_roundtrip_and_refusal_to_drop_observed_state(self):
        def migrate(sync, direction, prepare=False):
            context = MigrationContext.configure(sync, opts={"target_metadata": Base.metadata})
            with Operations.context(context) as op:
                if prepare:  # The 0149 schema: no rollout table or quiesce column.
                    op.drop_table(ROLLOUT.name)
                    op.drop_column(ROUTING.name, "quiesced_at")
                getattr(MIGRATION, direction)()
        async with self.q.engine.begin() as c:
            await c.run_sync(migrate, "upgrade", True)
            self.assertEqual([dict(r) for r in (await c.execute(select(ROLLOUT))).mappings()][0]["status"], "waiting")
            await c.run_sync(migrate, "downgrade")
            names, exists = await c.run_sync(lambda s: ({c["name"] for c in inspect(s).get_columns(ROUTING.name)},
                                                        inspect(s).has_table(ROLLOUT.name)))
            self.assertFalse(exists)
            self.assertNotIn("quiesced_at", names)
            await c.run_sync(migrate, "upgrade")
        self.assertEqual(await self.rollout.heartbeat(), 1)
        async with self.q.engine.begin() as c:
            with self.assertRaisesRegex(RuntimeError, "active or observed Smart rollout"):
                await c.run_sync(migrate, "downgrade")


class AdmissionChecks(FixtureChecks):
    def admission(self, **options):
        return SmartReminderAdmissionService(self.q.sessions, clock=lambda: self.q.tick,
            **(dict(telegram_ready=True) | options))

    async def routing(self):
        rows = await self.q.rows(ROUTING)
        return dict(rows[0]) if rows else None

    async def veto(self):
        async with self.q.sessions() as s:
            return await SmartReminderLifecycleService(s).legacy_send_veto(1, "telegram")

    async def admitted(self):
        """Real hold, then age only the drain clock; review is the real path."""
        self.assertEqual(await self.admission().step(4), ("held",))
        async with self.q.sessions.begin() as s:
            await s.execute(update(ROUTING).values(held_at=self.q.tick - LEGACY_DRAIN,
                quiesced_at=self.q.tick - LEGACY_DRAIN))
        self.assertEqual(await self.admission().step(4), ("admitted",))
        return await self.routing()

    async def test_early_owner_account_is_admitted_in_stage_one_with_every_guard(self):
        self.assertEqual(await self.admission().step(1), ())  # User 1 is cohort 3.
        with patch("app.config.settings.SMART_REMINDER_EARLY_USER_IDS", "1"):
            self.assertEqual(await self.admission().step(1), ("held",))
            self.assertEqual(await self.admission().step(1), ("draining",))  # Same 24-hour drain.
            await SmartReminderRolloutService(self.q.sessions, clock=lambda: self.q.tick).heartbeat()
            async with self.q.sessions() as s:
                self.assertTrue(await self.rollout.allowed(s, 1))

    async def test_open_cohort_is_held_drained_then_admitted_and_closed_cohorts_untouched(self):
        self.assertEqual(await self.admission().step(3), ())
        self.assertIsNone(await self.routing())
        self.assertFalse(await self.veto())
        self.assertEqual(await self.admission().step(4), ("held",))
        held = await self.routing()
        self.assertEqual((held["state"], held["generation"], held["verified_at"]), ("held", 1, None))
        self.assertEqual(_utc(held["quiesced_at"]), _utc(held["held_at"]))
        self.assertTrue(await self.veto())  # Every server legacy study sender stops now.
        self.assertEqual(await self.admission().step(4), ("draining",))
        self.q.tick += LEGACY_DRAIN - timedelta(seconds=1)
        self.assertEqual(await self.admission().step(4), ("draining",))
        self.q.tick += timedelta(seconds=1)
        self.assertEqual(await self.admission().step(4), ("admitted",))
        row = await self.routing()
        self.assertEqual((row["state"], row["generation"]), ("telegram", 1))
        self.assertEqual((_utc(row["verified_at"]), _utc(row["verified_until"])),
                         (self.q.tick, self.q.tick + REVIEW_TTL))
        self.assertRegex(row["evidence_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(await self.admission().step(4), ("current",))
        self.assertEqual(await self.admission(telegram_ready=False).step(4), ())

    async def test_admitted_account_is_served_once_by_the_real_production_runtime(self):
        await self.admitted()
        await open_rollout(self.q.sessions, self.q.tick)
        def runtime():
            return SmartReminderRuntime(self.q.settings, self.q.sessions, enabled=True, calibration=QA,
                history_window=timedelta(days=30), coverage_reader=self.q.service.coverage_reader,
                telegram_send=self.q.send, clock=lambda: self.q.tick, admission=True)
        planned, = await runtime().tick()
        self.assertEqual(planned.reason, "telegram_not_due")
        self.q.tick = self.q.tick.replace(hour=14, minute=1)
        sent, = await runtime().tick()
        self.assertEqual(sent.reason, "telegram_provider_accepted")
        await runtime().tick()
        self.assertEqual(self.q.bot.send_message.await_count, 1)
        self.assertEqual(len(await self.q.rows(ATTEMPT)), 1)

    async def test_old_android_device_keeps_the_account_on_legacy_senders(self):
        async with self.q.sessions.begin() as s:
            s.add(DesktopDevice(id="old-apk", user_id=1, platform="android", app_version="1.7.21",
                installation_key_hash="old-apk-fixture"))
        self.assertEqual(await self.admission().step(4), ("not_eligible",))
        self.assertIsNone(await self.routing())
        self.assertFalse(await self.veto())

    async def test_admitted_learner_with_iphone_pwa_push_gets_the_smart_web_push(self):
        """Learner iPhone PWA: an admitted account with study consent and a live
        push subscription is served once by Web Push, never also on Telegram."""
        async with self.q.sessions.begin() as s:
            s.add(DesktopDevice(id="iphone-pwa", user_id=1, platform="pwa", app_version="pwa",
                installation_key_hash="iphone-pwa-fixture", last_seen_at=self.q.tick))
            await s.flush()
            s.add(DesktopSession(id="iphone-pwa-session", device_id="iphone-pwa",
                refresh_token_hash="iphone-pwa-refresh", expires_at=self.q.tick + timedelta(days=30)))
            sealed, endpoint_hash = self.sealed_subscription()
            s.add(LearnerPwaPushSubscription(id=str(uuid4()), device_id="iphone-pwa", endpoint_hash=endpoint_hash,
                encrypted_payload=sealed, created_at=self.q.tick, updated_at=self.q.tick))
        # A typical PWA learner: no explicit Smart choice, only the existing
        # Telegram study consent. The PWA carries that same reminder.
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).values(master_enabled=None))
        await self.admitted()  # PWA is not an Android device: no fence change.
        await open_rollout(self.q.sessions, self.q.tick)
        config = ("private-key-test", "mailto:test@example.com", self.fernet)
        pushes = AsyncMock(return_value=201)
        def runtime():
            return SmartReminderRuntime(self.q.settings, self.q.sessions, enabled=True, calibration=QA,
                history_window=timedelta(days=30), coverage_reader=self.q.service.coverage_reader,
                telegram_send=self.q.send, clock=lambda: self.q.tick, admission=True)
        with patch("app.services.learner_pwa_push.sender_config", return_value=config), \
                patch("app.services.smart_reminder_pwa.sender_config", return_value=config), \
                patch("app.services.smart_reminder_pwa.send_webpush", pushes):
            await runtime().tick()
            self.q.tick = self.q.tick.replace(hour=14, minute=1)
            results = await runtime().tick()
            await runtime().tick()
        self.assertIn("pwa_provider_accepted", [getattr(r, "reason", None) for r in results])
        pushes.assert_awaited_once()
        self.q.bot.send_message.assert_not_awaited()
        attempt, = await self.q.rows(ATTEMPT)
        self.assertEqual((attempt["channel"], attempt["device_id"], attempt["state"]),
                         ("pwa", "iphone-pwa", "provider_accepted"))

    def sealed_subscription(self):
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        self.fernet = Fernet(Fernet.generate_key())
        public = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            Encoding.X962, PublicFormat.UncompressedPoint)
        b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
        raw = {"endpoint": "https://web.push.apple.com/device/synthetic",
               "keys": {"p256dh": b64(public), "auth": b64(b"a" * 16)}}
        import hashlib
        return (self.fernet.encrypt(json.dumps(raw).encode("ascii")).decode("ascii"),
                hashlib.sha256(raw["endpoint"].encode("utf-8")).hexdigest())

    async def test_smart_capable_phone_is_held_switched_and_served_on_telegram(self):
        """Public 1.7.29/60: the hold itself switches the phone to server-only."""
        async with self.q.sessions.begin() as s:
            s.add(DesktopDevice(id="phone-60", user_id=1, platform="android", app_version="1.7.29",
                installation_key_hash="phone-60-fixture"))
            await s.flush()
            s.add(DesktopSession(id="phone-60-session", device_id="phone-60",
                refresh_token_hash="phone-60-refresh", expires_at=self.q.tick + timedelta(days=30)))
        phone = SmartReminderActor(1, "android", device_id="phone-60", session_id="phone-60-session",
            access_expires_at=self.q.tick + timedelta(minutes=15))
        async def server_only():
            async with self.q.sessions() as s:
                service = SmartReminderAndroidService(s, clock=lambda: self.q.tick)
                return (await service.mode(phone))["server_claim_required"]
        self.assertFalse(await server_only())  # Before the hold the phone keeps its own reminder.
        self.assertEqual(await self.admission().step(4), ("held",))
        self.assertTrue(await server_only())  # Its next worker run stops local posting.
        async with self.q.sessions.begin() as s:
            await s.execute(update(ROUTING).values(held_at=self.q.tick - LEGACY_DRAIN,
                quiesced_at=self.q.tick - LEGACY_DRAIN))
        self.assertEqual(await self.admission().step(4), ("admitted",))
        row = await self.routing()
        self.assertEqual(row["state"], "telegram")
        self.assertEqual(_utc(row["verified_until"]), self.q.tick + REVIEW_TTL)  # No token cap.
        # The phone reports server-only Smart; the review is re-attested in place.
        async with self.q.sessions.begin() as s:
            s.add(SmartReminderCapability(user_id=1, device_id="phone-60", generation=1, protocol_version=1,
                autonomous_study_disabled=True, study_notifications_allowed=True,
                observed_at=self.q.tick, expires_at=self.q.tick + timedelta(minutes=15)))
        self.assertEqual(await self.admission().step(4), ("reviewed",))
        self.assertEqual((await self.routing())["generation"], 1)
        await open_rollout(self.q.sessions, self.q.tick)
        def runtime():
            return SmartReminderRuntime(self.q.settings, self.q.sessions, enabled=True, calibration=QA,
                history_window=timedelta(days=30), coverage_reader=self.q.service.coverage_reader,
                telegram_send=self.q.send, clock=lambda: self.q.tick, admission=True)
        await runtime().tick()
        self.q.tick = self.q.tick.replace(hour=14, minute=1)  # Capability long expired: still served.
        results = await runtime().tick()
        self.assertIn("telegram_provider_accepted", [getattr(r, "reason", None) for r in results])
        await runtime().tick()
        self.assertEqual(self.q.bot.send_message.await_count, 1)

    async def bot_only(self, *, enabled=True, offset=5):
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).values(timezone_name=None))
            await s.execute(update(CourseProgress).where(CourseProgress.user_id == 1).values(
                reminder_enabled=enabled, reminder_tz_offset=offset))

    async def test_bot_only_learner_gets_the_legacy_offset_zone_and_is_held(self):
        await self.bot_only(offset=5)
        self.assertEqual(await self.admission().step(4), ("held",))
        pref = (await self.q.rows(SmartReminderPreference.__table__))[0]
        self.assertEqual((pref["timezone_name"], pref["revision"], pref["grant_epoch"]), ("Etc/GMT-5", 3, 1))
        mutation = (await self.q.rows(SmartReminderMutation.__table__))[-1]
        self.assertEqual((mutation["actor_key"], mutation["applied_revision"]), ("telegram_bot", 3))
        self.assertEqual([r["state"] for r in await self.q.rows(SmartReminderConsent.__table__)], ["on"])
        self.assertEqual((await self.routing())["preference_revision"], 3)
        self.assertTrue(await self.veto())

    async def test_no_legacy_reminder_or_an_invalid_offset_gets_no_derived_zone(self):
        # A manual time lock always carries a zone (storage constraint).
        await self.bot_only(enabled=False)
        self.assertEqual(await self.admission().step(4), ())
        await self.bot_only(offset=15)  # Out-of-range legacy value: no guess.
        self.assertEqual(await self.admission().step(4), ("not_eligible",))
        pref = (await self.q.rows(SmartReminderPreference.__table__))[0]
        self.assertEqual((pref["timezone_name"], pref["revision"]), (None, 2))
        self.assertIsNone(await self.routing())

    async def old_phone(self, seen_days_ago):
        async with self.q.sessions.begin() as s:
            s.add(DesktopDevice(id="old-apk", user_id=1, platform="android", app_version="1.7.21",
                installation_key_hash="old-apk-fixture", created_at=self.q.tick - timedelta(days=200),
                last_seen_at=self.q.tick - timedelta(days=seen_days_ago)))

    async def test_dormant_old_phone_no_longer_blocks_but_a_recent_one_does(self):
        await self.old_phone(13)
        self.assertEqual(await self.admission().step(4), ("not_eligible",))
        async with self.q.sessions.begin() as s:
            await s.execute(update(DesktopDevice).values(last_seen_at=self.q.tick - timedelta(days=15)))
        await self.admitted()
        # The app wakes: its token refresh records last_seen_at, Telegram Smart
        # stops at once and the woken app keeps its own reminder (no double).
        async with self.q.sessions.begin() as s:
            await s.execute(update(DesktopDevice).values(last_seen_at=self.q.tick))
        async with self.q.sessions.begin() as s:
            with self.assertRaisesRegex(SmartReminderError, "telegram_cohort_unavailable"):
                await self.q.service._cohort(s, self.q.actor)
        self.assertEqual(await self.admission().step(4), ("not_eligible",))

    async def test_missing_zone_consent_off_or_blocked_bot_is_never_held(self):
        # No Smart zone and no legacy reminder to derive one from.
        await self.bot_only(enabled=False)
        self.assertEqual(await self.admission().step(4), ())
        async with self.q.sessions.begin() as s:
            await s.execute(update(CourseProgress).values(reminder_enabled=True))
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).values(timezone_name="Etc/UTC"))
            await s.execute(update(SmartReminderConsent).where(SmartReminderConsent.channel == "telegram")
                .values(state="off"))
        self.assertEqual(await self.admission().step(4), ("not_eligible",))
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderConsent).values(state="on"))
            await s.execute(update(User).where(User.id == 1).values(bot_blocked_at=self.q.tick))
        self.assertEqual(await self.admission().step(4), ("actor_unavailable",))
        self.assertIsNone(await self.routing())

    async def pending_job(self):
        day = self.q.tick.replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.q.sessions.begin() as s:
            await s.execute(insert(JOB).values(id=str(uuid4()), user_id=1, local_day=day.date(),
                timezone_name="Etc/UTC", day_start_utc=day, day_end_utc=day + timedelta(days=1),
                scheduled_at=day + timedelta(hours=14), expires_at=day + timedelta(days=1), state="pending",
                policy_version="synthetic-pending", preference_revision=2, grant_epoch=1, course_key="hsk1",
                lesson_order=5, selected_channel="telegram"))

    async def test_renewal_refreshes_in_place_without_a_new_drain_or_cancelled_work(self):
        first = await self.admitted()
        self.q.tick += REVIEW_TTL - timedelta(days=1)
        await self.pending_job()
        self.assertEqual(await self.admission().step(4), ("reviewed",))
        row = await self.routing()
        self.assertEqual((row["state"], row["generation"]), ("telegram", 1))
        self.assertEqual(_utc(row["verified_until"]), self.q.tick + REVIEW_TTL)
        self.assertEqual(_utc(row["quiesced_at"]), _utc(first["quiesced_at"]))
        self.assertNotEqual(row["evidence_sha256"], first["evidence_sha256"])
        self.assertEqual((await self.q.rows(JOB))[0]["state"], "pending")
        self.assertEqual(await self.admission().step(4), ("current",))

    async def test_owner_change_waits_for_pending_work_then_reholds_without_a_new_drain(self):
        await self.admitted()
        async with self.q.sessions.begin() as s:
            await s.execute(update(ROUTING).values(telegram_binding="f" * 64))
        await self.pending_job()
        self.assertEqual(await self.admission().step(4), ("renewal_deferred",))
        self.assertEqual(((await self.routing())["generation"], (await self.q.rows(JOB))[0]["state"]), (1, "pending"))
        async with self.q.sessions.begin() as s:
            await s.execute(update(JOB).values(state="provider_accepted"))
        self.assertEqual(await self.admission().step(4), ("reviewed",))
        row = await self.routing()
        self.assertEqual((row["state"], row["generation"]), ("telegram", 2))
        self.assertNotEqual(row["telegram_binding"], "f" * 64)

    async def test_preference_change_is_reattested_in_place(self):
        await self.admitted()
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderPreference).values(revision=3))
        self.assertEqual(await self.admission().step(4), ("reviewed",))
        row = await self.routing()
        self.assertEqual((row["generation"], row["preference_revision"], row["state"]), (1, 3, "telegram"))

    async def test_consent_off_after_admission_is_never_reattested(self):
        await self.admitted()
        async with self.q.sessions.begin() as s:
            await s.execute(update(SmartReminderConsent).where(SmartReminderConsent.channel == "telegram")
                .values(state="off"))
        self.q.tick += REVIEW_TTL - timedelta(days=1)
        self.assertEqual(await self.admission().step(4), ("not_eligible",))
        self.assertEqual((await self.routing())["generation"], 1)
        self.assertTrue(await self.veto())  # Turning Smart off never revives the legacy sender.

    async def test_browser_zone_setup_opens_with_the_cohort_or_an_existing_hold(self):
        settings = SimpleNamespace(SMART_REMINDER_ENABLED=True)
        async def gate(user_id):
            async with self.q.sessions() as s:
                return await automatic_timezone_initialization_allowed(s, user_id, settings)
        self.assertEqual([await gate(1), await gate(3)], [False, False])
        await SmartReminderRolloutService(self.q.sessions).heartbeat()
        self.assertEqual([await gate(1), await gate(3)], [False, True])
        await self.admission().step(4)
        self.assertTrue(await gate(1))
        self.assertFalse(await automatic_timezone_initialization_allowed(None, 3, SimpleNamespace()))

    async def test_guard_refusal_is_not_a_failure_but_repeated_exceptions_pause(self):
        await open_rollout(self.q.sessions, self.q.tick)
        runtime = SmartReminderRuntime(self.q.settings, self.q.sessions, enabled=True, calibration=QA,
            history_window=timedelta(days=30), coverage_reader=self.q.service.coverage_reader,
            telegram_send=self.q.send, clock=lambda: self.q.tick)
        runtime._page = AsyncMock(return_value=[1])
        runtime._account = AsyncMock(side_effect=SmartReminderError("shadow_actor_unavailable", 401))
        for _ in range(4):
            self.assertEqual(await runtime.tick(), ())
        self.assertEqual((await self.state())["status"], "complete")
        runtime._account = AsyncMock(side_effect=RuntimeError("synthetic-private-error"))
        with self.assertLogs("app.services.smart_reminder_runtime", level="WARNING"):
            for _ in range(3):
                await runtime.tick()
        self.assertEqual(((await self.state())["status"], (await self.state())["error_code"]),
                         ("paused", "runtime_exception"))
        self.assertFalse(await self.enabled())
        self.assertEqual(await runtime.tick(), ())

    async def test_forbidden_send_marks_the_learner_blocked_and_is_never_retried(self):
        await self.admitted()
        await open_rollout(self.q.sessions, self.q.tick)
        send = AsyncMock(side_effect=TelegramForbiddenError(method=Mock(), message="Forbidden: bot was blocked by the user"))
        def runtime():
            return SmartReminderRuntime(self.q.settings, self.q.sessions, enabled=True, calibration=QA,
                history_window=timedelta(days=30), coverage_reader=self.q.service.coverage_reader,
                telegram_send=send, clock=lambda: self.q.tick, admission=True)
        await runtime().tick()
        self.q.tick = self.q.tick.replace(hour=14, minute=1)
        result, = await runtime().tick()
        self.assertEqual(result.reason, "telegram_unknown")
        await runtime().tick()
        self.assertEqual(send.await_count, 1)
        async with self.q.sessions() as s:
            self.assertIsNotNone(await s.scalar(select(User.bot_blocked_at).where(User.id == 1)))
        self.assertEqual((await self.q.rows(ATTEMPT))[0]["state"], "unknown")
        self.assertEqual((await self.state())["status"], "complete")

    async def test_concurrent_replicas_hold_and_admit_once(self):
        if not self.postgres:
            self.skipTest("Independent PostgreSQL transactions required")
        results = await asyncio.gather(self.admission().step(4), self.admission().step(4))
        self.assertEqual(sorted(sum(map(list, results), [])), ["admission_refused", "held"])
        async with self.q.sessions.begin() as s:
            await s.execute(update(ROUTING).values(held_at=self.q.tick - LEGACY_DRAIN,
                quiesced_at=self.q.tick - LEGACY_DRAIN))
        results = await asyncio.gather(self.admission().step(4), self.admission().step(4))
        self.assertIn("admitted", sum(map(list, results), []))
        row = await self.routing()
        self.assertEqual((row["state"], row["generation"]), ("telegram", 1))


class AndroidAdmissionChecks:
    """A capable Smart APK (device capability = one access token) end to end."""
    postgres = False

    async def asyncSetUp(self):
        cls = native.PostgreSQLAndroidProtocolTests if self.postgres else native.SQLiteAndroidProtocolTests
        self.q = cls(methodName="test_due_is_non_persisting_and_claim_commits_once_before_response")
        await self.q.asyncSetUp()
        self.q.tick = self.q.tick.replace(second=0, microsecond=0)
        self.day_end = day_window("Etc/UTC", self.q.tick.date().isoformat())[1]
        if self.day_end - self.q.tick < timedelta(hours=1):
            self.skipTest("Fixture day ends within the synthetic capability window")
        async with self.q.sessions.begin() as s:
            await s.execute(delete(JOB))
            await s.execute(delete(ROUTING))
            await self.capability(s)

    async def asyncTearDown(self):
        await self.q.asyncTearDown()

    async def capability(self, s):
        await s.execute(update(SmartReminderCapability).values(observed_at=self.q.tick - timedelta(seconds=1),
            expires_at=self.q.tick + timedelta(minutes=15), generation=SmartReminderCapability.generation + 1))

    def admission(self):
        return SmartReminderAdmissionService(self.q.sessions, clock=lambda: self.q.tick, android_ready=True)

    async def native_admission(self, job_id):
        actor = SmartReminderActor(1, "android", device_id="device-1", session_id="session-1")
        async with self.q.sessions.begin() as s:
            return await read_android_admission(s, actor, job_id, self.q.tick, history_window=timedelta(days=30))

    async def test_capable_device_is_admitted_and_refreshed_in_place_for_the_native_path(self):
        self.assertEqual(await self.admission().step(4), ("held",))
        async with self.q.sessions.begin() as s:
            await s.execute(update(ROUTING).values(held_at=self.q.tick - LEGACY_DRAIN,
                quiesced_at=self.q.tick - LEGACY_DRAIN))
        self.assertEqual(await self.admission().step(4), ("admitted",))
        row = dict((await self.q.rows(ROUTING))[0])
        self.assertEqual((row["state"], row["generation"]), ("held", 1))
        self.assertEqual(_utc(row["verified_until"]), self.q.tick + timedelta(minutes=15))
        job_id = str(uuid4())
        start = day_window("Etc/UTC", self.q.tick.date().isoformat())[0]
        async with self.q.sessions.begin() as s:
            await s.execute(insert(JOB).values(id=job_id, user_id=1, local_day=self.q.tick.date(),
                timezone_name="Etc/UTC", day_start_utc=start, day_end_utc=self.day_end,
                scheduled_at=self.q.tick + timedelta(minutes=20), expires_at=self.q.tick + timedelta(minutes=40),
                state="pending", policy_version=self.q.service(s).policy_version, preference_revision=2,
                grant_epoch=1, course_key="hsk1", lesson_order=5, selected_channel="android",
                selected_device_id="device-1"))
        self.assertIsNotNone(await self.native_admission(job_id))
        self.q.tick += timedelta(minutes=10)
        async with self.q.sessions.begin() as s:
            await self.capability(s)  # The phone's next capability report.
        self.assertIsNotNone(await self.native_admission(job_id))  # A routine report is not drift.
        self.assertEqual(await self.admission().step(4), ("reviewed",))
        refreshed = dict((await self.q.rows(ROUTING))[0])
        self.assertEqual((refreshed["state"], refreshed["generation"]), ("held", 1))
        self.assertEqual(_utc(refreshed["verified_until"]), self.q.tick + timedelta(minutes=15))
        self.assertEqual((await self.q.rows(JOB))[0]["state"], "pending")
        self.assertIsNotNone(await self.native_admission(job_id))
        self.assertEqual(await self.admission().step(4), ("current",))

    async def test_second_device_without_the_smart_capability_excludes_the_account(self):
        async with self.q.sessions.begin() as s:
            s.add(DesktopDevice(id="old-apk", user_id=1, platform="android", app_version="1.7.21",
                installation_key_hash="old-apk-fixture"))
        self.assertEqual(await self.admission().step(4), ("not_eligible",))
        self.assertEqual(await self.q.rows(ROUTING), [])


class SQLiteAndroidAdmissionTests(AndroidAdmissionChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL, "Disposable loopback PostgreSQL required")
class PostgreSQLAndroidAdmissionTests(AndroidAdmissionChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class SQLiteRolloutTests(RolloutChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL, "Disposable loopback PostgreSQL required")
class PostgreSQLRolloutTests(RolloutChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


class SQLiteAdmissionTests(AdmissionChecks, unittest.IsolatedAsyncioTestCase):
    pass


@unittest.skipUnless(PG_URL, "Disposable loopback PostgreSQL required")
class PostgreSQLAdmissionTests(AdmissionChecks, unittest.IsolatedAsyncioTestCase):
    postgres = True


if __name__ == "__main__":
    unittest.main()
