"""Trial tugashidan oldingi ogohlantirishlar.

Jami IKKI xabar: 2 kun qolganda va oxirgi kuni. Loyihada allaqachon oltita
bildirishnoma servisi bor, va bot bloklanishi KPI ro'yxatidagi ko'rsatkich —
shuning uchun bu yerda "kamroq" ataylab tanlangan.

Eng nozik joyi tartib: yozuv XABARDAN OLDIN qilinadi. Yozuv unique kalit
bilan dedupe qiladi; teskari tartibda takroriy xabar allaqachon yuborilgan
bo'lardi va dedupe uni ushlab qololmasdi.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_user_notification import CourseUserNotification
from app.db.models.user import User
from app.services.trial_reminder_service import REMINDER_DAYS, TrialReminderService

from tests.test_entitlement_engine_limits import _user


class _BotSpy:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    async def send_message(self, *, chat_id, text, parse_mode=None):
        if self.fail:
            raise RuntimeError("bot bloklangan")
        self.sent.append((chat_id, text))


class TrialReminderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _seed(self, *, days_left):
        async with self.sessions() as session:
            user = _user()
            user.trial_used = True
            user.pro_trial_started_at = self.now - timedelta(days=7 - days_left)
            # `.days` pastga yaxlitlaydi, shuning uchun bir soat qo'shamiz.
            user.pro_trial_ends_at = self.now + timedelta(days=days_left, hours=1)
            session.add(user)
            await session.commit()

    async def _notifications(self):
        async with self.sessions() as session:
            return list(
                (await session.execute(select(CourseUserNotification))).scalars().all()
            )

    async def test_a_reminder_goes_out_two_days_before(self):
        await self._seed(days_left=2)
        bot = _BotSpy()

        async with self.sessions() as session:
            sent = await TrialReminderService(session).send_due_reminders(
                bot, now=self.now
            )

        self.assertEqual(1, sent)
        self.assertEqual(1, len(bot.sent))
        self.assertIn("2", bot.sent[0][1])

    async def test_a_reminder_goes_out_on_the_last_day(self):
        await self._seed(days_left=0)
        bot = _BotSpy()

        async with self.sessions() as session:
            sent = await TrialReminderService(session).send_due_reminders(
                bot, now=self.now
            )

        self.assertEqual(1, sent)

    async def test_nothing_goes_out_on_the_other_days(self):
        for days in (1, 3, 5):
            with self.subTest(days=days):
                await self.asyncTearDown()
                await self.asyncSetUp()
                await self._seed(days_left=days)
                bot = _BotSpy()

                async with self.sessions() as session:
                    sent = await TrialReminderService(session).send_due_reminders(
                        bot, now=self.now
                    )

                self.assertEqual(0, sent, f"{days} kun qolganda xabar ketmasligi kerak")

    async def test_the_same_reminder_never_goes_out_twice(self):
        await self._seed(days_left=2)
        bot = _BotSpy()

        async with self.sessions() as session:
            service = TrialReminderService(session)
            first = await service.send_due_reminders(bot, now=self.now)
            second = await service.send_due_reminders(bot, now=self.now)

        self.assertEqual(1, first)
        self.assertEqual(0, second)
        self.assertEqual(1, len(bot.sent))

    async def test_a_revoked_trial_is_left_alone(self):
        await self._seed(days_left=2)
        async with self.sessions() as session:
            user = (
                await session.execute(select(User).where(User.telegram_id == 4100))
            ).scalar_one()
            user.pro_trial_revoked_at = self.now
            await session.commit()

        bot = _BotSpy()
        async with self.sessions() as session:
            sent = await TrialReminderService(session).send_due_reminders(
                bot, now=self.now
            )

        self.assertEqual(0, sent)

    async def test_a_user_without_a_trial_is_never_reminded(self):
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

        bot = _BotSpy()
        async with self.sessions() as session:
            sent = await TrialReminderService(session).send_due_reminders(
                bot, now=self.now
            )

        self.assertEqual(0, sent)

    async def test_a_blocked_bot_does_not_break_the_run(self):
        await self._seed(days_left=2)
        bot = _BotSpy(fail=True)

        async with self.sessions() as session:
            sent = await TrialReminderService(session).send_due_reminders(
                bot, now=self.now
            )

        self.assertEqual(0, sent)

    async def test_only_two_reminders_exist_in_total(self):
        # "Kamroq" ataylab tanlangan: bot bloklanishi KPI ro'yxatida.
        self.assertEqual(2, len(REMINDER_DAYS))
        self.assertIn(2, REMINDER_DAYS)
        self.assertIn(0, REMINDER_DAYS)


if __name__ == "__main__":
    unittest.main()
