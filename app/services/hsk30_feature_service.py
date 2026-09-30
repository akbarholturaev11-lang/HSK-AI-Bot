from __future__ import annotations

from app.repositories.bot_setting_repo import BotSettingRepository


HSK30_ENABLED_SETTINGS_KEY = "hsk30_enabled"


class Hsk30FeatureService:
    """Server-owned HSK 3.0 kill switch.

    Missing/invalid settings fail closed. Merely adding nhsk* level keys must
    never make them user-visible before the rollout flag is explicitly enabled.
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
