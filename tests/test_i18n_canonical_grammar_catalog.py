import csv
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.i18n_canonical_grammar_catalog import (
    CATALOG,
    LANGS,
    audit_canonical_grammar,
    context_source_sha256,
    read_canonical_catalog,
)
from scripts.i18n_grammar_private_review_queue import assemble_private_review_queue
from scripts.i18n_legacy_lesson_content_risk_audit import ROOT


class CanonicalGrammarCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_path = ROOT / CATALOG
        with cls.catalog_path.open(encoding="utf-8", newline="") as stream:
            cls.catalog_text = stream.read()
        cls.queue, _ = assemble_private_review_queue(ROOT)
        cls.first_context = cls.queue["contexts"][0]

    def write_catalog(self, root, text=None):
        path = root / CATALOG
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.catalog_text if text is None else text, encoding="utf-8")
        return path

    def catalog_lines(self):
        return self.catalog_text.splitlines()

    def test_all_translation_cells_are_bound_to_source_context(self):
        reviewed = read_canonical_catalog(self.catalog_path)
        self.assertEqual(len(reviewed), 136)
        for context in self.queue["contexts"]:
            self.assertEqual(
                reviewed[context["review_id"]]["context_sha256"],
                context_source_sha256(context),
            )
            self.assertEqual(set(reviewed[context["review_id"]]["translations"]), set(LANGS))

    def test_g030_family_not_house_in_russian(self):
        context = next(c for c in self.queue["contexts"] if c["review_id"] == "G030")
        self.assertEqual(
            context["chinese_example"],
            "画我们的家！有爸爸、妈妈、弟弟，还有黑色的狗、白色的猫什么的。",
        )
        russian = read_canonical_catalog(self.catalog_path)["G030"]["translations"]["ru"]
        # Enumerated family members and pets, not the building.
        self.assertIn("нашу семью", russian)
        self.assertNotIn("наш дом", russian)

    def test_g131_roasted_duck_not_chicken_in_any_locale(self):
        context = next(c for c in self.queue["contexts"] if c["review_id"] == "G131")
        self.assertIn("烤鸭", context["chinese_example"])
        translations = read_canonical_catalog(self.catalog_path)["G131"]["translations"]
        self.assertIn("o‘rdak", translations["uz"])
        self.assertIn("утки", translations["ru"])
        self.assertIn("мурғобии", translations["tj"])
        self.assertNotIn("мурғи бирён", translations["tj"])

    def test_g128_tajik_repeat_visit_is_idiomatic(self):
        context = next(c for c in self.queue["contexts"] if c["review_id"] == "G128")
        self.assertIn("再去一次", context["chinese_example"])
        tajik = read_canonical_catalog(self.catalog_path)["G128"]["translations"]["tj"]
        self.assertIn("боз ҳам бисёр мехоҳам", tajik)
        self.assertNotIn("рафтанам хеле мехоҳад", tajik)

    def test_g051_russian_retains_observer_without_inventing_gender(self):
        context = next(c for c in self.queue["contexts"] if c["review_id"] == "G051")
        self.assertTrue(context["chinese_example"].startswith("我看网上说"))
        russian = read_canonical_catalog(self.catalog_path)["G051"]["translations"]["ru"]
        self.assertIn("Мне попадалось в интернете", russian)
        self.assertNotIn("Я прочитал", russian)

    def test_g109_uzbek_preserves_indefinite_one_book(self):
        context = next(c for c in self.queue["contexts"] if c["review_id"] == "G109")
        self.assertIn("一本中文书", context["chinese_example"])
        uzbek = read_canonical_catalog(self.catalog_path)["G109"]["translations"]["uz"]
        self.assertIn("bir kitob", uzbek)
        self.assertNotIn("kitobni sotdi", uzbek)

    def test_context_hash_changes_with_source_rule_or_occurrence(self):
        original = context_source_sha256(self.first_context)
        mutations = []

        changed_rule = copy.deepcopy(self.first_context)
        changed_rule["grammar"]["rule"]["uz"] += " "
        mutations.append(changed_rule)

        changed_example = copy.deepcopy(self.first_context)
        changed_example["chinese_example"] += "。"
        mutations.append(changed_example)

        changed_pinyin = copy.deepcopy(self.first_context)
        changed_pinyin["pinyin"] += " "
        mutations.append(changed_pinyin)

        changed_occurrence = copy.deepcopy(self.first_context)
        changed_occurrence["occurrences"][0]["source_git_blob_sha1"] = "0" * 40
        mutations.append(changed_occurrence)

        changed_mirror = copy.deepcopy(self.first_context)
        changed_mirror["occurrences"][0]["mirrored_paths"].append("/changed/mirror")
        mutations.append(changed_mirror)

        for context in mutations:
            with self.subTest(context=context["review_id"]):
                self.assertNotEqual(original, context_source_sha256(context))

    def test_reader_rejects_bad_schema_rows_and_normalization(self):
        lines = self.catalog_lines()
        mutations = {
            "wrong schema": ["review_id\tuz\tru\ttj", *lines[1:]],
            "reordered": [lines[0], lines[2], lines[1], *lines[3:]],
            "duplicate": [lines[0], lines[1], lines[1], *lines[3:]],
            "empty translation": [lines[0], lines[1].replace("\t", "\t", 2).split("\t")[0] + "\t" + "\t".join(lines[1].split("\t")[1:2] + [""] + lines[1].split("\t")[3:]) , *lines[2:]],
            "bad hash": [lines[0], "\t".join([lines[1].split("\t")[0], "A" * 64, *lines[1].split("\t")[2:]]), *lines[2:]],
            "extra column": [lines[0], lines[1] + "\textra", *lines[2:]],
        }
        non_nfc = lines[1].split("\t")
        non_nfc[2] = "e\u0301"
        mutations["non-NFC translation"] = [lines[0], "\t".join(non_nfc), *lines[2:]]

        for name, bad_lines in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "catalog.tsv"
                path.write_text("\n".join(bad_lines) + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_canonical_catalog(path)

    def test_source_context_digest_mismatch_fails_closed(self):
        rows = list(csv.DictReader(self.catalog_text.splitlines(), delimiter="\t"))
        rows[0]["context_sha256"] = "0" * 64
        output = ["review_id\tcontext_sha256\tuz\tru\ttj"]
        output.extend("\t".join(row[column] for column in ("review_id", "context_sha256", *LANGS)) for row in rows)
        fake_queue = {
            "unique_exact_contexts": 136,
            "missing_original_maps": 272,
            "contexts": [self.first_context],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_catalog(root, "\n".join(output) + "\n")
            with patch(
                "scripts.i18n_canonical_grammar_catalog.assemble_private_review_queue",
                return_value=(fake_queue, {}),
            ):
                with self.assertRaisesRegex(ValueError, "context SHA-256"):
                    audit_canonical_grammar(root)

    def test_direct_cli_works_and_only_prints_safe_counts(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/i18n_canonical_grammar_catalog.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("'contexts': 136", result.stdout)
        self.assertIn("'source_files_written': 0", result.stdout)
        self.assertNotIn("她去过中国", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_complete_audit_checks_all_original_and_mirrored_maps_without_writing(self):
        source_paths = sorted({item["source_file"] for context in self.queue["contexts"] for item in context["occurrences"]})
        before = {path: (ROOT / path).read_bytes() for path in source_paths}
        drafts, status = audit_canonical_grammar(ROOT)
        self.assertEqual(status, {
            "contexts": 136,
            "independent_values": 408,
            "source_lessons": 48,
            "original_maps": 272,
            "mirror_maps": 136,
            "source_files_written": 0,
        })
        self.assertEqual(len(drafts), 48)
        self.assertEqual(before, {path: (ROOT / path).read_bytes() for path in source_paths})


if __name__ == "__main__":
    unittest.main()
