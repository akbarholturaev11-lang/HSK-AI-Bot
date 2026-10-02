from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.services.course_levels import TRACK_HSK30
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_track_service import CourseTrackService
from app.services.hsk30_feature_service import Hsk30FeatureService
from app.services.hsk30_unlock_service import Hsk30UnlockService


HSK30_PROMO_MAX_SHOWS = 2
HSK30_PROMO_MIN_INTERVAL = timedelta(days=3)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class Hsk30PromoService:
    def __init__(self, session):
        self.session = session
        self.profile_service = CourseMiniAppProfileService(session)
        self.feature = Hsk30FeatureService(session)
        self.unlock = Hsk30UnlockService(session)

    async def _profile(self, user_id: int, *, for_update: bool = False):
        profile = await self.profile_service.get_or_create(int(user_id))
        if not for_update:
            return profile
        result = await self.session.execute(
            select(CourseMiniAppProfile)
            .where(CourseMiniAppProfile.user_id == int(user_id))
            .with_for_update()
        )
        return result.scalar_one()

    async def state(
        self,
        user,
        *,
        now: datetime | None = None,
        profile=None,
    ) -> dict:
        now = _utc(now) or datetime.now(timezone.utc)
        profile = profile or await self._profile(int(user.id))
        shown_count = max(0, int(getattr(profile, "hsk30_promo_shown_count", 0) or 0))
        last_shown = _utc(getattr(profile, "hsk30_promo_last_shown_at", None))
        feature_enabled = await self.feature.is_enabled()
        onboarded_at = _utc(getattr(profile, "onboarding_completed_at", None))
        active_track = CourseTrackService.track_for_level(
            getattr(user, "level", None)
        )
        permanently_unlocked = await self.unlock.is_permanently_unlocked(user)

        if not feature_enabled:
            eligible = False
            reason = "hsk30_disabled"
        elif active_track == TRACK_HSK30:
            eligible = False
            reason = "already_on_hsk30"
        elif permanently_unlocked:
            eligible = False
            reason = "already_unlocked"
        elif onboarded_at is None:
            eligible = False
            reason = "onboarding_not_completed"
        elif shown_count >= HSK30_PROMO_MAX_SHOWS:
            eligible = False
            reason = "show_cap_reached"
        elif last_shown and now - last_shown < HSK30_PROMO_MIN_INTERVAL:
            eligible = False
            reason = "cooldown"
        else:
            eligible = True
            reason = "eligible"

        next_eligible_at = None
        if (
            not eligible
            and reason == "cooldown"
            and last_shown is not None
        ):
            next_eligible_at = last_shown + HSK30_PROMO_MIN_INTERVAL

        legacy_level = str(getattr(user, "level", "") or "").strip().lower()
        recommended_level = {
            "beginner": "nhsk1",
            "hsk1": "nhsk1",
            "hsk2": "nhsk1",
            "hsk3": "nhsk2",
            "hsk4": "nhsk3",
        }.get(legacy_level, "nhsk1")

        return {
            "eligible": eligible,
            "reason": reason,
            "recommended_level": recommended_level,
            "shown_count": shown_count,
            "max_shows": HSK30_PROMO_MAX_SHOWS,
            "last_shown_at": last_shown.isoformat() if last_shown else None,
            "next_eligible_at": (
                next_eligible_at.isoformat() if next_eligible_at else None
            ),
        }

    async def mark_shown(
        self,
        user,
        *,
        now: datetime | None = None,
    ) -> dict:
        now = _utc(now) or datetime.now(timezone.utc)
        profile = await self._profile(int(user.id), for_update=True)
        current = await self.state(user, now=now, profile=profile)
        if not current["eligible"]:
            return {
                **current,
                "recorded": False,
            }

        profile.hsk30_promo_shown_count = int(
            getattr(profile, "hsk30_promo_shown_count", 0) or 0
        ) + 1
        profile.hsk30_promo_last_shown_at = now
        await self.session.flush()
        after = await self.state(user, now=now, profile=profile)
        return {
            **after,
            "recorded": True,
        }
