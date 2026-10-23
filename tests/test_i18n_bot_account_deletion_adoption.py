"""Keep account-deletion bot copy in the local three-locale catalog."""
import ast
import re
import unittest

from scripts.i18n_build_local_catalogs import LANGUAGES, ROOT, read_sources


ACCOUNT_DELETION_KEYS = {
    "bot.accountDeletion.webStarted",
    "bot.accountDeletion.webConfirmButton",
    "bot.accountDeletion.privateChatOnly",
    "bot.accountDeletion.expired",
    "bot.accountDeletion.accountVerified",
    "bot.accountDeletion.returnToWeb",
    "bot.accountDeletion.prompt",
    "bot.accountDeletion.submitButton",
    "bot.accountDeletion.submitFailed",
    "bot.accountDeletion.requestAccepted",
    "bot.accountDeletion.requestSaved",
}


class BotAccountDeletionCatalogTests(unittest.TestCase):
    def test_all_handler_copy_exists_in_each_local_catalog(self):
        catalogs = read_sources(ROOT)
        handler = ast.parse(
            (ROOT / "app/bot/handlers/account_deletion.py").read_text(encoding="utf-8")
        )
        referenced_keys = {
            node.args[0].value.removeprefix("common.")
            for node in ast.walk(handler)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "t"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.startswith("common.bot.accountDeletion.")
        }

        self.assertEqual(referenced_keys, ACCOUNT_DELETION_KEYS)
        for language in LANGUAGES:
            with self.subTest(language=language):
                for key in ACCOUNT_DELETION_KEYS:
                    self.assertTrue(catalogs[language][key].strip(), key)

    def test_receipt_placeholder_and_deletion_notice_keep_their_meaning(self):
        catalogs = read_sources(ROOT)
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(
                    set(re.findall(r"\{([a-zA-Z][a-zA-Z0-9_]*)\}",
                                   catalogs[language]["bot.accountDeletion.requestSaved"])),
                    {"requestId"},
                )

        self.assertIn("30 kun", catalogs["uz"]["bot.accountDeletion.prompt"])
        self.assertIn("hozir o‘chirilmaydi", catalogs["uz"]["bot.accountDeletion.prompt"])
        self.assertIn("30 дней", catalogs["ru"]["bot.accountDeletion.prompt"])
        self.assertIn("не удаляются сразу", catalogs["ru"]["bot.accountDeletion.prompt"])
        self.assertIn("30 рӯз", catalogs["tj"]["bot.accountDeletion.prompt"])
        self.assertIn("фавран нест карда намешавад", catalogs["tj"]["bot.accountDeletion.prompt"])


if __name__ == "__main__":
    unittest.main()
