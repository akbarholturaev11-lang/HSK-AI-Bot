"""Kurs reklamasi surat (photo) media turi testlari.

Talab: reklama bo'limi video bilan bir qatorda suratni ham qabul qilsin.
Muhim: eski video reklamalar xatti-harakati o'zgarmasligi kerak — `media_type`
ko'rsatilmasa yoki eski yozuvlarda NULL bo'lsa, u "video" deb qaraladi.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.services.course_ad_service import (
    COURSE_AD_ALLOWED_IMAGE_EXTENSIONS,
    COURSE_AD_ALLOWED_VIDEO_EXTENSIONS,
    COURSE_AD_DEFAULT_MEDIA_TYPE,
    COURSE_AD_MEDIA_TYPES,
    CourseAdService,
)


class CourseAdMediaTypeNormalizationTests(unittest.TestCase):
    def test_media_types_are_registered(self):
        self.assertEqual(COURSE_AD_MEDIA_TYPES, ("video", "photo"))
        self.assertEqual(COURSE_AD_DEFAULT_MEDIA_TYPE, "video")

    def test_photo_is_accepted(self):
        self.assertEqual(CourseAdService.normalize_media_type("photo"), "photo")
        self.assertEqual(CourseAdService.normalize_media_type("  PHOTO "), "photo")

    def test_unknown_and_empty_fall_back_to_video(self):
        """Eski yozuvlarda `media_type` NULL bo'lishi mumkin — ular video."""
        self.assertEqual(CourseAdService.normalize_media_type(None), "video")
        self.assertEqual(CourseAdService.normalize_media_type(""), "video")
        self.assertEqual(CourseAdService.normalize_media_type("gif"), "video")
        self.assertEqual(CourseAdService.normalize_media_type("nomalum"), "video")


class CourseAdPhotoStorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
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
            handle.write(b"fake-media-bytes")
        return filename

    async def test_photo_ad_is_stored_and_returned_in_payload(self):
        async with self.session_maker() as session:
            service = CourseAdService(session)
            ad = await service.create_video(
                title="surat reklama",
                media_path=self._write_media("banner.jpg"),
                duration_seconds=10,
                media_type="photo",
            )
            await session.commit()
            self.assertEqual(ad.media_type, "photo")

            payload = service.payload(ad)
            self.assertEqual(payload["media_type"], "photo")
            self.assertEqual(payload["media_url"], "/uploads/course_ads/banner.jpg")
            self.assertTrue(payload["media_available"])

    async def test_video_stays_default_when_media_type_not_given(self):
        """Mavjud video oqimi o'zgarmaydi — parametr berilmasa video."""
        async with self.session_maker() as session:
            service = CourseAdService(session)
            ad = await service.create_video(
                title="video reklama",
                media_path=self._write_media("clip.mp4"),
                duration_seconds=10,
            )
            await session.commit()
            self.assertEqual(ad.media_type, "video")
            self.assertEqual(service.payload(ad)["media_type"], "video")

    async def test_unknown_media_type_is_stored_as_video(self):
        async with self.session_maker() as session:
            service = CourseAdService(session)
            ad = await service.create_video(
                title="nomalum",
                media_path=self._write_media("x.mp4"),
                media_type="nomalum",
            )
            await session.commit()
            self.assertEqual(ad.media_type, "video")

    async def test_photo_ad_appears_in_active_slot_payloads(self):
        """Surat reklamasi ham video kabi slot bo'yicha chiqadi."""
        async with self.session_maker() as session:
            service = CourseAdService(session)
            await service.create_video(
                title="app surat",
                media_path=self._write_media("app.png"),
                ad_type="app",
                media_type="photo",
                skip_after_seconds=3,
            )
            await session.commit()

            ads = await service.list_active_payloads(language="uz", slot="app_open")
            self.assertEqual(len(ads), 1)
            self.assertEqual(ads[0]["media_type"], "photo")
            self.assertEqual(ads[0]["ad_type"], "app")

    async def test_legacy_null_media_type_reads_as_video(self):
        """Ustun keyin qo'shilgan; qiymati yo'q yozuv payloadda "video" bo'ladi.

        DB darajasida ustun NOT NULL, shuning uchun yozib emas — o'qish yo'lida
        tekshiramiz: `payload()` NULL kelsa ham "video" qaytarishi shart."""
        async with self.session_maker() as session:
            service = CourseAdService(session)
            ad = await service.create_video(
                title="eski",
                media_path=self._write_media("old.mp4"),
            )
            await session.commit()
            session.expunge(ad)
            ad.media_type = None
            self.assertEqual(service.payload(ad)["media_type"], "video")


class CourseAdUploadClassificationTests(unittest.TestCase):
    """Yuklangan fayl surat/video sifatida to'g'ri ajratilishi."""

    def test_extension_sets_do_not_overlap(self):
        self.assertEqual(
            set(COURSE_AD_ALLOWED_IMAGE_EXTENSIONS), {".jpg", ".jpeg", ".png", ".webp"}
        )
        self.assertFalse(
            set(COURSE_AD_ALLOWED_IMAGE_EXTENSIONS)
            & set(COURSE_AD_ALLOWED_VIDEO_EXTENSIONS)
        )

    def test_images_are_classified_as_photo(self):
        for name, ctype in [
            ("banner.jpg", "image/jpeg"),
            ("banner.PNG", "image/png"),
            ("banner.webp", "image/webp"),
            ("banner.jpeg", ""),
        ]:
            with self.subTest(name=name):
                self.assertEqual(
                    CourseAdService.classify_upload_media(name, ctype)[0], "photo"
                )

    def test_videos_are_classified_as_video(self):
        for name, ctype in [
            ("clip.mp4", "video/mp4"),
            ("clip.mov", "video/quicktime"),
            ("clip.webm", ""),
            ("clip.m4v", ""),
        ]:
            with self.subTest(name=name):
                self.assertEqual(
                    CourseAdService.classify_upload_media(name, ctype)[0], "video"
                )

    def test_missing_content_type_falls_back_to_extension(self):
        """Telegram WebView ba'zan content_type yubormaydi."""
        self.assertEqual(
            CourseAdService.classify_upload_media("banner.jpg", ""), ("photo", ".jpg")
        )
        self.assertEqual(
            CourseAdService.classify_upload_media("clip.mp4", None), ("video", ".mp4")
        )

    def test_unknown_extension_uses_content_type_and_safe_default(self):
        """HEIC kabi kengaytma tanilmasa ham content_type surat desa qabul
        qilinadi va xavfsiz `.jpg` nomi bilan saqlanadi."""
        self.assertEqual(
            CourseAdService.classify_upload_media("photo.heic", "image/heic"),
            ("photo", ".jpg"),
        )
        self.assertEqual(
            CourseAdService.classify_upload_media("clip.mkv", "video/x-matroska"),
            ("video", ".mp4"),
        )
        self.assertEqual(
            CourseAdService.classify_upload_media("", "image/png"), ("photo", ".jpg")
        )

    def test_unsupported_files_are_rejected(self):
        for name, ctype in [
            ("hujjat.pdf", "application/pdf"),
            ("arxiv.zip", ""),
            ("", ""),
            (None, None),
        ]:
            with self.subTest(name=name):
                self.assertIsNone(CourseAdService.classify_upload_media(name, ctype))


if __name__ == "__main__":
    unittest.main()
