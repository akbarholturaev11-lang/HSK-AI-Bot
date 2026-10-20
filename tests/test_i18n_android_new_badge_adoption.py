"""Android uses translated local catalog resources for visible NEW badges."""
import json
import unittest
import xml.etree.ElementTree as ET

from scripts.i18n_build_course_catalogs import ROOT


EXPECTED = {"uz": "YANGI", "ru": "НОВОЕ", "tj": "НАВ"}
RESOURCE_DIRS = {"uz": "values", "ru": "values-ru", "tj": "values-tg"}


class AndroidNewBadgeAdoptionTests(unittest.TestCase):
    def test_visible_badges_use_the_generated_course_string_resource(self):
        books = (
            ROOT / "android/app/src/main/java/com/pomp/hskai/core/design/components/"
            "Hsk30BooksHeader.kt"
        ).read_text(encoding="utf-8")
        practice = (
            ROOT / "android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("stringResource(R.string.hsk_course_new_section_badge)", books)
        self.assertIn("text = stringResource(R.string.hsk_course_new_section_badge)", practice)
        self.assertNotIn('"NEW"', books)
        self.assertNotIn('text = "NEW"', practice)

    def test_generated_android_and_source_course_values_match_each_locale(self):
        for locale, resource_dir in RESOURCE_DIRS.items():
            with self.subTest(locale=locale):
                catalog = json.loads(
                    (ROOT / f"localization/ui/{locale}/course.json").read_text(encoding="utf-8")
                )["messages"]
                self.assertEqual(catalog["newSectionBadge"], EXPECTED[locale])
                xml_root = ET.parse(
                    ROOT / f"android/app/src/main/res/{resource_dir}/hsk_course_i18n.xml"
                ).getroot()
                values = {item.attrib["name"]: item.text for item in xml_root.findall("string")}
                self.assertEqual(values["hsk_course_new_section_badge"], EXPECTED[locale])

    def test_onboarding_has_no_unused_english_badge_copy(self):
        source = (
            ROOT / "android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("newBadge", source)
        self.assertNotIn('"NEW"', source)


if __name__ == "__main__":
    unittest.main()
