"""Course ad translation: one AI call at upload, per-language copy at runtime."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.course_ad_translation_service import (
    CourseAdTranslationError,
    CourseAdTranslationService,
    localize_ad_copy,
)
from app.services.course_ad_service import CourseAdService


TRANSLATIONS = {
    "uz": {"title": "Yangi darslarni ko'ring", "button_text": "Hozir ko'rish"},
    "ru": {"title": "Посмотрите новые уроки", "button_text": "Смотреть"},
}


class CourseAdTranslationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_tajik_source_is_translated_once_to_both_languages(self):
        ai = SimpleNamespace(
            complete_messages_with_usage=AsyncMock(
                return_value=SimpleNamespace(content=json.dumps(TRANSLATIONS, ensure_ascii=False))
            )
        )
        with patch(
            "app.services.course_ad_translation_service.settings",
            SimpleNamespace(ai_enabled=True),
        ):
            result = await CourseAdTranslationService(ai).translate_from_tajik(
                title="Дарсҳои навро бинед", button_text="Ҳозир бинед"
            )
        parsed = json.loads(result)
        self.assertEqual("Дарсҳои навро бинед", parsed["tj"]["title"])
        self.assertEqual("Ҳозир бинед", parsed["tj"]["button_text"])
        self.assertEqual(TRANSLATIONS["uz"], parsed["uz"])
        self.assertEqual(TRANSLATIONS["ru"], parsed["ru"])
        ai.complete_messages_with_usage.assert_awaited_once()

    async def test_no_button_stays_without_button_in_all_languages(self):
        no_button = {
            "uz": {"title": "Yangi dars", "button_text": ""},
            "ru": {"title": "Новый урок", "button_text": ""},
        }
        ai = SimpleNamespace(
            complete_messages_with_usage=AsyncMock(
                return_value=SimpleNamespace(content=json.dumps(no_button, ensure_ascii=False))
            )
        )
        with patch(
            "app.services.course_ad_translation_service.settings",
            SimpleNamespace(ai_enabled=True),
        ):
            result = await CourseAdTranslationService(ai).translate_from_tajik(
                title="Дарси нав", button_text=None
            )
        self.assertEqual("", json.loads(result)["ru"]["button_text"])

    async def test_failed_or_disabled_ai_does_not_fake_translation(self):
        ai = SimpleNamespace(complete_messages_with_usage=AsyncMock(
            return_value=SimpleNamespace(content="No translation")
        ))
        with patch(
            "app.services.course_ad_translation_service.settings",
            SimpleNamespace(ai_enabled=True),
        ):
            with self.assertRaises(CourseAdTranslationError):
                await CourseAdTranslationService(ai).translate_from_tajik(
                    title="Салом", button_text="Бештар"
                )
        with patch(
            "app.services.course_ad_translation_service.settings",
            SimpleNamespace(ai_enabled=False),
        ):
            with self.assertRaises(CourseAdTranslationError):
                await CourseAdTranslationService(ai).translate_from_tajik(
                    title="Салом", button_text="Бештар"
                )

    async def test_missing_button_translation_does_not_create_false_copy(self):
        bad = {
            "uz": {"title": "Sarlavha", "button_text": ""},
            "ru": {"title": "Заголовок", "button_text": "Подробнее"},
        }
        ai = SimpleNamespace(complete_messages_with_usage=AsyncMock(
            return_value=SimpleNamespace(content=json.dumps(bad))
        ))
        with patch(
            "app.services.course_ad_translation_service.settings",
            SimpleNamespace(ai_enabled=True),
        ):
            with self.assertRaises(CourseAdTranslationError):
                await CourseAdTranslationService(ai).translate_from_tajik(
                    title="Сарлавҳа", button_text="Бештар"
                )


class StoredCourseAdCopyTests(unittest.TestCase):
    def setUp(self):
        self.stored = json.dumps({
            "tj": {"title": "Дарсҳои нав", "button_text": "Ҳозир бинед"},
            **TRANSLATIONS,
        }, ensure_ascii=False)

    def test_each_language_uses_own_copy(self):
        self.assertEqual(
            ("Дарсҳои нав", "Ҳозир бинед"),
            localize_ad_copy(self.stored, title="Дарсҳои нав", button_text="Ҳозир бинед", language="tj"),
        )
        self.assertEqual(
            ("Yangi darslarni ko'ring", "Hozir ko'rish"),
            localize_ad_copy(self.stored, title="Дарсҳои нав", button_text="Ҳозир бинед", language="uz"),
        )
        self.assertEqual(
            ("Посмотрите новые уроки", "Смотреть"),
            localize_ad_copy(self.stored, title="Дарсҳои нав", button_text="Ҳозир бинед", language="ru"),
        )

    def test_old_ads_and_corrupt_translations_fall_back_to_source(self):
        for stored in (None, "broken", '{"ru":{}}'):
            with self.subTest(stored=stored):
                self.assertEqual(
                    ("Дарсҳои нав", "Ҳозир бинед"),
                    localize_ad_copy(stored, title="Дарсҳои нав", button_text="Ҳозир бинед", language="ru"),
                )

    def test_payload_uses_localized_copy_for_all_language_ad(self):
        from app.db.models.course_ad import CourseAdCreative
        ad = CourseAdCreative(
            id=123, title="Дарсҳои нав", button_text="Ҳозир бинед",
            language="all", localized_copy=self.stored,
            ad_type="odiy", media_path="fake.mp4", media_type="video",
            duration_seconds=7, placements="lesson_end",
            is_active=True,
        )
        payload = CourseAdService.payload(ad, language="ru")
        self.assertEqual("Посмотрите новые уроки", payload["title"])
        self.assertEqual("Смотреть", payload["button_text"])
        self.assertEqual("all", payload["language"])
        admin = CourseAdService.payload(ad)
        self.assertEqual("Дарсҳои нав", admin["title"])

    def test_single_language_ad_is_never_translated(self):
        from app.db.models.course_ad import CourseAdCreative
        ad = CourseAdCreative(
            id=124, title="Новая акция", button_text="Открыть",
            language="ru", localized_copy=self.stored, ad_type="odiy",
            media_path="fake.mp4", media_type="video",
            duration_seconds=7, placements="lesson_end", is_active=True,
        )
        payload = CourseAdService.payload(ad, language="uz")
        self.assertEqual("Новая акция", payload["title"])
        self.assertEqual("Открыть", payload["button_text"])


class CourseAdClientTranslationWiringTests(unittest.TestCase):
    def test_all_language_uses_tajik_source_before_upload(self):
        main = Path("app/main.py").read_text(encoding="utf-8")
        self.assertIn('if language == "all":', main)
        self.assertIn('CourseAdTranslationService().translate_from_tajik(', main)
        self.assertIn("localized_copy=localized_copy", main)
        self.assertIn('"translation_status": "completed" if localized_copy', main)

    def test_miniapp_current_locale_sent_to_backend(self):
        js = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")
        api = Path("app/api/miniapp_ads.py").read_text(encoding="utf-8")
        self.assertIn('"&lang="+encodeURIComponent(', js)
        self.assertIn('request.query_params.get("lang")', api)
        self.assertIn('language=chosen_lang', api)

    def test_android_and_ad_placement_render_localized_text(self):
        android = Path("app/api/android_features.py").read_text(encoding="utf-8")
        placement = Path("app/services/ad_placement_service.py").read_text(encoding="utf-8")
        self.assertIn('service.payload(ad, language=getattr(user, "language", None))', android)
        self.assertIn('candidates[index], language=language or getattr(user, "language", None)', placement)

    def test_admin_explains_tajik_source_and_one_click_translation(self):
        html = Path("app/static/admin.html").read_text(encoding="utf-8")
        self.assertIn('id="caLanguageNote"', html)
        self.assertIn('id="caTitleLabel"', html)
        self.assertIn('"caLang").addEventListener("change",caTypeUI)', html)

if __name__ == "__main__":
    unittest.main()
