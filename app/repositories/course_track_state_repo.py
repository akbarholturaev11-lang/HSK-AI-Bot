from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_track_state import CourseTrackState


class CourseTrackStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self,
        user_id: int,
        track: str,
        *,
        for_update: bool = False,
    ) -> CourseTrackState | None:
        query = select(CourseTrackState).where(
            CourseTrackState.user_id == int(user_id),
            CourseTrackState.track == str(track),
        )
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[CourseTrackState]:
        result = await self.session.execute(
            select(CourseTrackState)
            .where(CourseTrackState.user_id == int(user_id))
            .order_by(CourseTrackState.track)
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        user_id: int,
        track: str,
        level: str,
        completed_lessons_count: int = 0,
    ) -> CourseTrackState:
        row = CourseTrackState(
            user_id=int(user_id),
            track=str(track),
            level=str(level),
            completed_lessons_count=max(0, int(completed_lessons_count or 0)),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def save_progress(
        self,
        row: CourseTrackState,
        *,
        level: str,
        completed_lessons_count: int,
    ) -> CourseTrackState:
        row.level = str(level)
        row.completed_lessons_count = max(0, int(completed_lessons_count or 0))
        await self.session.flush()
        return row
