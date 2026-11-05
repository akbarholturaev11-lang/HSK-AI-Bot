import base64
from datetime import timedelta
import hashlib
import json
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select, update

from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.learner_pwa_push import LearnerPwaPushOutbox, LearnerPwaPushSubscription
from app.db.models.smart_reminder import SmartReminderAttempt, SmartReminderConsent, SmartReminderJob, SmartReminderPreference
from app.services.smart_reminder_pwa import SmartReminderPwaService
from app.services.smart_reminder_preferences import SmartReminderActor
from app.services.smart_reminder_shadow_queue import ATTEMPT, JOB
from tests import test_smart_reminder_android as fixtures


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class SmartReminderPwaDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        case_cls = fixtures.SQLiteAndroidProtocolTests
        self.case = case_cls(methodName="test_due_is_non_persisting_and_claim_commits_once_before_response")
        await self.case.asyncSetUp()
        self.tick = self.case.tick
        self.actor = SmartReminderActor(1, "android", device_id="device-1", session_id="session-1")
        self.job_id = self.case.job_id
        self.device_id = "pwa-device"
        self.subscription_id = str(uuid4())
        self.fernet = Fernet(Fernet.generate_key())
        key = ec.generate_private_key(ec.SECP256R1())
        public = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        raw = {"endpoint": "https://web.push.apple.com/device/synthetic",
            "keys": {"p256dh": _b64(public), "auth": _b64(b"a" * 16)}}
        self.endpoint_hash = hashlib.sha256(raw["endpoint"].encode("utf-8")).hexdigest()
        self.sealed = self.fernet.encrypt(json.dumps(raw).encode("ascii")).decode("ascii")
        async with self.case.sessions.begin() as session:
            session.add(DesktopDevice(id=self.device_id, user_id=1, platform="pwa",
                installation_key_hash="p" * 64, app_version="synthetic", last_seen_at=self.tick))
            await session.flush()
            await session.execute(update(JOB).where(JOB.c.id == self.job_id).values(
                state="pending", policy_version="smart-pwa-v1", selected_channel="pwa",
                selected_device_id=self.device_id, lease_token=None, lease_expires_at=None))
            session.add(DesktopSession(id="pwa-session", device_id=self.device_id,
                refresh_token_hash="r" * 64, expires_at=self.tick + timedelta(days=1)))
            session.add(LearnerPwaPushSubscription(id=self.subscription_id, device_id=self.device_id,
                endpoint_hash=self.endpoint_hash, encrypted_payload=self.sealed,
                created_at=self.tick, updated_at=self.tick))

        class Queue:
            async def _fresh(_self, session, actor, row, now, history_since):
                return type("Context", (), {"permitted_channels": ("pwa",), "channel_mode": "auto"})(), None

        class AndroidGate:
            async def _legacy_contact(_self, actor, row):
                return None

        self.planner = type("Planner", (), {
            "queue": Queue(), "_reviewed": AsyncMock(return_value=None),
            "_android": lambda _self, session: AndroidGate(),
        })()
        self.settings = object()

    async def asyncTearDown(self):
        await self.case.asyncTearDown()

    def service(self, sender):
        return SmartReminderPwaService(self.settings, self.case.sessions,
            clock=lambda: self.tick, sender=sender)

    async def _dispatch(self, sender):
        with patch("app.services.smart_reminder_pwa.sender_config",
                   return_value=("private-key-test", "mailto:test@example.com", self.fernet)), \
             patch("app.services.smart_reminder_pwa.NotificationTemplateService.is_enabled",
                   new=AsyncMock(return_value=True)):
            return await self.service(sender).dispatch(self.planner, self.actor, self.job_id,
                self.device_id, history_since=self.tick - timedelta(days=30))

    async def test_provider_201_records_one_pwa_attempt_without_mirroring(self):
        sender = AsyncMock(return_value=201)
        result = await self._dispatch(sender)
        self.assertEqual((result.reason, result.state), ("pwa_provider_accepted", "provider_accepted"))
        sender.assert_awaited_once()
        args = sender.await_args.args
        payload = json.loads(args[1])
        self.assertEqual(payload["url"], "/iphone-pwa/course?notice=1")
        self.assertNotIn("lesson", payload["body"].lower())
        async with self.case.sessions() as session:
            attempt = (await session.scalars(select(SmartReminderAttempt).where(
                SmartReminderAttempt.job_id == self.job_id))).one()
            job = await session.get(SmartReminderJob, self.job_id)
            notices = (await session.scalars(select(CourseUserNotification).where(
                CourseUserNotification.dedupe_key == "job:" + self.job_id))).all()
            outbox = (await session.scalars(select(LearnerPwaPushOutbox).where(
                LearnerPwaPushOutbox.source == "course"))).all()
        self.assertEqual((attempt.channel, attempt.device_id, attempt.state),
            ("pwa", self.device_id, "provider_accepted"))
        self.assertEqual((job.state, job.selected_channel), ("provider_accepted", "pwa"))
        self.assertEqual([notice.source for notice in notices], ["smart_pwa"])
        self.assertEqual(outbox, [])

    async def test_job_is_not_sent_before_its_scheduled_time(self):
        # Regression: planning used to dispatch a PWA reminder immediately.
        async with self.case.sessions.begin() as session:
            await session.execute(update(JOB).where(JOB.c.id == self.job_id).values(
                scheduled_at=self.tick + timedelta(hours=2),
                expires_at=self.tick + timedelta(hours=6)))
        sender = AsyncMock(return_value=201)
        result = await self._dispatch(sender)
        self.assertEqual(result.reason, "pwa_job_not_due")
        sender.assert_not_awaited()
        async with self.case.sessions() as session:
            job = await session.get(SmartReminderJob, self.job_id)
            attempts = (await session.scalars(select(SmartReminderAttempt).where(
                SmartReminderAttempt.job_id == self.job_id))).all()
        self.assertEqual((job.state, attempts), ("pending", []))

    async def test_unknown_provider_result_is_terminal_and_never_replayed(self):
        sender = AsyncMock(side_effect=TimeoutError("provider reply lost"))
        result = await self._dispatch(sender)
        self.assertEqual((result.reason, result.state), ("pwa_unknown", "unknown"))
        retry = await self._dispatch(sender)
        self.assertEqual(retry.reason, "pwa_attempt_already_exists")
        sender.assert_awaited_once()
        async with self.case.sessions() as session:
            attempt = (await session.scalars(select(SmartReminderAttempt).where(
                SmartReminderAttempt.job_id == self.job_id))).one()
            job = await session.get(SmartReminderJob, self.job_id)
        self.assertEqual((attempt.state, job.state), ("unknown", "unknown"))

    async def test_expired_in_flight_attempt_becomes_unknown_instead_of_replaying(self):
        async with self.case.sessions.begin() as session:
            session.add(SmartReminderAttempt(id=str(uuid4()), job_id=self.job_id,
                attempt_key=hashlib.sha256((self.job_id + ":pwa:first").encode()).hexdigest(),
                channel="pwa", device_id=self.device_id, grant_epoch=1, state="in_flight",
                prepared_at=self.tick-timedelta(minutes=2), started_at=self.tick-timedelta(minutes=2),
                expires_at=self.tick-timedelta(minutes=1), reason_code="started"))
            await session.execute(update(JOB).where(JOB.c.id == self.job_id).values(
                state="claimed", lease_token="expired-lease", lease_expires_at=self.tick-timedelta(minutes=1)))
        sender = AsyncMock(return_value=201)
        result = await self._dispatch(sender)
        self.assertEqual((result.reason, result.state), ("pwa_outcome_unknown", "unknown"))
        sender.assert_not_awaited()

    async def test_non_2xx_is_not_retried_or_fallen_back(self):
        sender = AsyncMock(return_value=503)
        result = await self._dispatch(sender)
        self.assertEqual((result.reason, result.state), ("pwa_unknown", "unknown"))
        sender.assert_awaited_once()

    async def test_off_unknown_and_manual_lock_are_rechecked_before_provider(self):
        sender = AsyncMock(return_value=201)
        # No explicit Smart choice is refused only without existing study
        # consent; with Telegram study consent the PWA may carry the reminder.
        preferences = (
            ({"master_enabled": False, "channel_mode": "auto", "preferred_channel": None}, "on"),
            ({"master_enabled": None, "channel_mode": "auto", "preferred_channel": None}, "off"),
            ({"master_enabled": True, "channel_mode": "manual_locked", "preferred_channel": "android"}, "on"),
        )
        for values, telegram in preferences:
            async with self.case.sessions.begin() as session:
                await session.execute(update(SmartReminderPreference).where(
                    SmartReminderPreference.user_id == 1).values(**values))
                await session.execute(update(SmartReminderConsent).where(
                    SmartReminderConsent.user_id == 1, SmartReminderConsent.channel == "telegram").values(state=telegram))
                await session.execute(update(JOB).where(JOB.c.id == self.job_id).values(
                    state="pending", reason_code=None, lease_token=None, lease_expires_at=None,
                    selected_channel="pwa", selected_device_id=self.device_id))
            result = await self._dispatch(sender)
            self.assertEqual((result.reason, result.state), ("pwa_preference_changed", "cancelled"))
        sender.assert_not_awaited()
        async with self.case.sessions() as session:
            job = await session.get(SmartReminderJob, self.job_id)
            attempts = (await session.scalars(select(SmartReminderAttempt).where(
                SmartReminderAttempt.job_id == self.job_id))).all()
        self.assertEqual(job.state, "cancelled")
        self.assertEqual(attempts, [])

    async def test_expired_pwa_session_cancels_before_provider(self):
        async with self.case.sessions.begin() as session:
            await session.execute(update(DesktopSession).where(
                DesktopSession.id == "pwa-session").values(expires_at=self.tick))
        sender = AsyncMock(return_value=201)
        result = await self._dispatch(sender)
        self.assertEqual((result.reason, result.state), ("pwa_capability_unavailable", "cancelled"))
        sender.assert_not_awaited()
        async with self.case.sessions() as session:
            job = await session.get(SmartReminderJob, self.job_id)
            attempts = (await session.scalars(select(SmartReminderAttempt).where(
                SmartReminderAttempt.job_id == self.job_id))).all()
        self.assertEqual(job.state, "cancelled")
        self.assertEqual(attempts, [])


if __name__ == "__main__":
    unittest.main()
