"""Kurs reklama turlari va ular qaysi slotga tushishi.

Bu fayl ilgari `test_course_ad_app_type.py` deb atalardi va `app` turini —
Mini App ichidagi ilova reklamasini — himoya qilardi. Tur OLIB TASHLANDI.

Sabab: ilovani reklama qilishning ikkita mustaqil yo'li bor edi — shu tur
(o'z media va platforma havolalari bilan) va `App reklamasi` promosi (o'z
media va platforma chiplari bilan). Ular bir-birini bilmasdi: promoda
Android o'chirilsa ham `app` turidagi rolik baribir Android tugmasini
chiqarardi, chunki havolani to'g'ridan-to'g'ri reliz tizimidan olardi.
Admin esa ikkala joyni ham "ilova reklamasi" deb bilardi.

Endi ilovani FAQAT `desktop_app_promo` reklama qiladi. Shu yerdagi testlar
turning yo'qligini va eski yozuvlar jimgina yo'qolib qolmasligini ushlaydi.
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
    COURSE_AD_EXCLUSIVE_TYPES,
    COURSE_AD_LESSON_END_TYPE,
    COURSE_AD_SLOTS,
    COURSE_AD_TYPES,
    CourseAdService,
)


ADMIN = Path("app/static/admin.html").read_text(encoding="utf-8")
ADS_JS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")
ADS_API = Path("app/api/miniapp_ads.py").read_text(encoding="utf-8")
MAIN = Path("app/main.py").read_text(encoding="utf-8")
SERVICE = Path("app/services/course_ad_service.py").read_text(encoding="utf-8")


class TheAppAdTypeIsGoneTests(unittest.TestCase):
    def test_the_type_is_not_offered_anywhere(self):
        self.assertEqual(COURSE_AD_TYPES, ("odiy", "hamkorlik", "bot", "dars_yakuni"))
        self.assertNotIn('<option value="app">', ADMIN)
        self.assertNotIn("CA_TYPE_SPEC.app", ADMIN)

    def test_an_old_app_row_becomes_an_ordinary_ad_rather_than_vanishing(self):
        # Produkshnda `ad_type="app"` qatorlar bo'lishi mumkin. Ular
        # ko'rsatilaveradi — faqat platforma tugmalarisiz.
        self.assertEqual(CourseAdService.normalize_ad_type("app"), "odiy")
        self.assertEqual(CourseAdService.normalize_ad_type("  APP "), "odiy")
        self.assertEqual(CourseAdService.normalize_ad_type("nomalum"), "odiy")

    def test_the_platform_button_machinery_is_removed(self):
        for gone in (
            "app_platform_buttons",
            "normalize_platform_links",
            "COURSE_AD_APP_PLATFORMS",
            "COURSE_AD_APP_VISIBLE_PLATFORMS",
        ):
            with self.subTest(symbol=gone):
                self.assertNotIn(gone, SERVICE)
        self.assertNotIn("platform_links", ADS_API)
        self.assertNotIn("app_buttons", ADS_JS)
        self.assertNotIn("APP_PLATFORM_META", ADS_JS)
        self.assertNotIn('data-psplat', ADS_JS)

    def test_the_upload_form_no_longer_collects_platform_links(self):
        for gone in ('id="caLinkMacos"', 'id="caLinkWindows"', 'id="caLinkAndroid"'):
            with self.subTest(field=gone):
                self.assertNotIn(gone, ADMIN)
        self.assertNotIn('fd.append("link_macos"', ADMIN)
        self.assertNotIn('form.get("link_android")', MAIN)

    def test_the_release_link_resolver_left_with_it(self):
        # U faqat `app` turidagi tugmalar uchun yashardi.
        self.assertNotIn("_desktop_auto_download_links", MAIN)
        self.assertNotIn("download_links_resolver", ADS_API)

    def test_the_app_open_slot_is_gone_too(self):
        self.assertEqual(COURSE_AD_SLOTS, ("practice", "lesson_end"))
        self.assertEqual(CourseAdService.normalize_slot("app_open"), "practice")


class CourseAdTypeNormalizationTests(unittest.TestCase):
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

    def test_only_the_lesson_end_block_is_kept_out_of_practice(self):
        self.assertEqual(COURSE_AD_EXCLUSIVE_TYPES, (COURSE_AD_LESSON_END_TYPE,))

    def test_slot_normalization_falls_back_to_practice(self):
        self.assertEqual(CourseAdService.normalize_slot("lesson_end"), "lesson_end")
        self.assertEqual(CourseAdService.normalize_slot("nomalum"), "practice")
        self.assertEqual(CourseAdService.normalize_slot(None), "practice")

    def test_the_legacy_normalizers_still_bound_their_columns(self):
        # Ustunlar bazada qoldi va `create_video` ularni hamon
        # normallashtiradi — chegara buzilgan qiymat yozilmasin.
        self.assertEqual(CourseAdService.normalize_skip_after(-5), 0)
        self.assertEqual(CourseAdService.normalize_skip_after(999), 60)
        self.assertEqual(CourseAdService.normalize_skip_after(30, 10), 10)
        self.assertEqual(CourseAdService.normalize_daily_limit(-3), 0)
        self.assertEqual(CourseAdService.normalize_daily_limit(999), 50)


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
        for ad_type in ("odiy", "hamkorlik", "bot", "dars_yakuni"):
            await service.create_video(
                title=f"ad-{ad_type}",
                media_path=self._write_media(f"{ad_type}.mp4"),
                duration_seconds=15,
                language="all",
                ad_type=ad_type,
            )
        await session.commit()

    async def test_lesson_end_block_never_leaks_into_other_slots(self):
        async with self.session_maker() as session:
            await self._seed(session)
            service = CourseAdService(session)

            practice = await service.list_active(language="uz", slot="practice")
            self.assertEqual(
                {ad.ad_type for ad in practice}, {"odiy", "hamkorlik", "bot"}
            )

            lesson_end = await service.list_active(language="uz", slot="lesson_end")
            self.assertEqual({ad.ad_type for ad in lesson_end}, {"dars_yakuni"})

    async def test_the_ad_payload_does_not_claim_to_own_skip_limit_or_platforms(self):
        """Rolik yopish vaqtini, kunlik chegarani va platformani belgilamaydi.

        Yopish vaqtini server joy qoidasidan qo'yadi, kunlik chegarani
        `course_ad_views` qatorlaridan sanaydi, platforma tugmalari esa `app`
        turi bilan birga ketdi."""
        async with self.session_maker() as session:
            await self._seed(session)
            service = CourseAdService(session)
            ads = await service.list_active_payloads(language="uz", slot="practice")
            self.assertTrue(ads)
            for key in ("skip_after_seconds", "daily_limit", "platform_links"):
                with self.subTest(field=key):
                    self.assertNotIn(key, ads[0])

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


class CentreAdFlowTests(unittest.TestCase):
    def test_ads_js_exposes_the_centre_flow_in_all_three_languages(self):
        # Markazdagi reklama o'z joyi bilan chaqiriladi, eski `app_open`
        # sloti bilan emas.
        self.assertIn("playScreenCenter:playScreenCenter", ADS_JS)
        self.assertIn('fetchPlacementAd("screen_center")', ADS_JS)
        self.assertNotIn("slot=app_open", ADS_JS)
        # Foydalanuvchi O'ZI yopadi — avtomatik yopish yo'q.
        self.assertIn("appState.timer=setInterval", ADS_JS)
        self.assertIn('e.x.classList.add("on")', ADS_JS)
        # Uch tilda ham matn bor (CLAUDE.md talabi).
        for key in ("appCta", "appCloseIn"):
            self.assertEqual(
                ADS_JS.count(key + ":"),
                3,
                f"{key} uz/ru/tj uchtasida ham bo'lishi kerak",
            )

    def test_mini_app_shows_the_centre_ad_on_open_but_yields_to_user_intent(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        self.assertIn("maybeShowAppOpenAd", html)
        self.assertIn("CourseAds.playScreenCenter()", html)
        # Dars, chellenj yoki tur ochilayotgan bo'lsa reklama chiqmaydi.
        self.assertIn("if(ctx&&(ctx.lesson>0||ctx.challenge>0||ctx.tour))return;", html)

    def test_the_download_block_inside_the_ad_is_only_mounted_at_lesson_end(self):
        """Ilgari bu yerda `screen_center_ad` ga tushadigan tarmoq bor edi.

        U `if(isLessonEnd())` ning ichida yozilgani uchun HECH QACHON
        ishlamasdi — joy har doim `lesson_end_ad` bo'lardi."""
        self.assertNotIn("screen_center_ad\"", ADS_JS)
        self.assertIn('mountAdPromoTrigger(e.promo,{placement:"lesson_end_ad"})', ADS_JS)

    def test_the_block_is_mounted_through_the_global_that_actually_exists(self):
        """Nomi `desktop-download.js` e'lon qilgan global bilan bir xil.

        Bu yerda `window.DesktopDownloadPromo` deb yozilgan edi — bunday
        global umuman yo'q, ya'ni shart hech qachon bajarilmasdi va
        reklama oynasidagi ilova bloki chiqmasdi. Eski test faqat
        `mountAdPromoTrigger(...)` qismini tekshirgani uchun buni
        ko'rmagan."""
        download = Path(
            "app/static/course_v3_data/desktop-download.js"
        ).read_text(encoding="utf-8")
        self.assertIn("window.PompDesktopDownload = {", download)
        self.assertNotIn("window.DesktopDownloadPromo", ADS_JS)
        self.assertIn(
            "window.PompDesktopDownload.mountAdPromoTrigger(e.promo,", ADS_JS
        )


if __name__ == "__main__":
    unittest.main()
