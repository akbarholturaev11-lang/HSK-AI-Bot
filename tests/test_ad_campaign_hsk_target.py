import unittest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.user import User
from app.repositories.ad_campaign_repo import AdCampaignRepository
from app.repositories.user_repo import UserRepository


def _user(user_id: int, telegram_id: int, level: str, status: str = "free") -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=f"User {user_id}",
        language="uz",
        level=level,
        learning_mode="course",
        voice_mode="none",
        status=status,
        payment_status="approved" if status == "active" else "none",
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


class AdCampaignHskTargetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_hsk30_ad_target_filters_track_level_and_active_policy(self):
        async with self.sessions() as session:
            session.add_all(
                [
                    _user(1, 1001, "hsk1"),
                    _user(2, 1002, "nhsk1"),
                    _user(3, 1003, "nhsk2"),
                    _user(4, 1004, "nhsk1", status="active"),
                ]
            )
            await session.commit()
            repo = UserRepository(session)

            free_only = await repo.get_ad_target_users(
                course_track="hsk30",
                level="nhsk1",
                include_active_subscribers=False,
            )
            with_paid = await repo.get_ad_target_users(
                course_track="hsk30",
                level="nhsk1",
                include_active_subscribers=True,
            )

        self.assertEqual([u.telegram_id for u in free_only], [1002])
        self.assertEqual([u.telegram_id for u in with_paid], [1002, 1004])

    async def test_campaign_persists_hsk30_target(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            campaign = await AdCampaignRepository(session).create(
                title="HSK 3.0 N1",
                message_text="test",
                content_type="text",
                media_file_id=None,
                starts_at=now,
                ends_at=now,
                send_count_total=1,
                target_track="hsk30",
                target_level="nhsk1",
            )
            await session.commit()

            self.assertEqual(campaign.target_track, "hsk30")
            self.assertEqual(campaign.target_level, "nhsk1")


if __name__ == "__main__":
    unittest.main()
