"""What can be downloaded right now, for every platform at once.

The desktop installers and the Android APK are published by two different
pipelines and answered by two different services. The download page — and
anything reading this site without running its JavaScript, which now includes
search and AI crawlers — needs one answer covering all three.

Nothing new is decided here. Each platform is asked its own existing question
and the answers are put in one shape, so a platform that is not published
cannot accidentally look published in this view.
"""

import logging
from typing import Any

from app.services.android_release_service import AndroidReleaseService
from app.services.desktop_download_service import DesktopReleaseConfig


logger = logging.getLogger(__name__)

PLATFORMS = ("macos", "windows", "android")

#: Stable paths on our own origin. They outlive whichever bucket or host the
#: artifact currently sits behind, which is the whole reason they exist.
DOWNLOAD_PATHS = {
    "macos": "/downloads/macos",
    "windows": "/downloads/windows",
    "android": "/downloads/android",
}


def _empty(platform: str) -> dict[str, Any]:
    return {
        "available": False,
        "version": None,
        "download": None,
        "file": None,
        "size": None,
        "published": None,
    }


def _date(value: Any) -> str | None:
    """Just the day. A release is dated, not timed, to whoever reads this."""

    text = str(value or "").strip()
    if len(text) < 10:
        return None
    day = text[:10]
    return day if day.count("-") == 2 else None


async def app_download_status(
    *,
    session_factory,
    settings_obj,
    release_manifest_service=None,
) -> dict[str, Any]:
    """One payload describing every client a learner can install."""

    platforms = {name: _empty(name) for name in PLATFORMS}

    try:
        desktop = await DesktopReleaseConfig.resolve(
            settings_obj,
            release_manifest_service=release_manifest_service,
        )
        status = desktop.public_status_payload()
        desktop_published = None
        try:
            from app.services.desktop_release_manifest_service import (
                DesktopReleaseManifestService,
            )

            service = release_manifest_service or DesktopReleaseManifestService(settings_obj)
            manifest = await service.resolve()
            desktop_published = _date(getattr(manifest, "published_at", None))
        except Exception:
            logger.exception("Desktop release date could not be read")
        for name in ("macos", "windows"):
            if status.get("platforms", {}).get(name) and status.get("downloads", {}).get(name):
                platforms[name] = {
                    "available": True,
                    "version": status.get("versions", {}).get(name),
                    "download": DOWNLOAD_PATHS[name],
                    "file": status.get("files", {}).get(name),
                    # The desktop pipeline publishes no size, and inventing one
                    # would be worse than saying nothing.
                    "size": None,
                    "published": desktop_published,
                }
    except Exception:
        # A platform whose state cannot be read is reported as unavailable, not
        # as an error: the page must still offer the ones that do work.
        logger.exception("Desktop release status could not be read")

    try:
        async with session_factory() as session:
            release = await AndroidReleaseService(session).serve()
        # A published APK the bot can hand over is available even with no
        # public URL behind it: the chat is the channel. Only the link is
        # conditional, so the crawler list and the JSON-LD — both of which
        # need a real file to point at — keep describing exactly what can be
        # downloaded from this origin.
        if release is not None and (release.download_url or release.file_id):
            platforms["android"] = {
                "available": True,
                "version": release.version_text,
                "download": DOWNLOAD_PATHS["android"] if release.download_url else None,
                "file": release.file_name,
                "size": release.size or None,
                "published": _date(release.published_at),
            }
    except Exception:
        logger.exception("Android release status could not be read")

    return {
        "ok": True,
        "platforms": platforms,
        "any": any(entry["available"] for entry in platforms.values()),
    }
