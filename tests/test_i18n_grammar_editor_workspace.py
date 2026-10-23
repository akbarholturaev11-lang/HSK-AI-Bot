"""Private grammar worksheet: no graded answers, human draft stays unapproved."""
import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.i18n_grammar_editor_workspace import prepare_grammar_editor_workspace
from scripts.i18n_editor_translation_draft import validate_editor_draft
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


class GrammarEditorWorkspaceTests(unittest.TestCase):
    def test_real_nhsk2_lesson_16_six_blank_grammar_examples(self):
        source_path = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
        before = source_path.read_bytes()
        with tempfile.TemporaryDirectory() as top:
            dest = Path(top) / "editor_worksheet"
            status = prepare_grammar_editor_workspace(
                "nhsk2", 16, dest, root=ROOT
            )
            self.assertEqual(status["pending_display_maps"], 6)
            self.assertEqual(status["pending_locale_values"], 18)
            self.assertEqual(status["mirrored_display_paths"], 6)
            self.assertFalse(status["ready_to_ship"])
            self.assertEqual(status["source_git_blob_sha1"], _git_blob_sha1(before))
            ws = json.loads((dest / "worksheet.json").read_text(encoding="utf-8"))
            draft = json.loads((dest / "editor_draft.json").read_text(encoding="utf-8"))
            self.assertEqual(len(ws["examples"]), 6)
            self.assertEqual(
                [x["pointer"] for x in ws["examples"]],
                [x["pointer"] for x in draft["translations"]],
            )
            for entry in ws["examples"]:
                self.assertRegex(entry["pointer"], r"^/grammar/\d+/examples/\d+/translation$")
                self.assertTrue(entry["chinese_example"])
                self.assertEqual(set(entry), {"pointer", "chinese_example", "pinyin", "mirrored_paths"})
                self.assertEqual(len(entry["mirrored_paths"]), 1)
                self.assertTrue(entry["mirrored_paths"][0].startswith("/sections/"))
            self.assertFalse(any(
                bad in json.dumps(ws, ensure_ascii=False)
                for bad in ("correct_index", "answer_tokens", "requires_pro",
                            "SECRET_ANSWER", '"options"')
            ))
            with self.assertRaisesRegex(ValueError, "empty"):
                validate_editor_draft(before, draft)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            for name in ("worksheet.json", "editor_draft.json"):
                self.assertEqual(stat.S_IMODE((dest / name).stat().st_mode), 0o600)
        self.assertEqual(source_path.read_bytes(), before)

    def test_synthetic_context_excludes_answer_solutions_and_metadata(self):
        with tempfile.TemporaryDirectory() as top:
            root = Path(top) / "checkout"
            source_dir = root / "app/static/course_v3_data/nhsk2"
            source_dir.mkdir(parents=True)
            original = {
                "schema_version": 2, "level": "nhsk2",
                "lesson_id": 1, "part_no": 1,
                "grammar": [{"examples": [{
                    "zh": "源语言例句",
                    "pinyin": "yuán yǔyán",
                    "translation": {"uz": "", "ru": "", "tj": ""},
                    "correct_index": 2, "options": ["SECRET_OPTION"]
                }]}],
                "sections": [{"cards": [{
                    "type": "reverse_builder",
                    "answer_tokens": ["SECRET_TOKEN"],
                    "correct_index": 0,
                    "access": {"requires_pro": True}
                }]}]
            }
            source_path = source_dir / "lesson_01.json"
            source_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
            dest = Path(top) / "private"
            prepare_grammar_editor_workspace("nhsk2", 1, dest, root=root)
            worksheet = json.loads((dest / "worksheet.json").read_text())
            self.assertEqual(worksheet["examples"][0]["chinese_example"], "源语言例句")
            encoded = json.dumps(worksheet, ensure_ascii=False)
            for secret in ("SECRET_OPTION", "SECRET_TOKEN", "correct_index",
                           "answer_tokens", "requires_pro"):
                self.assertNotIn(secret, encoded)
            self.assertEqual(json.loads(source_path.read_text()), original)

    def test_checkout_output_overwrite_and_unapproved_tracks_rejected(self):
        with tempfile.TemporaryDirectory() as top:
            root = Path(top) / "repo"
            root.mkdir()
            base = root / "app/static/course_v3_data/nhsk2"
            base.mkdir(parents=True)
            (base / "lesson_01.json").write_text(json.dumps({
                "schema_version": 2, "level": "nhsk2",
                "lesson_id": 1, "part_no": 1,
                "grammar": [{"examples": [{
                    "zh": "原文",
                    "translation": {"uz": "", "ru": "", "tj": ""},
                }]}],
            }))
            with self.assertRaisesRegex(ValueError, "outside"):
                prepare_grammar_editor_workspace(
                    "nhsk2", 1, root / "app/static/editor_worksheet", root=root
                )
            outside = Path(top) / "worksheet"
            prepare_grammar_editor_workspace("nhsk2", 1, outside, root=root)
            with self.assertRaisesRegex(ValueError, "must not exist"):
                prepare_grammar_editor_workspace("nhsk2", 1, outside, root=root)
            with self.assertRaises(ValueError):
                prepare_grammar_editor_workspace("nhsk4", 1, Path(top)/"bad", root=root)
            with self.assertRaises(ValueError):
                prepare_grammar_editor_workspace("nhsk2", True, Path(top)/"bad", root=root)

    def test_missing_chinese_partial_locale_and_answer_paths_not_exported(self):
        with tempfile.TemporaryDirectory() as top:
            root = Path(top) / "repo"
            folder = root / "app/static/course_v3_data/nhsk2"
            folder.mkdir(parents=True)
            path = folder / "lesson_01.json"
            lesson = {
                "schema_version": 2, "level": "nhsk2",
                "lesson_id": 1, "part_no": 1,
                "grammar": [{"examples": [
                    {"zh": "", "translation": {"uz": "", "ru": "", "tj": ""}}
                ]}],
            }
            path.write_text(json.dumps(lesson), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Chinese"):
                prepare_grammar_editor_workspace(
                    "nhsk2", 1, Path(top)/"empty-zh", root=root
                )
            lesson["grammar"][0]["examples"][0]["zh"] = "例句"
            lesson["grammar"][0]["examples"][0]["translation"]["tj"] = "existing"
            path.write_text(json.dumps(lesson), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "partial"):
                prepare_grammar_editor_workspace(
                    "nhsk2", 1, Path(top)/"partial", root=root
                )

    def test_synthetic_duplicate_grammar_path_included_as_information_only(self):
        with tempfile.TemporaryDirectory() as top:
            root = Path(top) / "repo"
            folder = root / "app/static/course_v3_data/nhsk2"
            folder.mkdir(parents=True)
            group = {
                "no": 1,
                "examples": [{"zh": "例句", "pinyin": "",
                              "translation": {"uz": "", "ru": "", "tj": ""}}]
            }
            original = {
                "schema_version": 2, "level": "nhsk2", "lesson_id": 1,
                "part_no": 1, "grammar": [group],
                "sections": [{"cards": [
                    {"type": "_grammar", "g": json.loads(json.dumps(group))},
                    {"type": "reverse_builder", "answer_tokens": ["SECRET_TOKEN"],
                     "correct_index": 0},
                ]}],
            }
            source = folder / "lesson_01.json"
            source.write_text(json.dumps(original), encoding="utf-8")
            private = Path(top) / "review"
            report = prepare_grammar_editor_workspace("nhsk2", 1, private, root=root)
            self.assertEqual(report["mirrored_display_paths"], 1)
            ws = json.loads((private / "worksheet.json").read_text(encoding="utf-8"))
            draft = json.loads((private / "editor_draft.json").read_text(encoding="utf-8"))
            self.assertEqual(ws["examples"][0]["mirrored_paths"], [
                "/sections/0/cards/0/g/examples/0/translation"
            ])
            self.assertEqual([x["pointer"] for x in draft["translations"]], [
                "/grammar/0/examples/0/translation"
            ])
            self.assertNotIn("SECRET_TOKEN", json.dumps(ws))
            self.assertEqual(json.loads(source.read_text()), original)

    def test_mismatched_grammar_mirror_is_blocked(self):
        with tempfile.TemporaryDirectory() as top:
            root = Path(top) / "repo"
            folder = root / "app/static/course_v3_data/nhsk2"
            folder.mkdir(parents=True)
            original_group = {
                "no": 1, "examples": [{"zh": "原句",
                                      "translation": {"uz": "", "ru": "", "tj": ""}}],
            }
            bad_mirror = json.loads(json.dumps(original_group))
            bad_mirror["examples"][0]["zh"] = "WRONG"
            (folder / "lesson_01.json").write_text(json.dumps({
                "schema_version": 2, "level": "nhsk2", "lesson_id": 1,
                "part_no": 1, "grammar": [original_group],
                "sections": [{"cards": [{"type": "_grammar", "g": bad_mirror}]}],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mirrored grammar source differs"):
                prepare_grammar_editor_workspace(
                    "nhsk2", 1, Path(top) / "private", root=root,
                )

    def test_no_automatic_translation_or_public_write(self):
        source = (ROOT / "scripts/i18n_grammar_editor_workspace.py").read_text()
        for forbidden in ("requests.", "httpx.", "FastAPI(", "APIRouter(",
                          "send_file(", "app.mount(", "subprocess.",
                          "OpenAI(", "google.generativeai", "translate_text("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
