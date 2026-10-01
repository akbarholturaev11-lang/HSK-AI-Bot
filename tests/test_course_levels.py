import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.ai_service import AIService
from app.services.course_levels import (
    TRACK_HSK20,
    TRACK_HSK30,
    ai_level_context,
    content_level,
    hsk30_content_levels,
    is_hsk30_level,
    legacy_content_levels,
    level_spec,
    next_level,
    normalize_legacy_content_level,
    onboarding_levels,
    render_level,
)
from app.services.hsk30_feature_service import (
    HSK30_ENABLED_SETTINGS_KEY,
    Hsk30FeatureService,
)


class CourseLevelRegistryTests(unittest.TestCase):
    def test_legacy_levels_keep_their_existing_shape(self):
        self.assertEqual(legacy_content_levels(), ("hsk1", "hsk2", "hsk3", "hsk4"))
        self.assertEqual(
            onboarding_levels(),
            frozenset({"beginner", "hsk1", "hsk2", "hsk3", "hsk4"}),
        )
        self.assertEqual(content_level("beginner"), "hsk1")
        self.assertEqual(normalize_legacy_content_level("az0"), "hsk1")
        self.assertEqual(normalize_legacy_content_level("hsk4b"), "hsk4")
        self.assertEqual(render_level("hsk4", 10), "hsk4a")
        self.assertEqual(render_level("hsk4", 11), "hsk4b")

    def test_hsk30_levels_are_registered_but_not_selectable_by_default(self):
        self.assertEqual(hsk30_content_levels(), ("nhsk1", "nhsk2", "nhsk3", "nhsk4"))
        self.assertEqual(content_level("nbeginner"), "nhsk1")
        self.assertNotIn("nbeginner", onboarding_levels())
        self.assertIn("nbeginner", onboarding_levels(hsk30_enabled=True))
        for band in range(1, 5):
            key = f"nhsk{band}"
            spec = level_spec(key)
            self.assertIsNotNone(spec)
            self.assertEqual(spec.track, TRACK_HSK30)
            self.assertTrue(is_hsk30_level(key))
            self.assertNotIn(key, onboarding_levels())
            if band < 4:
                self.assertIn(key, onboarding_levels(hsk30_enabled=True))
            else:
                self.assertFalse(spec.selectable)
                self.assertNotIn(key, onboarding_levels(hsk30_enabled=True))

    def test_track_and_next_level_are_stable(self):
        self.assertEqual(level_spec("hsk1").track, TRACK_HSK20)
        self.assertEqual(next_level("hsk1"), "hsk2")
        self.assertEqual(next_level("hsk3"), "hsk4")
        self.assertIsNone(next_level("hsk4"))
        self.assertEqual(next_level("nhsk1"), "nhsk2")
        self.assertIsNone(next_level("nhsk3"))
        self.assertIsNone(next_level("nhsk4"))

    def test_ai_context_distinguishes_hsk30_from_legacy(self):
        self.assertEqual(
            ai_level_context("nhsk1"),
            "HSK 3.0, 1-daraja (N1), jami ~300 so'z",
        )
        self.assertEqual(
            ai_level_context("nhsk2"),
            "HSK 3.0, 2-daraja (N2), jami ~500 so'z",
        )
        self.assertEqual(
            ai_level_context("nhsk3"),
            "HSK 3.0, 3-daraja (N3), jami ~1000 so'z",
        )
        self.assertEqual(
            ai_level_context("hsk3"),
            "HSK 2.0, 3-daraja (HSK 3)",
        )

    def test_qa_system_prompt_receives_hsk30_curriculum_context(self):
        service = AIService.__new__(AIService)
        service.prompt_path = __import__("pathlib").Path("app/prompts/qa_system.txt")
        prompt = service._build_system_prompt("uz", "nhsk2")

        self.assertIn("Current level key: nhsk2", prompt)
        self.assertIn("HSK 3.0, 2-daraja (N2), jami ~500 so'z", prompt)

    def test_unknown_legacy_level_fails_back_exactly_as_before(self):
        self.assertEqual(normalize_legacy_content_level(None), "hsk1")
        self.assertEqual(normalize_legacy_content_level("nonsense"), "hsk1")
        self.assertEqual(normalize_legacy_content_level("nhsk1"), "hsk1")


class Hsk30FeatureServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_flag_is_off(self):
        service = Hsk30FeatureService(SimpleNamespace())
        service.setting_repo = SimpleNamespace(
            get_bool=AsyncMock(return_value=False),
        )
        self.assertFalse(await service.is_enabled())
        service.setting_repo.get_bool.assert_awaited_once_with(
            HSK30_ENABLED_SETTINGS_KEY,
            default=False,
        )

    async def test_flag_write_uses_bot_settings_boolean_value(self):
        service = Hsk30FeatureService(SimpleNamespace())
        setting = object()
        service.setting_repo = SimpleNamespace(
            get_record=AsyncMock(return_value=SimpleNamespace(value="0")),
            set_bool=AsyncMock(return_value=setting),
        )
        self.assertIs(await service.set_enabled(True), setting)
        service.setting_repo.set_bool.assert_awaited_once_with(
            HSK30_ENABLED_SETTINGS_KEY,
            True,
        )

    async def test_saving_same_enabled_value_does_not_restart_release_clock(self):
        service = Hsk30FeatureService(SimpleNamespace())
        record = SimpleNamespace(value="1")
        service.setting_repo = SimpleNamespace(
            get_record=AsyncMock(return_value=record),
            set_bool=AsyncMock(),
        )
        self.assertIs(await service.set_enabled(True), record)
        service.setting_repo.set_bool.assert_not_awaited()

    async def test_new_badge_is_server_timed_for_exactly_three_days(self):
        service = Hsk30FeatureService(SimpleNamespace())
        enabled_at = datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc)
        service.setting_repo = SimpleNamespace(
            get_record=AsyncMock(
                return_value=SimpleNamespace(value="1", updated_at=enabled_at)
            ),
        )
        before = await service.new_badge(
            now=enabled_at + timedelta(days=2, hours=23, minutes=59)
        )
        expired = await service.new_badge(now=enabled_at + timedelta(days=3))
        self.assertTrue(before["is_new"])
        self.assertFalse(expired["is_new"])
        self.assertEqual(
            before["new_until"],
            (enabled_at + timedelta(days=3)).isoformat(),
        )


if __name__ == "__main__":
    unittest.main()
