import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.course_gamification_service import CourseGamificationService


class CourseGamificationServiceTests(unittest.TestCase):
    def test_league_thresholds(self):
        self.assertEqual(CourseGamificationService.league_for_xp(0), "Bronze")
        self.assertEqual(CourseGamificationService.league_for_xp(500), "Silver")
        self.assertEqual(CourseGamificationService.league_for_xp(1500), "Gold")
        self.assertEqual(CourseGamificationService.league_for_xp(3000), "Sapphire")

    def test_streak_only_advances_once_per_day(self):
        day = date(2026, 6, 23)
        self.assertEqual(CourseGamificationService.next_streak(day, 4, day), (4, False))
        self.assertEqual(CourseGamificationService.next_streak(date(2026, 6, 22), 4, day), (5, True))
        self.assertEqual(CourseGamificationService.next_streak(date(2026, 6, 20), 4, day), (1, True))

    def test_week_starts_on_monday(self):
        self.assertEqual(CourseGamificationService._week_start(date(2026, 6, 25)), date(2026, 6, 22))

    def test_weekly_reset_countdown_uses_next_monday_midnight(self):
        reset_at, seconds = CourseGamificationService._weekly_reset(
            0,
            datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(reset_at, "2026-06-29T00:00:00+00:00")
        self.assertEqual(seconds, 12 * 60 * 60)


class CourseGamificationCalendarTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _scalar_result(value):
        result = MagicMock()
        result.scalar_one.return_value = value
        return result

    @staticmethod
    def _dates_result(values):
        result = MagicMock()
        result.scalars.return_value.all.return_value = values
        return result

    async def test_snapshot_returns_real_current_week_activity_dates(self):
        session = MagicMock()
        session.execute = AsyncMock(
            side_effect=[
                self._scalar_result(75),
                self._scalar_result(25),
                self._dates_result(
                    [date(2026, 6, 22), date(2026, 6, 24), date(2026, 6, 25)]
                ),
            ]
        )
        service = CourseGamificationService(session)
        profile = SimpleNamespace(
            timezone_offset_minutes=300,
            xp_total=240,
            current_streak=3,
            longest_streak=8,
            last_activity_date=date(2026, 6, 25),
        )
        user = SimpleNamespace(id=42)

        with patch.object(service, "_local_day", return_value=date(2026, 6, 25)):
            result = await service.snapshot(user, profile=profile)

        self.assertEqual(result["local_date"], "2026-06-25")
        self.assertEqual(result["week_start"], "2026-06-22")
        self.assertEqual(
            result["week_activity_dates"],
            ["2026-06-22", "2026-06-24", "2026-06-25"],
        )
        self.assertEqual(result["streak"], 3)
        self.assertEqual(session.execute.await_count, 3)

    async def test_snapshot_hides_expired_or_future_dated_streak(self):
        for last_activity in (date(2026, 6, 20), date(2026, 6, 26)):
            with self.subTest(last_activity=last_activity):
                session = MagicMock()
                session.execute = AsyncMock(
                    side_effect=[
                        self._scalar_result(0),
                        self._scalar_result(0),
                        self._dates_result([]),
                    ]
                )
                service = CourseGamificationService(session)
                profile = SimpleNamespace(
                    timezone_offset_minutes=0,
                    xp_total=20,
                    current_streak=5,
                    longest_streak=5,
                    last_activity_date=last_activity,
                )

                with patch.object(service, "_local_day", return_value=date(2026, 6, 25)):
                    result = await service.snapshot(SimpleNamespace(id=7), profile=profile)

                self.assertEqual(result["streak"], 0)
                self.assertEqual(result["previous_streak"], 5)

    async def test_award_reports_reset_even_when_streak_drops_from_five_to_one(self):
        session = MagicMock()
        existing = MagicMock()
        existing.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=existing)
        session.flush = AsyncMock()
        service = CourseGamificationService(session)
        profile = SimpleNamespace(
            timezone_offset_minutes=0,
            xp_total=100,
            current_streak=5,
            longest_streak=5,
            last_activity_date=date(2026, 6, 20),
        )
        service.profiles.get_or_create = AsyncMock(return_value=profile)
        service.snapshot = AsyncMock(return_value={"streak": 1})
        user = SimpleNamespace(id=9, telegram_id=9009)

        with (
            patch.object(service, "_local_day", return_value=date(2026, 6, 25)),
            patch(
                "app.services.course_gamification_service.CourseMiniAppAnalyticsService"
            ) as analytics_cls,
        ):
            analytics_cls.return_value.record_server_event = AsyncMock()
            await service.award(
                user,
                activity_type="lesson",
                activity_ref="v3-part:hsk1:8:complete",
                base_xp=20,
                level="hsk1",
            )

        kwargs = service.snapshot.await_args.kwargs
        self.assertTrue(kwargs["streak_updated"])
        self.assertTrue(kwargs["streak_reset"])
        self.assertEqual(kwargs["previous_streak"], 5)
        self.assertEqual(kwargs["activity_date"], date(2026, 6, 25))
        self.assertEqual(profile.current_streak, 1)


if __name__ == "__main__":
    unittest.main()
