"""Read-only Android translation XML audit unit tests."""
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_android_resource_audit import (
    audit, compare_resources, parse_resources, placeholder_signature,
)


class AndroidXmlAuditTests(unittest.TestCase):
    BASE = """<resources>
        <string name="hello">Hello {name}, %1$s</string>
        <plurals name="days">
          <item quantity="one">%d day</item>
          <item quantity="other">%d days</item>
        </plurals>
        <string-array name="steps">
          <item>Step %1$s</item><item>Next {name}</item>
        </string-array>
        <string name="brand" translatable="false">HSK AI</string>
    </resources>"""

    def test_parses_resources_and_excludes_no_translate(self):
        data = parse_resources(self.BASE)
        self.assertIn("string:hello", data)
        self.assertNotIn("string:brand", data)
        self.assertEqual(sorted(data["plurals:days"]["values"]), ["one", "other"])
        self.assertEqual(len(data["string-array:steps"]["values"]), 2)

    def test_detects_placeholder_plural_and_array_contract_drift(self):
        other = self.BASE.replace("%1$s", "%1$d", 1).replace(
            '<item quantity="other">%d days</item>', ""
        ).replace('<item>Next {name}</item>', "")
        delta = compare_resources(parse_resources(self.BASE), parse_resources(other))
        kinds = {row["issue"] for row in delta}
        self.assertIn("placeholder_drift", kinds)
        self.assertIn("plural_quantity_drift", kinds)
        self.assertIn("array_length_drift", kinds)
        self.assertNotIn("Hello", str(delta))

    def test_named_printf_and_escaped_percent(self):
        sig = placeholder_signature("10%% done, {count} %1$d %1$d")
        self.assertEqual(sig["named"], [("count", 1)])
        self.assertEqual(sig["printf"], [("1:d", 2)])
        self.assertNotEqual(sig, placeholder_signature("{count} %1$s"))

    def test_accepts_namespace_xliff_markup(self):
        source = ('<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">'
                  '<string name="greet">Hi <xliff:g id="user">%1$s</xliff:g></string>'
                  '</resources>')
        data = parse_resources(source)
        self.assertEqual(placeholder_signature(data["string:greet"]["values"]["text"])["printf"],
                         [("1:s", 1)])

    def test_reports_xml_errors_and_scans_each_source_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for source_set in ("main", "direct", "play"):
                base = root / "android/app/src" / source_set / "res" / "values" / "strings.xml"
                base.parent.mkdir(parents=True)
                base.write_text(self.BASE, encoding="utf-8")
                for locale in ("values-ru", "values-tg"):
                    target = base.parent.parent / locale / "strings.xml"
                    target.parent.mkdir()
                    target.write_text(self.BASE, encoding="utf-8")
            result = audit(root)
            self.assertEqual(result["compared_pairs"], 6)
            self.assertEqual(len(result["findings"]), 0)
            bad = root / "android/app/src/play/res/values-tg/strings.xml"
            bad.write_text("<resources><string", encoding="utf-8")
            result = audit(root)
            self.assertEqual(result["issues_by_type"]["invalid_locale_xml"], 1)
            self.assertEqual(len(result["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
