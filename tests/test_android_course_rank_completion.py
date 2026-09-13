"""Focused regression coverage for Android lesson-completion rank snapshots."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.android_course_service import AndroidCourseService
from app.services.desktop_course_service import DesktopCourseService


@pytest.mark.asyncio
async def test_completion_returns_verified_rank_before_and_after():
    service = AndroidCourseService.__new__(AndroidCourseService)
    user = SimpleNamespace(id=1)
    context = SimpleNamespace(user=user)
    base_result = {
        "ok": True,
        "completed_lesson": 1,
        "completed_lessons_count": 1,
        "gamification": {"xp": 25},
    }

    with (
        patch.object(service, "_context", AsyncMock(return_value=context)),
        patch.object(service, "_safe_rank", AsyncMock(side_effect=[12, 9])) as safe_rank,
        patch.object(DesktopCourseService, "complete", AsyncMock(return_value=base_result.copy())),
    ):
        result = await service.complete(
            "token",
            lesson_order=1,
            event_id="android:rank-snapshot-1",
        )

    assert result["rank_before"] == 12
    assert result["rank_after"] == 9
    assert safe_rank.await_count == 2


@pytest.mark.asyncio
async def test_duplicate_completion_does_not_requery_or_fake_a_rank_change():
    service = AndroidCourseService.__new__(AndroidCourseService)
    user = SimpleNamespace(id=1)
    context = SimpleNamespace(user=user)
    duplicate_result = {
        "ok": True,
        "duplicate": True,
        "completed_lesson": 1,
        "completed_lessons_count": 1,
        "gamification": {"xp": 25, "duplicate": True},
    }

    with (
        patch.object(service, "_context", AsyncMock(return_value=context)),
        patch.object(service, "_safe_rank", AsyncMock(return_value=12)) as safe_rank,
        patch.object(DesktopCourseService, "complete", AsyncMock(return_value=duplicate_result.copy())),
    ):
        result = await service.complete(
            "token",
            lesson_order=1,
            event_id="android:rank-snapshot-duplicate",
        )

    assert result["rank_before"] == 12
    assert result["rank_after"] == 12
    assert safe_rank.await_count == 1
