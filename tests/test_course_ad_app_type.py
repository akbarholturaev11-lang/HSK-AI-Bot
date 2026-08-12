"""App reklamasi ("app" turi) mavjud kurs reklama tizimiga qo'shilgani testlari.

Asosiy talab: app reklamasi ALOHIDA slotda (`app_open`) ishlaydi va mashq
bo'limlaridagi ("practice") reklamalarga ARALASHMAYDI. Aksincha ham — mashq
reklamalari Mini App ochilganda chiqmaydi.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.services.course_ad_service import (
    COURSE_AD_APP_TYPE,
    COURSE_AD_EXCLUSIVE_TYPES,
    COURSE_AD_LESSON_END_TYPE,
    COURSE_AD_SLOTS,
    COURSE_AD_TYPES,
    CourseAdService,
)


class CourseAdAppTypeNormalizationTests(unittest.TestCase):
    def test_practice_filter_still_accepts_legacy_null_ad_type(self):
        """Produkshnda `ad_type` NULL bo'lgan eski yozuvlar bor (ustun keyin
        qo'shilgan). Mashq filtri ularni tashlab yubormasligi kerak."""
        clause = str(
            CourseAdService._slot_filter("practice").compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        self.assertIn("IS NULL", clause)
        self.assertIn("NOT IN", clause.upper())
        self.assertIn("dars_yakuni", clause)
        self.assertIn("app", clause)

    def test_app_type_and_slot_are_registered(self):
        self.assertIn("app", COURSE_AD_TYPES)
        self.assertEqual(COURSE_AD_APP_TYPE, "app")
        self.assertIn("app_open", COURSE_AD_SLOTS)
        # Eksklyuziv turlar mashq slotidan chiqarib tashlanadi.
        self.assertIn(COURSE_AD_APP_TYPE, COURSE_AD_EXCLUSIVE_TYPES)
        self.assertIn(COURSE_AD_LESSON_END_TYPE, COURSE_AD_EXCLUSIVE_TYPES)

    def test_ad_type_normalization_accepts_app_and_rejects_unknown(self):
        self.assertEqual(CourseAdService.normalize_ad_type("app"), "app")
        self.assertEqual(CourseAdService.normalize_ad_type("  APP "), "app")
        self.assertEqual(CourseAdService.normalize_ad_type("nomalum"), "odiy")

    def test_slot_normalization_accepts_app_open_and_falls_back(self):
        self.assertEqual(CourseAdService.normalize_slot("app_open"), "app_open")
        self.assertEqual(CourseAdService.normalize_slot("nomalum"), "practice")
        self.assertEqual(CourseAdService.normalize_slot(None), "practice")

    def test_skip_after_is_bounded_and_never_exceeds_duration(self):
        # Chegaralar.
        self.assertEqual(CourseAdService.normalize_skip_after(-5), 0)
        self.assertEqual(CourseAdService.normalize_skip_after(999), 60)
        self.assertEqual(CourseAdService.normalize_skip_after("bekor"), 0)
        self.assertEqual(CourseAdService.normalize_skip_after(None), 0)
        # X reklama davomiyligidan kech chiqa olmaydi — aks holda foydalanuvchi
        # reklamani umuman yopa olmay qoladi.
        self.assertEqual(CourseAdService.normalize_skip_after(30, 10), 10)
        self.assertEqual(CourseAdService.normalize_skip_after(5, 10), 5)

    def test_daily_limit_is_bounded_and_zero_means_unlimited(self):
        self.assertEqual(CourseAdService.normalize_daily_limit(0), 0)
        self.assertEqual(CourseAdService.normalize_daily_limit(None), 0)
        self.assertEqual(CourseAdService.normalize_daily_limit(-3), 0)
        self.assertEqual(CourseAdService.normalize_daily_limit(999), 50)
        self.assertEqual(CourseAdService.normalize_daily_limit("2"), 2)


class CourseAdSlotIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reklama media fayli diskda mavjud bo'lmasa servis uni ko'rsatmaydi
        # (ephemeral disk himoyasi), shuning uchun testda haqiqiy fayl yaratamiz.
        self._tmp = tempfile.TemporaryDirectory()
        self._media_patch = patch(
            "app.services.course_ad_service.COURSE_AD_MEDIA_ROOT", self._tmp.name
        )
        self._media_patch.start()

        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._media_patch.stop()
        self._tmp.cleanup()

    def _write_media(self, filename: str) -> str:
        path = os.path.join(self._tmp.name, filename)
        with open(path, "wb") as handle:
            handle.write(b"fake-mp4-bytes")
        return filename

    async def _seed(self, session):
        service = CourseAdService(session)
        for ad_type in ("odiy", "hamkorlik", "bot", "dars_yakuni", "app"):
            await service.create_video(
                title=f"ad-{ad_type}",
                media_path=self._write_media(f"{ad_type}.mp4"),
                duration_seconds=15,
                language="all",
                ad_type=ad_type,
                skip_after_seconds=5 if ad_type == "app" else 0,
                daily_limit=2 if ad_type == "app" else 0,
            )
        await session.commit()

    async def test_app_ad_never_leaks_into_practice_or_lesson_end(self):
        async with self.session_maker() as session:
            await self._seed(session)
            service = CourseAdService(session)

            practice = await service.list_active(language="uz", slot="practice")
            practice_types = {ad.ad_type for ad in practice}
            # Mashq bo'limlarida faqat aralashadigan turlar.
            self.assertEqual(practice_types, {"odiy", "hamkorlik", "bot"})
            self.assertNotIn("app", practice_types)
            self.assertNotIn("dars_yakuni", practice_types)

            lesson_end = await service.list_active(language="uz", slot="lesson_end")
            self.assertEqual({ad.ad_type for ad in lesson_end}, {"dars_yakuni"})

            app_open = await service.list_active(language="uz", slot="app_open")
            self.assertEqual({ad.ad_type for ad in app_open}, {"app"})

    async def test_app_ad_payload_carries_skip_and_limit(self):
        async with self.session_maker() as session:
            await self._seed(session)
            service = CourseAdService(session)
            ads = await service.list_active_payloads(language="uz", slot="app_open")
            self.assertEqual(len(ads), 1)
            payload = ads[0]
            self.assertEqual(payload["ad_type"], "app")
            self.assertEqual(payload["skip_after_seconds"], 5)
            self.assertEqual(payload["daily_limit"], 2)

    async def test_default_ad_type_is_odiy_so_new_ads_stay_in_practice(self):
        """Tur ko'rsatilmasa reklama "odiy" bo'ladi va mashq slotida qoladi."""
        async with self.session_maker() as session:
            service = CourseAdService(session)
            await service.create_video(
                title="default-type",
                media_path=self._write_media("default.mp4"),
                language="all",
            )
            await session.commit()

            practice = await CourseAdService(session).list_active(
                language="uz", slot="practice"
            )
            self.assertEqual([a.title for a in practice], ["default-type"])
            self.assertEqual(practice[0].ad_type, "odiy")

            app_open = await CourseAdService(session).list_active(
                language="uz", slot="app_open"
            )
            self.assertEqual(app_open, [])


class CourseAdAppAdminAndClientTests(unittest.TestCase):
    def test_admin_uses_existing_ads_section_not_a_separate_panel(self):
        html = Path("app/static/admin.html").read_text(encoding="utf-8")
        # Yangi tur mavjud ochiluvchi ro'yxatga qo'shilgan.
        self.assertIn('<option value="app">📱 App reklamasi</option>', html)
        # App uchun ikkita alohida sozlama maydoni bor.
        self.assertIn('id="caSkipAfter"', html)
        self.assertIn('id="caDailyLimit"', html)
        # Maydonlar faqat "app" turi tanlanganda ko'rinadi.
        self.assertIn('id="caAppRow"', html)
        self.assertIn('appRow.style.display = t==="app" ? "" : "none"', html)
        # Yuklashda ikkala qiymat ham yuboriladi.
        self.assertIn('fd.append("skip_after_seconds"', html)
        self.assertIn('fd.append("daily_limit"', html)

    def test_upload_endpoint_normalizes_new_app_fields(self):
        main = Path("app/main.py").read_text(encoding="utf-8")
        self.assertIn("CourseAdService.normalize_skip_after(", main)
        self.assertIn("CourseAdService.normalize_daily_limit(", main)
        # app_open sloti dars/bo'lim talab qilmaydi.
        self.assertIn('app_open = ad_slot == "app_open"', main)
        self.assertIn("and not app_open", main)

    def test_ads_js_exposes_app_open_flow_in_all_three_languages(self):
        ads = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")
        self.assertIn("playAppOpen:playAppOpen", ads)
        self.assertIn("slot=app_open", ads)
        # Foydalanuvchi O'ZI yopadi — avtomatik yopish yo'q.
        self.assertIn("appState.timer=setInterval", ads)
        self.assertIn('e.x.classList.add("on")', ads)
        # Uch tilda ham yangi matnlar bor (CLAUDE.md talabi).
        for key in ("appCta", "appCloseIn"):
            self.assertEqual(
                ads.count(key + ":"),
                3,
                f"{key} uz/ru/tj uchtasida ham bo'lishi kerak",
            )

    def test_mini_app_shows_app_ad_on_open_but_yields_to_user_intent(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn("maybeShowAppOpenAd", html)
        self.assertIn("CourseAds.playAppOpen()", html)
        # Dars, chellenj yoki tur ochilayotgan bo'lsa reklama chiqmaydi.
        self.assertIn("if(ctx&&(ctx.lesson>0||ctx.challenge>0||ctx.tour))return;", html)


if __name__ == "__main__":
    unittest.main()
