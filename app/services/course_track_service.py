from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.course_track_state_repo import CourseTrackStateRepository
from app.services.course_levels import (
    TRACK_HSK20,
    TRACK_HSK30,
    content_level,
    level_spec,
)
from app.services.hsk30_feature_service import Hsk30FeatureService
from app.services.hsk30_unlock_service import Hsk30UnlockService
from app.services.user_access_state_service import UserAccessStateService


class CourseTrackError(RuntimeError):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class CourseTrackAccess:
    feature_enabled: bool
    paid_access: bool
    permanently_unlocked: bool
    payment_pending: bool = False
    provisional_access: bool = False
    payment_rejected: bool = False

    @property
    def allowed(self) -> bool:
        return self.feature_enabled and (
            self.paid_access or self.permanently_unlocked or self.provisional_access
        )

    @property
    def reason(self) -> str:
        if not self.feature_enabled:
            return "hsk30_disabled"
        if self.permanently_unlocked:
            return "permanent_unlock"
        if self.paid_access:
            return "paid_subscription"
        if self.payment_pending:
            return "payment_pending"
        if self.payment_rejected:
            return "payment_rejected"
        return "hsk30_unlock_required"

    def payload(self) -> dict:
        return {
            "feature_enabled": self.feature_enabled,
            "paid_access": self.paid_access,
            "permanently_unlocked": self.permanently_unlocked,
            "payment_pending": self.payment_pending,
            "provisional_access": self.provisional_access,
            "payment_rejected": self.payment_rejected,
            "allowed": self.allowed,
            "reason": self.reason,
        }


