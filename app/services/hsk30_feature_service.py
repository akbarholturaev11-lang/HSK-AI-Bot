from __future__ import annotations

from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_levels import hsk30_content_levels, level_spec


HSK30_ENABLED_SETTINGS_KEY = "hsk30_enabled"
HSK30_LIVE_LEVELS_SETTINGS_KEY = "hsk30_live_levels"
DEFAULT_HSK30_LIVE_LEVELS = ("nhsk1",)


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

    async def set_enabled(self, enabled: bool):
        return await self.setting_repo.set_bool(
            HSK30_ENABLED_SETTINGS_KEY,
            bool(enabled),
        )

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
