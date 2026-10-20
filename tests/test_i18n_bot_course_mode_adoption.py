"""Bot course-mode fallback uses the generated local common catalog."""
import ast
import unittest

from scripts.i18n_build_local_catalogs import ROOT, read_sources


EXPECTED = {
    "uz": "🚧 Kurs rejimi hozircha ishlab chiqilmoqda.",
    "ru": "🚧 Режим курса сейчас в разработке.",
    "tj": "🚧 Реҷаи курс ҳоло дар таҳия аст.",
}


class BotCourseModeAdoptionTests(unittest.TestCase):
    def test_three_locale_copy_matches_generated_bot_catalog(self):
        source = read_sources(ROOT)
        self.assertEqual(
            {lang: source[lang]["bot.courseModeUnavailable"] for lang in EXPECTED},
            EXPECTED,
        )

        generated = ast.parse(
            (ROOT / "app/bot/generated/common_i18n.py").read_text(encoding="utf-8")
        )
        assignment = generated.body[0]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual(ast.literal_eval(assignment.value), source)

    def test_disabled_course_guard_uses_the_catalog_without_changing_flow(self):
        path = ROOT / "app/bot/handlers/menu.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        handler = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "handle_course_mode_button"
        )
        guard = next(
            node for node in handler.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.UnaryOp)
            and isinstance(node.test.op, ast.Not)
            and isinstance(node.test.operand, ast.Name)
            and node.test.operand.id == "COURSE_MODE_ENABLED"
        )

        localized_reply = False
        for node in ast.walk(guard):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if (isinstance(node.func.value, ast.Name) and node.func.value.id == "message"
                    and node.func.attr == "answer" and node.args):
                reply = node.args[0]
                localized_reply = (
                    isinstance(reply, ast.Call)
                    and isinstance(reply.func, ast.Name)
                    and reply.func.id == "t"
                    and len(reply.args) >= 2
                    and isinstance(reply.args[0], ast.Constant)
                    and reply.args[0].value == "common.bot.courseModeUnavailable"
                    and isinstance(reply.args[1], ast.Name)
                    and reply.args[1].id == "lang"
                )
                if localized_reply:
                    break
        self.assertTrue(localized_reply)
        self.assertTrue(any(isinstance(node, ast.Return) for node in guard.body))
        self.assertFalse(any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "send_course_miniapp_entry"
            for node in ast.walk(guard)
        ))


if __name__ == "__main__":
    unittest.main()
