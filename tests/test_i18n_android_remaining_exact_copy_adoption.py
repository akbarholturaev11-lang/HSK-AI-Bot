"""Exact-copy Android UI resources moved into the local generated catalogs."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ANDROID_RES = ROOT / "android/app/src/main/res"

# Every value below is an existing UI label whose three Android translations
# were verified against the generated local common/course catalog before its
# Compose call sites were switched to the generated resource.
LEGACY_TO_GENERATED = {
    "action_back": "hsk_common_action_back",
    "action_clear": "hsk_course_dictionary_page_clear_history",
    "action_close": "hsk_common_action_close",
    "action_continue": "hsk_common_action_continue",
    "ad_continue": "hsk_common_action_continue",
    "ad_ready": "hsk_common_action_done",
    "cd_language_switch": "hsk_course_lang",
    "challenge_finish": "hsk_common_action_finish",
    "challenge_start": "hsk_common_action_start",
    "dictionary_all_words": "hsk_course_dictionary_page_all_words",
    "dictionary_filter_all_levels": "hsk_course_dictionary_page_all_levels",
    "dictionary_filter_all_versions": "hsk_course_dictionary_page_all_versions",
    "dictionary_stroke_next": "hsk_course_dictionary_fast_writer_next",
    "dictionary_stroke_previous": "hsk_course_dictionary_fast_writer_previous",
    "exit_confirm_leave": "hsk_common_action_exit",
    "exit_confirm_stay": "hsk_common_action_continue",
    "hint_close": "hsk_common_action_close",
    "lesson_next": "hsk_common_action_continue",
    "lesson_skip_card": "hsk_course_pronunciation_skip",
    "lesson_streak_days": "hsk_course_streak_display_many",
    "notify_hsk30_payment_approved_title": "hsk_course_subscription_page_payment_approved_title",
    "practice_characters_title": "hsk_course_mistakes_page_sources_recognition",
    "profile_avatar_note": "hsk_course_android_profile_avatar_edit_note",
    "profile_help": "hsk_course_help",
    "profile_logout": "hsk_common_action_logout",
    "ready_phrases_back": "hsk_common_action_back",
    "skip_test_confirm_no": "hsk_common_action_back",
    "state_loading": "hsk_common_state_loading",
    "voice_what_to_say": "hsk_course_voice_page_what_to_say",
    "action_retry": "hsk_course_lesson_flow_retry",
    "rating_weekly_top_five": "hsk_course_rating_weekly_top_five",
    "rating_friends_joined": "hsk_course_rating_referral_joined",
    "rating_weekly_result": "hsk_course_rating_weekly_heading",
    "writing_finish": "hsk_common_action_done",
    "writing_start": "hsk_common_action_start",
}

# Includes six existing call sites that already used the destination resource.
EXPECTED_GENERATED_CALLS = {
    "hsk_common_action_back": 5,
    "hsk_course_dictionary_page_clear_history": 1,
    "hsk_common_action_close": 20,
    "hsk_common_action_continue": 16,
    "hsk_common_action_done": 2,
    "hsk_course_lang": 2,
    "hsk_common_action_finish": 1,
    "hsk_common_action_start": 2,
    "hsk_course_dictionary_page_all_words": 1,
    "hsk_course_dictionary_page_all_levels": 1,
    "hsk_course_dictionary_page_all_versions": 1,
    "hsk_course_dictionary_fast_writer_next": 1,
    "hsk_course_dictionary_fast_writer_previous": 1,
    "hsk_course_pronunciation_skip": 1,
    "hsk_common_action_exit": 1,
    "hsk_course_streak_display_many": 1,
    "hsk_course_subscription_page_payment_approved_title": 1,
    "hsk_course_mistakes_page_sources_recognition": 2,
    "hsk_course_android_profile_avatar_edit_note": 1,
    "hsk_course_help": 1,
    "hsk_common_action_logout": 1,
    "hsk_common_state_loading": 1,
    "hsk_course_voice_page_what_to_say": 1,
    "hsk_course_lesson_flow_retry": 11,
    "hsk_course_rating_weekly_top_five": 1,
    "hsk_course_rating_referral_joined": 1,
    "hsk_course_rating_weekly_heading": 1,
}

LOCALES = (("", "uz"), ("-ru", "ru"), ("-tg", "tj"))


def _strings(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    return {entry.attrib["name"]: entry.text or "" for entry in root.findall("string")}


class AndroidRemainingExactCopyAdoptionTests(unittest.TestCase):
    def test_legacy_android_values_match_generated_resources_in_all_locales(self):
        self.assertEqual(len(LEGACY_TO_GENERATED), 35)
        for qualifier, locale in LOCALES:
            with self.subTest(locale=locale):
                legacy = _strings(ANDROID_RES / f"values{qualifier}/strings.xml")
                common = _strings(ANDROID_RES / f"values{qualifier}/hsk_common_i18n.xml")
                course = _strings(ANDROID_RES / f"values{qualifier}/hsk_course_i18n.xml")
                for old_name, generated_name in LEGACY_TO_GENERATED.items():
                    generated = common if generated_name.startswith("hsk_common_") else course
                    with self.subTest(locale=locale, resource=old_name):
                        self.assertIn(old_name, legacy)
                        self.assertIn(generated_name, generated)
                        self.assertEqual(legacy[old_name], generated[generated_name])

    def test_compose_call_sites_use_generated_resources(self):
        kotlin_files = sorted((ROOT / "android/app/src/main/java").rglob("*.kt"))
        sources = "\n".join(path.read_text(encoding="utf-8") for path in kotlin_files)
        for old_name in LEGACY_TO_GENERATED:
            with self.subTest(legacy_resource=old_name):
                self.assertIsNone(re.search(
                    r"R\.string\." + re.escape(old_name) + r"\b", sources
                ))
        actual = {
            resource: len(re.findall(
                r"R\.string\." + re.escape(resource) + r"\b", sources
            ))
            for resource in EXPECTED_GENERATED_CALLS
        }
        self.assertEqual(actual, EXPECTED_GENERATED_CALLS)


if __name__ == "__main__":
    unittest.main()
