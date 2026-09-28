"""Server-side realtime Android push triggers.

The server only wakes the device. Android still verifies release/course/account
state before showing a notification, and WorkManager remains the fallback.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from app.config import settings
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.android_push_service import AndroidPushService, AndroidPushTarget
from app.services.android_release_service import AndroidReleaseService


logger = logging.getLogger(__name__)
LAST_UPDATE_PUSH_VERSION_KEY = "android_last_update_push_version"
STUDY_PUSH_HOUR = 20
STUDY_PUSH_TTL_SECONDS = 2 * 60 * 60


class AndroidRealtimePushService:
    def __init__(self, session, settings_obj=settings):
        self.session = session
        self.settings = settings_obj
        self.push = AndroidPushService(session, settings_obj)

    async def send_release_if_needed(self) -> int:
        if not bool(getattr(self.settings, "ANDROID_PUSH_UPDATES_ENABLED", False)):
            return 0
        if not self.push.configured:
            return 0

        release = await AndroidReleaseService(self.session).serve()
        if (
            release is None
            or release.version_code is None
            or not release.can_self_update
        ):
            return 0

        repo = BotSettingRepository(self.session)
        raw = await repo.get(LAST_UPDATE_PUSH_VERSION_KEY)
        try:
            last_version = int(raw or 0)
        except (TypeError, ValueError):
            last_version = 0
        if release.version_code <= last_version:
            return 0

        rows = (
            await self.session.execute(
                select(AndroidPushToken.token, AndroidPushToken.device_id)
                .join(DesktopDevice, AndroidPushToken.device_id == DesktopDevice.id)
                .where(
                    DesktopDevice.platform == "android",
                    DesktopDevice.revoked_at.is_(None),
                )
            )
        ).all()
        if not rows:
            return 0

        targets = [
            AndroidPushTarget(
                token=token,
                device_id=device_id,
                data={
                    "kind": "app_update",
                    "version_code": release.version_code,
                },
            )
            for token, device_id in rows
        ]
        results = await self.push.send_batch(targets, ttl_seconds=86400)
        accepted = sum(1 for result in results if result.accepted)
        transient_failure = any(
            not result.accepted and not result.stale_token
            for result in results
        )

        # Client-side UpdateNotices has its own per-version dedupe, so retrying
        # after a partial transport failure cannot show duplicate notices.
        if not transient_failure:
            await repo.set(LAST_UPDATE_PUSH_VERSION_KEY, str(release.version_code))
            await self.session.commit()
        return accepted

    async def send_due_study(self, now: datetime | None = None) -> int:
        if not bool(getattr(self.settings, "ANDROID_PUSH_STUDY_ENABLED", False)):
            return 0
        if not self.push.configured:
            return 0

        now_utc = now or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        else:
            now_utc = now_utc.astimezone(timezone.utc)

        rows = (
            await self.session.execute(
                select(AndroidPushToken, DesktopDevice)
                .join(DesktopDevice, AndroidPushToken.device_id == DesktopDevice.id)
                .where(
                    AndroidPushToken.study_reminders_enabled.is_(True),
                    AndroidPushToken.timezone_name.is_not(None),
                    DesktopDevice.platform == "android",
                    DesktopDevice.revoked_at.is_(None),
                )
            )
        ).all()

        due_rows = []
        targets = []
        for row, device in rows:
            try:
                local_now = now_utc.astimezone(ZoneInfo(row.timezone_name or ""))
            except (ZoneInfoNotFoundError, ValueError):
                continue
            if local_now.hour != STUDY_PUSH_HOUR:
                continue
            local_day = local_now.date().isoformat()
            if row.last_study_push_day == local_day:
                continue
            due_rows.append((row, local_day))
            targets.append(
                AndroidPushTarget(
                    token=row.token,
                    device_id=device.id,
                    data={
                        "kind": "study_reminder",
                        "local_day": local_day,
                    },
                )
            )

        results = await self.push.send_batch(
            targets,
            ttl_seconds=STUDY_PUSH_TTL_SECONDS,
        )

        accepted = 0
        dirty = False
        for (row, local_day), result in zip(due_rows, results):
            if not result.accepted:
                continue
            row.last_study_push_day = local_day
            row.updated_at = now_utc
            dirty = True
            accepted += 1

        if dirty:
            await self.session.commit()
        return accepted
