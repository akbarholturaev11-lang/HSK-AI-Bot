"""`ads.js` moduli haqiqatan o'rnatiladimi.

Bu testning sababi aniq va u bir marta jonli sodir bo'ldi: `window.CourseAds`
obyekt literali ichida e'lon qilinmagan `_closeLimit` nomi qoldi. JavaScript
literalni baholaganda `ReferenceError` tashladi, ya'ni MODUL UMUMAN
o'rnatilmadi — markazdagi reklama ham, dars yakunidagi reklama ham, limit
paywalli ham jimgina yo'qoldi. Hech qanday xato ko'rinmadi, chunki chaqiruv
joylari `if(!window.CourseAds)return` bilan himoyalangan.

Shuning uchun bu yerda tekshiriladigan narsa mantiq emas: modul eksport
qiladigan HAR BIR nom fayl ichida haqiqatan mavjudmi.
"""

import re
import unittest
from pathlib import Path


ADS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")


def _exported_names() -> dict[str, str]:
    """`window.CourseAds = {...}` dan `kalit: qiymat` juftlari."""
    # Izohlarda ham "window.CourseAds" uchraydi — haqiqiy tayinlash kerak.
    start = ADS.index("window.CourseAds = {")
    brace = ADS.index("{", start)
    depth, end = 0, brace
    for i in range(brace, len(ADS)):
        if ADS[i] == "{":
            depth += 1
        elif ADS[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = ADS[brace + 1 : end]
    out = {}
    for key, value in re.findall(r"(\w+)\s*:\s*([A-Za-z_$][\w$]*)\s*(?:,|$)", body):
        out[key] = value
    return out


class CourseAdsModuleTests(unittest.TestCase):
    def test_the_module_exports_something(self):
        self.assertTrue(_exported_names(), "eksport ro'yxati topilmadi")

    def test_every_exported_name_is_actually_declared(self):
        """Har bir eksport qilingan nom faylda e'lon qilingan bo'lishi shart.

        Bitta yo'q nom butun modulni o'ldiradi — kalitning o'zi emas,
        LITERAL yiqiladi.
        """
        for key, name in _exported_names().items():
            with self.subTest(export=key, name=name):
                declared = re.search(
                    rf"\b(?:function\s+{re.escape(name)}\s*\(|"
                    rf"(?:var|let|const)\s+{re.escape(name)}\b)",
                    ADS,
                )
                self.assertIsNotNone(
                    declared, f"`{key}` `{name}` ga ishora qiladi, u esa e'lon qilinmagan"
                )

    def test_the_two_placements_are_the_only_ones_offered(self):
        exports = _exported_names()
        self.assertIn("playScreenCenter", exports)
        self.assertIn("playLessonEnd", exports)

    def test_the_limit_paywall_can_be_closed(self):
        # Yopilmaydigan paywall — ekranda qamalib qolish.
        self.assertIn("closeLimit", _exported_names())
        self.assertIn("function _closeLimit(", ADS)

    def test_closing_the_paywall_puts_the_overlay_back(self):
        """`limit` klassi qaytarilmasa keyingi reklama paywall bo'lib ochiladi."""
        body = ADS[ADS.index("function _closeLimit("):]
        body = body[: body.index("\n  function ", 1)]
        self.assertIn("closeOverlay()", body)
        self.assertIn('classList.remove("limit")', body)


class EveryNameUsedInsideTheModuleExistsTests(unittest.TestCase):
    """Ichkarida chaqiriladigan yordamchilar ham joyida bo'lsin.

    Eksport ro'yxati faqat modul yuklanishida yiqiladi; ichkaridagi yo'q nom
    esa foydalanuvchi tugmani bosgandagina yiqiladi — bu battar.
    """

    #: Modul ichida chaqiriladigan va shu faylda e'lon qilinishi SHART
    #: bo'lgan yordamchilar.
    HELPERS = (
        "closeOverlay",
        "resetState",
        "showCenterAd",
        "fetchPlacementAd",
        "recordView",
        "_closeLimit",
    )

    def test_the_helpers_the_flows_depend_on_are_declared(self):
        for name in self.HELPERS:
            with self.subTest(name=name):
                self.assertRegex(ADS, rf"function\s+{re.escape(name)}\s*\(")


if __name__ == "__main__":
    unittest.main()
