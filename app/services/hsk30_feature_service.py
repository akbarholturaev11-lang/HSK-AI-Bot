from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_levels import hsk30_content_levels, level_spec


HSK30_ENABLED_SETTINGS_KEY = "hsk30_enabled"
HSK30_LIVE_LEVELS_SETTINGS_KEY = "hsk30_live_levels"
DEFAULT_HSK30_LIVE_LEVELS = ("nhsk1",)
HSK30_NEW_BADGE_WINDOW = timedelta(days=3)


class Hsk30FeatureService:
    """Server-owned HSK 3.0 rollout controls.

    hsk30_enabled is the global kill switch. hsk30_live_levels is the release
    boundary inside the track. Runtime data for a later level may be checked
    in without making that level selectable or startable.

    Missing hsk30_live_levels intentionally defaults to N1 only: this is the
    first public release defined by the HSK 3.0 rollout plan. An explicitly
    empty value means no HSK 3.0 level is live.
    """

    def __init__(self, session):
        self.setting_repo = BotSettingRepository(session)

    async def is_enabled(self) -> bool:
        return await self.setting_repo.get_bool(
            HSK30_ENABLED_SETTINGS_KEY,
            default=False,
        )

    async def enabled_at(self):
        row = await self.setting_repo.get_record(HSK30_ENABLED_SETTINGS_KEY)
        if not row or str(row.value or "").strip().lower() not in {"1", "true", "yes", "on"}:
            return None
        value = row.updated_at
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc) if value is not None else None

    async def set_enabled(self, enabled: bool):
        """Persist only a real on/off transition.

        The setting row's updated_at is the public-release timestamp used by
        the three-day NEW badge. Saving price/live-level settings while the
        course is already enabled must not restart that clock.
        """
        target = bool(enabled)
        record = await self.setting_repo.get_record(HSK30_ENABLED_SETTINGS_KEY)
        if record is not None:
            current = str(record.value or "").strip().lower() in {"1", "true", "yes", "on"}
            if current == target:
                return record
        elif not target:
            return None
        return await self.setting_repo.set_bool(
            HSK30_ENABLED_SETTINGS_KEY,
            target,
        )

    async def new_badge(self, *, now: datetime | None = None) -> dict:
        enabled_at = await self.enabled_at()
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        else:
            current = current.astimezone(timezone.utc)
        new_until = enabled_at + HSK30_NEW_BADGE_WINDOW if enabled_at else None
        is_new = bool(enabled_at and new_until and current < new_until)
        return {
            "is_new": is_new,
            "enabled_at": enabled_at.isoformat() if enabled_at else None,
            "new_until": new_until.isoformat() if new_until else None,
        }

    @staticmethod
    def _normalize_live_levels(value: str | None) -> tuple[str, ...]:
        if value is None:
            return DEFAULT_HSK30_LIVE_LEVELS
        allowed = set(hsk30_content_levels())
        selected = {
            item.strip().lower()
            for item in str(value).split(",")
            if item.strip()
        }
        return tuple(
            level
            for level in hsk30_content_levels()
            if level in selected
            and level in allowed
            and (level_spec(level) is not None and level_spec(level).selectable)
        )

    async def live_levels(self) -> tuple[str, ...]:
        raw = await self.setting_repo.get(HSK30_LIVE_LEVELS_SETTINGS_KEY)
        return self._normalize_live_levels(raw)

    async def is_level_live(self, level: str | None) -> bool:
        normalized = str(level or "").strip().lower()
        return normalized in await self.live_levels()

    async def set_live_levels(self, levels: list[str] | tuple[str, ...] | set[str]):
        requested = ",".join(str(level or "").strip().lower() for level in levels)
        normalized = self._normalize_live_levels(requested)
        return await self.setting_repo.set(
            HSK30_LIVE_LEVELS_SETTINGS_KEY,
            ",".join(normalized),
        )
