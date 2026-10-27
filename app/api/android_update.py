"""What an installed Android app asks before it offers to update itself.

The `/check` APK artifact route belongs to Direct exclusively. The
non-secret `/policy` endpoint is shared, but its independently verified
published-release ledger is channel-specific. Google Play clients must
update using Play Core / Store, never via a Direct APK URL.

The answer is deliberately thin: a version code to compare, a name to show and
one https link. The server does not decide whether to update — it cannot know
whether the learner is mid-lesson or on mobile data — it only says what exists.
"""

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.services.android_release_service import AndroidReleaseService
from app.services.android_update_policy_service import (
    DEFAULT_ANDROID_ALLOWED_VERSIONS, read_allowed_versions,
    minimum_supported_published_version,
)


logger = logging.getLogger(__name__)

_NO_STORE = {"Cache-Control": "no-store"}


def create_android_update_router(*, session_factory) -> APIRouter:
    router = APIRouter(tags=["android-update"])

    @router.get("/api/v3/android-update/policy", response_model=None)
    async def android_update_policy(channel: str = Query("direct", pattern="^(direct|play)$")):
        # A channel has its own real publication ledger. Never count arbitrary
        # versionCode gaps or copy a Direct release into the Play channel.
        allowed = DEFAULT_ANDROID_ALLOWED_VERSIONS
        try:
            async with session_factory() as session:
                allowed = await read_allowed_versions(session)
        except Exception:
            logger.warning("Android update setting unavailable")

        minimum = None
        try:
            if channel == "direct":
                from app.config import settings
                from app.services.android_release_manifest_service import AndroidReleaseManifestService
                manifest = await AndroidReleaseManifestService(settings).resolve()
                codes = manifest.published_version_codes if manifest else ()
            else:
                from app.services.android_play_release_history_service import AndroidPlayReleaseHistoryService
                codes = await AndroidPlayReleaseHistoryService().resolve()
            minimum = minimum_supported_published_version(codes, allowed)
        except Exception:
            logger.warning("Android %s release history unavailable", channel)
        return JSONResponse(content={"allowed_versions": allowed,
            "minimum_version_code": minimum}, headers=_NO_STORE)

    @router.get("/api/v3/android-update/check", response_model=None)
    async def android_update_check(
        version_code: int = Query(..., ge=0, le=2_000_000_000),
    ):
        """204 when there is nothing to offer — which is most of the time.

        Every reason to say nothing collapses to the same empty answer: no
        release, no link, no version code on it, or the caller is already on
        it or ahead of it. A client that cannot tell those apart cannot get
        them wrong either.
        """

        try:
            async with session_factory() as session:
                release = await AndroidReleaseService(session).serve()
        except Exception:
            logger.exception("Android update check failed")
            # Fail closed. An app that cannot reach us must keep working, not
            # be told something is wrong with a build it is running fine.
            return Response(status_code=204, headers=_NO_STORE)

        if release is None or not release.can_self_update:
            return Response(status_code=204, headers=_NO_STORE)
        if release.version_code <= version_code:
            return Response(status_code=204, headers=_NO_STORE)

        return JSONResponse(
            content={
                "version_name": release.version_name,
                "version_code": release.version_code,
                "url": release.download_url,
                "size": release.size,
            },
            headers=_NO_STORE,
        )

    @router.get("/downloads/android", name="android_download_redirect")
    async def android_download_redirect():
        """The same file, reachable by a stable link.

        Mirrors `/downloads/macos` and `/downloads/windows` so the Android
        artifact can be handed out or linked to without anyone having to know
        the storage URL, which changes whenever the bucket does.
        """

        try:
            async with session_factory() as session:
                release = await AndroidReleaseService(session).serve()
        except Exception:
            logger.exception("Android download redirect failed")
            release = None

        if release is None or not release.download_url:
            return JSONResponse(
                status_code=404,
                content={"ok": False, "error": "android_download_unavailable"},
                headers=_NO_STORE,
            )
        return RedirectResponse(
            url=release.download_url,
            status_code=307,
            headers={
                **_NO_STORE,
                "Referrer-Policy": "no-referrer",
                "Content-Disposition": f'attachment; filename="{release.file_name}"',
            },
        )

    return router
