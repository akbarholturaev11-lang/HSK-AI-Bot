"""Bir tilning so'zi boshqa tilning matniga tushib qolmasin.

Loyihaning qat'iy qoidasi: uz / ru / tj hech qachon ARALASHMAYDI. Buni buzish
uchun tarjima qilmaslik shart emas — bitta UMUMIY maydon ham yetadi.

Aynan shunday bo'ldi: `pinyin` maydoni bitta va uchala til uchun ishlatiladi,
unga esa o'zbekcha izoh yozib qo'yilgandi:

    "pinyin": "nǐ hǎo (tabiiy: ní hǎo)"

Rus va tojik foydalanuvchi ekranda "tabiiy" so'zini shundayligicha ko'rdi.
Tarjima maydonlari joyida edi — muammo tarjima qilinmaydigan maydonda edi.

Shuning uchun bu yerda tekshiriladigan narsa: TILGA BOG'LIQ BO'LMAGAN
maydonlarda tilga bog'liq so'z bo'lmasligi.
"""

import json
import re
import unittest
from pathlib import Path


COURSE_ROOT = Path("app/static/course_v3_data")

#: Tilga bog'liq bo'lmagan maydonlar: xitoycha yozuv, pinyin, ohang.
#: Bularda kirill harflari ham, lotin so'zlari ham bo'lmasligi kerak.
NEUTRAL_FIELDS = ("pinyin", "zh", "audio_text")

CYRILLIC = re.compile(r"[а-яёА-ЯЁӣӯҳқғҷӢӮҲҚҒҶ]")

#: Uchala tildan biriga tegishli, tarjimasiz qolib ketishi mumkin bo'lgan
#: so'zlar. Ro'yxat to'liq emas — u faqat allaqachon sodir bo'lgan va yana
#: sodir bo'lishi mumkin bo'lgan holatlarni ushlaydi.
LANGUAGE_WORDS = re.compile(
    r"(?<![a-zA-Z])(tabiiy|yoziladi|o'qiladi|talaffuz|deb\s|pishetsya|navishta)",
    re.IGNORECASE,
)


def _lesson_files():
    return sorted(COURSE_ROOT.glob("hsk*/lesson_*.json"))


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


class NeutralFieldsCarryNoLanguageTests(unittest.TestCase):
    def test_the_course_data_is_there_to_check(self):
        # Fayllar topilmasa test jimgina o'tib ketmasin.
        self.assertTrue(_lesson_files(), "kurs ma'lumotlari topilmadi")

    def test_no_neutral_field_contains_cyrillic(self):
        for path in _lesson_files():
            data = json.loads(path.read_text(encoding="utf-8"))
            for node in _walk(data):
                for field in NEUTRAL_FIELDS:
                    value = node.get(field)
                    if not isinstance(value, str):
                        continue
                    with self.subTest(file=path.name, field=field):
                        self.assertIsNone(
                            CYRILLIC.search(value),
                            f"{path}: `{field}` da kirill matni: {value[:80]}",
                        )

    def test_no_neutral_field_contains_a_language_word(self):
        for path in _lesson_files():
            data = json.loads(path.read_text(encoding="utf-8"))
            for node in _walk(data):
                for field in NEUTRAL_FIELDS:
                    value = node.get(field)
                    if not isinstance(value, str):
                        continue
                    with self.subTest(file=path.name, field=field):
                        self.assertIsNone(
                            LANGUAGE_WORDS.search(value),
                            f"{path}: `{field}` da til so'zi: {value[:80]}",
                        )


class EveryVisibleStringHasThreeLanguagesTests(unittest.TestCase):
    """uz/ru/tj bloklarining birortasi bo'sh qolmasin."""

    def test_no_translation_block_is_missing_a_language(self):
        missing = []
        for path in _lesson_files():
            data = json.loads(path.read_text(encoding="utf-8"))
            for node in _walk(data):
                keys = set(node.keys())
                if not {"uz", "ru", "tj"} <= keys:
                    continue
                for lang in ("uz", "ru", "tj"):
                    value = node.get(lang)
                    if isinstance(value, str) and not value.strip():
                        missing.append(f"{path.name}: {lang} bo'sh")
        self.assertEqual([], missing[:20])


if __name__ == "__main__":
    unittest.main()
