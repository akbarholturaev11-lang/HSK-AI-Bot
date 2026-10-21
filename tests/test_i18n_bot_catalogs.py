"""Exact Bot copy, local generation and lookup compatibility regressions."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts.i18n_build_bot_catalogs import (
    ROOT, generate, materialize_tables, output_files, read_sources,
)


class BotCatalogTests(unittest.TestCase):
    def _copy_sources(self, root):
        for locale in ("uz", "ru", "tj"):
            for namespace in ("bot", "common", "course"):
                relative = f"localization/ui/{locale}/{namespace}.json"
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)

    def test_original_effective_tables_are_preserved_exactly(self):
        tables = materialize_tables(read_sources())
        expected = {
            "TEXTS": "4a085a75d7a161a57098ca1d4767b39ee3b1ae2794faba21f78c3c385338163f",
            "COURSE_I18N": "13d80a296ad414f320ac01d7d894ada0238f30b590bae7c03d2211c0de7cc30e",
        }
        from app.bot.utils.i18n import COURSE_I18N, TEXTS
        self.assertEqual(tables, {"TEXTS": TEXTS, "COURSE_I18N": COURSE_I18N})
        for name, value in tables.items():
            serialized = json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(serialized).hexdigest(), expected[name])
        self.assertEqual({locale: len(values) for locale, values in TEXTS.items()},
                         {"uz": 276, "ru": 276, "tj": 276})
        self.assertEqual({locale: len(values) for locale, values in COURSE_I18N.items()},
                         {"uz": 92, "ru": 92, "tj": 92})

    def test_generated_artifact_is_current_and_deterministic(self):
        self.assertEqual(generate(check=True), [])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_sources(root)
            self.assertEqual(len(generate(root, check=False)), 1)
            self.assertEqual(generate(root, check=True), [])
            target = root / "app/bot/generated/bot_i18n.py"
            original = target.read_bytes()
            self.assertEqual(generate(root, check=False), [])
            self.assertEqual(original, target.read_bytes())
            target.write_text("stale", encoding="utf-8")
            self.assertEqual(len(generate(root, check=True)), 1)
            self.assertEqual(target.read_text(), "stale")

    def test_shared_values_are_references_not_duplicate_bot_sources(self):
        data = read_sources()
        for locale, catalog in data.items():
            self.assertEqual(len(catalog["messages"]), 339)
            self.assertEqual(len(catalog["references"]), 41)
            self.assertFalse(set(catalog["messages"]) & set(catalog["references"]))
            self.assertEqual(catalog["references"]["texts.menu_profile"],
                             {"namespace": "common", "key": "bot.menu.profile"})
            self.assertEqual(catalog["references"]["texts.hint_section_voice_title"],
                             {"namespace": "course", "key": "nav.voice"})

    def test_placeholder_and_key_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_sources(root)
            target = root / "localization/ui/tj/bot.json"
            data = json.loads(target.read_text())
            data["messages"]["texts.welcome"] = "Салом {different}"
            target.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "placeholder parity"):
                read_sources(root)
            data["messages"].pop("texts.welcome")
            target.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "Unknown Bot compatibility"):
                read_sources(root)

    def test_source_edit_reaches_generated_lookup_without_service_calls(self):
        from app.bot.utils import i18n
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_sources(root)
            target = root / "localization/ui/uz/bot.json"
            data = json.loads(target.read_text())
            data["messages"]["texts.welcome"] = "Changed locally {name}"
            target.write_text(json.dumps(data))
            generated = next(iter(output_files(read_sources(root)).values()))
            namespace = {}
            exec(compile(generated, "generated_bot_fixture", "exec"), namespace)
            with patch.object(i18n, "TEXTS", namespace["TEXTS"]), \
                    patch.object(i18n, "_gemini_texts_active", return_value=False):
                self.assertEqual(i18n.t("welcome", "uz", name="QA"), "Changed locally QA")

    def test_gemini_formatting_and_existing_fallbacks_are_preserved(self):
        from app.bot.utils import i18n
        with patch.object(i18n, "_gemini_texts_active", return_value=False):
            self.assertEqual(i18n.t("welcome", "uz", name="QA"), "Xush kelibsiz, QA!")
            self.assertEqual(i18n.t("welcome", "unsupported", name="QA"),
                             i18n.TEXTS["ru"]["welcome"].format(name="QA"))
            self.assertEqual(i18n.t("welcome", "uz", bad="QA"),
                             i18n.TEXTS["uz"]["welcome"])
            self.assertEqual(i18n.t("missing_key", "uz"), "missing_key")
        with patch.object(i18n, "_gemini_texts_active", return_value=True):
            self.assertEqual(i18n.t("free_mode_info", "uz"),
                             i18n.TEXTS["uz"]["free_mode_info_gemini"])



if __name__ == "__main__":
    unittest.main()
