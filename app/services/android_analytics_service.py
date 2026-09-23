"""Read-only Android client statistics for the admin Mini App.

Two sources are read, and they are deliberately kept apart because they
answer different questions:

* ``desktop_devices`` rows on a mobile platform are the install registry.
  One row is one phone that installed the APK and linked an account — the
  only record that can say how many installs exist without estimating.
* ``course_miniapp_events`` carries the distribution funnel (the APK is
  handed out from the bot chat, so ``android_apk_requested``/``_sent`` are
  the only measurement of it) and ``android_app_opened``, which the server
  writes once per device per day when the app itself starts.

Active users are counted from ``android_app_opened`` and never from
``desktop_devices.last_seen_at``: the home-screen widget refreshes in the
background and touches the session, so ``last_seen_at`` proves the phone is
online, not that anybody opened the app. Both are reported, each under its
own name, instead of merging them into one flattering number.

Nothing here is estimated or back-filled. A number that cannot be read from
one of those two tables is not shown at all.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy import func, select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.desktop import DesktopDevice
from app.services.desktop_auth_service import MOBILE_PLATFORMS
from app.services.desktop_semver import parse_desktop_semver


ANDROID_PLATFORMS = tuple(sorted(MOBILE_PLATFORMS))

# The APK funnel, in the order a phone actually walks it. Every stage is a
# server-written event; none of them is inferred from another.
ANDROID_FUNNEL_STAGES = (
    ("apk_requested", "android_apk_requested"),
    ("apk_sent", "android_apk_sent"),
    ("session_linked", "android_session_linked"),
    ("first_open", "android_first_open"),
)

ANDROID_OPEN_EVENT = "android_app_opened"
ANDROID_UPDATE_EVENT = "android_update_installed"

ANDROID_TOTAL_EVENTS = tuple(name for _, name in ANDROID_FUNNEL_STAGES) + (
    ANDROID_UPDATE_EVENT,
)

# Rolling windows for "is anybody using it". Days, counted back from now.
ANDROID_ACTIVE_WINDOWS = (("dau", 1), ("wau", 7), ("mau", 30))
ANDROID_ACTIVE_WINDOW_DAYS = 30


class AndroidAnalyticsService:
    """Android product analytics over the device registry and the event log.

    Reading contract:
    - ``desktop_devices.platform`` is ``android`` for every row counted here.
    - ``android_app_opened`` is deduped per device per day by the auth
      service, so one row is one device-day and needs no de-duplication.
    - ``payload.device_id`` on the lifecycle events is the server device id,
      never a hardware identifier.
    """

    EVENT_NAMES = ANDROID_TOTAL_EVENTS + (ANDROID_OPEN_EVENT,)

    def __init__(self, session):
        self.session = session

    # ---------- helpers ----------

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _payload(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _pct(part: int, total: int) -> float:
        return round(part / total * 100, 1) if total > 0 else 0.0

    @staticmethod
    def _version(value: Any) -> str:
        return str(value or "").strip()

    # ---------- fetching ----------

    async def _event_totals(
        self, *, since: datetime | None
    ) -> dict[str, dict[str, int]]:
        conditions = [CourseMiniAppEvent.event_name.in_(ANDROID_TOTAL_EVENTS)]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    func.count(func.distinct(CourseMiniAppEvent.telegram_id)),
                    func.count(),
                )
                .where(*conditions)
                .group_by(CourseMiniAppEvent.event_name)
            )
        ).fetchall()
        return {
            str(name): {"users": int(users or 0), "events": int(events or 0)}
            for name, users, events in rows
        }

    async def _open_rows(self, *, since: datetime) -> list[Any]:
        return list(
            (
                await self.session.execute(
                    select(
                        CourseMiniAppEvent.created_at,
                        CourseMiniAppEvent.telegram_id,
                        CourseMiniAppEvent.payload_json,
                    ).where(
                        CourseMiniAppEvent.event_name == ANDROID_OPEN_EVENT,
                        CourseMiniAppEvent.created_at >= since,
                    )
                )
            ).fetchall()
        )

    async def _device_rows(self) -> list[Any]:
        """Every Android device row.

        One row per installed-and-linked phone, so this stays small: it is
        bounded by the number of installs, not by activity.
        """

        return list(
            (
                await self.session.execute(
                    select(
                        DesktopDevice.id,
                        DesktopDevice.user_id,
                        DesktopDevice.app_version,
                        DesktopDevice.first_open_at,
                        DesktopDevice.last_seen_at,
                        DesktopDevice.revoked_at,
                        DesktopDevice.created_at,
                    ).where(DesktopDevice.platform.in_(ANDROID_PLATFORMS))
                )
            ).fetchall()
        )

    # ---------- building ----------

    @classmethod
    def _funnel(cls, totals: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, int]]:
        funnel: dict[str, dict[str, int]] = {}
        for key, event_name in ANDROID_FUNNEL_STAGES:
            counts = totals.get(event_name) or {}
            funnel[key] = {
                "users": int(counts.get("users", 0) or 0),
                "events": int(counts.get("events", 0) or 0),
            }
        return funnel

    @classmethod
    def _registry(
        cls,
        *,
        device_rows: Iterable[Any],
        now: datetime,
        since: datetime | None,
    ) -> dict[str, Any]:
        """Counts straight off the device table — installs, not estimates."""

        installed = 0
        opened = 0
        never_opened = 0
        unlinked = 0
        new_in_period = 0
        installed_users: set[int] = set()
        opened_users: set[int] = set()
        new_users: set[int] = set()
        online: dict[str, set[str]] = {key: set() for key, _ in ANDROID_ACTIVE_WINDOWS}
        online_users: dict[str, set[int]] = {
            key: set() for key, _ in ANDROID_ACTIVE_WINDOWS
        }

        for row in device_rows:
            device_id = str(getattr(row, "id", "") or "").strip()
            user_id = int(getattr(row, "user_id", 0) or 0)
            revoked_at = cls._as_utc(getattr(row, "revoked_at", None))
            first_open_at = cls._as_utc(getattr(row, "first_open_at", None))
            last_seen_at = cls._as_utc(getattr(row, "last_seen_at", None))
            created_at = cls._as_utc(getattr(row, "created_at", None))

            if revoked_at is not None:
                unlinked += 1
                continue

            installed += 1
            if user_id:
                installed_users.add(user_id)
            if first_open_at is not None:
                opened += 1
                if user_id:
                    opened_users.add(user_id)
            else:
                never_opened += 1
            if since is not None and created_at is not None and created_at >= since:
                new_in_period += 1
                if user_id:
                    new_users.add(user_id)
            if last_seen_at is not None:
                for key, days in ANDROID_ACTIVE_WINDOWS:
                    if last_seen_at >= now - timedelta(days=days):
                        if device_id:
                            online[key].add(device_id)
                        if user_id:
                            online_users[key].add(user_id)

        registry = {
            "installed_devices": installed,
            "installed_users": len(installed_users),
            "opened_devices": opened,
            "opened_users": len(opened_users),
            "never_opened_devices": never_opened,
            "unlinked_devices": unlinked,
            # All-time periods have no "new in period" — the whole table is.
            "new_devices_in_period": new_in_period if since is not None else installed,
            "new_users_in_period": len(new_users) if since is not None else len(installed_users),
            "period_bounded": since is not None,
        }
        for key, days in ANDROID_ACTIVE_WINDOWS:
            registry[f"online_devices_{days}d"] = len(online[key])
            registry[f"online_users_{days}d"] = len(online_users[key])
        return registry

    @classmethod
    def _active(
        cls,
        *,
        open_rows: Iterable[Any],
        now: datetime,
        current_device_ids: set[str],
    ) -> dict[str, Any]:
        """Real opens from devices that are still linked.

        Historical open events from revoked/unlinked phones are ignored so
        DAU/WAU/MAU cannot be larger than the current install registry.
        """

        users: dict[str, set[int]] = {key: set() for key, _ in ANDROID_ACTIVE_WINDOWS}
        devices: dict[str, set[str]] = {key: set() for key, _ in ANDROID_ACTIVE_WINDOWS}

        for row in open_rows:
            created_at = cls._as_utc(getattr(row, "created_at", None))
            if created_at is None:
                continue
            telegram_id = int(getattr(row, "telegram_id", 0) or 0)
            payload = cls._payload(getattr(row, "payload_json", None))
            device_id = str(payload.get("device_id") or "").strip()
            if not device_id or device_id not in current_device_ids:
                continue
            for key, days in ANDROID_ACTIVE_WINDOWS:
                if created_at >= now - timedelta(days=days):
                    if telegram_id:
                        users[key].add(telegram_id)
                    if device_id:
                        devices[key].add(device_id)

        active: dict[str, Any] = {"window_days": ANDROID_ACTIVE_WINDOW_DAYS}
        for key, _ in ANDROID_ACTIVE_WINDOWS:
            active[key] = len(users[key])
            active[f"{key}_devices"] = len(devices[key])
        return active

    @classmethod
    def _versions(
        cls,
        *,
        device_rows: Iterable[Any],
        now: datetime,
        latest_release: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Version split of the phones that reached the server in 30 days."""

        window_start = now - timedelta(days=ANDROID_ACTIVE_WINDOW_DAYS)
        devices: dict[str, int] = {}
        users: dict[str, set[int]] = {}

        for row in device_rows:
            if cls._as_utc(getattr(row, "revoked_at", None)) is not None:
                continue
            last_seen_at = cls._as_utc(getattr(row, "last_seen_at", None))
            if last_seen_at is None or last_seen_at < window_start:
                continue
            version = cls._version(getattr(row, "app_version", None))
            key = version or "—"
            devices[key] = devices.get(key, 0) + 1
            user_id = int(getattr(row, "user_id", 0) or 0)
            if user_id:
                users.setdefault(key, set()).add(user_id)

        rows = [
            {
                "version": version,
                "devices": count,
                "users": len(users.get(version) or ()),
            }
            for version, count in sorted(
                devices.items(), key=lambda item: (-item[1], item[0])
            )
        ]

        latest_name = cls._version((latest_release or {}).get("version_name"))
        latest_semver = None
        if latest_name:
            try:
                latest_semver = parse_desktop_semver(latest_name)
            except ValueError:
                latest_semver = None

        outdated: int | None = None
        comparable = 0
        if latest_semver is not None:
            outdated = 0
            for row in rows:
                try:
                    semver = parse_desktop_semver(row["version"])
                except ValueError:
                    # An unparseable version is not evidence of anything, so
                    # it is left out of both sides of the ratio.
                    continue
                comparable += row["devices"]
                if semver < latest_semver:
                    outdated += row["devices"]

        return {
            "rows": rows,
            "latest": latest_name or None,
            "outdated_devices_30d": outdated,
            "comparable_devices_30d": comparable,
            "window_days": ANDROID_ACTIVE_WINDOW_DAYS,
        }

    @classmethod
    def build_snapshot(
        cls,
        *,
        totals: Mapping[str, Mapping[str, int]],
        device_rows: Iterable[Any],
        open_rows: Iterable[Any],
        now: datetime,
        since: datetime | None = None,
        latest_release: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        device_rows = list(device_rows)
        funnel = cls._funnel(totals)
        registry = cls._registry(device_rows=device_rows, now=now, since=since)
        current_device_ids = {
            str(getattr(row, "id", "") or "").strip()
            for row in device_rows
            if cls._as_utc(getattr(row, "revoked_at", None)) is None
            and str(getattr(row, "id", "") or "").strip()
        }
        active = cls._active(
            open_rows=open_rows,
            now=now,
            current_device_ids=current_device_ids,
        )
        versions = cls._versions(
            device_rows=device_rows, now=now, latest_release=latest_release
        )
        update_counts = totals.get(ANDROID_UPDATE_EVENT) or {}

        installed = registry["installed_devices"]
        return {
            "funnel": funnel,
            "registry": registry,
            "active": active,
            "versions": versions,
            "updates": {
                "installed": {
                    "users": int(update_counts.get("users", 0) or 0),
                    "events": int(update_counts.get("events", 0) or 0),
                }
            },
            "rates": {
                # Of the phones that still hold a linked account, how many
                # opened the app at all, and how many opened it this month.
                "opened_per_installed": cls._pct(
                    registry["opened_devices"], installed
                ),
                "mau_devices_per_installed": cls._pct(
                    int(active.get("mau_devices") or 0), installed
                ),
            },
            "notes": {
                "install_definition": (
                    "O'rnatish = APK o'rnatilib, akkaunt ulangan qurilma "
                    "(server qurilma yozuvi). Botdan APK yuborilgani "
                    "o'rnatish hisoblanmaydi."
                ),
                "active_definition": (
                    "Faol = hozir akkaunti ulangan telefonda ilovaning o'zi "
                    "ochilgan user. Uzilgan eski telefonlar va fon widgeti "
                    "faol hisobiga kirmaydi."
                ),
                "not_measured": (
                    "Akkaunt ulanmagan o'rnatishlar, ilova o'chirib "
                    "tashlangani va saytdan to'g'ridan-to'g'ri yuklab "
                    "olishlar o'lchanmaydi — bu raqamlarda ular yo'q."
                ),
            },
        }

    async def snapshot(
        self,
        *,
        now: datetime | None = None,
        since: datetime | None = None,
        latest_release: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now_utc = self._as_utc(now) or datetime.now(timezone.utc)
        since_utc = self._as_utc(since)
        totals = await self._event_totals(since=since_utc)
        device_rows = await self._device_rows()
        open_rows = await self._open_rows(
            since=now_utc - timedelta(days=ANDROID_ACTIVE_WINDOW_DAYS)
        )
        return self.build_snapshot(
            totals=totals,
            device_rows=device_rows,
            open_rows=open_rows,
            now=now_utc,
            since=since_utc,
            latest_release=latest_release,
        )
