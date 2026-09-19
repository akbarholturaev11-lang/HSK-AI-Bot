"""What an installed Android app asks before it offers to update itself.

Only the `direct` channel ever calls this. Google Play forbids an app it
distributes from updating itself by any other route, which is why the client
half lives in `src/direct` and the Play build has a no-op in its place.

The answer is deliberately thin: a version code to compare, a name to show and
one https link. The server does not decide whether to update — it cannot know
whether the learner is mid-lesson or on mobile data — it only says what exists.
"""

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.services.android_release_service import AndroidReleaseService


logger = logging.getLogger(__name__)

_NO_STORE = {"Cache-Control": "no-store"}


def create_android_update_router(*, session_factory) -> APIRouter:
    router = APIRouter(tags=["android-update"])

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
