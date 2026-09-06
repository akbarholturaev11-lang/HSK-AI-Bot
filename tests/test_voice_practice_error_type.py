"""AI javobidagi xato TURI (`error_type`).

Ilgari suhbatdagi har qanday tuzatish `category="pronunciation"` deb
yozilardi — klaviaturadan yozilgan grammatik xato ham. Natijada
`LearningSignals._weakness` talaffuz zaifligini shishirar va kunlik reja
grammatika xatosi qilgan o'quvchiga hal qilib bo'lmaydigan TALAFFUZ mashqini
berardi.

Bu testlar shartnomani qadaydi: model bergan tur tekshiriladi, noma'lum
qiymat tashlanadi, tuzatish yo'q bo'lsa tur "none" bo'ladi.
"""

import json
import unittest

from app.services.voice_practice_service import VoicePracticeService


def clean(**fields) -> dict:
    payload = {"chinese_reply": "你好！", "pinyin": "nǐ hǎo", "translation": "Salom"}
    payload.update(fields)
    return VoicePracticeService._clean_reply(json.dumps(payload, ensure_ascii=False))


class VoiceErrorTypeTests(unittest.TestCase):
    def test_a_valid_type_passes_through(self):
        for expected in ("grammar", "word", "pronunciation"):
            with self.subTest(expected=expected):
                reply = clean(correction="我去了北京", error_type=expected)
                self.assertEqual(expected, reply["error_type"])

    def test_an_unknown_type_falls_back_to_word(self):
        # Tasniflab bo'lmagan xato uchun loyihaning mavjud odati "word".
        reply = clean(correction="我去了北京", error_type="tone_disaster")
        self.assertEqual("word", reply["error_type"])

    def test_a_missing_type_with_a_correction_falls_back_to_word(self):
        reply = clean(correction="我去了北京")
        self.assertEqual("word", reply["error_type"])

    def test_no_correction_means_no_mistake_type(self):
        # Model "grammar" desa ham, tuzatish yo'q ekan — xato ham yo'q.
        reply = clean(correction=None, error_type="grammar")
        self.assertIsNone(reply["correction"])
        self.assertEqual("none", reply["error_type"])

    def test_the_reply_contract_still_carries_the_old_fields(self):
        # Desktop va Android aynan shu maydonlarni o'qiydi — buzilmasligi shart.
        reply = clean(correction="我去了北京", error_type="grammar")
        for key in ("chinese_reply", "pinyin", "translation", "correction"):
            self.assertIn(key, reply)


class VoiceReplySuggestionTests(unittest.TestCase):
    """"Nima deyish?" varag'i uchun takliflar.

    Ilgari bu varaqda 4 ta QOTIB QOLGAN HSK1 iborasi turardi: HSK1 uchun ham,
    HSK4 uchun ham, birinchi javobda ham, oxirgisida ham bir xil. Endi AI
    ularni suhbat javobi bilan BIR chaqiruvda qaytaradi — qo'shimcha so'rov
    ham, qo'shimcha kechikish ham yo'q.
    """

    def test_valid_suggestions_pass_through(self):
        reply = clean(
            correction=None,
            suggestions=[
                {"zh": "我很好", "pinyin": "wǒ hěn hǎo", "translation": "Men yaxshiman"},
                {"zh": "不太好", "pinyin": "bú tài hǎo", "translation": "Unchalik emas"},
            ],
        )
        self.assertEqual(["我很好", "不太好"], [s["zh"] for s in reply["suggestions"]])

    def test_at_most_two_are_kept(self):
        reply = clean(suggestions=[{"zh": f"我很好{i}"} for i in range(5)])
        self.assertEqual(2, len(reply["suggestions"]))

    def test_duplicates_and_non_chinese_are_dropped(self):
        # Xitoycha bo'lmagan taklif klaviaturaga qo'yilsa foydasiz.
        reply = clean(
            suggestions=[
                {"zh": "我很好"},
                {"zh": "我很好"},
                {"zh": "yaxshi"},
                {"zh": ""},
                "not a dict",
            ]
        )
        self.assertEqual(["我很好"], [s["zh"] for s in reply["suggestions"]])

    def test_a_missing_or_broken_field_falls_back_to_an_empty_list(self):
        # Klient bo'sh ro'yxatda doimiy xavfsiz iboralarga qaytadi.
        for raw in (None, "нет", 5, {}):
            with self.subTest(raw=raw):
                self.assertEqual([], clean(suggestions=raw)["suggestions"])
        self.assertEqual([], clean()["suggestions"])


class VoiceOpeningSuggestionTests(unittest.TestCase):
    def test_every_opening_offers_two_level_safe_answers(self):
        # Sessiya boshida AI hali chaqirilmagan, shuning uchun bu takliflar
        # qo'lda yozilgan — tekin va kafolatli to'g'ri.
        from app.services.voice_practice_service import OPENING_MESSAGES

        for role, variants in OPENING_MESSAGES.items():
            for variant in variants:
                with self.subTest(role=role, opening=variant["chinese_reply"]):
                    suggestions = variant.get("suggestions") or []
                    self.assertEqual(2, len(suggestions))
                    for entry in suggestions:
                        self.assertTrue(entry["zh"] and entry["pinyin"])
                        # Uchchala til majburiy (loyiha qoidasi).
                        for lang in ("uz", "ru", "tj"):
                            self.assertTrue(entry["translations"][lang], lang)

    def test_the_opening_resolves_suggestions_in_the_learners_language(self):
        for language in ("uz", "ru", "tj"):
            with self.subTest(language=language):
                opening = VoicePracticeService._opening_message("friend", language)
                self.assertEqual(2, len(opening["suggestions"]))
                self.assertTrue(all(s["translation"] for s in opening["suggestions"]))
