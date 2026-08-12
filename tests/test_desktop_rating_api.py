import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.desktop_rating import create_desktop_rating_router
from app.db.base import Base
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_progress import CourseProgress
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.user import User
from app.services.course_gamification_service import CourseGamificationService
from app.services.desktop_auth_service import DesktopAuthService


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="desktop-rating-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
    )


def _user(user_id: int, telegram_id: int, full_name: str, username: str) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class DesktopRatingApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = _settings()
        async with self.sessions() as session:
            session.add(_user(1, 1001, "Desktop Student", "desktop_student"))
            session.add(_user(2, 1002, "Fast Learner", "fast_learner"))
            await session.flush()

            day = CourseGamificationService._local_day(300)
            week_start = CourseGamificationService._week_start(day)
            session.add_all(
                [
                    CourseMiniAppProfile(user_id=1, xp_total=35),
                    CourseMiniAppProfile(user_id=2, xp_total=90),
                    CourseProgress(user_id=1, level="hsk1", completed_lessons_count=1),
                    CourseProgress(user_id=2, level="hsk1", completed_lessons_count=3),
                    CourseXpEvent(
                        user_id=1,
                        activity_type="lesson",
                        activity_ref="rating-test-current",
                        xp=35,
                        activity_date=day,
                        week_start=week_start,
                    ),
                    CourseXpEvent(
                        user_id=2,
                        activity_type="lesson",
                        activity_ref="rating-test-rival",
                        xp=90,
                        activity_date=day,
                        week_start=week_start,
                    ),
                ]
            )
            await session.commit()

            auth = DesktopAuthService(session, self.settings)
            started = await auth.start_link(
                platform="macos",
                app_version="0.1.0",
                installation_key="i" * 48,
            )
            await auth.approve_link(
                display_code=started["display_code"],
                telegram_id=1001,
            )
            linked = await auth.poll_link(
                link_request_id=started["link_request_id"],
                polling_secret=started["polling_secret"],
            )
            self.access_token = linked["access_token"]

        self.app = FastAPI()
        self.app.include_router(
            create_desktop_rating_router(
                session_factory=self.sessions,
                settings_obj=self.settings,
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="https://desktop.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    async def test_leaderboard_returns_success_envelope_and_current_user(self):
        response = await self.client.get(
            "/api/v3/desktop/rating/leaderboard?tz=300",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["weekly_xp"], 35)
        self.assertEqual(payload["league_size"], 2)
        self.assertEqual(payload["rank"], 2)
        self.assertEqual(payload["leaderboard"][0]["name"], "Fast Learner")
        current = [row for row in payload["leaderboard"] if row["is_current_user"]]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["name"], "Desktop Student")
        self.assertNotIn("telegram_id", current[0])

    async def test_rejects_unexpected_query_parameters(self):
        response = await self.client.get(
            "/api/v3/desktop/rating/leaderboard?tz=300&admin=true",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "desktop_rating_request_invalid")


if __name__ == "__main__":
    unittest.main()
