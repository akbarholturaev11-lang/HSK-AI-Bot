import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.course_levels import TRACK_HSK20, TRACK_HSK30
from app.services.course_track_service import CourseTrackError, CourseTrackService
from app.services.hsk30_unlock_service import (
    HSK30_UNLOCK_PLAN_TYPE,
    Hsk30UnlockService,
)


class _FakeState:
    def __init__(
        self,
        *,
        track,
        level,
        completed=0,
        unlocked_at=None,
        unlock_payment_id=None,
    ):
        self.track = track
        self.level = level
        self.completed_lessons_count = completed
        self.unlocked_at = unlocked_at
        self.unlock_payment_id = unlock_payment_id


class CourseTrackServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = CourseTrackService(SimpleNamespace())
        self.user = SimpleNamespace(
            id=7,
            telegram_id=700,
            level="hsk2",
            status="free",
            payment_status="none",
            end_date=None,
        )
        self.progress = SimpleNamespace(
            level="hsk2",
            completed_lessons_count=11,
            current_lesson_id=55,
            current_step="quiz",
            waiting_for="answer",
            homework_status="started",
            needs_review_prompt=True,
            last_opened_at=None,
        )

    async def test_unpaid_user_cannot_switch_to_hsk30(self):
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=None),
            list_for_user=AsyncMock(return_value=[]),
        )
        with self.assertRaises(CourseTrackError) as ctx:
            await self.service.switch(
                self.user,
                target_track=TRACK_HSK30,
                requested_level="nhsk1",
            )
        self.assertEqual(ctx.exception.code, "hsk30_unlock_required")

    async def test_same_track_switch_is_a_noop(self):
        state = _FakeState(track=TRACK_HSK20, level="hsk2", completed=11)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=False),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=None),
            list_for_user=AsyncMock(return_value=[state]),
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(),
        )

        result = await self.service.switch(
            self.user,
            target_track=TRACK_HSK20,
        )

        self.assertEqual(result["active_track"], TRACK_HSK20)
        self.assertEqual(self.user.level, "hsk2")
        self.service.progress_repo.get_by_user_id.assert_not_awaited()

    async def test_same_track_band_change_uses_existing_level_flow(self):
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=False),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=None),
            list_for_user=AsyncMock(return_value=[]),
        )

        with self.assertRaises(CourseTrackError) as ctx:
            await self.service.switch(
                self.user,
                target_track=TRACK_HSK20,
                requested_level="hsk3",
            )

        self.assertEqual(
            ctx.exception.code,
            "course_track_level_change_use_level_flow",
        )

    async def test_change_level_resets_progress_and_updates_saved_hsk20_state(self):
        state = _FakeState(track=TRACK_HSK20, level="hsk2", completed=11)

        async def save_state(row, *, level, completed_lessons_count):
            row.level = level
            row.completed_lessons_count = completed_lessons_count
            return row

        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=False),
            live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(
                side_effect=lambda user_id, track, for_update=False: (
                    state if track == TRACK_HSK20 else None
                )
            ),
            create=AsyncMock(),
            save_progress=AsyncMock(side_effect=save_state),
            list_for_user=AsyncMock(return_value=[state]),
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(return_value=self.progress),
        )
        self.service.session = SimpleNamespace(flush=AsyncMock())

        result = await self.service.change_level(self.user, "hsk3")

        self.assertEqual(self.user.level, "hsk3")
        self.assertEqual(self.progress.level, "hsk3")
        self.assertEqual(self.progress.completed_lessons_count, 0)
        self.assertIsNone(self.progress.current_lesson_id)
        self.assertEqual(self.progress.current_step, "intro")
        self.assertEqual(self.progress.waiting_for, "none")
        self.assertEqual(self.progress.homework_status, "none")
        self.assertFalse(self.progress.needs_review_prompt)
        self.assertEqual(state.level, "hsk3")
        self.assertEqual(state.completed_lessons_count, 0)
        self.assertEqual(result["active_track"], TRACK_HSK20)
        self.service.state_repo.save_progress.assert_awaited_once_with(
            state,
            level="hsk3",
            completed_lessons_count=0,
        )

    async def test_change_level_rejects_cross_track_level(self):
        with self.assertRaises(CourseTrackError) as ctx:
            await self.service.change_level(self.user, "nhsk1")

        self.assertEqual(ctx.exception.code, "course_track_switch_required")

    async def test_change_level_rejects_unreleased_hsk30_band(self):
        self.user.level = "nhsk1"
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        state = _FakeState(track=TRACK_HSK30, level="nhsk1", completed=5)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
            live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=state),
        )

        with self.assertRaises(CourseTrackError) as ctx:
            await self.service.change_level(self.user, "nhsk2")

        self.assertEqual(ctx.exception.code, "hsk30_level_not_live")

    async def test_change_level_moves_paid_hsk30_user_to_live_band(self):
        self.user.level = "nhsk1"
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        self.progress.level = "nhsk1"
        self.progress.completed_lessons_count = 7
        state = _FakeState(track=TRACK_HSK30, level="nhsk1", completed=7)

        async def save_state(row, *, level, completed_lessons_count):
            row.level = level
            row.completed_lessons_count = completed_lessons_count
            return row

        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
            live_levels=AsyncMock(return_value=("nhsk1", "nhsk2")),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=state),
            create=AsyncMock(),
            save_progress=AsyncMock(side_effect=save_state),
            list_for_user=AsyncMock(return_value=[state]),
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(return_value=self.progress),
        )
        self.service.session = SimpleNamespace(flush=AsyncMock())

        result = await self.service.change_level(self.user, "nhsk2")

        self.assertEqual(self.user.level, "nhsk2")
        self.assertEqual(self.progress.level, "nhsk2")
        self.assertEqual(self.progress.completed_lessons_count, 0)
        self.assertEqual(state.level, "nhsk2")
        self.assertEqual(state.completed_lessons_count, 0)
        self.assertEqual(result["active_track"], TRACK_HSK30)
        self.assertEqual(result["active_level"], "nhsk2")

    async def test_nhsk2_cannot_be_selected_before_it_is_live(self):
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
            live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=None),
            list_for_user=AsyncMock(return_value=[]),
        )

        with self.assertRaises(CourseTrackError) as ctx:
            await self.service.switch(
                self.user,
                target_track=TRACK_HSK30,
                requested_level="nhsk2",
            )

        self.assertEqual(ctx.exception.code, "hsk30_level_not_live")

    async def test_unavailable_nhsk4_cannot_be_selected_directly(self):
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=None),
            list_for_user=AsyncMock(return_value=[]),
        )

        with self.assertRaises(CourseTrackError) as ctx:
            await self.service.switch(
                self.user,
                target_track=TRACK_HSK30,
                requested_level="nhsk4",
            )

        self.assertEqual(ctx.exception.code, "invalid_course_track_level")

    async def test_expired_paid_subscription_locks_hsk30_without_permanent_unlock(self):
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(
                return_value=_FakeState(
                    track=TRACK_HSK30,
                    level="nhsk1",
                    completed=8,
                )
            ),
        )

        access = await self.service.hsk30_access(self.user)

        self.assertFalse(access.allowed)
        self.assertFalse(access.paid_access)
        self.assertFalse(access.permanently_unlocked)
        self.assertEqual(access.reason, "hsk30_unlock_required")

    async def test_expired_paid_subscription_keeps_hsk30_with_permanent_unlock(self):
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(
                return_value=_FakeState(
                    track=TRACK_HSK30,
                    level="nhsk1",
                    completed=8,
                    unlocked_at=datetime.now(timezone.utc) - timedelta(days=2),
                )
            ),
        )

        access = await self.service.hsk30_access(self.user)

        self.assertTrue(access.allowed)
        self.assertFalse(access.paid_access)
        self.assertTrue(access.permanently_unlocked)
        self.assertEqual(access.reason, "permanent_unlock")

    async def test_trial_does_not_open_hsk30(self):
        self.user.status = "active"
        self.user.payment_status = "none"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=7)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=None),
        )

        access = await self.service.hsk30_access(self.user)

        self.assertFalse(access.allowed)
        self.assertFalse(access.paid_access)
        self.assertEqual(access.reason, "hsk30_unlock_required")

    async def test_paid_user_can_switch_without_permanent_unlock(self):
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )

        states = {
            TRACK_HSK20: _FakeState(track=TRACK_HSK20, level="hsk2", completed=0),
        }

        async def get_state(user_id, track, for_update=False):
            return states.get(track)

        async def create_state(*, user_id, track, level, completed_lessons_count=0):
            row = _FakeState(
                track=track,
                level=level,
                completed=completed_lessons_count,
            )
            states[track] = row
            return row

        async def save_state(row, *, level, completed_lessons_count):
            row.level = level
            row.completed_lessons_count = completed_lessons_count
            return row

        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(side_effect=get_state),
            create=AsyncMock(side_effect=create_state),
            save_progress=AsyncMock(side_effect=save_state),
            list_for_user=AsyncMock(side_effect=lambda user_id: list(states.values())),
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(return_value=self.progress),
        )
        self.service.session = SimpleNamespace(flush=AsyncMock())

        result = await self.service.switch(
            self.user,
            target_track=TRACK_HSK30,
            requested_level="nhsk1",
        )

        self.assertEqual(self.user.level, "nhsk1")
        self.assertEqual(self.progress.level, "nhsk1")
        self.assertEqual(self.progress.completed_lessons_count, 0)
        self.assertEqual(states[TRACK_HSK20].completed_lessons_count, 11)
        self.assertFalse(result["tracks"][TRACK_HSK30]["access"]["permanently_unlocked"])
        self.assertTrue(result["tracks"][TRACK_HSK30]["access"]["paid_access"])

    async def test_switch_to_existing_hsk30_state_honors_explicit_n3_choice(self):
        self.user.level = "hsk3"
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        self.progress.level = "hsk3"
        self.progress.completed_lessons_count = 11

        hsk20 = _FakeState(track=TRACK_HSK20, level="hsk3", completed=11)
        hsk30 = _FakeState(track=TRACK_HSK30, level="nhsk1", completed=8)
        states = {TRACK_HSK20: hsk20, TRACK_HSK30: hsk30}

        async def save_state(row, *, level, completed_lessons_count):
            row.level = level
            row.completed_lessons_count = completed_lessons_count
            return row

        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
            live_levels=AsyncMock(return_value=("nhsk1", "nhsk2", "nhsk3")),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(side_effect=lambda user_id, track, for_update=False: states.get(track)),
            create=AsyncMock(),
            save_progress=AsyncMock(side_effect=save_state),
            list_for_user=AsyncMock(side_effect=lambda user_id: list(states.values())),
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(return_value=self.progress),
        )
        self.service.session = SimpleNamespace(flush=AsyncMock())

        result = await self.service.switch(
            self.user,
            target_track=TRACK_HSK30,
            requested_level="nhsk3",
        )

        self.assertEqual("nhsk3", self.user.level)
        self.assertEqual("nhsk3", self.progress.level)
        self.assertEqual(0, self.progress.completed_lessons_count)
        self.assertEqual("nhsk3", hsk30.level)
        self.assertEqual(0, hsk30.completed_lessons_count)
        self.assertEqual("nhsk3", result["active_level"])

    async def test_switch_back_restores_saved_progress(self):
        self.user.level = "nhsk1"
        self.user.status = "active"
        self.user.payment_status = "approved"
        self.user.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        self.progress.level = "nhsk1"
        self.progress.completed_lessons_count = 4

        hsk20 = _FakeState(track=TRACK_HSK20, level="hsk3", completed=17)
        hsk30 = _FakeState(track=TRACK_HSK30, level="nhsk1", completed=0)
        states = {TRACK_HSK20: hsk20, TRACK_HSK30: hsk30}

        async def save_state(row, *, level, completed_lessons_count):
            row.level = level
            row.completed_lessons_count = completed_lessons_count
            return row

        self.service.hsk30_feature = SimpleNamespace(
            is_enabled=AsyncMock(return_value=True),
        live_levels=AsyncMock(return_value=("nhsk1",)),
        )
        self.service.state_repo = SimpleNamespace(
            get=AsyncMock(side_effect=lambda user_id, track, for_update=False: states.get(track)),
            create=AsyncMock(),
            save_progress=AsyncMock(side_effect=save_state),
            list_for_user=AsyncMock(side_effect=lambda user_id: list(states.values())),
        )
        self.service.progress_repo = SimpleNamespace(
            get_by_user_id=AsyncMock(return_value=self.progress),
        )
        self.service.session = SimpleNamespace(flush=AsyncMock())

        await self.service.switch(self.user, target_track=TRACK_HSK20)

        self.assertEqual(self.user.level, "hsk3")
        self.assertEqual(self.progress.level, "hsk3")
        self.assertEqual(self.progress.completed_lessons_count, 17)


class Hsk30UnlockServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_grant_does_not_touch_subscription_fields(self):
        user = SimpleNamespace(
            id=9,
            telegram_id=900,
            status="expired",
            payment_status="approved",
            end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            selected_plan_type=None,
        )
        original = (
            user.status,
            user.payment_status,
            user.end_date,
            user.selected_plan_type,
        )
        payment = SimpleNamespace(
            id=44,
            user_telegram_id=900,
            plan_type=HSK30_UNLOCK_PLAN_TYPE,
            payment_status="approved",
        )
        state = _FakeState(track=TRACK_HSK30, level="nhsk1")

        service = Hsk30UnlockService(SimpleNamespace())
        service.state_repo = SimpleNamespace(
            get=AsyncMock(return_value=state),
            create=AsyncMock(),
        )
        service.session = SimpleNamespace(flush=AsyncMock())

        self.assertTrue(await service.grant(user=user, payment=payment))
        self.assertIsNotNone(state.unlocked_at)
        self.assertEqual(state.unlock_payment_id, 44)
        self.assertEqual(
            (
                user.status,
                user.payment_status,
                user.end_date,
                user.selected_plan_type,
            ),
            original,
        )


if __name__ == "__main__":
    unittest.main()
