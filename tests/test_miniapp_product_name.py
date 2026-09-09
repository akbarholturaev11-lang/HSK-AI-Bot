"""Bitta mahsulot — bitta nom.

Foydalanuvchi buni jonli ilovada ko'rib aytdi: ayni obuna Mini App ichida
uchta boshqa-boshqa nom bilan atalardi —

    "HSK AI Pro"       (trial va reja tanlovida)
    "HSK AI Premium"   (paywall sarlavhasida)
    "Premium"          (tugmalarda)

Odam buni bitta narsa deb tushunmaydi: u ikkita boshqa mahsulot bor deb
o'ylaydi va qaysi birini olishni bilmaydi. Yagona nom — **HSK AI Pro**.

Ikkinchi qoida: limitga urilganda ASOSIY tugma har doim bitta va u aynan
shu nomni aytadi. Trialni allaqachon ishlatgan odamga boshqa hech narsa
taklif qilinmaydi.
"""

import re
import unittest
from pathlib import Path


MINIAPP_FILES = [
    Path("app/static/course-v3.html"),
    Path("app/static/course_v3_recognition.html"),
    Path("app/static/course_v3_pronunciation.html"),
    Path("app/static/course_v3_memorize.html"),
    Path("app/static/course_v3_test.html"),
    Path("app/static/course_v3_mistakes.html"),
    Path("app/static/course_v3_voice.html"),
    Path("app/static/course_v3_data/ads.js"),
]

#: Foydalanuvchiga ko'rinadigan matn — `key:"..."` shaklidagi satrlar.
STRING_LITERAL = re.compile(r'[A-Za-z_][A-Za-z0-9_]*:"([^"]*)"')

PRODUCT = "HSK AI Pro"


def _visible_strings(path: Path):
    return STRING_LITERAL.findall(path.read_text(encoding="utf-8"))


class OneProductOneNameTests(unittest.TestCase):
    def test_the_files_are_there_to_check(self):
        for path in MINIAPP_FILES:
            with self.subTest(file=path.name):
                self.assertTrue(path.exists(), f"{path} topilmadi")

    def test_no_visible_text_says_premium(self):
        offenders = []
        for path in MINIAPP_FILES:
            for value in _visible_strings(path):
                if "Premium" in value or "премиум" in value.lower():
                    offenders.append(f"{path.name}: {value[:70]}")
        self.assertEqual([], offenders)

    def test_the_product_name_is_always_written_in_full(self):
        """Yalang'och "Pro" — bu ham boshqa mahsulotdek o'qiladi."""
        offenders = []
        for path in MINIAPP_FILES:
            for value in _visible_strings(path):
                for match in re.finditer(r"\bPro\b", value):
                    before = value[: match.start()]
                    if not before.rstrip().endswith("HSK AI"):
                        offenders.append(f"{path.name}: {value[:70]}")
                        break
        self.assertEqual([], offenders)


class TheLimitOffersOneThingTests(unittest.TestCase):
    """Limitga urilganda asosiy tugma bitta va u Pro ni taklif qiladi."""

    ADS = Path("app/static/course_v3_data/ads.js")

    def test_the_main_limit_button_names_the_product(self):
        text = self.ADS.read_text(encoding="utf-8")
        buttons = re.findall(r'limitSubscribe:"([^"]*)"', text)

        self.assertEqual(3, len(buttons), "uchala tilda ham bo'lishi kerak")
        for label in buttons:
            with self.subTest(label=label):
                self.assertIn(PRODUCT, label)
                self.assertIn("⭐️", label)

    def test_the_trial_is_the_only_second_option(self):
        """Reklama tugmasi butunlay yo'q — u hech narsani ochmaydi."""
        text = self.ADS.read_text(encoding="utf-8")

        # `limAd` elementi endi FAQAT trial uchun ishlatiladi.
        self.assertIn("showTrialButton", text)
        self.assertNotIn("onContinueAd", text)

    def test_no_limit_screen_still_offers_an_ad(self):
        """Matn "reklama ko'ring" deb turgani — eng chalg'ituvchi ziddiyat:
        tugma yo'q, taklif esa bor."""
        offenders = []
        for path in MINIAPP_FILES:
            for value in _visible_strings(path):
                low = value.lower()
                if not any(k in low for k in ("limit", "bepul", "ройгон", "бесплат")):
                    continue
                if any(
                    k in low
                    for k in ("reklama ko'ring", "рекламу", "рекламаи кӯтоҳро бинед")
                ):
                    offenders.append(f"{path.name}: {value[:70]}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()


class TheCopyMatchesTheButtonItNamesTests(unittest.TestCase):
    """Izoh mavjud bo'lmagan tugmani ko'rsatmasin.

    Foydalanuvchi buni jonli ilovada ko'rdi: paywall ostidagi izoh
    «Obuna bo'lish» tugmasini ko'rsatardi, ekranда esa «HSK AI Pro olish»
    tugmasi turardi. Odam «Obuna bo'lish»ni qidiradi, topa olmaydi.
    """

    COURSE = Path("app/static/course-v3.html").read_text(encoding="utf-8")

    def test_the_paywall_hint_does_not_name_a_button_that_is_not_there(self):
        for phantom in (
            "«Obuna bo'lish» tugmasi",
            "«Оформить подписку» откроет",
            "«Обуна шудан» саҳифаи",
        ):
            with self.subTest(phantom=phantom):
                self.assertNotIn(phantom, self.COURSE)

    def test_the_paywall_hint_points_at_the_button_generically(self):
        # Tugma matni holatga qarab o'zgaradi (obuna / trial), shuning uchun
        # izoh aniq nomni takrorlamay "yuqoridagi tugma" deydi.
        for generic in ("Yuqoridagi tugma", "Кнопка выше", "Тугмаи боло"):
            with self.subTest(generic=generic):
                self.assertIn(generic, self.COURSE)

    def test_the_ad_subscribe_button_names_the_product(self):
        # Reklama oxiridagi obuna tugmasi ham «HSK AI Pro» deydi — ilgari u
        # «Obuna olish» / «Оформить подписку» edi, ya'ni boshqa nom.
        buttons = re.findall(r'adSubPay:"([^"]*)"', self.COURSE)
        self.assertEqual(3, len(buttons), "uchala tilda ham bo'lishi kerak")
        for value in buttons:
            with self.subTest(button=value):
                self.assertIn(PRODUCT, value)
