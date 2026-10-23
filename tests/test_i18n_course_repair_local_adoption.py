"""P2 recovery copy uses local course catalogs and preserves its old fallbacks."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "uz": {
        "lessonFlow.guidedRepairTitle": "Birga to'g'rilaymiz",
        "lessonFlow.guidedRepairBody": "To'g'ri javobni ko'ring va uni o'zingiz tasdiqlang.",
        "lessonFlow.guidedRepairAction": "Shu javobni tanlayman",
        "foundation.guidedRepairBody": "To'g'ri javobni ko'ring va o'zingiz tasdiqlang.",
        "foundation.repairReminder": "Javobni yana bir bor ko'ring — birozdan keyin o'zingiz topasiz.",
        "lessonFlow.encouragement1": "Xato bo'ldi — demak siz haqiqatan o'ylayapsiz. Aynan shunday esda qoladi.",
        "lessonFlow.encouragement2": "Bu so'z hozir qiyin keldi. Ikkinchi uchrashuvda osonroq bo'ladi — shu bilan o'rganiladi.",
        "lessonFlow.encouragement3": "To'xtamang: bitta xato butun darsni buzmaydi.",
    },
    "ru": {
        "lessonFlow.guidedRepairTitle": "Исправим вместе",
        "lessonFlow.guidedRepairBody": "Посмотрите на правильный ответ и подтвердите его сами.",
        "lessonFlow.guidedRepairAction": "Выбрать этот ответ",
        "foundation.guidedRepairBody": "Посмотрите на правильный ответ и подтвердите его.",
        "foundation.repairReminder": "Посмотрите на ответ ещё раз — скоро вы найдёте его сами.",
        "lessonFlow.encouragement1": "Ошибка — значит, вы действительно думаете. Именно так и запоминается.",
        "lessonFlow.encouragement2": "Это слово сейчас далось трудно. При второй встрече будет легче — так и учатся.",
        "lessonFlow.encouragement3": "Не останавливайтесь: одна ошибка не портит весь урок.",
    },
    "tj": {
        "lessonFlow.guidedRepairTitle": "Якҷоя ислоҳ мекунем",
        "lessonFlow.guidedRepairBody": "Ҷавоби дурустро бинед ва худатон тасдиқ кунед.",
        "lessonFlow.guidedRepairAction": "Ҳамин ҷавобро интихоб мекунам",
        "foundation.guidedRepairBody": "Ҷавоби дурустро бинед ва тасдиқ кунед.",
        "foundation.repairReminder": "Ҷавобро боз як бор бинед — каме пас худатон меёбед.",
        "lessonFlow.encouragement1": "Хато шуд — яъне шумо воқеан фикр карда истодаед. Маҳз ҳамин тавр дар ёд мемонад.",
        "lessonFlow.encouragement2": "Ин калима ҳоло душвор омад. Бори дуюм осонтар мешавад — ҳамин тавр меомӯзанд.",
        "lessonFlow.encouragement3": "Наистед: як хато тамоми дарсро вайрон намекунад.",
    },
}


class CourseRepairLocalAdoptionTests(unittest.TestCase):
    def test_local_catalog_values_match_the_existing_inline_copy(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        for locale, expected in EXPECTED.items():
            path = ROOT / f"localization/ui/{locale}/course.json"
            messages = json.loads(path.read_text(encoding="utf-8"))["messages"]
            for key, value in expected.items():
                with self.subTest(locale=locale, key=key):
                    self.assertEqual(messages[key], value)
                    self.assertIn(value, html)

    def test_guided_repair_reminder_and_cheer_read_the_local_bundle(self):
        html = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")
        for adoption in (
            'courseMessage("lessonFlow.guidedRepairTitle",M.h)',
            'courseMessage("lessonFlow.guidedRepairBody",M.p)',
            'courseMessage("lessonFlow.guidedRepairAction",M.go)',
            'courseMessage("foundation.guidedRepairBody",M.p)',
            'courseMessage("foundation.repairReminder",',
            'courseMessage("lessonFlow.encouragement"+(idx+1),msg)',
        ):
            with self.subTest(adoption=adoption):
                self.assertIn(adoption, html)


if __name__ == "__main__":
    unittest.main()
