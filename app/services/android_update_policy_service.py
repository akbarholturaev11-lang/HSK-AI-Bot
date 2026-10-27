"""Admin-selected count of PUBLISHED releases, never versionCode arithmetic."""
from app.repositories.bot_setting_repo import BotSettingRepository

ANDROID_UPDATE_ALLOWED_VERSIONS_KEY = "android_update_allowed_versions"
DEFAULT_ANDROID_ALLOWED_VERSIONS = 4
ANDROID_ALLOWED_VERSION_CHOICES = (1, 2, 3, 4)


def normalize_allowed_versions(raw: str | None) -> int:
    value = str(raw).strip() if raw is not None else ""
    return int(value) if value in ("1", "2", "3", "4") else DEFAULT_ANDROID_ALLOWED_VERSIONS


async def read_allowed_versions(session) -> int:
    return normalize_allowed_versions(
        await BotSettingRepository(session).get(ANDROID_UPDATE_ALLOWED_VERSIONS_KEY)
    )


def minimum_supported_published_version(
    published_codes: tuple[int, ...] | list[int],
    allowed_versions: int,
) -> int | None:
    """Oldest permitted code among the last N *confirmed* published releases.

    A partial legacy ledger must never treat missing historical releases as
    if they did not exist. Until at least N are confirmed, no forced update.
    """
    if (type(allowed_versions) is not int or allowed_versions not in ANDROID_ALLOWED_VERSION_CHOICES
            or len(published_codes) < allowed_versions
            or any(type(code) is not int or code < 1 for code in published_codes)
            or list(published_codes) != sorted(set(published_codes))):
        return None
    return published_codes[-allowed_versions]
