"""Course v3 adapter for the native Android client.

Android shares every course rule with the desktop client: the same access
policy, the same XP and streak awards, the same mistake persistence and the
same idempotent completion. Nothing is reimplemented here.

The only difference is the analytics and dedupe namespace, so that an Android
completion can never collide with a desktop one and Android never appears in
the desktop funnel.
"""

from __future__ import annotations

from app.services.desktop_course_service import (
    DesktopCourseError,
    DesktopCourseService,
)


__all__ = ["AndroidCourseError", "AndroidCourseService"]

# The error contract is shared on purpose: one stable set of codes for every
# native client means the clients can share their error-to-copy mapping.
AndroidCourseError = DesktopCourseError


class AndroidCourseService(DesktopCourseService):
    CLIENT_NAMESPACE = "android"
