import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.course_track_state import CourseTrackState
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.admin_notify_service import AdminNotifyService
from app.services.hsk30_feature_service import HSK30_ENABLED_SETTINGS_KEY
from app.services.hsk30_unlock_service import (
    HSK30_UNLOCK_PLAN_TYPE,
    HSK30_UNLOCK_PRICE_KEY,
)
from app.services.subscription_miniapp_service import (
    PAYMENT_DETAILS_KEY,
    SubscriptionMiniAppService,
)


PNG_1X1_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _user(
    telegram_id: int,
    *,
    status: str = "free",
    payment_status: str = "none",
    end_date=None,
) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=1,
        telegram_id=telegram_id,
        full_name="HSK 3 Test",
        language="uz",
        level="hsk2",
        learning_mode="course",
        voice_mode="none",
        status=status,
        payment_status=payment_status,
        end_date=end_date,
        selected_plan_type="1_month",
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


class _BotStub:
    async def get_me(self):
        return SimpleNamespace(username="hsk_ai_test_bot")

    async def send_photo(self, **kwargs):
        return SimpleNamespace(photo=[SimpleNamespace(file_id="HSK30_RECEIPT")])

    async def send_message(self, **kwargs):
        return SimpleNamespace(message_id=1)


class Hsk30UnlockCheckoutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.bot = _BotStub()

        async with self.sessions() as session:
            session.add(_user(5001))
            settings = BotSettingRepository(session)
            await settings.set_bool(HSK30_ENABLED_SETTINGS_KEY, True)
            await settings.set(HSK30_UNLOCK_PRICE_KEY, "10")
            await settings.set(PAYMENT_DETAILS_KEY, "4713380023849546\nTEST HOLDER")
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_quote_is_fixed_ten_tjs_and_never_discounted(self):
        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).quote(
                telegram_id=5001,
                plan_type=HSK30_UNLOCK_PLAN_TYPE,
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
                mode="admin_discount",
            )

        self.assertTrue(result["ok"], result)
        quote = result["quote"]
        self.assertEqual(quote["base_amount"], 10)
        self.assertEqual(quote["final_amount"], 10)
        self.assertEqual(quote["base_currency"], "TJS")
        self.assertFalse(quote["discount_applied"])
        self.assertEqual(quote["discount_percent"], 0)
        self.assertEqual(quote["discount_source"], "none")

    async def test_trial_is_not_treated_as_paid_subscription(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "none"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=2)
            await session.commit()

        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).quote(
                telegram_id=5001,
                plan_type=HSK30_UNLOCK_PLAN_TYPE,
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
            )

        self.assertTrue(result["ok"], result)

    async def test_paid_subscription_never_creates_extra_unlock_checkout(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = datetime.now(timezone.utc) + timedelta(days=2)
            await session.commit()

        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).quote(
                telegram_id=5001,
                plan_type=HSK30_UNLOCK_PLAN_TYPE,
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
            )

        self.assertEqual(result, {"ok": False, "error": "hsk30_subscription_active"})

    async def test_permanent_unlock_cannot_be_paid_twice(self):
        async with self.sessions() as session:
            session.add(
                CourseTrackState(
                    user_id=1,
                    track="hsk30",
                    level="nhsk1",
                    completed_lessons_count=0,
                    unlocked_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        async with self.sessions() as session:
            result = await SubscriptionMiniAppService(session).quote(
                telegram_id=5001,
                plan_type=HSK30_UNLOCK_PLAN_TYPE,
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
            )

        self.assertEqual(result, {"ok": False, "error": "hsk30_already_unlocked"})

    async def test_submit_preserves_subscription_selection_and_writes_special_product(self):
        async with self.sessions() as session, patch.object(
            AdminNotifyService,
            "notify_payment_review",
            return_value="HSK30_RECEIPT",
        ):
            result = await SubscriptionMiniAppService(session).submit(
                telegram_id=5001,
                plan_type=HSK30_UNLOCK_PLAN_TYPE,
                payment_method="visa",
                card_country="tj",
                card_bank="dc_city",
                screenshot_data_url=PNG_1X1_DATA_URL,
                bot=self.bot,
                mode="subscription",
            )

        self.assertTrue(result["ok"], result)
        async with self.sessions() as session:
            user = await session.get(User, 1)
            payment = (await session.execute(select(Payment))).scalar_one()
        self.assertEqual(user.selected_plan_type, "1_month")
        self.assertEqual(payment.plan_type, HSK30_UNLOCK_PLAN_TYPE)
        self.assertEqual(payment.amount, 10)
        self.assertEqual(payment.currency, "TJS")
        self.assertEqual(payment.discount_percent, 0)
        self.assertEqual(payment.discount_source, "none")

    async def test_hsk30_review_label_is_not_shown_as_raw_plan_key(self):
        text = AdminNotifyService().build_payment_review_text(
            lang="uz",
            telegram_id=5001,
            full_name="Test",
            plan_type=HSK30_UNLOCK_PLAN_TYPE,
            amount=10,
            currency="TJS",
            payment_id=1,
            payment_method="visa",
        )
        self.assertIn("HSK 3.0 ochish", text)
        self.assertNotIn("Tarif: hsk30_unlock", text)


if __name__ == "__main__":
    unittest.main()