class CourseTrackService:
    """Persist and restore the active HSK 2.0 and HSK 3.0 course states.

    users.level and the existing single course_progress row stay the active
    state used by the old course engine. Before switching, that active state is
    copied to course_track_states; the target track is restored into the same
    legacy fields. This preserves parallel progress without replacing the
    current course engine.
    """

    def __init__(self, session):
        self.session = session
        self.state_repo = CourseTrackStateRepository(session)
        self.progress_repo = CourseProgressRepository(session)
        self.hsk30_feature = Hsk30FeatureService(session)
        self.hsk30_unlock = Hsk30UnlockService(session)

    @staticmethod
    def track_for_level(level: str | None) -> str:
        spec = level_spec(level)
        return spec.track if spec else TRACK_HSK20

    @staticmethod
    def default_level(track: str) -> str:
        if track == TRACK_HSK30:
            return "nhsk1"
        if track == TRACK_HSK20:
            return "hsk1"
        raise CourseTrackError("invalid_course_track", status_code=422)

    @staticmethod
    def _validate_level_for_track(level: str | None, track: str) -> str:
        normalized = str(level or "").strip().lower()
        if not normalized:
            return CourseTrackService.default_level(track)
        spec = level_spec(normalized)
        if not spec or spec.track != track or not spec.selectable:
            raise CourseTrackError("invalid_course_track_level", status_code=422)
        return normalized

    async def _state(
        self,
        user_id: int,
        track: str,
        *,
        for_update: bool = False,
    ):
        return await self.state_repo.get(user_id, track, for_update=for_update)

    async def hsk30_access(self, user) -> CourseTrackAccess:
        enabled = await self.hsk30_feature.is_enabled()
        row = await self._state(int(user.id), TRACK_HSK30)
        permanently_unlocked = bool(row and row.unlocked_at)
        paid = UserAccessStateService.is_paid(user)
        if not enabled or permanently_unlocked or paid:
            return CourseTrackAccess(
                feature_enabled=enabled,
                paid_access=paid,
                permanently_unlocked=permanently_unlocked,
            )

        review = await self.hsk30_unlock.review_state(user)
        pending = review["pending_payment"] is not None
        return CourseTrackAccess(
            feature_enabled=enabled,
            paid_access=paid,
            permanently_unlocked=permanently_unlocked,
            payment_pending=pending,
            provisional_access=bool(review["provisional_access"]),
            payment_rejected=bool(review["payment_rejected"]),
        )

    async def status(self, user) -> dict:
        active_track = self.track_for_level(getattr(user, "level", None))
        states = {
            row.track: row
            for row in await self.state_repo.list_for_user(int(user.id))
        }
        access = await self.hsk30_access(user)
        live_levels = await self.hsk30_feature.live_levels()
        new_badge_reader = getattr(self.hsk30_feature, "new_badge", None)
        new_badge = (
            await new_badge_reader()
            if callable(new_badge_reader)
            else {"is_new": False, "enabled_at": None, "new_until": None}
        )

        def state_payload(track: str) -> dict:
            row = states.get(track)
            if row:
                return {
                    "track": track,
                    "level": row.level,
                    "completed_lessons_count": int(row.completed_lessons_count or 0),
                    "unlocked_at": row.unlocked_at.isoformat() if row.unlocked_at else None,
                    "unlock_payment_id": row.unlock_payment_id,
                }
            return {
                "track": track,
                "level": self.default_level(track),
                "completed_lessons_count": 0,
                "unlocked_at": None,
                "unlock_payment_id": None,
            }

        return {
            "active_track": active_track,
            "active_level": str(getattr(user, "level", "") or ""),
            "tracks": {
                TRACK_HSK20: state_payload(TRACK_HSK20),
                TRACK_HSK30: {
                    **state_payload(TRACK_HSK30),
                    "access": access.payload(),
                    "live_levels": list(live_levels),
                    "new_badge": new_badge,
                },
            },
        }

    async def _save_active_state(self, user, progress) -> None:
        current_track = self.track_for_level(getattr(user, "level", None))
        current_level = self._validate_level_for_track(
            getattr(user, "level", None),
            current_track,
        )
        completed = int(getattr(progress, "completed_lessons_count", 0) or 0)

        row = await self._state(int(user.id), current_track, for_update=True)
        if row is None:
            await self.state_repo.create(
                user_id=int(user.id),
                track=current_track,
                level=current_level,
                completed_lessons_count=completed,
            )
        else:
            await self.state_repo.save_progress(
                row,
                level=current_level,
                completed_lessons_count=completed,
            )

    async def change_level(
        self,
        user,
        requested_level: str,
        *,
        allow_locked_hsk30: bool = False,
    ) -> dict:
        """Change band inside the active course track.

        Track switching is a separate operation. A level change resets the
        current track progress to the beginning of the selected band and keeps
        the saved track state in sync, so switching away and back restores the
        same band instead of an older one.
        """

        current_track = self.track_for_level(getattr(user, "level", None))
        requested_spec = level_spec(requested_level)
        if (
            requested_spec
            and requested_spec.selectable
            and requested_spec.track != current_track
        ):
            raise CourseTrackError("course_track_switch_required", status_code=409)
        target_level = self._validate_level_for_track(
            requested_level,
            current_track,
        )

        if current_track == TRACK_HSK30:
            access = await self.hsk30_access(user)
            if not access.feature_enabled:
                raise CourseTrackError(access.reason, status_code=403)
            if not access.allowed and not allow_locked_hsk30:
                raise CourseTrackError(access.reason, status_code=403)
            live_levels = await self.hsk30_feature.live_levels()
            if target_level not in live_levels:
                raise CourseTrackError("hsk30_level_not_live", status_code=403)

        current_level = self._validate_level_for_track(
            getattr(user, "level", None),
            current_track,
        )
        if target_level == current_level:
            return await self.status(user)

        progress = await self.progress_repo.get_by_user_id(
            int(user.id),
            for_update=True,
        )
        if progress is None:
            progress = await self.progress_repo.create(
                user_id=int(user.id),
                level=target_level,
                current_lesson_id=None,
            )

        user.level = target_level
        progress.level = content_level(target_level)
        progress.completed_lessons_count = 0
        progress.current_lesson_id = None
        progress.current_step = "intro"
        progress.waiting_for = "none"
        progress.homework_status = "none"
        progress.needs_review_prompt = False
        progress.last_opened_at = datetime.now(timezone.utc)

        row = await self._state(int(user.id), current_track, for_update=True)
        if row is None:
            await self.state_repo.create(
                user_id=int(user.id),
                track=current_track,
                level=target_level,
                completed_lessons_count=0,
            )
        else:
            await self.state_repo.save_progress(
                row,
                level=target_level,
                completed_lessons_count=0,
            )

        await self.session.flush()
        return await self.status(user)

    async def switch(
        self,
        user,
        *,
        target_track: str,
        requested_level: str | None = None,
        allow_locked_hsk30: bool = False,
    ) -> dict:
        target_track = str(target_track or "").strip().lower()
        if target_track not in {TRACK_HSK20, TRACK_HSK30}:
            raise CourseTrackError("invalid_course_track", status_code=422)

        current_track = self.track_for_level(getattr(user, "level", None))
        live_levels: tuple[str, ...] = ()
        if target_track == TRACK_HSK30:
            access = await self.hsk30_access(user)
            if not access.feature_enabled:
                raise CourseTrackError(access.reason, status_code=403)
            if not access.allowed and not allow_locked_hsk30:
                raise CourseTrackError(access.reason, status_code=403)
            live_levels = await self.hsk30_feature.live_levels()
            if not live_levels:
                raise CourseTrackError("hsk30_no_live_levels", status_code=403)

        validated_requested_level = (
            self._validate_level_for_track(requested_level, target_track)
            if requested_level
            else None
        )
        if (
            target_track == TRACK_HSK30
            and validated_requested_level
            and validated_requested_level not in live_levels
        ):
            raise CourseTrackError("hsk30_level_not_live", status_code=403)

        if target_track == current_track:
            if (
                target_track == TRACK_HSK30
                and self._validate_level_for_track(
                    getattr(user, "level", None),
                    TRACK_HSK30,
                )
                not in live_levels
            ):
                raise CourseTrackError("hsk30_level_not_live", status_code=403)
            current_level = self._validate_level_for_track(
                getattr(user, "level", None),
                current_track,
            )
            if requested_level:
                requested = self._validate_level_for_track(
                    requested_level,
                    current_track,
                )
                if requested != current_level:
                    raise CourseTrackError(
                        "course_track_level_change_use_level_flow",
                        status_code=409,
                    )
            return await self.status(user)

        progress = await self.progress_repo.get_by_user_id(
            int(user.id),
            for_update=True,
        )
        if progress is None:
            progress = await self.progress_repo.create(
                user_id=int(user.id),
                level=content_level(getattr(user, "level", None)),
                current_lesson_id=None,
            )

        await self._save_active_state(user, progress)

        target_state = await self._state(
            int(user.id),
            target_track,
            for_update=True,
        )
        if target_state is None:
            target_level = (
                validated_requested_level
                or (live_levels[0] if target_track == TRACK_HSK30 else self.default_level(target_track))
            )
            target_state = await self.state_repo.create(
                user_id=int(user.id),
                track=target_track,
                level=target_level,
                completed_lessons_count=0,
            )
            target_completed = 0
        else:
            stored_level = self._validate_level_for_track(
                target_state.level,
                target_track,
            )
            target_level = validated_requested_level or stored_level
            if target_track == TRACK_HSK30 and target_level not in live_levels:
                raise CourseTrackError("hsk30_level_not_live", status_code=403)

            # A level explicitly chosen while entering the other track is a
            # real band change, not a hint. Preserve progress when the learner
            # picks the saved band; reset only when they deliberately choose a
            # different band.
            if validated_requested_level and target_level != stored_level:
                await self.state_repo.save_progress(
                    target_state,
                    level=target_level,
                    completed_lessons_count=0,
                )
                target_completed = 0
            else:
                target_completed = int(
                    target_state.completed_lessons_count or 0
                )

        user.level = target_level
        progress.level = content_level(target_level)
        progress.completed_lessons_count = target_completed
        progress.current_lesson_id = None
        progress.current_step = "intro"
        progress.waiting_for = "none"
        progress.homework_status = "none"
        progress.needs_review_prompt = False
        progress.last_opened_at = datetime.now(timezone.utc)

        await self.session.flush()
        return await self.status(user)
