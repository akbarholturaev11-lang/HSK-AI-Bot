"""Public course-map template cache: private mutations must never leak."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.course_map_template_cache import (
    _parsed_template,
    load_course_map_template,
)


class CourseMapTemplateCacheTests(unittest.TestCase):
    def setUp(self):
        _parsed_template.cache_clear()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.path = self.directory / "hsk1.json"
        self.path.write_text(
            json.dumps({"level": "hsk1", "units": [{"lessons": [{"n": 1, "status": "locked"}]}]}),
            encoding="utf-8",
        )

    def tearDown(self):
        _parsed_template.cache_clear()

    def test_reuses_parsed_template_without_sharing_mutable_user_state(self):
        first = load_course_map_template("hsk1", directory=self.directory)
        first["units"][0]["lessons"][0]["status"] = "done"
        first["user"] = {"id": 17, "is_paid": True}
        second = load_course_map_template("hsk1", directory=self.directory)

        self.assertEqual(second["units"][0]["lessons"][0]["status"], "locked")
        self.assertNotIn("user", second)
        self.assertEqual((_parsed_template.cache_info().misses,
                          _parsed_template.cache_info().hits), (1, 1))
        self.assertIsNot(first["units"], second["units"])

    def test_changed_template_is_reparsed_and_old_versions_are_bounded(self):
        before = load_course_map_template("hsk1", directory=self.directory)
        self.path.write_text(json.dumps({"level": "hsk1", "units": [], "new": True}),
                             encoding="utf-8")
        after = load_course_map_template("hsk1", directory=self.directory)
        self.assertNotIn("new", before)
        self.assertTrue(after["new"])
        self.assertEqual(_parsed_template.cache_info().misses, 2)
        self.assertEqual(_parsed_template.cache_info().maxsize, 16)

    def test_unknown_or_missing_level_falls_back_to_hsk1_without_path_traversal(self):
        for level in ("unknown", "../../secrets", "hsk2"):
            with self.subTest(level=level):
                self.assertEqual(
                    load_course_map_template(level, directory=self.directory)["level"],
                    "hsk1",
                )

    def test_invalid_file_is_not_cached_and_recovers_after_fix(self):
        self.path.write_text("not json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            load_course_map_template("hsk1", directory=self.directory)
        self.path.write_text('{"units": [], "level": "hsk1"}', encoding="utf-8")
        self.assertEqual(load_course_map_template("hsk1", directory=self.directory)["level"],
                         "hsk1")

    def test_real_templates_retained_in_contract(self):
        real_dir = Path("app/static/course_v3_data")
        for level in ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"):
            with self.subTest(level=level):
                template = load_course_map_template(level, directory=real_dir)
                self.assertEqual(template["level"], level)
                self.assertIsInstance(template["units"], list)
                self.assertNotIn("user", template)


if __name__ == "__main__":
    unittest.main()
