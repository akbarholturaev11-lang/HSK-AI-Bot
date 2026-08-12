import json
import os
from dataclasses import dataclass
from typing import Any

from app.repositories.bot_setting_repo import BotSettingRepository


DESKTOP_APP_PROMO_SETTINGS_KEY = "desktop_app_promo_settings"
DESKTOP_APP_PROMO_PLACEMENTS = ("home_prompt", "lesson_end_promo", "ad_promo")
DESKTOP_APP_PROMO_PLATFORMS = ("macos", "windows", "android", "ios")
DESKTOP_APP_PROMO_MEDIA_ROOT_BASE = (
    os.environ.get("MEDIA_ROOT")
    or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    or "app/static/uploads"
)
DESKTOP_APP_PROMO_MEDIA_ROOT = os.path.join(
    DESKTOP_APP_PROMO_MEDIA_ROOT_BASE,
    "app_promo",
)
DESKTOP_APP_PROMO_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DESKTOP_APP_PROMO_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DESKTOP_APP_PROMO_ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
DESKTOP_APP_PROMO_MEDIA_TYPES = ("photo", "video")


def _bool_map(value: Any, keys: tuple[str, ...], defaults: dict[str, bool]) -> dict[str, bool]:
    source = value if isinstance(value, dict) else {}
    return {key: bool(source.get(key, defaults.get(key, False))) for key in keys}


def _bounded_daily_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 3
    return max(1, min(3, parsed))


def _safe_media_path(value: Any) -> str | None:
    filename = os.path.basename(str(value or "").strip())
    if not filename:
        return None
    ext = os.path.splitext(filename.lower())[1]
    allowed_extensions = (
        DESKTOP_APP_PROMO_ALLOWED_IMAGE_EXTENSIONS
        | DESKTOP_APP_PROMO_ALLOWED_VIDEO_EXTENSIONS
    )
    if ext not in allowed_extensions or len(filename) > 160:
        return None
    if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._+-" for ch in filename):
        return None
    return filename


def _safe_media_type(value: Any) -> str | None:
    media_type = str(value or "").strip().lower()
    return media_type if media_type in DESKTOP_APP_PROMO_MEDIA_TYPES else None


def desktop_app_promo_media_url(media_path: str | None) -> str | None:
    safe = _safe_media_path(media_path)
    return f"/uploads/app_promo/{safe}" if safe else None


def desktop_app_promo_media_full_path(media_path: str | None) -> str | None:
    safe = _safe_media_path(media_path)
    return os.path.join(DESKTOP_APP_PROMO_MEDIA_ROOT, safe) if safe else None


def desktop_app_promo_media_available(media_path: str | None) -> bool:
    path = desktop_app_promo_media_full_path(media_path)
    if not path:
        return False
    try:
        return os.path.exists(path) and os.path.getsize(path) > 0
    except OSError:
        return False


@dataclass(frozen=True)
class DesktopAppPromoSettings:
    enabled: bool
    daily_limit: int
    placements: dict[str, bool]
    platforms: dict[str, bool]
    media_type: str | None = None
    media_path: str | None = None
    require_learning_progress: bool = False

    @classmethod
    def default(cls) -> "DesktopAppPromoSettings":
        return cls(
            enabled=True,
            daily_limit=3,
            placements={
                "home_prompt": True,
                "lesson_end_promo": True,
                "ad_promo": True,
            },
            platforms={
                "macos": True,
                "windows": True,
                "android": False,
                "ios": False,
            },
        )

    @classmethod
    def from_raw(cls, raw: str | None) -> "DesktopAppPromoSettings":
        default = cls.default()
        if not raw:
            return default
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return default
        if not isinstance(data, dict):
            return default
        media_type = _safe_media_type(data.get("media_type"))
        media_path = _safe_media_path(data.get("media_path"))
        if not media_type or not media_path:
            media_type = None
            media_path = None
        return cls(
            enabled=bool(data.get("enabled", default.enabled)),
            daily_limit=_bounded_daily_limit(data.get("daily_limit", default.daily_limit)),
            placements=_bool_map(data.get("placements"), DESKTOP_APP_PROMO_PLACEMENTS, default.placements),
            platforms=_bool_map(data.get("platforms"), DESKTOP_APP_PROMO_PLATFORMS, default.platforms),
            media_type=media_type,
            media_path=media_path,
            require_learning_progress=bool(
                data.get("require_learning_progress", default.require_learning_progress)
            ),
        )

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        previous: "DesktopAppPromoSettings | None" = None,
    ) -> "DesktopAppPromoSettings":
        default = cls.default()
        base = previous or default
        placement_defaults = default.placements if "placements" in payload else base.placements
        platform_defaults = default.platforms if "platforms" in payload else base.platforms
        media_type = base.media_type
        media_path = base.media_path
        if "media_type" in payload or "media_path" in payload:
            media_type = _safe_media_type(payload.get("media_type"))
            media_path = _safe_media_path(payload.get("media_path"))
            if not media_type or not media_path:
                media_type = None
                media_path = None
        return cls(
            enabled=bool(payload.get("enabled", base.enabled)),
            daily_limit=_bounded_daily_limit(payload.get("daily_limit", base.daily_limit)),
            placements=_bool_map(payload.get("placements"), DESKTOP_APP_PROMO_PLACEMENTS, placement_defaults),
            platforms=_bool_map(payload.get("platforms"), DESKTOP_APP_PROMO_PLATFORMS, platform_defaults),
            media_type=media_type,
            media_path=media_path,
            require_learning_progress=bool(
                payload.get("require_learning_progress", base.require_learning_progress)
            ),
        )

    def storage_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "daily_limit": self.daily_limit,
            "placements": {key: bool(self.placements.get(key)) for key in DESKTOP_APP_PROMO_PLACEMENTS},
            "platforms": {key: bool(self.platforms.get(key)) for key in DESKTOP_APP_PROMO_PLATFORMS},
            "media_type": self.media_type,
            "media_path": self.media_path,
            "require_learning_progress": self.require_learning_progress,
        }

    def payload(self) -> dict[str, Any]:
        value = self.storage_payload()
        value.pop("media_path", None)
        value["media_url"] = desktop_app_promo_media_url(self.media_path)
        value["media_available"] = desktop_app_promo_media_available(self.media_path)
        return value

    def storage_value(self) -> str:
        return json.dumps(self.storage_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def get_desktop_app_promo_settings(session) -> DesktopAppPromoSettings:
    raw = await BotSettingRepository(session).get(DESKTOP_APP_PROMO_SETTINGS_KEY)
    return DesktopAppPromoSettings.from_raw(raw)


async def save_desktop_app_promo_settings(
    session,
    payload: dict[str, Any],
) -> DesktopAppPromoSettings:
    current = await get_desktop_app_promo_settings(session)
    settings = DesktopAppPromoSettings.from_payload(payload, previous=current)
    await BotSettingRepository(session).set(
        DESKTOP_APP_PROMO_SETTINGS_KEY,
        settings.storage_value(),
    )
    return settings
