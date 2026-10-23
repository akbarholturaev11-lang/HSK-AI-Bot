"""Desktop copy is centrally authored and bundled identically for macOS/Windows."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.i18n_build_desktop_catalogs import (
    LOCALES, ROOT, TARGET, generate, output_files, read_sources,
)
from scripts.i18n_miniapp_catalog_audit import extract_literal, key_value, split_top


def legacy_messages():
    source = (ROOT / "desktop/ui/js/i18n.js").read_text(encoding="utf-8")
    literal, _ = extract_literal(source, "messages")
    return literal, {
        locale: {key: ast.literal_eval(value)
                 for key, value in (key_value(row) for row in split_top(body))}
        for locale, body in (key_value(row) for row in split_top(literal))
    }


def shared_keys():
    source = (ROOT / "desktop/ui/js/i18n.js").read_text(encoding="utf-8")
    keys = set()
    for name in ("SHARED_COMMON_KEY", "SHARED_COURSE_KEY"):
        body = source.split("const " + name + " = Object.freeze(", 1)[1].split("\n});", 1)[0] + "}"
        keys.update(key_value(row)[0] for row in split_top(body))
    return keys


class DesktopCatalogAdoptionTests(unittest.TestCase):
    def test_all_remaining_desktop_keys_match_original_three_locale_copy(self):
        literal, legacy = legacy_messages()
        self.assertEqual(hashlib.sha256(literal.encode()).hexdigest(),
                         "f021130f58264d53c6a7f72024bbd0fde09e0457cceffa7331e5bf6a94e2e63c")
        catalogs = read_sources(ROOT)
        mapped = shared_keys()
        for locale in LOCALES:
            self.assertEqual(len(legacy[locale]), 824)
            self.assertEqual(len(catalogs[locale]), 745)
            self.assertFalse(set(catalogs[locale]) & mapped)
            self.assertEqual(catalogs[locale], {
                key: value for key, value in legacy[locale].items() if key not in mapped
            })

    def test_generated_file_is_current_and_has_only_desktop_target(self):
        self.assertEqual(generate(ROOT, check=True), [])
        self.assertEqual(set(output_files(read_sources(ROOT))), {TARGET})
        source = (ROOT / TARGET).read_text(encoding="utf-8")
        self.assertIn("window.HSKAI_DESKTOP_I18N", source)
        for forbidden in ("fetch(", "XMLHttpRequest(", "import(", "http://", "https://"):
            self.assertNotIn(forbidden, source)

    def _source_dir(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for locale in LOCALES:
            directory = root / "localization/ui" / locale
            directory.mkdir(parents=True)
            shutil.copyfile(ROOT / "localization/ui" / locale / "desktop.json",
                            directory / "desktop.json")
        return root

    def _edit(self, root, locale, edit):
        path = root / "localization/ui" / locale / "desktop.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        edit(value)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def test_generation_is_deterministic_and_detects_stale_files(self):
        root = self._source_dir()
        self.assertEqual(generate(root, check=True), [TARGET])
        self.assertEqual(generate(root, check=False), [TARGET])
        original = (root / TARGET).read_bytes()
        self.assertEqual(generate(root, check=False), [])
        self.assertEqual((root / TARGET).read_bytes(), original)
        (root / TARGET).write_text("stale", encoding="utf-8")
        self.assertEqual(generate(root, check=True), [TARGET])
        self.assertEqual((root / TARGET).read_text(), "stale")

    def test_missing_or_extra_locale_keys_fail_closed(self):
        for operation in ("missing", "extra"):
            with self.subTest(operation=operation):
                root = self._source_dir()
                self._edit(root, "ru", lambda data: (
                    data["messages"].pop("courseTitle") if operation == "missing"
                    else data["messages"].update({"unreviewedKey": "text"})
                ))
                with self.assertRaisesRegex(ValueError, "key parity"):
                    generate(root, check=False)
                self.assertFalse((root / TARGET).exists())

    def test_metadata_and_duplicate_keys_fail_closed(self):
        root = self._source_dir()
        self._edit(root, "tj", lambda data: data.update({"locale": "tg"}))
        with self.assertRaisesRegex(ValueError, "metadata"):
            read_sources(root)
        root = self._source_dir()
        path = root / "localization/ui/uz/desktop.json"
        source = path.read_text(encoding="utf-8")
        path.write_text(source.replace('"schema_version": 1,',
                                       '"schema_version": 1, "schema_version": 1,'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            read_sources(root)

    def test_placeholder_names_counts_and_braces_are_checked(self):
        for text in ("{wrong}", "{provider} {provider}", "{provider"):
            with self.subTest(text=text):
                root = self._source_dir()
                self._edit(root, "ru", lambda data: data["messages"].update({"identityProviderConnect": text}))
                with self.assertRaisesRegex(ValueError, "placeholder"):
                    read_sources(root)

    def test_untrusted_text_and_keys_are_rejected(self):
        for key, value in (("courseTitle", ""), ("courseTitle", "<script>"),
                           ("constructor", "text"), ("__proto__", "text")):
            with self.subTest(key=key, value=value):
                root = self._source_dir()
                self._edit(root, "uz", lambda data: data["messages"].update({key: value}))
                with self.assertRaisesRegex(ValueError, "Untrusted"):
                    read_sources(root)

    def test_json_escaping_keeps_javascript_line_separators_safe(self):
        sources = {locale: {"escaped": 'line\n"quote" \\ slash\u2028next\u2029end'} for locale in LOCALES}
        bundle = output_files(sources)[TARGET]
        self.assertNotIn("\u2028", bundle)
        self.assertNotIn("\u2029", bundle)
        self.assertIn(r"\u2028", bundle)
        self.assertIn(r"\u2029", bundle)
        self.assertIn(r'\"quote\"', bundle)

    def test_shared_desktop_runtime_preserves_copy_fallback_and_precedence(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js required for Desktop JavaScript runtime contract")
        script = r'''
const fs = require("node:fs");
const vm = require("node:vm");
const root = process.argv[1];
const context = vm.createContext({window: {}, document: {documentElement: {}}});
for (const name of ["common", "course", "desktop"]) {
  vm.runInContext(fs.readFileSync(root + "/desktop/ui/js/generated/hsk-" + name + "-i18n.js", "utf8"), context);
}
const source = fs.readFileSync(root + "/desktop/ui/js/i18n.js", "utf8")
  .replace(/^import .*;\s*$/gm, "")
  .replace(/^export /gm, "");
vm.runInContext(source, context);
const output = vm.runInContext(`(() => {
  const original = {};
  for (const locale of ["uz", "ru", "tj"]) {
    setLanguage(locale);
    original[locale] = Object.fromEntries(Object.keys(messages[locale]).map(key => [key, t(key)]));
  }
  setLanguage("uz");
  window.HSKAI_DESKTOP_I18N = {uz: {courseTitle: "canonical Desktop", course: "wrong owner", identityProviderConnect: "Connect {provider}"}};
  const canonical = t("courseTitle");
  const shared = t("course");
  const variables = t("identityProviderConnect", {provider: "Example"});
  const missingVariable = t("identityProviderConnect");
  delete window.HSKAI_DESKTOP_I18N;
  const fallback = t("courseTitle");
  const unknown = t("unknownKey");
  delete window.HSKAI_COMMON_I18N;
  delete window.HSKAI_COURSE_I18N;
  const allMissing = t("course");
  return {original, canonical, shared, variables, missingVariable, fallback, unknown, allMissing};
})()`, context);
process.stdout.write(JSON.stringify(output));
'''
        process = subprocess.run([node, "-e", script, str(ROOT)], check=True,
                                 capture_output=True, text=True, timeout=30)
        actual = json.loads(process.stdout)
        _, legacy = legacy_messages()
        self.assertEqual(actual["original"], legacy)
        self.assertEqual(actual["canonical"], "canonical Desktop")
        self.assertEqual(actual["shared"], legacy["uz"]["course"])
        self.assertEqual(actual["variables"], "Connect Example")
        self.assertEqual(actual["missingVariable"], "Connect {provider}")
        self.assertEqual(actual["fallback"], legacy["uz"]["courseTitle"])
        self.assertEqual(actual["unknown"], "unknownKey")
        self.assertEqual(actual["allMissing"], legacy["uz"]["course"])


if __name__ == "__main__":
    unittest.main()
