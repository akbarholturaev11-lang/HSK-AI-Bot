"""Fail-closed tests for three local-first Mini App course UI catalogs."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_course_ui_catalog_guard import (
    EXPECTED_COUNT, LOCALES, ROOT, review_sources, signature,
)


class CourseUICatalogGuardTests(unittest.TestCase):
    def test_existing_three_locale_104_key_contract(self):
        result = review_sources(ROOT)
        self.assertEqual(result["status"], "SOURCE_CONTRACT_VALID_RUNTIME_NOT_TESTED")
        self.assertEqual(result["message_keys"], 104)
        self.assertEqual(result["locales"], list(LOCALES))
        self.assertEqual(result["placeholder_keys"], 2)
        self.assertEqual(len(result["sources"]), 3)
        self.assertNotIn("HSK AI Pro открыт", str(result))

    def test_placeholders_are_multisets_not_just_names(self):
        self.assertEqual(signature("Remaining {n} / {n}"), (("n", 2),))
        with self.assertRaises(ValueError):
            signature("Broken {n")

    def test_duplicate_keys_and_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for locale in LOCALES:
                dst = root / "localization/ui" / locale / "course.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                src = ROOT / "localization/ui" / locale / "course.json"
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(review_sources(root)["message_keys"], EXPECTED_COUNT)

            ru = root / "localization/ui/ru/course.json"
            data = json.loads(ru.read_text(encoding="utf-8"))
            data["messages"]["trialLeft"] = "days remaining {other}"
            ru.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "placeholder mismatch"):
                review_sources(root)

            data["messages"]["trialLeft"] = "days remaining {n}"
            data["messages"]["correct_index"] = "private grading metadata"
            ru.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                review_sources(root)

            data["messages"].pop("correct_index")
            data["messages"]["trialLeft"] = "<script>not UI copy</script>"
            ru.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                review_sources(root)

            data["messages"]["trialLeft"] = "days remaining {n}"
            data["messages"].pop("trialLeftHours")
            ru.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                review_sources(root)

            # A hand-written duplicate in JSON cannot silently override text.
            source = (ROOT / "localization/ui/ru/course.json").read_text(encoding="utf-8")
            ru.write_text(source.replace('"schema_version": 1,',
                                         '"schema_version": 1, "schema_version": 1,', 1),
                          encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate source JSON key"):
                review_sources(root)


if __name__ == "__main__":
    unittest.main()
