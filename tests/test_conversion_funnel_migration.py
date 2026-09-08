"""Voronka event ro'yxatining kengaytirilishi.

`conversion_funnel_events.event_name` CHECK cheklovi bilan qotirilgan, ya'ni
yangi nom qo'shish migratsiya talab qiladi. Ikkita narsa noto'g'ri ketishi
mumkin va ikkalasi ham jimgina:

* nom `EVENT_NAMES` ga qo'shilib, `EVENT_LABELS` ga qo'shilmasa — admin
  voronka hisoboti `KeyError` bilan yiqiladi;
* migratsiya orqaga qaytmasa — yangi nomdagi qatorlar eski CHECK ni buzadi.

Shu ikkisi tekshiriladi.
"""

import unittest
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.conversion_funnel_event import (
    CONVERSION_FUNNEL_EVENT_NAMES,
    ConversionFunnelEvent,
)
from app.services.conversion_funnel_service import ConversionFunnelService


NEW_NAMES = (
    "onboarding_completed",
    "plan_choice_seen",
    "trial_started",
    "trial_expired",
    "trial_converted",
    "limit_hit",
    "paywall_cta_clicked",
    "ad_shown",
    "ad_skipped",
)


class FunnelEventNameTests(unittest.TestCase):
    def test_every_name_has_a_label(self):
        # `admin_funnel_text` `EVENT_LABELS[name]` qiladi — yozuvi yo'q nom
        # butun admin hisobotini yiqitadi.
        missing = [
            name
            for name in CONVERSION_FUNNEL_EVENT_NAMES
            if name not in ConversionFunnelService.EVENT_LABELS
        ]
        self.assertEqual([], missing)

    def test_the_new_names_are_registered(self):
        for name in NEW_NAMES:
            with self.subTest(name=name):
                self.assertIn(name, CONVERSION_FUNNEL_EVENT_NAMES)

    def test_the_old_names_are_untouched(self):
        # Eski nomlar tarixiy qatorlarda bor — biri yo'qolsa hisobot buziladi.
        for name in (
            "course_cta_seen",
            "course_started",
            "lesson_started",
            "quiz_completed",
            "ai_explanation_seen",
            "homework_completed",
            "paywall_seen",
            "checkout_opened",
            "payment_screenshot_submitted",
            "payment_approved",
            "payment_rejected",
        ):
            with self.subTest(name=name):
                self.assertIn(name, CONVERSION_FUNNEL_EVENT_NAMES)

    def test_every_rate_pair_points_at_a_known_event(self):
        for label, numerator, denominator in ConversionFunnelService.RATE_PAIRS:
            with self.subTest(label=label):
                self.assertIn(numerator, CONVERSION_FUNNEL_EVENT_NAMES)
                self.assertIn(denominator, CONVERSION_FUNNEL_EVENT_NAMES)

    def test_the_trial_conversion_rate_is_reported(self):
        labels = [pair[0] for pair in ConversionFunnelService.RATE_PAIRS]
        self.assertIn("Trial → To'lov", labels)


class FunnelRowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def test_the_new_names_pass_the_check_constraint(self):
        async with self.sessions() as session:
            for index, name in enumerate(NEW_NAMES):
                session.add(
                    ConversionFunnelEvent(
                        telegram_id=1000 + index,
                        event_name=name,
                        source="test",
                        created_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()

            rows = (
                await session.execute(select(ConversionFunnelEvent.event_name))
            ).scalars().all()

        self.assertEqual(set(NEW_NAMES), set(rows))

    async def test_an_unknown_name_is_still_refused_by_the_service(self):
        recorded = await ConversionFunnelService(None).record(
            event_name="totally_made_up", telegram_id=1, source="test"
        )
        self.assertFalse(recorded)


if __name__ == "__main__":
    unittest.main()
