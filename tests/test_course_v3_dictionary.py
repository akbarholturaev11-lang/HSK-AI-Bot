import unittest

from app.services import course_v3_dictionary as dictionary


class CourseV3DictionaryTests(unittest.TestCase):
    def setUp(self):
        dictionary._cache = None

    def test_native_dictionary_contains_both_hsk_versions(self):
        words = dictionary.dictionary_for_language("uz")
        levels = {item["lv"] for item in words}

        self.assertIn("HSK1", levels)
        self.assertIn("N1", levels)
        self.assertGreater(len(words), 1000)
        self.assertTrue(dictionary.dictionary_version())

    def test_all_three_languages_keep_same_word_count(self):
        counts = {
            lang: len(dictionary.dictionary_for_language(lang))
            for lang in ("uz", "ru", "tj")
        }
        self.assertEqual(len(set(counts.values())), 1)


if __name__ == "__main__":
    unittest.main()
