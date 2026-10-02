import json
import unittest

from scripts.hsk30 import build_dictionary_assets


class Hsk30DictionaryContentTests(unittest.TestCase):
    def test_every_hsk30_word_has_a_localized_example(self):
        examples = build_dictionary_assets.build_examples()
        _, hsk30_words = build_dictionary_assets.dictionary_words()

        legacy_examples = build_dictionary_assets.js_json(
            build_dictionary_assets.LEGACY_EXAMPLES_JS, "const EXAMPLES="
        )
        manual_rows = json.loads(
            build_dictionary_assets.MANUAL_EXAMPLES.read_text(encoding="utf-8")
        )
        expected_examples = {
            word
            for word in hsk30_words
            if not (isinstance(legacy_examples.get(word), dict) and legacy_examples[word].get("zh"))
        } | {row["word"] for row in manual_rows if row.get("prefer") is True}
        self.assertEqual(set(examples), expected_examples)
        self.assertEqual(len(hsk30_words), 970)
        for word in hsk30_words:
            self.assertTrue(
                (isinstance(legacy_examples.get(word), dict) and legacy_examples[word].get("zh"))
                or word in examples,
                word,
            )
        for word, example in examples.items():
            with self.subTest(word=word):
                self.assertTrue(build_dictionary_assets.valid_example(word, example))

    def test_generated_dictionary_examples_are_current_and_served(self):
        examples = build_dictionary_assets.build_examples()
        expected = build_dictionary_assets.render_asset(examples)
        self.assertEqual(build_dictionary_assets.OUTPUT.read_text(encoding="utf-8"), expected)

        page = (build_dictionary_assets.STATIC / "hsk-lugat.html").read_text(encoding="utf-8")
        main = (build_dictionary_assets.ROOT / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn("hsk30-dictionary-examples.js", page)
        self.assertIn('"hsk30-dictionary-examples.js": "application/javascript"', main)
        self.assertIn("examplePinyin.textContent = ex.p || ''", page)
        self.assertIn("loadStrokeData(c, onComplete, onError, loadToken)", page)
        self.assertIn("hsk30MemoryFallback(word)", page)


if __name__ == "__main__":
    unittest.main()
