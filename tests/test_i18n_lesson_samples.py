"""Representative learner-text source baseline for all 7 course tracks."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_lesson_samples import check_samples, source_sample


def seed(root: Path, level: str = "hsk1") -> Path:
    path = root / "app/static/course_v3_data" / level / "lesson_01.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "level": level, "lesson_id": 1, "source_lesson": 1,
        "part_no": 1, "part_count": 3,
        "title": "你好",
        "subtitle": {"uz": "Salom", "ru": "Привет", "tj": "Салом"},
        "active_words": [{
            "zh": "你好", "pinyin": "nǐ hǎo",
            "meaning": {"uz": "salom", "ru": "привет", "tj": "салом"},
        }],
        "sections": [{"cards": [{"type": "active_word"}]}],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class LocaleSamplesTests(unittest.TestCase):
    def test_exact_source_locale_values_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = source_sample(seed(root), "hsk1")
            self.assertEqual(result["locales"]["tj"]["first_word_meaning"], "салом")
            self.assertEqual(result["locales"]["ru"]["subtitle"], "Привет")
            self.assertEqual(result["first_word_pinyin"], "nǐ hǎo")
            self.assertEqual(result["first_card_type"], "active_word")

    def test_missing_locale_is_not_silently_replaced_with_russian(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = seed(root)
            data = json.loads(file.read_text())
            del data["subtitle"]["tj"]
            file.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing tj"):
                source_sample(file, "hsk1")

    def test_wrong_lesson_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = seed(root)
            data = json.loads(file.read_text())
            data["lesson_id"] = 2
            file.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity"):
                source_sample(file, "hsk1")

    def test_changed_chinese_and_translated_copy_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
            baseline = {"schema_version": 1, "lessons": [
                source_sample(seed(root, track), track) for track in tracks
            ]}
            self.assertEqual(check_samples(root, baseline)["issues_count"], 0)
            file = root / "app/static/course_v3_data/nhsk3/lesson_01.json"
            data = json.loads(file.read_text())
            data["title"] = "再见"
            data["subtitle"]["uz"] = "other"
            file.write_text(json.dumps(data), encoding="utf-8")
            result = check_samples(root, baseline)
            self.assertEqual(result["issues_count"], 2)
            self.assertIn({"track": "nhsk3", "field": "title_zh"}, result["issues"])
            self.assertIn({"track": "nhsk3", "locale": "uz", "field": "subtitle"},
                          result["issues"])

    def test_absent_sample_file_is_review_issue(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3")
            baseline = {"schema_version": 1, "lessons": [
                source_sample(seed(root, track), track) for track in tracks
            ]}
            (root / "app/static/course_v3_data/hsk4/lesson_01.json").unlink()
            result = check_samples(root, baseline)
            self.assertEqual(result["issues_count"], 1)
            self.assertEqual(result["issues"][0]["field"], "file_or_shape")

    def test_duplicate_track_baseline_is_invalid(self):
        baseline = {"schema_version": 1, "lessons": [
            {"level": "hsk1"} for _ in range(7)
        ]}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            check_samples(Path("."), baseline)


if __name__ == "__main__":
    unittest.main()
