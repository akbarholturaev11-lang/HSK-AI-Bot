"""Shared Android release-count policy for both distribution channels.

The Admin PWA owns the persisted setting; clients choose their own official
installer/Play delivery. Missing or malformed settings keep the safe default.
No entitlement, account, or release artifact is changed by this preference.
"""
from app.repositories.bot_setting_repo import BotSettingRepository

ANDROID_UPDATE_ALLOWED_VERSIONS_KEY = "android_update_allowed_versions"
DEFAULT_ANDROID_ALLOWED_VERSIONS = 4
ANDROID_ALLOWED_VERSION_CHOICES = (1, 2, 3, 4)


def normalize_allowed_versions(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_ANDROID_ALLOWED_VERSIONS
    value = str(raw).strip()
    if value not in ("1", "2", "3", "4"):
        return DEFAULT_ANDROID_ALLOWED_VERSIONS
    return int(value)


async def read_allowed_versions(session) -> int:
    raw = await BotSettingRepository(session).get(ANDROID_UPDATE_ALLOWED_VERSIONS_KEY)
    return normalize_allowed_versions(raw)
