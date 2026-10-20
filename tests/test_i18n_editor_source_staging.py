"""P3 private grammar integration staging: source and assessment integrity."""
import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.i18n_editor_source_staging import stage_private_grammar_lessons
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def _draft(number: int):
    relative = f"app/static/course_v3_data/nhsk2/lesson_{number:02d}.json"
    original_bytes = (ROOT / relative).read_bytes()
    original = json.loads(original_bytes)
    entries = []
    for gi, group in enumerate(original["grammar"]):
        for ei, ex in enumerate(group["examples"]):
            if ex.get("translation") == {"uz": "", "ru": "", "tj": ""}:
                entries.append({
                    "pointer": f"/grammar/{gi}/examples/{ei}/translation",
                    "values": {
                        "uz": f"Private sample {number}-{gi}-{ei}",
                        "ru": f"Private RU {number}-{gi}-{ei}",
                        "tj": f"Private TJ {number}-{gi}-{ei}",
                    },
                })
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": relative,
        "source_git_blob_sha1": _git_blob_sha1(original_bytes),
        "translations": entries,
    }


class PrivateGrammarSourceStagingTests(unittest.TestCase):
    def _seed(self, folder, number):
        folder.mkdir(exist_ok=True)
        draft = _draft(number)
        (folder / f"lesson_{number}.json").write_text(json.dumps(draft))
        return draft

    def test_real_lesson16_staged_with_grammar_mirror_only(self):
        relative = "app/static/course_v3_data/nhsk2/lesson_16.json"
        source_file = ROOT / relative
        raw = source_file.read_bytes()
        source = json.loads(raw)
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            source_dir = base / "input"
            draft = self._seed(source_dir, 16)
            with self.assertRaisesRegex(ValueError, "full lesson candidate coverage"):
                stage_private_grammar_lessons(source_dir, base / "no", root=ROOT)
            self.assertFalse((base / "no").exists())
            staged = base / "staged"
            result = stage_private_grammar_lessons(
                source_dir, staged, root=ROOT, require_complete=False,
            )
            self.assertEqual(result["original_lessons_staged"], 1)
            self.assertEqual(result["original_grammar_display_maps_staged"], 6)
            self.assertEqual(result["mirrored_grammar_display_maps_staged"], 6)
            self.assertFalse(result["ready_to_ship"])
            self.assertEqual(result["original_source_files_mutated"], 0)
            self.assertFalse(result["graded_or_pro_fields_changed"])
            target = staged / "nhsk2" / "lesson_16.json"
            copy = json.loads(target.read_bytes())
            self.assertEqual(stat.S_IMODE(staged.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(source_file.read_bytes(), raw)
            for gi, group in enumerate(copy["grammar"]):
                for ei, ex in enumerate(group["examples"]):
                    field = f"/grammar/{gi}/examples/{ei}/translation"
                    chosen = next(x["values"] for x in draft["translations"]
                                  if x["pointer"] == field)
                    self.assertEqual(ex["translation"], chosen)
            self.assertEqual(
                copy["sections"][0]["cards"][0]["type"],
                source["sections"][0]["cards"][0]["type"],
            )
            self.assertEqual(copy["schema_version"], source["schema_version"])

    def test_real_lesson20_has_no_mirrored_cards(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            src = base / "drafts"
            self._seed(src, 20)
            result = stage_private_grammar_lessons(
                src, base / "output", root=ROOT, require_complete=False,
            )
            self.assertEqual(result["original_grammar_display_maps_staged"], 12)
            self.assertEqual(result["mirrored_grammar_display_maps_staged"], 0)
            self.assertTrue((base / "output" / "nhsk2" / "lesson_20.json").exists())

    def test_invalid_sha_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            folder = base / "input"
            draft = self._seed(folder, 16)
            draft["source_git_blob_sha1"] = "0" * 40
            (folder / "lesson_16.json").write_text(json.dumps(draft))
            with self.assertRaises(ValueError):
                stage_private_grammar_lessons(
                    folder, base / "output", root=ROOT, require_complete=False,
                )
            self.assertFalse((base / "output").exists())

    def test_output_cannot_write_into_checkout_or_input(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            folder = base / "input"
            self._seed(folder, 16)
            for destination in (
                ROOT / "app/static/course_v3_data/nhsk2/preview",
                folder / "nested", folder,
            ):
                with self.assertRaises(ValueError):
                    stage_private_grammar_lessons(
                        folder, destination, root=ROOT, require_complete=False,
                    )
            self.assertFalse((folder / "nested").exists())

    def test_symlinked_input_fails_without_preview(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            folder = base / "input"
            self._seed(folder, 16)
            (folder / "alias.json").symlink_to(folder / "lesson_16.json")
            with self.assertRaises(ValueError):
                stage_private_grammar_lessons(
                    folder, base / "output", root=ROOT, require_complete=False,
                )
            self.assertFalse((base / "output").exists())

    def test_empty_input_fails_without_preview(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            folder = base / "input"
            folder.mkdir()
            with self.assertRaisesRegex(ValueError, "no valid lesson grammar"):
                stage_private_grammar_lessons(
                    folder, base / "output", root=ROOT, require_complete=False,
                )
            self.assertFalse((base / "output").exists())

    def test_no_deployable_content_or_server_endpoints_are_added(self):
        code = (ROOT / "scripts/i18n_editor_source_staging.py").read_text()
        for forbidden in ("FastAPI(", "APIRouter(", "requests.", "httpx.",
                          "source_path.write_text(", "send_file(", "write_bytes("):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
