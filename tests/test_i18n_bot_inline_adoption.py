"""Every migrated inline Bot map preserves original locale/value ordering."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

from app.bot.generated.bot_i18n import BOT_MESSAGES, bot_locale_map
from scripts.i18n_baseline_guard import git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


class BotInlineCatalogAdoptionTests(unittest.TestCase):
    def test_all_98_migrated_maps_keep_exact_locale_values_and_types(self):
        proof = json.loads((ROOT / "localization/review/bot_inline_map_migration.json").read_text())
        self.assertEqual(len(proof["maps"]), 98)
        for row in proof["maps"]:
            with self.subTest(key=row["id"]):
                value = bot_locale_map(row["id"])
                self.assertEqual(list(value), row["locale_order"])
                for locale, expected in row["locale_value_sha1"].items():
                    self.assertEqual(git_blob_sha1(repr(value[locale]).encode()), expected)
                self.assertIn(repr(row["id"]), (ROOT / row["source"]).read_text())

    def test_each_call_builds_an_independent_mutable_map(self):
        key = "inline.handlers.challenge.helper_text.copy1"
        first = bot_locale_map(key)
        second = bot_locale_map(key)
        first["uz"]["bad_button"] = "mutated"
        self.assertNotEqual(first, second)
        self.assertNotIn("mutated", BOT_MESSAGES["uz"].values())

    def test_backend_fixed_maps_preserve_original_copy_and_order(self):
        proof = json.loads((ROOT / "localization/review/backend_fixed_map_migration.json").read_text())
        rows = [row for row in proof["maps"] if "locale_value_sha1" in row]
        self.assertEqual(len(rows), 52)
        for row in rows:
            with self.subTest(key=row["id"]):
                rendered = bot_locale_map(row["id"])
                self.assertEqual(list(rendered), row["locale_order"])
                for locale, expected in row["locale_value_sha1"].items():
                    self.assertEqual(git_blob_sha1(repr(rendered[locale]).encode()), expected)

    def test_dynamic_templates_keep_all_92_original_formatting_samples(self):
        checked = 0
        for filename in ("bot_dynamic_map_migration.json", "backend_fixed_map_migration.json"):
            proof = json.loads((ROOT / "localization/review" / filename).read_text())
            for row in proof["maps"]:
                for case in row.get("runtime_cases", []):
                    with self.subTest(key=case["key"]):
                        value = bot_locale_map(case["key"], **case["arguments"])
                        self.assertEqual(git_blob_sha1(repr(value).encode()), case["expected_sha1"])
                        checked += 1
        self.assertEqual(checked, 92)

    def test_limit_display_preserves_all_30_original_snapshots(self):
        source = (ROOT / "app/services/entitlements/decision.py").read_text()
        function = next(node for node in ast.parse(source).body
                        if isinstance(node, ast.FunctionDef) and node.name == "limit_text")
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]),
                     "<actual limit display function>", "exec"), namespace)
        proof = json.loads((ROOT / "localization/review/entitlement_limit_text_parity.json").read_text())
        self.assertEqual(len(proof["samples"]), 30)
        for case in proof["samples"]:
            with self.subTest(arguments=case["arguments"]):
                text = namespace["limit_text"](**case["arguments"])
                self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), case["expected_sha256"])


if __name__ == "__main__":
    unittest.main()
