from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any, Iterable, Mapping

from sqlalchemy import func, select

from app.db.models.course_miniapp_event import CourseMiniAppEvent


DESKTOP_EVENT_NAMES = (
    "desktop_promo_seen",
    "desktop_promo_dismissed",
    "desktop_download_requested",
    "desktop_download_started",
    # Historical compatibility only; new acquisition is direct download.
    "desktop_download_message_sent",
    "desktop_download_link_clicked",
    "desktop_session_linked",
    "desktop_first_open",
    "desktop_app_opened",
    "desktop_active_day",
    "desktop_ai_pack_started",
    "desktop_ai_pack_completed",
    "desktop_offline_ai_used",
    "desktop_progress_sync_succeeded",
    "desktop_progress_sync_failed",
    "desktop_update_installed",
)

DESKTOP_FUNNEL_EVENTS = (
    "desktop_download_requested",
    "desktop_download_started",
    "desktop_download_link_clicked",
    "desktop_session_linked",
    "desktop_first_open",
)

DESKTOP_FUNNEL_STAGES = (
    ("download_requested", "desktop_download_requested"),
    ("download_started", "desktop_download_started"),
    ("link_clicked", "desktop_download_link_clicked"),
    ("session_linked", "desktop_session_linked"),
    ("verified_first_open", "desktop_first_open"),
)

DESKTOP_PROMO_SOURCES = (
    "home_prompt",
    "lesson_end_promo",
    "ad_promo",
)

DESKTOP_COHORT_EVENTS = (
    "desktop_promo_seen",
    "desktop_promo_dismissed",
    *DESKTOP_FUNNEL_EVENTS,
)

DESKTOP_ACTIVITY_PROOF_EVENTS = (
    "desktop_first_open",
    "desktop_app_opened",
    "desktop_active_day",
)

DESKTOP_DETAIL_EVENTS = (
    "desktop_download_requested",
    "desktop_first_open",
    "desktop_app_opened",
    "desktop_active_day",
)

DESKTOP_PLATFORMS = ("macos", "windows")
DESKTOP_DETAIL_WINDOW_DAYS = 30


