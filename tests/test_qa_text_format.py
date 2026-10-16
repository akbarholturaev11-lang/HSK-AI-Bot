"""Regression for literal Markdown stars in HSK AI Telegram chat replies."""

import unittest

from app.services.qa_text_format import clean_ai_qa_markup


class TestTelegramQAMarkdownCleanup(unittest.TestCase):
    def test_real_tajik_chinese_word_list_example(self):
        original = (
            "4. **书** (shū) — китоб\n"
            " * **Мисол:** 这是一本书。 (Zhè shì yì běn shū.) — Ин як китоб аст.\n\n"
            "5. **水** (shuǐ) — об\n"
            " * **Мисол:** 我想喝水。 (Wǒ xiǎng hē shuǐ.) — Ман об нӯшидан мехоҳам."
        )
        expected = (
            "4. 书 (shū) — китоб\n"
            " • Мисол: 这是一本书。 (Zhè shì yì běn shū.) — Ин як китоб аст.\n\n"
            "5. 水 (shuǐ) — об\n"
            " • Мисол: 我想喝水。 (Wǒ xiǎng hē shuǐ.) — Ман об нӯшидан мехоҳам."
        )
        self.assertEqual(clean_ai_qa_markup(original), expected)

    def test_heading_and_italics(self):
        self.assertEqual(
            clean_ai_qa_markup("### **HSK 3**\n- *Дарс:* 你好 (nǐ hǎo) — салом"),
            "HSK 3\n• Дарс: 你好 (nǐ hǎo) — салом",
        )

    def test_preserves_arithmetic_and_code_asterisks(self):
        original = "2 * 3 = 6, 2**3 = 8, price*qty, a*b*c"
        self.assertEqual(clean_ai_qa_markup(original), original)

    def test_keeps_natural_text_untouched(self):
        original = "Ман ба мактаб меравам. 我去学校。 (Wǒ qù xuéxiào.)"
        self.assertEqual(clean_ai_qa_markup(original), original)

    def test_bullet_does_not_erase_numbered_lists(self):
        self.assertEqual(clean_ai_qa_markup("1. **去** (qù)\n2. **买** (mǎi)"), "1. 去 (qù)\n2. 买 (mǎi)")

    def test_only_well_formed_markup_is_removed(self):
        self.assertEqual(clean_ai_qa_markup("_test_ **unclosed"), "_test_ **unclosed")

    def test_none_empty_and_whitespace(self):
        self.assertEqual(clean_ai_qa_markup(None), "")
        self.assertEqual(clean_ai_qa_markup("  \n "), "")


if __name__ == "__main__":
    unittest.main()
