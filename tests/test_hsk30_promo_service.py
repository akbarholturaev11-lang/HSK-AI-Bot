import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_track_state import CourseTrackState
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.hsk30_feature_service import HSK30_ENABLED_SETTINGS_KEY, Hsk30FeatureService
from app.services.hsk30_promo_service import Hsk30PromoService


def _user() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=5001,
        full_name="Promo Test",
        language="uz",
        level="hsk2",
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


class Hsk30PromoServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(_user())
            await session.flush()
            profile = await CourseMiniAppProfileService(session).get_or_create(1)
            profile.onboarding_completed_at = datetime.now(timezone.utc) - timedelta(days=30)
            await session.flush()
            await BotSettingRepository(session).set_bool(
                HSK30_ENABLED_SETTINGS_KEY,
                True,
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_two_show_cap_and_three_day_interval_are_server_owned(self):
        t0 = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)

        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = Hsk30PromoService(session)

            initial = await service.state(user, now=t0)
            self.assertTrue(initial["eligible"])
            self.assertEqual(initial["shown_count"], 0)

            first = await service.mark_shown(user, now=t0)
            await session.commit()
            self.assertTrue(first["recorded"])
            self.assertEqual(first["shown_count"], 1)
            self.assertEqual(first["reason"], "cooldown")

        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = Hsk30PromoService(session)

            blocked = await service.mark_shown(
                user,
                now=t0 + timedelta(days=2, hours=23),
            )
            self.assertFalse(blocked["recorded"])
            self.assertEqual(blocked["shown_count"], 1)
            self.assertEqual(blocked["reason"], "cooldown")

            second = await service.mark_shown(
                user,
                now=t0 + timedelta(days=3),
            )
            await session.commit()
            self.assertTrue(second["recorded"])
            self.assertEqual(second["shown_count"], 2)
            self.assertEqual(second["reason"], "show_cap_reached")

        async with self.sessions() as session:
            user = await session.get(User, 1)
            state = await Hsk30PromoService(session).state(
                user,
                now=t0 + timedelta(days=30),
            )
            self.assertFalse(state["eligible"])
            self.assertEqual(state["reason"], "show_cap_reached")

    async def test_user_onboarded_after_hsk30_release_gets_promo(self):
        async with self.sessions() as session:
            release_at = await Hsk30FeatureService(session).enabled_at()
            profile = await CourseMiniAppProfileService(session).get_or_create(1)
            profile.onboarding_completed_at = release_at + timedelta(seconds=1)
            await session.commit()

        async with self.sessions() as session:
            user = await session.get(User, 1)
            state = await Hsk30PromoService(session).state(user)
            self.assertTrue(state["eligible"])
            self.assertEqual(state["reason"], "eligible")

    async def test_feature_off_hides_promo(self):
        async with self.sessions() as session:
            await BotSettingRepository(session).set_bool(
                HSK30_ENABLED_SETTINGS_KEY,
                False,
            )
            await session.commit()

        async with self.sessions() as session:
            user = await session.get(User, 1)
            state = await Hsk30PromoService(session).state(user)
            self.assertFalse(state["eligible"])
            self.assertEqual(state["reason"], "hsk30_disabled")

    async def test_unlocked_or_active_hsk30_user_does_not_get_promo(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            session.add(
                CourseTrackState(
                    user_id=user.id,
                    track="hsk30",
                    level="nhsk1",
                    completed_lessons_count=0,
                    unlocked_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        async with self.sessions() as session:
            user = await session.get(User, 1)
            state = await Hsk30PromoService(session).state(user)
            self.assertFalse(state["eligible"])
            self.assertEqual(state["reason"], "already_unlocked")

            user.level = "nhsk1"
            await session.commit()
            state = await Hsk30PromoService(session).state(user)
            self.assertFalse(state["eligible"])
            self.assertEqual(state["reason"], "already_on_hsk30")


if __name__ == "__main__":
    unittest.main()
