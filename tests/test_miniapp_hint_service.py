"""Mini App ichidagi tushuntirish blokchalari.

To'rtta qoida tekshiriladi va ular foydalanuvchi aniq aytgan talablar:

1. Yangilik faqat O'SHA yangilikka duch kelganda — umumiy "yangiliklar
   oynasi" emas.
2. Yangilik faqat ESKI foydalanuvchilarga: yangi kelgan odam boshqacha
   holatni ko'rmagan, unga bu "o'zgarish" emas.
3. Bir marta — yopilgach qaytmaydi.
4. Istisno: bo'lim tanishtiruvi uzoq tanaffusdan keyin qayta chiqadi.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_miniapp_event import (
    CLIENT_COURSE_MINIAPP_EVENT_NAMES,
    COURSE_MINIAPP_EVENT_NAMES,
    CourseMiniAppEvent,
)
from app.services.miniapp_hint_service import (
    CHANGE_CUTOFF,
    CHANGE_HINT_ADS,
    CHANGE_HINT_PAYWALL,
    CHANGE_HINT_TRIAL,
    HINT_EVENT_NAME,
    REINTRODUCE_AFTER,
    SECTION_HINTS,
    MiniAppHintService,
)

from tests.test_entitlement_engine_limits import _user


TELEGRAM_ID = 4100


class HintServiceTests(unittest.IsolatedAsyncioTestCase):
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

    async def _user_row(self, *, created_at=None, **overrides):
        async with self.sessions() as session:
            user = _user(**overrides)
            user.created_at = created_at or (CHANGE_CUTOFF - timedelta(days=30))
            session.add(user)
            await session.commit()
            return user

    async def _dismiss(self, key, *, at=None):
        async with self.sessions() as session:
            session.add(
                CourseMiniAppEvent(
                    telegram_id=TELEGRAM_ID,
                    event_name=HINT_EVENT_NAME,
                    source="course_v3",
                    dedupe_key=MiniAppHintService.dedupe_key(key),
                    created_at=at or self.now,
                )
            )
            await session.commit()

    async def _hints(self, user, section=None):
        async with self.sessions() as session:
            return await MiniAppHintService(session).hints_for(
                user, section=section, now=self.now
            )

    # --- yangiliklar ------------------------------------------------------

    async def test_an_existing_free_user_is_told_what_changed(self):
        user = await self._user_row()
        keys = {h["key"] for h in await self._hints(user)}

        self.assertIn(CHANGE_HINT_PAYWALL, keys)
        self.assertIn(CHANGE_HINT_TRIAL, keys)
        self.assertIn(CHANGE_HINT_ADS, keys)

    async def test_a_new_user_is_never_told_about_a_change_they_never_saw(self):
        user = await self._user_row(created_at=CHANGE_CUTOFF + timedelta(days=1))
        keys = {h["key"] for h in await self._hints(user)}

        for key in (CHANGE_HINT_PAYWALL, CHANGE_HINT_TRIAL, CHANGE_HINT_ADS):
            with self.subTest(key=key):
                self.assertNotIn(key, keys)

    async def test_a_paid_user_is_not_told_about_the_paywall_change(self):
        # Obunachi limitga urilmaydi — unga bu o'zgarish tegishli emas.
        user = await self._user_row(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
        )
        keys = {h["key"] for h in await self._hints(user)}

        self.assertNotIn(CHANGE_HINT_PAYWALL, keys)
        self.assertNotIn(CHANGE_HINT_TRIAL, keys)

    async def test_a_change_hint_belongs_to_the_section_it_is_about(self):
        # "Umumiy yangiliklar oynasi" emas: odam o'sha bo'limga kirganda chiqadi.
        user = await self._user_row()
        sections = {h["key"]: h["section"] for h in await self._hints(user)}

        self.assertEqual("mashq", sections[CHANGE_HINT_PAYWALL])
        self.assertEqual("profile", sections[CHANGE_HINT_TRIAL])

    async def test_only_one_section_is_returned_when_asked_for_one(self):
        user = await self._user_row()
        hints = await self._hints(user, section="voice")

        self.assertTrue(hints)
        self.assertTrue(all(h["section"] == "voice" for h in hints))

    # --- bo'lim tanishtiruvi ----------------------------------------------

    async def test_every_section_introduces_itself(self):
        user = await self._user_row()
        keys = {h["key"] for h in await self._hints(user)}

        for key in SECTION_HINTS.values():
            with self.subTest(key=key):
                self.assertIn(key, keys)

    async def test_a_dismissed_hint_does_not_come_back(self):
        user = await self._user_row()
        await self._dismiss(SECTION_HINTS["voice"])

        keys = {h["key"] for h in await self._hints(user)}
        self.assertNotIn(SECTION_HINTS["voice"], keys)
        # Boshqalari joyida qoladi.
        self.assertIn(SECTION_HINTS["rating"], keys)

    async def test_a_long_absence_brings_the_section_intro_back(self):
        user = await self._user_row()
        await self._dismiss(
            SECTION_HINTS["voice"], at=self.now - REINTRODUCE_AFTER - timedelta(days=1)
        )

        keys = {h["key"] for h in await self._hints(user)}
        self.assertIn(SECTION_HINTS["voice"], keys)

    async def test_a_change_hint_never_comes_back(self):
        # Yangilik bir marta. Uni qayta ko'rsatish — spam.
        user = await self._user_row()
        await self._dismiss(
            CHANGE_HINT_ADS, at=self.now - REINTRODUCE_AFTER - timedelta(days=30)
        )

        keys = {h["key"] for h in await self._hints(user)}
        self.assertNotIn(CHANGE_HINT_ADS, keys)

    # --- xavfsizlik -------------------------------------------------------

    async def test_a_missing_user_returns_nothing_rather_than_raising(self):
        self.assertEqual([], await self._hints(None))

    async def test_a_broken_query_never_reaches_the_caller(self):
        # Maslahat hech qachon oqimni buzmasligi kerak.
        from unittest.mock import patch

        user = await self._user_row()
        async with self.sessions() as session:
            service = MiniAppHintService(session)
            with patch.object(
                service, "_dismissed", side_effect=RuntimeError("baza yo'q")
            ):
                self.assertEqual([], await service.hints_for(user, now=self.now))

    async def test_every_hint_carries_real_text_not_a_key(self):
        user = await self._user_row()
        for hint in await self._hints(user):
            with self.subTest(key=hint["key"]):
                self.assertNotEqual(hint["key"] + "_title", hint["title"])
                self.assertTrue(hint["title"].strip())
                self.assertTrue(hint["body"].strip())


class HintEventRegistrationTests(unittest.TestCase):
    def test_the_dismissal_event_is_allowed_from_the_client(self):
        # Yopish klientdan keladi, shuning uchun oq ro'yxatda bo'lishi shart.
        self.assertIn(HINT_EVENT_NAME, COURSE_MINIAPP_EVENT_NAMES)
        self.assertIn(HINT_EVENT_NAME, CLIENT_COURSE_MINIAPP_EVENT_NAMES)

    def test_the_dedupe_key_is_namespaced(self):
        # Boshqa eventlar bilan to'qnashmasin.
        self.assertTrue(MiniAppHintService.dedupe_key("x").startswith("hint:"))


if __name__ == "__main__":
    unittest.main()
