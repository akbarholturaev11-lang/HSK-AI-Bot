"""Bot stale-button alerts use the locally generated common catalog."""
import ast
import unittest

from scripts.i18n_build_local_catalogs import ROOT, read_sources


EXPECTED = {
    "uz": "Tugma eskirgan yoki noto‘g‘ri.",
    "ru": "Кнопка устарела или некорректна.",
    "tj": "Тугма дигар эътибор надорад ё нодуруст аст.",
}


class BotInvalidButtonAdoptionTests(unittest.TestCase):
    def test_copy_matches_all_locales_and_generated_catalog(self):
        source = read_sources(ROOT)
        self.assertEqual(
            {lang: source[lang]["bot.buttonInvalid"] for lang in EXPECTED},
            EXPECTED,
        )
        generated = ast.parse(
            (ROOT / "app/bot/generated/common_i18n.py").read_text(encoding="utf-8")
        )
        self.assertEqual(ast.literal_eval(generated.body[0].value), source)

    def test_invalid_callback_alert_uses_local_catalog_and_remains_an_alert(self):
        tree = ast.parse((ROOT / "app/bot/handlers/menu.py").read_text(encoding="utf-8"))
        handler = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "handle_promo_action_callback"
        )
        localized_alert = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "callback"
            and node.func.attr == "answer"
            and node.args
            and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)
            and node.args[0].func.id == "t"
            and len(node.args[0].args) >= 2
            and isinstance(node.args[0].args[0], ast.Constant)
            and node.args[0].args[0].value == "common.bot.buttonInvalid"
            and isinstance(node.args[0].args[1], ast.Name)
            and node.args[0].args[1].id == "lang"
            and any(
                keyword.arg == "show_alert"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )
            for node in ast.walk(handler)
        )
        self.assertTrue(localized_alert)


if __name__ == "__main__":
    unittest.main()
