from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import func, select

from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService


LEAGUES = (
    ("Bronze", 0, 500),
    ("Silver", 500, 1500),
    ("Gold", 1500, 3000),
    ("Sapphire", 3000, None),
)


class CourseGamificationService:
    def __init__(self, session):
        self.session = session
        self.profiles = CourseMiniAppProfileService(session)

    @staticmethod
    def league_for_xp(xp_total: int) -> str:
        xp_total = max(0, int(xp_total or 0))
        return next(name for name, low, high in reversed(LEAGUES) if xp_total >= low)

    @staticmethod
    def _league_range(xp_total: int) -> tuple[int, int | None]:
        xp_total = max(0, int(xp_total or 0))
        return next((low, high) for _, low, high in reversed(LEAGUES) if xp_total >= low)

    @staticmethod
    def _local_day(offset_minutes: int, now: datetime | None = None) -> date:
        now = now or datetime.now(timezone.utc)
        return (now + timedelta(minutes=max(-720, min(840, int(offset_minutes or 0))))).date()

    @staticmethod
    def _week_start(day: date) -> date:
        return day - timedelta(days=day.weekday())

    @classmethod
    def _weekly_reset(cls, offset_minutes: int, now: datetime | None = None) -> tuple[str, int]:
        now_utc = now or datetime.now(timezone.utc)
        offset = timedelta(minutes=max(-720, min(840, int(offset_minutes or 0))))
        local_now = now_utc + offset
        next_reset_day = cls._week_start(local_now.date()) + timedelta(days=7)
        next_reset_utc = datetime.combine(
            next_reset_day,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) - offset
        return next_reset_utc.isoformat(), max(0, int((next_reset_utc - now_utc).total_seconds()))

    @staticmethod
    def next_streak(last_activity_date: date | None, current_streak: int, day: date) -> tuple[int, bool]:
        if last_activity_date == day:
            return max(1, int(current_streak or 0)), False
        if last_activity_date == day - timedelta(days=1):
            return max(1, int(current_streak or 0) + 1), True
        return 1, True

    async def award(
        self,
        user,
        *,
        activity_type: str,
        activity_ref: str,
        base_xp: int,
        level: str | None = None,
    ) -> dict:
        activity_type = str(activity_type or "").strip().lower()[:32]
        activity_ref = str(activity_ref or "").strip()[:120]
        if not activity_type or not activity_ref:
            raise ValueError("Gamification activity type and ref are required")
        profile = await self.profiles.get_or_create(user.id)
        existing_result = await self.session.execute(
            select(CourseXpEvent).where(
                CourseXpEvent.user_id == user.id,
                CourseXpEvent.activity_ref == activity_ref,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return await self.snapshot(user, profile=profile, awarded_xp=0, duplicate=True)

        day = self._local_day(profile.timezone_offset_minutes)
        streak, first_activity_today = self.next_streak(
            profile.last_activity_date,
            profile.current_streak,
            day,
        )
        streak_bonus = 5 if first_activity_today else 0
        awarded_xp = max(1, min(200, int(base_xp or 0))) + streak_bonus
        profile.xp_total = int(profile.xp_total or 0) + awarded_xp
        profile.current_streak = streak
        profile.longest_streak = max(int(profile.longest_streak or 0), streak)
        profile.last_activity_date = day
        event = CourseXpEvent(
            user_id=user.id,
            activity_type=activity_type,
            activity_ref=activity_ref,
            xp=awarded_xp,
            activity_date=day,
            week_start=self._week_start(day),
        )
        self.session.add(event)
        await self.session.flush()

        analytics = CourseMiniAppAnalyticsService(self.session)
        shared = {
            "telegram_id": user.telegram_id,
            "user_id": user.id,
            "level": level,
            "dedupe_key": activity_ref,
        }
        await analytics.record_server_event(
            event_name="xp_earned",
            payload={"activity_type": activity_type, "xp": awarded_xp, "streak_bonus": streak_bonus},
            **shared,
        )
        await analytics.record_server_event(
            event_name="league_points_earned",
            payload={"activity_type": activity_type, "xp": awarded_xp},
            **shared,
        )
        if first_activity_today:
            await analytics.record_server_event(
                event_name="streak_updated",
                payload={"streak": streak, "activity_date": day.isoformat()},
                **shared,
            )
        return await self.snapshot(user, profile=profile, awarded_xp=awarded_xp, duplicate=False)

    async def snapshot(
        self,
        user,
        *,
        profile: CourseMiniAppProfile | None = None,
        awarded_xp: int = 0,
        duplicate: bool = False,
    ) -> dict:
        profile = profile or await self.profiles.get_or_create(user.id)
        day = self._local_day(profile.timezone_offset_minutes)
        week_start = self._week_start(day)
        weekly_result = await self.session.execute(
            select(func.coalesce(func.sum(CourseXpEvent.xp), 0)).where(
                CourseXpEvent.user_id == user.id,
                CourseXpEvent.week_start == week_start,
            )
        )
        weekly_xp = int(weekly_result.scalar_one() or 0)
        chest_progress = int(profile.xp_total or 0) % 100
        energy_current = max(0, min(5, 3 + weekly_xp // 120))
        weekly_reset_at, weekly_reset_seconds = self._weekly_reset(profile.timezone_offset_minutes)
        return {
            "xp": int(profile.xp_total or 0),
            "awarded_xp": int(awarded_xp or 0),
            "duplicate": bool(duplicate),
            "streak": int(profile.current_streak or 0),
            "longest_streak": int(profile.longest_streak or 0),
            "league": self.league_for_xp(profile.xp_total),
            "weekly_xp": weekly_xp,
            "league_points": weekly_xp,
            "weekly_reset_day": "monday",
            "weekly_reset_at": weekly_reset_at,
            "weekly_reset_seconds": weekly_reset_seconds,
            "energy": {
                "current": energy_current,
                "max": 5,
                "blocks_study": False,
            },
            "reward_chest": {
                "ready": chest_progress >= 80 and int(profile.xp_total or 0) > 0,
                "progress": chest_progress,
                "next_xp": 0 if chest_progress >= 80 else 80 - chest_progress,
            },
        }

    async def leaderboard(
        self,
        user,
        limit: int | None = None,
        timezone_offset_minutes: int | None = None,
    ) -> dict:
        profile = await self.profiles.get_or_create(user.id)
        if timezone_offset_minutes is not None:
            profile.timezone_offset_minutes = max(-720, min(840, int(timezone_offset_minutes)))
        snapshot = await self.snapshot(user, profile=profile)
        day = self._local_day(profile.timezone_offset_minutes)
        week_start = self._week_start(day)
        weekly = (
            select(
                CourseXpEvent.user_id.label("user_id"),
                func.sum(CourseXpEvent.xp).label("weekly_xp"),
            )
            .where(CourseXpEvent.week_start == week_start)
            .group_by(CourseXpEvent.user_id)
            .subquery()
        )
        query = (
            select(
                User.id,
                User.telegram_id,
                User.full_name,
                User.username,
                User.status,
                User.payment_status,
                User.end_date,
                CourseMiniAppProfile.xp_total,
                CourseProgress.level,
                CourseProgress.completed_lessons_count,
                func.coalesce(weekly.c.weekly_xp, 0),
            )
            .join(CourseMiniAppProfile, CourseMiniAppProfile.user_id == User.id)
            .outerjoin(CourseProgress, CourseProgress.user_id == User.id)
            .outerjoin(weekly, weekly.c.user_id == User.id)
            .order_by(
                func.coalesce(weekly.c.weekly_xp, 0).desc(),
                User.id.asc(),
            )
        )
        rows = (await self.session.execute(query)).all()
        ranked = []
        current_rank = 0
        max_items = max(1, min(500, int(limit))) if limit else None
        for index, (
            user_id,
            telegram_id,
            full_name,
            username,
            status,
            payment_status,
            end_date,
            xp_total,
            course_level,
            completed_lessons_count,
            weekly_xp,
        ) in enumerate(rows, 1):
            if int(user_id) == int(user.id):
                current_rank = index
            if max_items is None or index <= max_items or int(user_id) == int(user.id):
                ranked.append(
                    {
                        "rank": index,
                        "name": str(full_name or "HSK Student").strip()[:40],
                        "telegram_id": int(telegram_id) if telegram_id else None,
                        "username": str(username or "").strip().lstrip("@")[:32],
                        "xp": int(weekly_xp or 0),
                        "league_points": int(weekly_xp or 0),
                        "total_xp": int(xp_total or 0),
                        "course_level": str(course_level or "").strip()[:32],
                        "completed_lessons": int(completed_lessons_count or 0),
                        "is_paid": CourseMiniAppAccessService.is_paid_user(
                            SimpleNamespace(status=status, payment_status=payment_status, end_date=end_date)
                        ),
                        "is_current_user": int(user_id) == int(user.id),
                    }
                )
        if current_rank and profile.last_known_rank is None:
            profile.last_known_rank = current_rank
        return {**snapshot, "rank": current_rank or 1, "league_size": len(rows), "leaderboard": ranked}

    async def open_reward_chest(self, user) -> dict:
        profile = await self.profiles.get_or_create(user.id)
        snapshot = await self.snapshot(user, profile=profile)
        if not snapshot["reward_chest"]["ready"]:
            return {"ok": False, "error": "reward_chest_not_ready", **snapshot}
        reward_xp = (5, 10, 20)[int(profile.xp_total or 0) % 3]
        reward = await self.award(
            user,
            activity_type="reward_chest",
            activity_ref=f"reward-chest:{user.id}:{profile.xp_total // 100}:{profile.xp_total}",
            base_xp=reward_xp,
        )
        return {"ok": True, "reward_type": "xp", "reward_value": reward_xp, **reward}
