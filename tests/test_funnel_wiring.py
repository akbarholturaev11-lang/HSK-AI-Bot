"""Voronka hodisalari haqiqatan yozilyaptimi.

Yangi event nomlarini ro'yxatga qo'shish oson; ularni CHAQIRISHNI unutish ham
shunchalik oson, va natijasi jimgina: admin hisobotida nol turadi va "hech kim
limitga urilmadi" degan xulosa chiqadi.

Ikkita eng muhim hodisa shu yerda tekshiriladi:

* `limit_hit` — konversiya voronkasining eng muhim nuqtasi, kuniga har action
  uchun BIR MARTA (aks holda bir foydalanuvchi o'nta qator yozib sonni buzadi);
* `trial_converted` — trialdan to'lovga o'tish, ya'ni butun trial g'oyasining
  yagona o'lchovi.
"""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.user import User
from app.services.entitlements import actions as A
from app.services.entitlements.engine import EntitlementEngine
from app.services.entitlements.limits_config import WINDOW_DAILY, config_from_payload
from app.services.entitlements.state import EntitlementState
from app.services.subscription_service import SubscriptionService

from tests.test_entitlement_engine_limits import _user


class FunnelWiringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        # Voronka ataylab o'z sessiyasida yozadi.
        self.patch = patch(
            "app.services.conversion_funnel_service.async_session_maker", self.sessions
        )
        self.patch.start()

    async def asyncTearDown(self):
        self.patch.stop()
        await self.db.dispose()

    async def _events(self, name=None):
        async with self.sessions() as session:
            rows = (
                await session.execute(select(ConversionFunnelEvent))
            ).scalars().all()
        return [r for r in rows if name is None or r.event_name == name]

    async def _get_user(self, session) -> User:
        return (
            await session.execute(select(User).where(User.telegram_id == 4100))
        ).scalar_one()

    # --- limitga urilish --------------------------------------------------

    async def test_a_refused_action_records_a_limit_hit(self):
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            config = config_from_payload(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            A.PRACTICE_RECOGNITION: {"limit": 1, "window": WINDOW_DAILY}
                        }
                    }
                }
            )
            engine = EntitlementEngine(session, config=config)
            user = await self._get_user(session)

            await engine.consume(user, A.PRACTICE_RECOGNITION)
            refused = await engine.consume(user, A.PRACTICE_RECOGNITION)
            await session.commit()

        self.assertFalse(refused.allowed)
        hits = await self._events("limit_hit")
        self.assertEqual(1, len(hits))
        self.assertIn(A.PRACTICE_RECOGNITION, hits[0].source)

    async def test_repeated_refusals_are_counted_once_a_day(self):
        # Bir foydalanuvchi limitga o'n marta urilishi mumkin. O'nta qator
        # "limitga urilganlar soni" ni buzib ko'rsatardi.
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            config = config_from_payload(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            A.PRACTICE_RECOGNITION: {"limit": 1, "window": WINDOW_DAILY}
                        }
                    }
                }
            )
            engine = EntitlementEngine(session, config=config)
            user = await self._get_user(session)
            for _ in range(6):
                await engine.consume(user, A.PRACTICE_RECOGNITION)
            await session.commit()

        self.assertLessEqual(len(await self._events("limit_hit")), 1)

    async def test_an_allowed_action_records_nothing(self):
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            config = config_from_payload(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            A.PRACTICE_RECOGNITION: {"limit": 5, "window": WINDOW_DAILY}
                        }
                    }
                }
            )
            user = await self._get_user(session)
            await EntitlementEngine(session, config=config).consume(
                user, A.PRACTICE_RECOGNITION
            )
            await session.commit()

        self.assertEqual([], await self._events("limit_hit"))

    async def test_analytics_never_breaks_the_limit_decision(self):
        # Voronka yiqilsa ham qaror o'z ishini qilishi kerak.
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            config = config_from_payload(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            A.PRACTICE_RECOGNITION: {"limit": 1, "window": WINDOW_DAILY}
                        }
                    }
                }
            )
            user = await self._get_user(session)
            await EntitlementEngine(session, config=config).consume(
                user, A.PRACTICE_RECOGNITION
            )
            await session.commit()
            with patch(
                "app.services.entitlements.engine.ConversionFunnelService",
                side_effect=RuntimeError("voronka yiqildi"),
            ):
                decision = await EntitlementEngine(session, config=config).consume(
                    user, A.PRACTICE_RECOGNITION
                )

        self.assertFalse(decision.allowed)

    async def test_slow_limit_hit_analytics_does_not_delay_the_limit_decision(self):
        # Limit oynasi userga darhol chiqishi kerak; funnel yozuvi sekin DBda
        # critical path bo'lib qolmasligi shart.
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            config = config_from_payload(
                {
                    "plans": {
                        EntitlementState.FREE: {
                            A.PRACTICE_RECOGNITION: {"limit": 1, "window": WINDOW_DAILY}
                        }
                    }
                }
            )
            user = await self._get_user(session)
            await EntitlementEngine(session, config=config).consume(
                user, A.PRACTICE_RECOGNITION
            )
            await session.commit()

            async def slow_record_once(**_kwargs):
                await asyncio.sleep(0.05)
                return True

            with patch(
                "app.services.entitlements.engine.LIMIT_HIT_ANALYTICS_TIMEOUT_SECONDS",
                0.001,
            ), patch(
                "app.services.entitlements.engine.ConversionFunnelService"
            ) as service_cls:
                service_cls.return_value.record_once = AsyncMock(
                    side_effect=slow_record_once
                )
                decision = await EntitlementEngine(session, config=config).consume(
                    user, A.PRACTICE_RECOGNITION
                )

        self.assertFalse(decision.allowed)
        service_cls.return_value.record_once.assert_awaited()

    # --- trialdan to'lovga --------------------------------------------------

    async def test_a_paying_trial_user_records_a_conversion(self):
        async with self.sessions() as session:
            user = _user()
            user.trial_used = True
            user.pro_trial_started_at = datetime.now(timezone.utc) - timedelta(days=3)
            user.pro_trial_ends_at = datetime.now(timezone.utc) + timedelta(days=4)
            session.add(user)
            await session.commit()

            activated = await SubscriptionService(session).activate_plan(
                4100, "3_months"
            )
            await session.commit()

        self.assertTrue(activated)
        conversions = await self._events("trial_converted")
        self.assertEqual(1, len(conversions))

    async def test_a_user_who_never_took_a_trial_records_no_conversion(self):
        async with self.sessions() as session:
            session.add(_user())
            await session.commit()

            await SubscriptionService(session).activate_plan(4100, "1_month")
            await session.commit()

        self.assertEqual([], await self._events("trial_converted"))


if __name__ == "__main__":
    unittest.main()