class DesktopAnalyticsService:
    """Read-only desktop product analytics over the existing Mini App event table.

    The event table already has indexed event/time/user fields plus a flexible
    payload, so desktop analytics does not need a new table or migration. High
    volume/all-time funnel totals stay inside SQL aggregation. Platform/version
    inspection reads only the rolling 30-day activity window.

    Recording contract:
    - ``source`` is the placement or server flow (profile, promo, bot, desktop).
    - ``payload.platform`` is ``macos`` or ``windows``.
    - desktop runtime events include ``payload.app_version``.
    - ``session_id`` is an opaque server-issued desktop session/device key.
      Never put a raw hardware identifier in analytics.
    """

    EVENT_NAMES = DESKTOP_EVENT_NAMES

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _pct(part: int, total: int) -> float:
        return round(part / total * 100, 1) if total > 0 else 0.0

    @classmethod
    def _bounded_pct(cls, part: int, total: int) -> float:
        return min(100.0, cls._pct(part, total))

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
    def _normalize_platform(value: Any) -> str | None:
        raw = str(value or "").strip().lower()
        aliases = {
            "mac": "macos",
            "mac_os": "macos",
            "osx": "macos",
            "darwin": "macos",
            "win": "windows",
            "win32": "windows",
            "win64": "windows",
        }
        normalized = aliases.get(raw, raw)
        return normalized if normalized in DESKTOP_PLATFORMS else None

    @classmethod
    def _row_platform(cls, row: Any, payload: Mapping[str, Any]) -> str | None:
        platform = cls._normalize_platform(payload.get("platform"))
        if platform:
            return platform

        # Compatibility fallback for early server-side events. New writers
        # should always use payload.platform and keep source for attribution.
        source = str(getattr(row, "source", "") or "").strip().lower()
        for candidate in DESKTOP_PLATFORMS:
            if source in {candidate, f"desktop_{candidate}"}:
                return candidate
        return None

    @staticmethod
    def _normalize_entry_source(value: Any) -> str:
        raw = str(value or "").strip().lower()
        if raw.startswith("desktop_"):
            raw = raw[len("desktop_") :]
        return raw[:40]

    @classmethod
    def _row_entry_source(cls, row: Any, payload: Mapping[str, Any]) -> str:
        return cls._normalize_entry_source(
            payload.get("entry_source")
            or payload.get("source")
            or getattr(row, "source", "")
        )

    @classmethod
    def _row_key(cls, row: Any) -> tuple[datetime, int]:
        created_at = cls._as_utc(getattr(row, "created_at", None))
        if created_at is None:
            created_at = datetime.min.replace(tzinfo=timezone.utc)
        return created_at, int(getattr(row, "id", 0) or 0)

    @staticmethod
    def _row_session_id(row: Any) -> str:
        return str(getattr(row, "session_id", "") or "").strip()

    @classmethod
    def _same_platform(cls, first: Any, second: Any) -> bool:
        first_payload = cls._payload(getattr(first, "payload_json", None))
        second_payload = cls._payload(getattr(second, "payload_json", None))
        first_platform = cls._row_platform(first, first_payload)
        second_platform = cls._row_platform(second, second_payload)
        return not first_platform or not second_platform or first_platform == second_platform

    @classmethod
    def _ordered_funnel(
        cls,
        *,
        rows: Iterable[Any],
        totals: Mapping[str, Mapping[str, int]],
    ) -> tuple[dict[str, dict[str, int]], dict[str, float]]:
        by_user: dict[int, list[Any]] = defaultdict(list)
        for row in rows:
            event_name = str(getattr(row, "event_name", "") or "")
            telegram_id = int(getattr(row, "telegram_id", 0) or 0)
            if event_name in DESKTOP_FUNNEL_EVENTS and telegram_id:
                by_user[telegram_id].append(row)

        cohort_users = {key: 0 for key, _ in DESKTOP_FUNNEL_STAGES}

        for user_rows in by_user.values():
            events = sorted(user_rows, key=cls._row_key)
            deepest_stage = 0

            def first_after(event_name: str, previous: Any, predicate) -> Any | None:
                previous_key = cls._row_key(previous)
                for candidate in events:
                    if str(getattr(candidate, "event_name", "") or "") != event_name:
                        continue
                    if cls._row_key(candidate) <= previous_key:
                        continue
                    if predicate(candidate):
                        return candidate
                return None

            for request in (
                item
                for item in events
                if str(getattr(item, "event_name", "") or "")
                == "desktop_download_requested"
            ):
                deepest_for_request = 1
                request_payload = cls._payload(getattr(request, "payload_json", None))
                request_source = cls._row_entry_source(request, request_payload)
                request_token = cls._row_session_id(request)

                if not request_token or not request_source:
                    deepest_stage = max(deepest_stage, deepest_for_request)
                    continue

                def same_request(candidate: Any) -> bool:
                    payload = cls._payload(getattr(candidate, "payload_json", None))
                    return (
                        cls._row_session_id(candidate) == request_token
                        and cls._row_entry_source(candidate, payload) == request_source
                        and cls._same_platform(request, candidate)
                    )

                started = first_after(
                    "desktop_download_started",
                    request,
                    same_request,
                )
                if started is None:
                    deepest_stage = max(deepest_stage, deepest_for_request)
                    continue
                deepest_for_request = 2

                click = first_after(
                    "desktop_download_link_clicked",
                    request,
                    same_request,
                )
                if click is None:
                    deepest_stage = max(deepest_stage, deepest_for_request)
                    continue
                deepest_for_request = 3

                # Telegram may resolve the tracked URL just before its
                # downloadFile callback reports acceptance. Both events must
                # follow the request, but their relative order is not stable.
                download_anchor = max((started, click), key=cls._row_key)
                linked = first_after(
                    "desktop_session_linked",
                    download_anchor,
                    lambda candidate: cls._same_platform(request, candidate),
                )
                if linked is None:
                    deepest_stage = max(deepest_stage, deepest_for_request)
                    continue
                deepest_for_request = 4

                linked_session_id = cls._row_session_id(linked)
                first_open = first_after(
                    "desktop_first_open",
                    linked,
                    lambda candidate: (
                        cls._same_platform(linked, candidate)
                        and (
                            not linked_session_id
                            or not cls._row_session_id(candidate)
                            or cls._row_session_id(candidate) == linked_session_id
                        )
                    ),
                )
                if first_open is not None:
                    deepest_for_request = 5
                deepest_stage = max(deepest_stage, deepest_for_request)

            for index, (key, _) in enumerate(DESKTOP_FUNNEL_STAGES, start=1):
                if deepest_stage >= index:
                    cohort_users[key] += 1

        funnel: dict[str, dict[str, int]] = {}
        for key, event_name in DESKTOP_FUNNEL_STAGES:
            raw = totals.get(event_name) or {}
            funnel[key] = {
                "events": int(raw.get("events", 0) or 0),
                "users": cohort_users[key],
                "raw_users": int(raw.get("users", 0) or 0),
            }

        rates = {
            "download_started_per_request": cls._bounded_pct(
                cohort_users["download_started"],
                cohort_users["download_requested"],
            ),
            "link_click_per_download_started": cls._bounded_pct(
                cohort_users["link_clicked"],
                cohort_users["download_started"],
            ),
            "session_linked_per_link_click": cls._bounded_pct(
                cohort_users["session_linked"],
                cohort_users["link_clicked"],
            ),
            "verified_first_open_per_session_linked": cls._bounded_pct(
                cohort_users["verified_first_open"],
                cohort_users["session_linked"],
            ),
        }
        return funnel, rates

    @classmethod
    def _promotion_cohort(
        cls,
        *,
        rows: Iterable[Any],
        totals: Mapping[str, Mapping[str, int]],
    ) -> dict[str, Any]:
        by_source_user: dict[tuple[str, int], list[Any]] = defaultdict(list)
        for row in rows:
            event_name = str(getattr(row, "event_name", "") or "")
            if event_name not in {
                "desktop_promo_seen",
                "desktop_promo_dismissed",
                "desktop_download_requested",
            }:
                continue
            telegram_id = int(getattr(row, "telegram_id", 0) or 0)
            payload = cls._payload(getattr(row, "payload_json", None))
            source = cls._row_entry_source(row, payload)
            if telegram_id and source in DESKTOP_PROMO_SOURCES:
                by_source_user[(source, telegram_id)].append(row)

        seen_users: set[int] = set()
        dismissed_users: set[int] = set()
        converted_users: set[int] = set()
        seen_events = 0
        dismissed_events = 0
        converted_request_events = 0
        source_values: dict[str, dict[str, set[int] | int]] = {
            source: {
                "seen_users": set(),
                "converted_users": set(),
                "seen_events": 0,
                "converted_request_events": 0,
            }
            for source in DESKTOP_PROMO_SOURCES
        }

        for (source, telegram_id), source_rows in by_source_user.items():
            ordered = sorted(source_rows, key=cls._row_key)
            seen = [
                row
                for row in ordered
                if str(getattr(row, "event_name", "") or "") == "desktop_promo_seen"
            ]
            if not seen:
                continue

            seen_users.add(telegram_id)
            source_values[source]["seen_users"].add(telegram_id)
            seen_events += len(seen)
            source_values[source]["seen_events"] += len(seen)
            first_seen_key = cls._row_key(seen[0])

            valid_dismissals = [
                row
                for row in ordered
                if (
                    str(getattr(row, "event_name", "") or "")
                    == "desktop_promo_dismissed"
                    and cls._row_key(row) > first_seen_key
                )
            ]
            if valid_dismissals:
                dismissed_users.add(telegram_id)
                dismissed_events += len(valid_dismissals)

            valid_requests = [
                row
                for row in ordered
                if (
                    str(getattr(row, "event_name", "") or "")
                    == "desktop_download_requested"
                    and cls._row_key(row) > first_seen_key
                )
            ]
            if valid_requests:
                converted_users.add(telegram_id)
                source_values[source]["converted_users"].add(telegram_id)
                converted_request_events += len(valid_requests)
                source_values[source]["converted_request_events"] += len(valid_requests)

        source_payload = {}
        for source, values in source_values.items():
            source_seen_users = len(values["seen_users"])
            source_converted_users = len(values["converted_users"])
            source_payload[source] = {
                "seen": {
                    "events": int(values["seen_events"]),
                    "users": source_seen_users,
                },
                "requested_after_seen": {
                    "events": int(values["converted_request_events"]),
                    "users": source_converted_users,
                },
                "request_per_seen": cls._bounded_pct(
                    source_converted_users,
                    source_seen_users,
                ),
            }

        raw_seen = totals.get("desktop_promo_seen") or {}
        raw_dismissed = totals.get("desktop_promo_dismissed") or {}
        return {
            "eligible_sources": list(DESKTOP_PROMO_SOURCES),
            "seen": {
                "events": seen_events,
                "users": len(seen_users),
                "raw_events": int(raw_seen.get("events", 0) or 0),
                "raw_users": int(raw_seen.get("users", 0) or 0),
            },
            "dismissed": {
                "events": dismissed_events,
                "users": len(dismissed_users),
                "raw_events": int(raw_dismissed.get("events", 0) or 0),
                "raw_users": int(raw_dismissed.get("users", 0) or 0),
            },
            "requested_after_seen": {
                "events": converted_request_events,
                "users": len(converted_users),
            },
            "request_per_seen": cls._bounded_pct(
                len(converted_users),
                len(seen_users),
            ),
            "sources": source_payload,
        }

    @staticmethod
    def _version(value: Any) -> str | None:
        raw = str(value or "").strip()
        if not raw or len(raw) > 48:
            return None
        return raw

    @staticmethod
    def _semver_key(value: str | None) -> tuple[int, int, int, int] | None:
        if not value:
            return None
        match = re.fullmatch(
            r"[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?",
            value.strip(),
        )
        if not match:
            return None
        major, minor, patch = (int(match.group(index) or 0) for index in (1, 2, 3))
        # A prerelease is older than the release with the same numeric parts.
        release_rank = 0 if match.group(4) else 1
        return major, minor, patch, release_rank

    @classmethod
    def _is_outdated(cls, current: str | None, latest: str | None) -> bool | None:
        current_key = cls._semver_key(current)
        latest_key = cls._semver_key(latest)
        if current_key is None or latest_key is None:
            return None
        return current_key < latest_key

    @classmethod
    def _latest_versions(cls, values: Mapping[str, Any] | None) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for raw_platform, raw_version in (values or {}).items():
            platform = cls._normalize_platform(raw_platform)
            version = cls._version(raw_version)
            if platform and version:
                normalized[platform] = version
        return normalized

    async def _event_totals(
        self,
        *,
        since: datetime | None,
    ) -> dict[str, dict[str, int]]:
        stmt = (
            select(
                CourseMiniAppEvent.event_name,
                func.count().label("events"),
                func.count(func.distinct(CourseMiniAppEvent.telegram_id)).label("users"),
            )
            .select_from(CourseMiniAppEvent)
            .where(CourseMiniAppEvent.event_name.in_(self.EVENT_NAMES))
            .group_by(CourseMiniAppEvent.event_name)
        )
        if since is not None:
            stmt = stmt.where(CourseMiniAppEvent.created_at >= since)

        rows = (await self.session.execute(stmt)).fetchall()
        result = {
            name: {"events": 0, "users": 0}
            for name in self.EVENT_NAMES
        }
        for row in rows:
            name = str(row.event_name or "")
            if name in result:
                result[name] = {
                    "events": int(row.events or 0),
                    "users": int(row.users or 0),
                }
        return result

    async def _detail_rows(self, *, since: datetime) -> list[Any]:
        stmt = (
            select(
                CourseMiniAppEvent.event_name,
                CourseMiniAppEvent.telegram_id,
                CourseMiniAppEvent.source,
                CourseMiniAppEvent.session_id,
                CourseMiniAppEvent.payload_json,
                CourseMiniAppEvent.created_at,
            )
            .select_from(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.event_name.in_(DESKTOP_DETAIL_EVENTS),
                CourseMiniAppEvent.created_at >= since,
            )
            .order_by(CourseMiniAppEvent.created_at.asc())
        )
        return list((await self.session.execute(stmt)).fetchall())

    async def _cohort_rows(self, *, since: datetime | None) -> list[Any]:
        stmt = (
            select(
                CourseMiniAppEvent.id,
                CourseMiniAppEvent.event_name,
                CourseMiniAppEvent.telegram_id,
                CourseMiniAppEvent.source,
                CourseMiniAppEvent.session_id,
                CourseMiniAppEvent.payload_json,
                CourseMiniAppEvent.created_at,
            )
            .select_from(CourseMiniAppEvent)
            .where(CourseMiniAppEvent.event_name.in_(DESKTOP_COHORT_EVENTS))
            .order_by(
                CourseMiniAppEvent.created_at.asc(),
                CourseMiniAppEvent.id.asc(),
            )
        )
        if since is not None:
            stmt = stmt.where(CourseMiniAppEvent.created_at >= since)
        return list((await self.session.execute(stmt)).fetchall())

    @classmethod
    def build_snapshot(
        cls,
        *,
        totals: Mapping[str, Mapping[str, int]],
        detail_rows: Iterable[Any],
        now: datetime,
        cohort_rows: Iterable[Any] = (),
        since: datetime | None = None,
        latest_versions: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now_utc = cls._as_utc(now) or datetime.now(timezone.utc)
        since_utc = cls._as_utc(since)
        current_versions = cls._latest_versions(latest_versions)
        cohort_rows = list(cohort_rows)

        def count(event_name: str, field: str) -> int:
            return int((totals.get(event_name) or {}).get(field, 0) or 0)

        funnel, rates = cls._ordered_funnel(
            rows=cohort_rows,
            totals=totals,
        )
        promotion = cls._promotion_cohort(
            rows=cohort_rows,
            totals=totals,
        )

        activity_users = {
            "dau": set(),
            "wau": set(),
            "mau": set(),
        }
        platform_users: dict[str, dict[str, set[int]]] = {
            metric: {platform: set() for platform in DESKTOP_PLATFORMS}
            for metric in ("download_requests_30d", "verified_first_open_30d", "active_users_30d")
        }
        platform_unknown = {
            "download_requests_30d": 0,
            "verified_first_open_30d": 0,
            "active_users_30d": 0,
        }

        latest_device_rows: dict[str, tuple[datetime, int, str | None, str | None]] = {}
        day_ago = now_utc - timedelta(days=1)
        week_ago = now_utc - timedelta(days=7)
        month_ago = now_utc - timedelta(days=DESKTOP_DETAIL_WINDOW_DAYS)

        for row in detail_rows:
            event_name = str(getattr(row, "event_name", "") or "")
            telegram_id = int(getattr(row, "telegram_id", 0) or 0)
            created_at = cls._as_utc(getattr(row, "created_at", None))
            if not telegram_id or created_at is None or created_at < month_ago:
                continue

            payload = cls._payload(getattr(row, "payload_json", None))
            platform = cls._row_platform(row, payload)

            if event_name == "desktop_download_requested":
                if platform:
                    platform_users["download_requests_30d"][platform].add(telegram_id)
                else:
                    platform_unknown["download_requests_30d"] += 1

            if event_name == "desktop_first_open":
                if platform:
                    platform_users["verified_first_open_30d"][platform].add(telegram_id)
                else:
                    platform_unknown["verified_first_open_30d"] += 1

            if event_name in DESKTOP_ACTIVITY_PROOF_EVENTS:
                activity_users["mau"].add(telegram_id)
                if created_at >= week_ago:
                    activity_users["wau"].add(telegram_id)
                if created_at >= day_ago:
                    activity_users["dau"].add(telegram_id)

                if platform:
                    platform_users["active_users_30d"][platform].add(telegram_id)
                else:
                    platform_unknown["active_users_30d"] += 1

                version = cls._version(payload.get("app_version"))
                # A device may rotate desktop sessions after relinking; use the
                # server-issued physical installation/device id when present.
                device_key = str(payload.get("device_id") or "").strip()
                if not device_key:
                    device_key = str(
                        getattr(row, "session_id", "") or ""
                    ).strip()
                if not device_key:
                    device_key = f"user:{telegram_id}:{platform or 'unknown'}"
                candidate = (
                    created_at,
                    telegram_id,
                    platform,
                    version,
                )
                previous = latest_device_rows.get(device_key)
                if previous is None or created_at >= previous[0]:
                    latest_device_rows[device_key] = candidate

        versions_by_platform: dict[str, dict[str, dict[str, set[Any]]]] = {
            platform: defaultdict(lambda: {"devices": set(), "users": set()})
            for platform in DESKTOP_PLATFORMS
        }
        known_version_devices = 0
        unknown_version_devices = 0
        comparable_devices = 0
        outdated_devices = 0

        for device_key, (_, telegram_id, platform, version) in latest_device_rows.items():
            if platform not in DESKTOP_PLATFORMS or not version:
                unknown_version_devices += 1
                continue
            known_version_devices += 1
            versions_by_platform[platform][version]["devices"].add(device_key)
            versions_by_platform[platform][version]["users"].add(telegram_id)

            outdated = cls._is_outdated(version, current_versions.get(platform))
            if outdated is not None:
                comparable_devices += 1
                outdated_devices += int(outdated)

        versions_payload: dict[str, list[dict[str, Any]]] = {}
        for platform in DESKTOP_PLATFORMS:
            rows = [
                {
                    "version": version,
                    "devices": len(values["devices"]),
                    "users": len(values["users"]),
                }
                for version, values in versions_by_platform[platform].items()
            ]
            rows.sort(key=lambda item: (item["devices"], item["users"], item["version"]), reverse=True)
            versions_payload[platform] = rows

        ai_started_users = count("desktop_ai_pack_started", "users")
        ai_completed_users = count("desktop_ai_pack_completed", "users")
        sync_success_events = count("desktop_progress_sync_succeeded", "events")
        sync_failed_events = count("desktop_progress_sync_failed", "events")

        return {
            "period": {
                "since": since_utc.isoformat() if since_utc else None,
                "activity_window_days": DESKTOP_DETAIL_WINDOW_DAYS,
            },
            "promotion": promotion,
            "funnel": funnel,
            "rates": rates,
            "active": {
                "dau": len(activity_users["dau"]),
                "wau": len(activity_users["wau"]),
                "mau": len(activity_users["mau"]),
                "proof_events": list(DESKTOP_ACTIVITY_PROOF_EVENTS),
            },
            "platforms": {
                metric: {
                    **{
                        platform: len(users)
                        for platform, users in values.items()
                    },
                    "unknown_events": platform_unknown[metric],
                }
                for metric, values in platform_users.items()
            },
            "versions": {
                "latest": current_versions,
                "by_platform_30d": versions_payload,
                "known_devices_30d": known_version_devices,
                "unknown_version_devices_30d": unknown_version_devices,
                "comparable_devices_30d": comparable_devices,
                "outdated_devices_30d": (
                    outdated_devices if current_versions else None
                ),
                "outdated_rate_30d": (
                    cls._pct(outdated_devices, comparable_devices)
                    if current_versions and comparable_devices
                    else None
                ),
            },
            "ai_pack": {
                "started": dict(totals.get("desktop_ai_pack_started") or {"events": 0, "users": 0}),
                "completed": dict(totals.get("desktop_ai_pack_completed") or {"events": 0, "users": 0}),
                "completion_rate": cls._pct(ai_completed_users, ai_started_users),
                "offline_ai_used": dict(totals.get("desktop_offline_ai_used") or {"events": 0, "users": 0}),
            },
            "sync": {
                "succeeded": dict(totals.get("desktop_progress_sync_succeeded") or {"events": 0, "users": 0}),
                "failed": dict(totals.get("desktop_progress_sync_failed") or {"events": 0, "users": 0}),
                "success_rate": cls._pct(
                    sync_success_events,
                    sync_success_events + sync_failed_events,
                ),
            },
            "updates": {
                "installed": dict(
                    totals.get("desktop_update_installed")
                    or {"events": 0, "users": 0}
                ),
            },
            "notes": {
                "install_definition": (
                    "Download click install hisoblanmaydi; faqat desktop_first_open "
                    "server eventi tasdiqlangan o'rnatish hisoblanadi."
                ),
                "active_definition": (
                    "DAU/WAU/MAU server-authenticated desktop_first_open, "
                    "desktop_app_opened yoki desktop_active_day eventidan hisoblanadi."
                ),
            },
        }

    async def snapshot(
        self,
        *,
        now: datetime | None = None,
        since: datetime | None = None,
        latest_versions: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now_utc = self._as_utc(now) or datetime.now(timezone.utc)
        since_utc = self._as_utc(since)
        totals = await self._event_totals(since=since_utc)
        cohort_rows = await self._cohort_rows(since=since_utc)
        detail_rows = await self._detail_rows(
            since=now_utc - timedelta(days=DESKTOP_DETAIL_WINDOW_DAYS)
        )
        return self.build_snapshot(
            totals=totals,
            detail_rows=detail_rows,
            now=now_utc,
            cohort_rows=cohort_rows,
            since=since_utc,
            latest_versions=latest_versions,
        )

    @classmethod
    def admin_text(cls, snapshot: Mapping[str, Any]) -> str:
        funnel = snapshot.get("funnel") or {}
        active = snapshot.get("active") or {}
        platforms = snapshot.get("platforms") or {}
        versions = snapshot.get("versions") or {}
        ai_pack = snapshot.get("ai_pack") or {}
        sync = snapshot.get("sync") or {}
        updates = snapshot.get("updates") or {}

        def users(step: str) -> int:
            return int((funnel.get(step) or {}).get("users", 0) or 0)

        active_platforms = platforms.get("active_users_30d") or {}
        latest = versions.get("latest") or {}
        outdated = versions.get("outdated_devices_30d")
        outdated_text = (
            "release versiyasi sozlanmagan"
            if not latest
            else f"<b>{int(outdated or 0)}</b>/<b>{int(versions.get('comparable_devices_30d') or 0)}</b>"
        )

        return "\n".join(
            [
                "<b>🖥 DESKTOP APP</b>",
                (
                    "  Funnel user: "
                    f"So'rov <b>{users('download_requested')}</b> → "
                    f"Download <b>{users('download_started')}</b> → "
                    f"Link <b>{users('link_clicked')}</b> → "
                    f"Ulandi <b>{users('session_linked')}</b> → "
                    f"First open <b>{users('verified_first_open')}</b>"
                ),
                (
                    "  Aktiv: "
                    f"DAU <b>{int(active.get('dau') or 0)}</b> · "
                    f"WAU <b>{int(active.get('wau') or 0)}</b> · "
                    f"MAU <b>{int(active.get('mau') or 0)}</b>"
                ),
                (
                    "  Platforma MAU: "
                    f"Mac <b>{int(active_platforms.get('macos') or 0)}</b> · "
                    f"Windows <b>{int(active_platforms.get('windows') or 0)}</b>"
                ),
                (
                    "  AI Pack: "
                    f"<b>{int((ai_pack.get('started') or {}).get('users', 0) or 0)}</b>→"
                    f"<b>{int((ai_pack.get('completed') or {}).get('users', 0) or 0)}</b> "
                    f"(<b>{float(ai_pack.get('completion_rate') or 0)}%</b>)"
                ),
                (
                    "  Sync: "
                    f"OK <b>{int((sync.get('succeeded') or {}).get('events', 0) or 0)}</b> · "
                    f"Xato <b>{int((sync.get('failed') or {}).get('events', 0) or 0)}</b> · "
                    f"<b>{float(sync.get('success_rate') or 0)}%</b>"
                ),
                (
                    "  Update o'rnatildi: "
                    f"<b>{int((updates.get('installed') or {}).get('users', 0) or 0)}</b> user · "
                    f"<b>{int((updates.get('installed') or {}).get('events', 0) or 0)}</b> marta"
                ),
                f"  Eskirgan versiya: {escape(outdated_text) if not latest else outdated_text}",
                "  Eslatma: link bosilishi install emas; faqat First open tasdiqlaydi.",
            ]
        )
