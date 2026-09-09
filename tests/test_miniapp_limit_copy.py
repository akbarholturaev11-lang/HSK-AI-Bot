"""Mini App chegara haqida O'ZI gapirmasin.

Foydalanuvchi buni aniq aytdi: chegara matni admin panelidagi sozlamaga
bog'lansin va yolg'on ma'lumot bermasin. "Bepul rejimda 5 ta dars" deb
qo'yilsa, ekranda ham aynan 5 turishi kerak.

Ilgari server haqiqiy raqamni (`limit_text`) yuborardi, Mini App esa uni
umuman o'qimasdi va o'z ichidagi qattiq matnini ko'rsatardi:

    "Bu dars faqat HSK AI Pro uchun."

Bu ikki marta noto'g'ri edi — dars Pro'ga bog'liq emas, u kunlik chegara
tugagani uchun yopilgan va admin sozlagan oynada qayta ochiladi.
"""

import unittest
from pathlib import Path


MINIAPP = Path("app/static/course-v3.html").read_text(encoding="utf-8")


class TheLimitSentenceComesFromTheServerTests(unittest.TestCase):
    def test_the_server_sentence_is_read_and_remembered(self):
        self.assertIn("function rememberLimitText(d)", MINIAPP)
        self.assertIn("limit_text", MINIAPP)
        # Xarita javobidagi `lesson_limit.limit_text` ham o'qiladi.
        self.assertIn("d.lesson_limit&&typeof d.lesson_limit.limit_text", MINIAPP)

    def test_every_map_load_remembers_it(self):
        # Uchala kirish nuqtasi ham (boot, qayta yuklash, daraja almashish)
        # xaritani o'qiganda matnni yangilaydi.
        self.assertEqual(3, MINIAPP.count("MAP=rememberLimitText(d);"))
        self.assertNotIn("MAP=d;", MINIAPP)

    def test_the_limit_refusal_shows_the_server_sentence(self):
        self.assertIn("function serverSaveErrorText(code,serverText)", MINIAPP)
        self.assertIn("serverSaveErrorText(d.error,d.limit_text)", MINIAPP)

    def test_the_paywall_reason_starts_from_the_server_sentence(self):
        self.assertIn("var lesson=((LIMIT_TEXT||m.lesson||\"\")+\" \"+(m.offer||\"\")).trim();", MINIAPP)

    def test_every_section_refusal_remembers_the_server_sentence(self):
        # Mashq bo'limlari (tanish, talaffuz, xatolar, test markazi) 403
        # javobidagi gapni oladi. Ilgari ularning hammasi "kuniga 1 marta"
        # deb qattiq yozilgan matnni ko'rsatardi, admin nechchi qo'ysa ham.
        self.assertIn("function rememberSectionLimit(j)", MINIAPP)
        # 1 ta e'lon + har bir 403 tarmog'ida bittadan chaqiruv.
        self.assertEqual(9, MINIAPP.count("rememberSectionLimit("))
        for sheet in (
            "esc(SECTION_LIMIT_TEXT||t.limitSub)",
            "SECTION_LIMIT_TEXT||t.limitText",
            "esc(SECTION_LIMIT_TEXT||t.limSub)",
        ):
            with self.subTest(sheet=sheet):
                self.assertIn(sheet, MINIAPP)

    def test_the_ad_promo_sheet_is_given_the_same_sentence(self):
        # Reklama moduli o'z `limitWhy` matnini saqlaydi, lekin `reason`
        # berilsa o'shani ko'rsatadi — server gapi ustun turadi.
        self.assertEqual(4, MINIAPP.count("reason:SECTION_LIMIT_TEXT"))

    def test_the_section_text_does_not_leak_into_the_lesson_paywall(self):
        # Ikki xotira ATAYLAB alohida: mashq chegarasi dars paywallidagi
        # gapni almashtirib yuborsa, foydalanuvchi yana yolg'on o'qiydi.
        self.assertIn('var LIMIT_TEXT="",SECTION_LIMIT_TEXT="";', MINIAPP)
        self.assertNotIn("LIMIT_TEXT=SECTION_LIMIT_TEXT", MINIAPP)

    def test_the_old_untrue_copy_is_gone(self):
        # Chegara — kunlik, ya'ni dars "faqat Pro uchun" emas.
        for untrue in (
            "Bu dars faqat HSK AI Pro uchun.",
            "Этот урок доступен только в HSK AI Pro.",
            "Ин дарс танҳо барои HSK AI Pro аст.",
            # Daraja bo'yicha "dastlabki qismlar" qoidasi olib tashlangan.
            "bepul rejimda har darajadan dastlabki qismlar ochiladi",
            "открыты только первые части каждого уровня",
            "танҳо қисмҳои аввали ҳар сатҳ кушода мешаванд",
        ):
            with self.subTest(copy=untrue):
                self.assertNotIn(untrue, MINIAPP)


if __name__ == "__main__":
    unittest.main()
