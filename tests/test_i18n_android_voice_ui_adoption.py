"""Exact-copy Android Voice UI adoption from the generated local catalog."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"uz": "values", "ru": "values-ru", "tj": "values-tg"}
VOICE_RESOURCES = {
    "voice_a11y_keyboard": "hsk_course_course_voice_inline_a11y_keyboard",
    "voice_a11y_mic": "hsk_course_course_voice_inline_a11y_mic",
    "voice_a11y_send": "hsk_course_course_voice_inline_a11y_send",
    "voice_hints_phrases": "hsk_course_voice_page_hint_phrases",
    "voice_hints_title": "hsk_course_voice_page_hint_title",
    "voice_keyboard_hint": "hsk_course_voice_page_kb_placeholder",
    "voice_partner": "hsk_course_voice_page_opt_persona",
    "voice_rate_normal": "hsk_course_voice_page_rate_normal",
    "voice_rate_slow": "hsk_course_voice_page_rate_slow",
    "voice_setting_on": "hsk_course_voice_page_on",
    "voice_setting_partner": "hsk_course_voice_page_opt_persona",
    "voice_setting_rate": "hsk_course_voice_page_opt_rate",
    "voice_setting_subtitles": "hsk_course_voice_page_opt_sub",
    "voice_settings_title": "hsk_course_voice_page_settings",
    "voice_status_analyzing": "hsk_course_voice_page_analyzing",
    "voice_status_connecting": "hsk_course_voice_page_connecting",
    "voice_status_listening": "hsk_course_voice_page_listening",
    "voice_status_speaking": "hsk_course_voice_page_speaking",
    "voice_start": "hsk_course_voice_start",
    "voice_you": "hsk_course_you",
    "voice_box_title": "hsk_course_voice_title",
}
VOICE_FILES = (
    "android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceCallScreen.kt",
    "android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceScreen.kt",
    "android/app/src/main/java/com/pomp/hskai/feature/practice/WordDrillScreen.kt",
    "android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCards.kt",
)


def read_android_strings(locale_dir, file_name):
    root = ET.parse(ROOT / "android/app/src/main/res" / locale_dir / file_name).getroot()
    return {node.attrib["name"]: "".join(node.itertext())
            for node in root.findall("string")}


class AndroidVoiceUIAdoptionTests(unittest.TestCase):
    def test_voice_strings_match_generated_values_in_all_locales(self):
        self.assertEqual(len(VOICE_RESOURCES), 21)
        for locale, directory in LOCALES.items():
            original = read_android_strings(directory, "strings.xml")
            generated = read_android_strings(directory, "hsk_course_i18n.xml")
            for original_key, generated_key in VOICE_RESOURCES.items():
                with self.subTest(locale=locale, key=original_key):
                    self.assertIn(original_key, original)
                    self.assertIn(generated_key, generated)
                    self.assertEqual(original[original_key], generated[generated_key])

    def test_voice_screens_read_generated_resources_and_keep_behavioral_copy(self):
        sources = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in VOICE_FILES
        }
        combined = "\n".join(sources.values())
        for original_key, generated_key in VOICE_RESOURCES.items():
            with self.subTest(key=original_key):
                self.assertIn(f"R.string.{generated_key}", combined)
                self.assertNotIn(f"R.string.{original_key}", combined)
        call_screen = sources[VOICE_FILES[0]]
        self.assertIn("state.isLiveMuted -> stringResource(R.string.voice_status_muted)",
                      call_screen)
        self.assertIn("state.isLive && !state.isLiveConnected -> stringResource(R.string.voice_status_live_disconnected)",
                      call_screen)
        self.assertIn("else R.string.voice_setting_off", call_screen)
        for callback in ("onToggleRecording", "onSendText", "onEndSession"):
            self.assertIn(callback, call_screen)


if __name__ == "__main__":
    unittest.main()
