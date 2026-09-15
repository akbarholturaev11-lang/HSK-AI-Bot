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
    }


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
                }
    except Exception:
        # A platform whose state cannot be read is reported as unavailable, not
        # as an error: the page must still offer the ones that do work.
        logger.exception("Desktop release status could not be read")

    try:
        async with session_factory() as session:
            release = await AndroidReleaseService(session).serve()
        if release is not None and release.download_url:
            platforms["android"] = {
                "available": True,
                "version": release.version_text,
                "download": DOWNLOAD_PATHS["android"],
                "file": release.file_name,
                "size": release.size or None,
            }
    except Exception:
        logger.exception("Android release status could not be read")

    return {
        "ok": True,
        "platforms": platforms,
        "any": any(entry["available"] for entry in platforms.values()),
    }
