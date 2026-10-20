"""Release-feedback system copy uses the generated local common catalog."""
import ast
import unittest

from scripts.i18n_build_local_catalogs import ROOT, read_sources


EXPECTED = {
    "uz": {
        "bot.releaseFeedback.prompt": "\n\nYangilikni sinab ko'ring va 1-5 ball bering. Fikr qoldirsangiz, obunangiz bo'lmasa sizga 24 soatlik 20% chegirma beriladi.",
        "bot.releaseFeedback.lowRatingComment": "Nima noqulay bo'ldi? Qisqa izoh yoki screenshot yuboring. Shundan keyin chegirma ochiladi.",
        "bot.releaseFeedback.optionalComment": "Rahmat. Xohlasangiz, qisqa izoh ham qoldiring.",
        "bot.releaseFeedback.thanks": "Rahmat, fikringiz qabul qilindi.",
        "bot.releaseFeedback.discount": "Rahmat. Aytganimizdek, sizga 24 soatlik 20% chegirma berildi.",
        "bot.releaseFeedback.tryGranted": "Test access ochildi: 30 minut ichida yangilangan joyni limitsiz sinab ko'ring.",
        "bot.releaseFeedback.tryAlready": "Sizda bu funksiyani sinab ko'rish uchun access bor.",
        "bot.releaseFeedback.tryButton": "🚀 Sinab ko'rish",
        "bot.releaseFeedback.discountButton": "🎁 20% chegirmani olish",
        "bot.releaseFeedback.commentButton": "✍️ Izoh yozish",
        "bot.releaseFeedback.skipButton": "➡️ O'tkazib yuborish",
        "bot.releaseFeedback.notFoundAlert": "Fikr-mulohaza topilmadi.",
        "bot.releaseFeedback.alreadyRatedAlert": "Siz allaqachon baho bergansiz.",
        "bot.releaseFeedback.chooseRatingAlert": "Avval 1 dan 5 gacha baho tanlang.",
        "bot.releaseFeedback.commentPrompt": "Izohni matn yoki screenshot qilib yuboring.",
    },
    "ru": {
        "bot.releaseFeedback.prompt": "\n\nПопробуйте обновление и оцените от 1 до 5. Если оставите отзыв и у вас нет подписки, вам откроется скидка 20% на 24 часа.",
        "bot.releaseFeedback.lowRatingComment": "Что было неудобно? Отправьте короткий комментарий или скриншот. После этого скидка откроется.",
        "bot.releaseFeedback.optionalComment": "Спасибо. Если хотите, оставьте короткий комментарий.",
        "bot.releaseFeedback.thanks": "Спасибо, ваш отзыв принят.",
        "bot.releaseFeedback.discount": "Спасибо. Как и обещали, для вас открыта скидка 20% на 24 часа.",
        "bot.releaseFeedback.tryGranted": "Тестовый доступ открыт: в течение 30 минут пробуйте обновлённый раздел без лимита.",
        "bot.releaseFeedback.tryAlready": "У вас уже есть доступ, чтобы попробовать эту функцию.",
        "bot.releaseFeedback.tryButton": "🚀 Попробовать",
        "bot.releaseFeedback.discountButton": "🎁 Получить скидку 20%",
        "bot.releaseFeedback.commentButton": "✍️ Оставить комментарий",
        "bot.releaseFeedback.skipButton": "➡️ Пропустить",
        "bot.releaseFeedback.notFoundAlert": "Отзыв не найден.",
        "bot.releaseFeedback.alreadyRatedAlert": "Вы уже поставили оценку.",
        "bot.releaseFeedback.chooseRatingAlert": "Сначала выберите оценку от 1 до 5.",
        "bot.releaseFeedback.commentPrompt": "Отправьте комментарий текстом или скриншотом.",
    },
    "tj": {
        "bot.releaseFeedback.prompt": "\n\nНавигариро санҷед ва аз 1 то 5 баҳо диҳед. Агар фикр гузоред ва обуна надошта бошед, барои шумо тахфифи 20% ба 24 соат кушода мешавад.",
        "bot.releaseFeedback.lowRatingComment": "Чӣ ноқулай буд? Шарҳи кӯтоҳ ё скриншот фиристед. Баъд аз ин тахфиф кушода мешавад.",
        "bot.releaseFeedback.optionalComment": "Ташаккур. Агар хоҳед, шарҳи кӯтоҳ ҳам гузоред.",
        "bot.releaseFeedback.thanks": "Ташаккур, фикри шумо қабул шуд.",
        "bot.releaseFeedback.discount": "Ташаккур. Тавре гуфта будем, барои шумо тахфифи 20% ба 24 соат дода шуд.",
        "bot.releaseFeedback.tryGranted": "Дастрасии тестӣ кушода шуд: дар 30 дақиқа қисми навшударо бе лимит санҷед.",
        "bot.releaseFeedback.tryAlready": "Шумо аллакай барои санҷидани ин функсия дастрасӣ доред.",
        "bot.releaseFeedback.tryButton": "🚀 Санҷидан",
        "bot.releaseFeedback.discountButton": "🎁 20% тахфифро гирифтан",
        "bot.releaseFeedback.commentButton": "✍️ Шарҳ навиштан",
        "bot.releaseFeedback.skipButton": "➡️ Гузарондан",
        "bot.releaseFeedback.notFoundAlert": "Фикр ёфт нашуд.",
        "bot.releaseFeedback.alreadyRatedAlert": "Шумо аллакай баҳо додаед.",
        "bot.releaseFeedback.chooseRatingAlert": "Аввал баҳои аз 1 то 5-ро интихоб кунед.",
        "bot.releaseFeedback.commentPrompt": "Шарҳро матн ё скриншот фиристед.",
    },
}


