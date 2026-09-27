from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.desktop import DesktopDevice
from app.db.models.user_client_presence import UserClientPresence
from app.repositories.user_repo import UserRepository


MINIAPP_SURFACE = "telegram_miniapp"
NATIVE_PLATFORMS = frozenset({"android", "macos", "windows"})
CLIENT_PLATFORMS = frozenset({"android", "ios", "macos", "windows", "web", "unknown"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized else ""


def normalize_client_platform(value: Any) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "android": "android",
        "ios": "ios",
        "iphone": "ios",
        "ipad": "ios",
        "mac": "macos",
        "macos": "macos",
        "darwin": "macos",
        "windows": "windows",
        "win32": "windows",
        "win64": "windows",
        "web": "web",
        "weba": "web",
        "webk": "web",
        "unknown": "unknown",
        "": "unknown",
    }
    return aliases.get(raw, "unknown")


class UserDeviceInventoryService:
    """Unifies Mini App presence with the existing authoritative native registry."""

    def __init__(self, session):
        self.session = session

    async def record_miniapp_presence(
        self,
        *,
        telegram_id: int,
        platform: str,
        source: str = "course_miniapp",
        app_version: str | None = None,
        foreground: bool = True,
    ) -> UserClientPresence | None:
        user = await UserRepository(self.session).get_by_telegram_id(int(telegram_id))
        if not user:
            return None

        normalized = normalize_client_platform(platform)
        now = _utcnow()
        result = await self.session.execute(
            select(UserClientPresence).where(
                UserClientPresence.user_id == user.id,
                UserClientPresence.surface == MINIAPP_SURFACE,
                UserClientPresence.platform == normalized,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            item = UserClientPresence(
                user_id=user.id,
                telegram_id=user.telegram_id,
                surface=MINIAPP_SURFACE,
                platform=normalized,
                app_version=(str(app_version).strip()[:40] if app_version else None),
                source=str(source or "course_miniapp").strip()[:40] or None,
                first_seen_at=now,
                last_seen_at=now,
                last_foreground_at=now,
                updated_at=now,
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(item)
                    await self.session.flush()
                return item
            except IntegrityError:
                result = await self.session.execute(
                    select(UserClientPresence).where(
                        UserClientPresence.user_id == user.id,
                        UserClientPresence.surface == MINIAPP_SURFACE,
                        UserClientPresence.platform == normalized,
                    )
                )
                item = result.scalar_one_or_none()
                if item is None:
                    raise

        item.telegram_id = user.telegram_id
        item.last_seen_at = now
        if foreground:
            item.last_foreground_at = now
        if app_version:
            item.app_version = str(app_version).strip()[:40] or item.app_version
        if source:
            item.source = str(source).strip()[:40] or item.source
        item.updated_at = now
        await self.session.flush()
        return item

    async def installed_native_platforms(self, telegram_id: int) -> set[str]:
        rows = (
            await self.session.execute(
                select(DesktopDevice.platform).where(
                    DesktopDevice.telegram_id == int(telegram_id),
                    DesktopDevice.revoked_at.is_(None),
                )
            )
        ).scalars().all()
        return {
            str(platform)
            for platform in rows
            if str(platform) in NATIVE_PLATFORMS
        }

    @staticmethod
    def _payload(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def snapshot(self, telegram_id: int) -> dict[str, Any]:
        telegram_id = int(telegram_id)
        presence_rows = list(
            (
                await self.session.execute(
                    select(UserClientPresence)
                    .where(UserClientPresence.telegram_id == telegram_id)
                    .order_by(UserClientPresence.last_foreground_at.desc())
                )
            ).scalars().all()
        )
        device_rows = list(
            (
                await self.session.execute(
                    select(DesktopDevice)
                    .where(DesktopDevice.telegram_id == telegram_id)
                    .order_by(DesktopDevice.created_at.asc())
                )
            ).scalars().all()
        )

        latest_native_rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.payload_json,
                    CourseMiniAppEvent.created_at,
                )
                .where(
                    CourseMiniAppEvent.telegram_id == telegram_id,
                    CourseMiniAppEvent.event_name.in_(
                        ("android_app_opened", "desktop_app_opened")
                    ),
                )
                .order_by(CourseMiniAppEvent.created_at.desc())
                .limit(100)
            )
        ).all()

        native_opened: dict[str, datetime] = {}
        for event_name, payload_json, created_at in latest_native_rows:
            payload = self._payload(payload_json)
            platform = normalize_client_platform(payload.get("platform"))
            if event_name == "android_app_opened":
                platform = "android"
            if platform in NATIVE_PLATFORMS and platform not in native_opened:
                native_opened[platform] = created_at

        presences = [
            {
                "surface": row.surface,
                "platform": row.platform,
                "app_version": row.app_version or "",
                "source": row.source or "",
                "first_seen_at": _iso(row.first_seen_at),
                "last_seen_at": _iso(row.last_seen_at),
                "last_foreground_at": _iso(row.last_foreground_at),
            }
            for row in presence_rows
        ]

        native_devices = []
        for row in device_rows:
            platform = str(row.platform or "")
            if platform not in NATIVE_PLATFORMS:
                continue
            native_devices.append(
                {
                    "platform": platform,
                    "app_version": row.app_version or "",
                    "installed": row.revoked_at is None,
                    "first_open_at": _iso(row.first_open_at),
                    "last_contact_at": _iso(row.last_seen_at),
                    "last_foreground_at": _iso(native_opened.get(platform)),
                    "revoked_at": _iso(row.revoked_at),
                    "created_at": _iso(row.created_at),
                }
            )

        candidates: list[tuple[datetime, str, str]] = []
        for row in presence_rows:
            at = _as_utc(row.last_foreground_at)
            if at:
                candidates.append((at, row.surface, row.platform))
        for platform, at_raw in native_opened.items():
            at = _as_utc(at_raw)
            if at:
                candidates.append((at, "native", platform))
        candidates.sort(key=lambda item: item[0], reverse=True)

        installed = sorted(
            {
                item["platform"]
                for item in native_devices
                if item["installed"]
            }
        )
        return {
            "presences": presences,
            "native_devices": native_devices,
            "installed_native_platforms": installed,
            "primary": (
                {
                    "surface": candidates[0][1],
                    "platform": candidates[0][2],
                    "last_foreground_at": candidates[0][0].isoformat(),
                }
                if candidates
                else None
            ),
        }

    async def aggregate(self) -> dict[str, Any]:
        presence_rows = (
            await self.session.execute(
                select(
                    UserClientPresence.user_id,
                    UserClientPresence.platform,
                    UserClientPresence.first_seen_at,
                ).where(UserClientPresence.surface == MINIAPP_SURFACE)
            )
        ).all()
        native_rows = (
            await self.session.execute(
                select(
                    DesktopDevice.user_id,
                    DesktopDevice.platform,
                    DesktopDevice.id,
                ).where(
                    DesktopDevice.revoked_at.is_(None),
                    DesktopDevice.platform.in_(tuple(NATIVE_PLATFORMS)),
                )
            )
        ).all()

        miniapp_by_platform: dict[str, set[int]] = {}
        presence_users: set[int] = set()
        tracking_started_at: datetime | None = None
        for user_id, platform, first_seen_at in presence_rows:
            uid = int(user_id)
            presence_users.add(uid)
            key = str(platform or "unknown")
            miniapp_by_platform.setdefault(key, set()).add(uid)
            seen = _as_utc(first_seen_at)
            if seen and (tracking_started_at is None or seen < tracking_started_at):
                tracking_started_at = seen

        native_by_platform_users: dict[str, set[int]] = {}
        native_by_platform_devices: dict[str, int] = {}
        native_platforms_by_user: dict[int, set[str]] = {}
        native_users: set[int] = set()
        for user_id, platform, _device_id in native_rows:
            key = str(platform or "")
            if key not in NATIVE_PLATFORMS:
                continue
            uid = int(user_id)
            native_users.add(uid)
            native_by_platform_users.setdefault(key, set()).add(uid)
            native_by_platform_devices[key] = native_by_platform_devices.get(key, 0) + 1
            native_platforms_by_user.setdefault(uid, set()).add(key)

        both = presence_users & native_users
        miniapp_only = presence_users - native_users
        native_only = native_users - presence_users
        multi_native = {
            uid for uid, platforms in native_platforms_by_user.items()
            if len(platforms) > 1
        }
        conversion = (
            round(len(both) / len(presence_users) * 100, 1)
            if presence_users
            else 0.0
        )

        return {
            "tracking_started_at": _iso(tracking_started_at),
            "miniapp_users_total": len(presence_users),
            "miniapp_users_by_platform": {
                platform: len(users)
                for platform, users in sorted(miniapp_by_platform.items())
            },
            "native_users_total": len(native_users),
            "native_by_platform": {
                platform: {
                    "users": len(native_by_platform_users.get(platform, set())),
                    "devices": int(native_by_platform_devices.get(platform, 0)),
                }
                for platform in sorted(NATIVE_PLATFORMS)
            },
            "miniapp_only_users": len(miniapp_only),
            "native_only_users": len(native_only),
            "miniapp_and_native_users": len(both),
            "multi_native_platform_users": len(multi_native),
            "miniapp_to_native_pct": conversion,
        }

