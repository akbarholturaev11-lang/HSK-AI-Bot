"""Bo'lim tanishtiruvi ekran USTIDA suzadi, bo'limga o'xshamaydi.

Foydalanuvchi buni aniq aytdi: bu yo'l ko'rsatkichlar alohida blok bo'lib
turmasin — ular bo'limni tanishtiradi, shuning uchun ekran ustida suzsin,
bo'limning o'ziga o'xshab layoutда joy egallamasin.

Ilgari `hintsHtml(section)` har bo'lim markupi ICHIGA chizilardi: kartochka
fon/ramka bilan, bo'limning bir qismidek. Endi u bitta suzuvchi konteynerда
(`#hint-float`, fixed) turadi va bo'lim almashganda yangilanadi.
"""

import re
import unittest
from pathlib import Path


MINIAPP = Path("app/static/course-v3.html").read_text(encoding="utf-8")


class TheHintFloatsAboveTheScreenTests(unittest.TestCase):
    def test_a_dedicated_floating_container_exists(self):
        self.assertIn('id="hint-float"', MINIAPP)
        # Fixed va oqimdan tashqarida — joy egallamaydi.
        self.assertRegex(MINIAPP, r"#hint-float\{position:fixed;")

    def test_the_container_is_filled_when_the_section_changes(self):
        self.assertIn("function renderFloatHint(section)", MINIAPP)
        self.assertIn("renderFloatHint(s);", MINIAPP)

    def test_no_section_renders_the_hint_inline_any_more(self):
        # Faqat funksiya ta'rifi va suzuvchi render qoladi; hech bir bo'lim
        # markupi `hintsHtml(...)` ni O'Z ichiga qo'ymaydi.
        inline = re.findall(r'\+hintsHtml\("(\w+)"\)', MINIAPP)
        self.assertEqual([], inline, f"inline hint chaqiruvlari qoldi: {inline}")

    def test_the_floating_hint_still_closes_and_stays_closed(self):
        # Suzuvchi bo'lsa ham "bir marta" qoidasi buzilmaydi: X yopadi,
        # yopilgani serverga yoziladi.
        self.assertIn("function closeHint(key)", MINIAPP)
        self.assertIn('_apiPost("/api/v3/hints/dismiss"', MINIAPP)


if __name__ == "__main__":
    unittest.main()