class BotReleaseFeedbackAdoptionTests(unittest.TestCase):
    def test_existing_locales_keep_reviewed_copy_in_the_canonical_catalog(self):
        source = read_sources(ROOT)
        for lang, expected in EXPECTED.items():
            with self.subTest(locale=lang):
                self.assertEqual({key: source[lang][key] for key in expected}, expected)

        generated = ast.parse(
            (ROOT / "app/bot/generated/common_i18n.py").read_text(encoding="utf-8")
        )
        self.assertEqual(ast.literal_eval(generated.body[0].value), source)

    def test_catalog_consumers_use_the_saved_user_language(self):
        keyboard = ast.parse(
            (ROOT / "app/bot/keyboards/release_feedback.py").read_text(encoding="utf-8")
        )
        keyboard_keys = {
            node.args[0].value
            for node in ast.walk(keyboard)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "t"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        self.assertTrue({
            "common.bot.releaseFeedback.tryButton",
            "common.bot.releaseFeedback.discountButton",
            "common.bot.releaseFeedback.commentButton",
            "common.bot.releaseFeedback.skipButton",
        }.issubset(keyboard_keys))

        service_path = ROOT / "app/services/release_feedback_service.py"
        service = ast.parse(service_path.read_text(encoding="utf-8"))
        service_keys = {
            node.args[0].value
            for node in ast.walk(service)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_release_feedback_text"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        self.assertEqual(service_keys, {
            "prompt", "lowRatingComment", "optionalComment", "thanks", "discount",
            "tryGranted", "tryAlready",
        })
        campaign_send = next(
            node for node in ast.walk(service)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "release_feedback_rating_keyboard"
        )
        self.assertEqual(len(campaign_send.args), 2)
        self.assertIsInstance(campaign_send.args[1], ast.BoolOp)
        self.assertIsInstance(campaign_send.args[1].values[0], ast.Attribute)
        self.assertEqual(campaign_send.args[1].values[0].attr, "language")

        handler = ast.parse(
            (ROOT / "app/bot/handlers/release_feedback.py").read_text(encoding="utf-8")
        )
        handler_keys = {
            node.args[0].value
            for node in ast.walk(handler)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "t"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        self.assertTrue({
            "common.bot.releaseFeedback.notFoundAlert",
            "common.bot.releaseFeedback.alreadyRatedAlert",
            "common.bot.releaseFeedback.chooseRatingAlert",
            "common.bot.releaseFeedback.commentPrompt",
        }.issubset(handler_keys))
        self.assertNotIn("Feedback topilmadi.", handler_path_text := (ROOT / "app/bot/handlers/release_feedback.py").read_text(encoding="utf-8"))
        self.assertNotIn("Izohni matn yoki screenshot qilib yuboring.", handler_path_text)


if __name__ == "__main__":
    unittest.main()
