"""Independent bounded shadow-only worker; disabled means zero Smart SQL.

Processes existing reservations only. No producer, provider or body/endpoint
logging. Technical intervals are not product cadence/coordination calibration.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import select

from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.user import User
from app.services.smart_reminder_preferences import SmartReminderActor, SmartReminderError, _utc
from app.services.smart_reminder_shadow_queue import SmartReminderShadowQueue


logger = logging.getLogger(__name__)


class SmartReminderShadowWorker:
    def __init__(self, settings, sessions, *, clock=None, interval=60, timeout=30, batch=16):
        if interval <= 0 or timeout <= 0 or type(batch) is not int or not 1 <= batch <= 128:
            raise ValueError("Positive bounded technical worker settings required")
        self.settings, self.sessions = settings, sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.queue = SmartReminderShadowQueue(sessions, clock=self.clock)
        self.interval, self.timeout, self.batch = interval, timeout, batch

    async def actor_for(self, user_id):
        # Trusted server actor metadata only. P1 rechecks current ownership,
        # status/deletion/session/device on each claim and finish under User.
        async with self.sessions() as session:
            account = (await session.execute(select(User.telegram_id, User.bot_blocked_at).where(
                User.id == user_id))).mappings().one_or_none()
            if account is None:
                raise SmartReminderError("smart_account_not_found", 404)
            row = (await session.execute(select(DesktopDevice.id, DesktopSession.id.label("session_id")).join(
                DesktopSession, DesktopSession.device_id == DesktopDevice.id).where(
                    DesktopDevice.user_id == user_id, DesktopDevice.platform == "android",
                    DesktopDevice.revoked_at.is_(None), DesktopSession.revoked_at.is_(None),
                    DesktopSession.expires_at > self.clock(),
                ).order_by(DesktopSession.expires_at.desc(), DesktopSession.id).limit(1))).mappings().one_or_none()
            if row is not None:
                # A native actor can observe its own study permission as well
                # as linked Telegram state. This is not D06 endpoint selection.
                return SmartReminderActor(user_id, "android", device_id=row["id"], session_id=row["session_id"])
            if account["telegram_id"] and account["telegram_id"] > 0 and account["bot_blocked_at"] is None:
                return SmartReminderActor(user_id, "telegram_bot", telegram_id=account["telegram_id"])
            raise SmartReminderError("shadow_actor_unavailable", 401)

    async def tick(self):
        if not getattr(self.settings, "SMART_REMINDER_SHADOW_ENABLED", False):
            return ()
        # A UTC-midnight weekly read window includes current-day facts across
        # IANA offsets/DST. This is bounded work, not a confidence/retention or
        # inactivity threshold; legacy negative learning coverage stays unknown.
        since = _utc(self.clock()).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
        return await asyncio.wait_for(self.queue.drain(
            self.actor_for, history_since=since, lease_for=timedelta(seconds=self.timeout), limit=self.batch,
        ), timeout=self.timeout)

    async def run(self):
        while getattr(self.settings, "SMART_REMINDER_SHADOW_ENABLED", False):
            try:
                results = await self.tick()
                if results:
                    logger.info("Smart shadow results: %d (dispatch disabled)", len(results))
            except asyncio.TimeoutError:
                logger.warning("Smart shadow tick timed out (dispatch disabled)")
            except Exception:
                logger.warning("Smart shadow tick failed (dispatch disabled)")
            await asyncio.sleep(self.interval)
