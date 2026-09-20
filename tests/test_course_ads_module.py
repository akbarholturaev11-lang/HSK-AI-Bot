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


def _code_only(source: str) -> str:
    """Izoh, matn (string) va regex literallarini bo'shliqqa almashtiradi.

    Nomlarni matndan qidirish uchun bu SHART: `ads.js` ichida butun CSS
    satrlari va uch tilli izohlar bor — ularsiz har qanday skaner
    `rgba(` yoki `bloki (` ni «chaqiruv» deb o'qiydi.
    """
    out = []
    i, n = 0, len(source)
    # Regex literali bo'lishi mumkin bo'lgan joy: `/` dan oldin operator yoki
    # ochiluvchi qavs turgan bo'lsa. Aks holda bu bo'lish amali.
    before_regex = set("(,=:[!&|?{};\n+-*%~^<>")
    while i < n:
        ch = source[i]
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            end = source.find("*/", i + 2)
            end = n if end < 0 else end + 2
            out.append(" " * (end - i))
            i = end
        elif ch == "/" and i + 1 < n and source[i + 1] == "/":
            end = source.find("\n", i)
            end = n if end < 0 else end
            out.append(" " * (end - i))
            i = end
        elif ch in "\"'":
            j = i + 1
            while j < n and source[j] != ch:
                j += 2 if source[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(" " * (j - i))
            i = j
        elif ch == "/":
            prev = next(
                (c for c in reversed("".join(out)) if not c.isspace()), "\n"
            )
            if prev in before_regex:
                j = i + 1
                in_class = False
                while j < n and (in_class or source[j] != "/"):
                    if source[j] == "\\":
                        j += 1
                    elif source[j] == "[":
                        in_class = True
                    elif source[j] == "]":
                        in_class = False
                    j += 1
                j = min(j + 1, n)
                out.append(" " * (j - i))
                i = j
            else:
                out.append(ch)
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


ADS_CODE = _code_only(ADS)


def _declared_names() -> set[str]:
    """Modul ichida e'lon qilingan HAR QANDAY nom."""
    names = set(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(", ADS))
    names |= set(re.findall(r"\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)", ADS))
    # `var a=1,b=2` ko'rinishidagi qo'shimcha e'lonlar.
    for chunk in re.findall(r"\b(?:var|let|const)\s+([^;\n]+)", ADS):
        for part in chunk.split(","):
            found = re.match(r"\s*([A-Za-z_$][\w$]*)\s*(?:=|$)", part)
            if found:
                names.add(found.group(1))
    # Funksiya parametrlari va `catch (e)`.
    for params in re.findall(r"\bfunction\s*[A-Za-z_$\w$]*\s*\(([^)]*)\)", ADS):
        for part in params.split(","):
            part = part.strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", part):
                names.add(part)
    names |= set(re.findall(r"\bcatch\s*\(\s*([A-Za-z_$][\w$]*)\s*\)", ADS))
    names |= set(re.findall(r"\bfor\s*\(\s*var\s+([A-Za-z_$][\w$]*)", ADS))
    return names


class EveryNameUsedInsideTheModuleExistsTests(unittest.TestCase):
    """Ichkarida chaqiriladigan yordamchilar ham joyida bo'lsin.

    Eksport ro'yxati faqat modul yuklanishida yiqiladi; ichkaridagi yo'q nom
    esa foydalanuvchi tugmani bosgandagina yiqiladi — bu battar.

    Ikkinchi marta aynan shunday bo'ldi: `e.x.onclick=closeAppAd` — bunday
    funksiya yo'q edi (u `closeCenterAd` deb ataladi), qator esa overlay
    ochiladigan joydan OLDIN turardi. Ya'ni markazdagi va dars yakunidagi
    reklama HECH QACHON chiqmagan, xato esa `.catch()` larda yutilgan.

    Shuning uchun bu test endi qo'lda yozilgan ro'yxatga tayanmaydi.
    """

    #: Modul ichida chaqiriladigan va shu faylda e'lon qilinishi SHART
    #: bo'lgan yordamchilar. Ro'yxat pastdagi umumiy skanerga qo'shimcha:
    #: u oqimning umurtqasini nomma-nom qotirib qo'yadi.
    HELPERS = (
        "closeOverlay",
        "resetState",
        "showCenterAd",
        "closeCenterAd",
        "fetchPlacementAd",
        "recordView",
        "_closeLimit",
    )

    #: Brauzer beradigan (yoki tilning o'zi beradigan) va modul e'lon
    #: qilmaydigan nomlar.
    GLOBALS = frozenset(
        {
            "null", "true", "false", "undefined",
            "window", "document", "navigator", "localStorage", "location",
            "setTimeout", "clearTimeout", "setInterval", "clearInterval",
            "Promise", "Object", "Number", "String", "Math", "Date", "JSON",
            "Array", "Error", "isNaN", "parseInt", "parseFloat", "fetch",
            "encodeURIComponent", "decodeURIComponent", "console",
            "requestAnimationFrame", "void", "typeof", "this",
        }
    )

    def test_the_helpers_the_flows_depend_on_are_declared(self):
        for name in self.HELPERS:
            with self.subTest(name=name):
                self.assertRegex(ADS, rf"function\s+{re.escape(name)}\s*\(")

    def test_no_handler_is_wired_to_a_name_that_does_not_exist(self):
        """`x.onclick=nom` — `nom` shu faylda e'lon qilingan bo'lishi shart.

        Aynan shu shakl bir marta butun reklama bo'limini o'ldirgan.
        """
        declared = _declared_names() | self.GLOBALS
        wired = re.findall(
            r"\.on(?:click|change|load|error|ended)\s*=\s*([A-Za-z_$][\w$]*)\s*[;,}]",
            ADS,
        )
        self.assertTrue(wired, "hech qanday handler topilmadi — regex eskirgan")
        for name in sorted(set(wired)):
            with self.subTest(handler=name):
                self.assertIn(
                    name,
                    declared,
                    f"`{name}` handler sifatida ulangan, lekin e'lon qilinmagan",
                )

    def test_every_called_helper_exists(self):
        """`nom(...)` shaklida chaqirilgan har bir nom mavjud bo'lsin."""
        declared = _declared_names() | self.GLOBALS
        # Metod chaqiruvlari (`a.b()`) va kalit so'zlar hisobga olinmaydi.
        called = {
            name
            for name in re.findall(
                r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(", ADS_CODE
            )
            if name
            not in {
                "function", "if", "for", "while", "switch", "catch", "return",
                "typeof", "new", "delete", "in", "of", "do", "else",
            }
        }
        missing = sorted(called - declared)
        self.assertEqual(
            missing,
            [],
            f"shu nomlar chaqiriladi, lekin e'lon qilinmagan: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
