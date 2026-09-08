"""Reklama joylari — aynan ikkita, chegara serverda.

Eng muhim tekshiruv: `test_the_daily_cap_is_shared_across_devices`. Ilgari
markazdagi reklamaning kunlik chegarasi `localStorage` da edi — ya'ni
qurilmani almashtirgan yoki brauzer xotirasini tozalagan odam uchun chegara
umuman yo'q edi. Endi u Telegram akkaunti bo'yicha serverda sanaladi.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_ad import CourseAdCreative, CourseAdView
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User
from app.services.ad_placement_service import (
    AUDIENCE_EVERYONE,
    PLACEMENT_LESSON_END,
    PLACEMENT_SCREEN_CENTER,
    AdPlacementService,
    normalize_placements,
    placements_of,
)


TELEGRAM_ID = 9300


def _user(**overrides) -> User:
    now = datetime.now(timezone.utc)
    fields = dict(
        id=1,
        telegram_id=TELEGRAM_ID,
        full_name="Ad tester",
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
        created_at=now,
        last_active_at=now,
    )
    fields.update(overrides)
    return User(**fields)


def _creative(ad_id: int, *, placements: str, ad_type="odiy", language="all"):
    now = datetime.now(timezone.utc)
    return CourseAdCreative(
        id=ad_id,
        title=f"Reklama {ad_id}",
        media_path=f"ad{ad_id}.mp4",
        media_type="video",
        language=language,
        ad_type=ad_type,
        placements=placements,
        duration_seconds=7,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


class PlacementNormalizationTests(unittest.TestCase):
    def test_the_two_placements_round_trip(self):
        self.assertEqual(
            "lesson_end,screen_center",
            normalize_placements("screen_center,lesson_end"),
        )

    def test_unknown_values_fall_back_to_the_centre(self):
        # Reklama yo'qolib qolmasin, lekin dars yakunidagi maxsus joyga ham
        # tasodifan tushmasin.
        for value in ("", None, "wat", "start,middle,end", "app_open"):
            with self.subTest(value=value):
                self.assertEqual(PLACEMENT_SCREEN_CENTER, normalize_placements(value))

    def test_one_ad_may_live_in_both_places(self):
        ad = _creative(1, placements="lesson_end,screen_center")
        self.assertEqual([PLACEMENT_LESSON_END, PLACEMENT_SCREEN_CENTER], placements_of(ad))


class AdPlacementServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

        # Media fayli yo'q reklama ATAYLAB o'tkazib yuboriladi (u WebView'da
        # qora ekran beradi), shuning uchun testda fayllar haqiqiy bo'lishi
        # kerak — mavjud reklama testlari ham shunday qiladi.
        self._media = tempfile.TemporaryDirectory()
        self.addCleanup(self._media.cleanup)
        self._media_patch = patch(
            "app.services.course_ad_service.COURSE_AD_MEDIA_ROOT", self._media.name
        )
        self._media_patch.start()
        self.addCleanup(self._media_patch.stop)

    async def asyncTearDown(self):
        await self.db.dispose()

    def _write_media(self, filename: str) -> str:
        path = os.path.join(self._media.name, filename)
        with open(path, "wb") as handle:
            handle.write(b"\x00\x00\x00\x18ftypmp42")
        return filename

    async def _seed(self, *creatives, user_kwargs=None, offset_minutes=None):
        async with self.sessions() as session:
            session.add(_user(**(user_kwargs or {})))
            for creative in creatives:
                creative.media_path = self._write_media(creative.media_path)
                session.add(creative)
            await session.commit()
            if offset_minutes is not None:
                session.add(
                    CourseMiniAppProfile(user_id=1, timezone_offset_minutes=offset_minutes)
                )
                await session.commit()

    async def _user_row(self, session) -> User:
        return (
            await session.execute(select(User).where(User.telegram_id == TELEGRAM_ID))
        ).scalar_one()

    async def _views(self):
        async with self.sessions() as session:
            return list(
                (await session.execute(select(CourseAdView))).scalars().all()
            )

    # --- kunlik chegara ---------------------------------------------------

    async def test_the_daily_cap_is_shared_across_devices(self):
        """Telefonda ikkita ko'rgan odam desktopda uchinchisini olmaydi.

        Chegara qurilmaga emas, Telegram akkauntiga. Bu "bitta boshqaruv,
        bir nechta ulanish yo'li" degan talabning butun mohiyati.
        """
        await self._seed(_creative(1, placements=PLACEMENT_SCREEN_CENTER))

        async with self.sessions() as session:
            service = AdPlacementService(session)
            user = await self._user_row(session)

            first = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")
            self.assertIsNotNone(first)
            await service.record_view(
                user, placement=PLACEMENT_SCREEN_CENTER, ad_id=1, watched_seconds=7
            )

            second = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")
            self.assertIsNotNone(second)
            await service.record_view(
                user, placement=PLACEMENT_SCREEN_CENTER, ad_id=1, watched_seconds=7
            )
            await session.commit()

            # Uchinchisi — BOSHQA klientdan. Baribir rad etiladi.
            third = await service.next_ad(
                user, placement=PLACEMENT_SCREEN_CENTER, client="desktop"
            )

        self.assertIsNone(third)
        self.assertEqual(2, len(await self._views()))

    async def test_the_lesson_end_placement_has_no_cap_by_default(self):
        await self._seed(_creative(1, placements=PLACEMENT_LESSON_END))

        async with self.sessions() as session:
            service = AdPlacementService(session)
            user = await self._user_row(session)
            for _ in range(5):
                shown = await service.next_ad(user, placement=PLACEMENT_LESSON_END, client="miniapp")
                self.assertIsNotNone(shown)
                await service.record_view(
                    user, placement=PLACEMENT_LESSON_END, ad_id=1, watched_seconds=7
                )
            await session.commit()

        self.assertEqual(5, len(await self._views()))

    async def test_the_two_placements_are_counted_apart(self):
        await self._seed(_creative(1, placements="lesson_end,screen_center"))

        async with self.sessions() as session:
            service = AdPlacementService(session)
            user = await self._user_row(session)
            for _ in range(2):
                await service.record_view(
                    user, placement=PLACEMENT_SCREEN_CENTER, ad_id=1, watched_seconds=7
                )
            await session.commit()

            centre = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")
            lesson_end = await service.next_ad(user, placement=PLACEMENT_LESSON_END, client="miniapp")

        self.assertIsNone(centre)
        self.assertIsNotNone(lesson_end)

    async def test_the_cap_follows_the_learner_local_day(self):
        # UTC+5 o'quvchisining kuni UTC yarim tunda emas, o'z yarim tunida
        # yangilanadi.
        await self._seed(
            _creative(1, placements=PLACEMENT_SCREEN_CENTER), offset_minutes=300
        )

        async with self.sessions() as session:
            service = AdPlacementService(session)
            user = await self._user_row(session)
            # Kechagi ko'rsatishlar bugungi chegarani yemasligi kerak.
            old = datetime.now(timezone.utc) - timedelta(days=2)
            for _ in range(2):
                session.add(
                    CourseAdView(
                        ad_id=1,
                        user_id=1,
                        user_telegram_id=TELEGRAM_ID,
                        level="hsk1",
                        lesson_order=0,
                        placement=PLACEMENT_SCREEN_CENTER,
                        watched_seconds=7,
                        completed=True,
                        created_at=old,
                    )
                )
            await session.commit()

            shown = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")
            status = await service.status(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")

        self.assertIsNotNone(shown)
        self.assertEqual(0, status["used"])
        self.assertIsNotNone(status["reset_at"])

    # --- auditoriya -------------------------------------------------------

    async def test_a_paid_user_is_never_shown_an_ad(self):
        await self._seed(
            _creative(1, placements=PLACEMENT_SCREEN_CENTER),
            user_kwargs={
                "status": "active",
                "payment_status": "approved",
                "end_date": datetime.now(timezone.utc) + timedelta(days=30),
            },
        )

        async with self.sessions() as session:
            shown = await AdPlacementService(session).next_ad(
                await self._user_row(session),
                placement=PLACEMENT_SCREEN_CENTER,
                client="miniapp",
            )

        self.assertIsNone(shown)

    async def test_a_referral_bonus_user_is_treated_as_paid_for_ads(self):
        # Vaqtinchalik kirishi bor odamga ham reklama ko'rsatilmaydi:
        # u kontentga to'liq kirishga ega.
        await self._seed(
            _creative(1, placements=PLACEMENT_SCREEN_CENTER),
            user_kwargs={
                "status": "active",
                "end_date": datetime.now(timezone.utc) + timedelta(days=2),
            },
        )

        async with self.sessions() as session:
            shown = await AdPlacementService(session).next_ad(
                await self._user_row(session),
                placement=PLACEMENT_SCREEN_CENTER,
                client="miniapp",
            )

        self.assertIsNone(shown)

    async def test_the_audience_can_be_opened_to_everyone(self):
        await self._seed(
            _creative(1, placements=PLACEMENT_SCREEN_CENTER),
            user_kwargs={
                "status": "active",
                "payment_status": "approved",
                "end_date": datetime.now(timezone.utc) + timedelta(days=30),
            },
        )

        async with self.sessions() as session:
            service = AdPlacementService(session)
            await service.save_settings(
                {
                    "placements": {
                        PLACEMENT_SCREEN_CENTER: {
                            "enabled": True,
                            "audience": AUDIENCE_EVERYONE,
                            "daily_cap": 2,
                        }
                    }
                }
            )
            await session.commit()
            shown = await service.next_ad(
                await self._user_row(session),
                placement=PLACEMENT_SCREEN_CENTER,
                client="miniapp",
            )

        self.assertIsNotNone(shown)

    # --- admin boshqaruvi -------------------------------------------------

    async def test_each_placement_is_switched_off_on_its_own(self):
        await self._seed(_creative(1, placements="lesson_end,screen_center"))

        async with self.sessions() as session:
            service = AdPlacementService(session)
            await service.save_settings(
                {
                    "placements": {
                        PLACEMENT_SCREEN_CENTER: {"enabled": False},
                        PLACEMENT_LESSON_END: {"enabled": True},
                    }
                }
            )
            await session.commit()
            user = await self._user_row(session)
            centre = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")
            lesson_end = await service.next_ad(user, placement=PLACEMENT_LESSON_END, client="miniapp")

        self.assertIsNone(centre)
        self.assertIsNotNone(lesson_end)

    async def test_a_placement_can_be_limited_to_some_clients(self):
        await self._seed(_creative(1, placements=PLACEMENT_SCREEN_CENTER))

        async with self.sessions() as session:
            service = AdPlacementService(session)
            await service.save_settings(
                {
                    "placements": {
                        PLACEMENT_SCREEN_CENTER: {
                            "enabled": True,
                            "clients": ["miniapp"],
                        }
                    }
                }
            )
            await session.commit()
            user = await self._user_row(session)
            in_miniapp = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="miniapp")
            on_desktop = await service.next_ad(user, placement=PLACEMENT_SCREEN_CENTER, client="desktop")

        self.assertIsNotNone(in_miniapp)
        self.assertIsNone(on_desktop)

    async def test_a_corrupt_settings_row_falls_back_to_the_defaults(self):
        await self._seed(_creative(1, placements=PLACEMENT_SCREEN_CENTER))

        async with self.sessions() as session:
            from app.repositories.bot_setting_repo import BotSettingRepository
            from app.services.ad_placement_service import AD_PLACEMENTS_KEY

            await BotSettingRepository(session).set(AD_PLACEMENTS_KEY, "{broken")
            await session.commit()

            settings = await AdPlacementService(session).get_settings()

        self.assertEqual(2, settings.rule(PLACEMENT_SCREEN_CENTER).daily_cap)

    async def test_an_unknown_placement_is_refused_on_save(self):
        await self._seed()
        async with self.sessions() as session:
            service = AdPlacementService(session)
            for payload in ({}, {"placements": {}}, {"placements": {"app_open": {}}}):
                with self.subTest(payload=payload):
                    with self.assertRaises(ValueError):
                        await service.save_settings(payload)

    # --- katalog ----------------------------------------------------------

    async def test_an_empty_catalogue_is_a_quiet_no_not_an_error(self):
        # Bo'sh katalog hech qachon bo'limni yopib qo'ymasligi kerak.
        await self._seed()

        async with self.sessions() as session:
            shown = await AdPlacementService(session).next_ad(
                await self._user_row(session),
                placement=PLACEMENT_SCREEN_CENTER,
                client="miniapp",
            )

        self.assertIsNone(shown)

    async def test_the_ad_type_no_longer_decides_the_placement(self):
        # `dars_yakuni` turidagi reklamani markazga ham qo'yish mumkin —
        # tur va joy endi mustaqil.
        await self._seed(
            _creative(1, placements=PLACEMENT_SCREEN_CENTER, ad_type="dars_yakuni")
        )

        async with self.sessions() as session:
            shown = await AdPlacementService(session).next_ad(
                await self._user_row(session),
                placement=PLACEMENT_SCREEN_CENTER,
                client="miniapp",
            )

        self.assertIsNotNone(shown)
        self.assertEqual("dars_yakuni", shown["ad_type"])

    async def test_lesson_end_rotates_rather_than_repeating(self):
        await self._seed(
            _creative(1, placements=PLACEMENT_LESSON_END),
            _creative(2, placements=PLACEMENT_LESSON_END),
        )

        async with self.sessions() as session:
            service = AdPlacementService(session)
            user = await self._user_row(session)
            shown = [
                (
                    await service.next_ad(
                        user,
                        placement=PLACEMENT_LESSON_END,
                        client="miniapp",
                        lesson_order=order,
                    )
                )["id"]
                for order in (1, 2, 3, 4)
            ]

        self.assertEqual(2, len(set(shown)))

    async def test_the_client_is_told_how_long_to_wait_before_closing(self):
        await self._seed(_creative(1, placements=PLACEMENT_SCREEN_CENTER))

        async with self.sessions() as session:
            shown = await AdPlacementService(session).next_ad(
                await self._user_row(session),
                placement=PLACEMENT_SCREEN_CENTER,
                client="miniapp",
            )

        self.assertEqual(5, shown["skip_after_seconds"])
        self.assertEqual(PLACEMENT_SCREEN_CENTER, shown["placement"])


if __name__ == "__main__":
    unittest.main()
