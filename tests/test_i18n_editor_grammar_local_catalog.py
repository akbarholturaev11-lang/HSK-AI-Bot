"""Grammar display overlays stay private, SHA pinned and answer-free."""
import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.i18n_editor_grammar_local_catalog import build_local_grammar_previews
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def private_fixture():
    relative = "app/static/course_v3_data/nhsk2/lesson_16.json"
    raw = (ROOT / relative).read_bytes()
    lesson = json.loads(raw)
    translations = [
        {
            "pointer": f"/grammar/{gi}/examples/{ei}/translation",
            "values": {"uz": "Sinov matni", "ru": "Тестовый текст",
                       "tj": "Матни санҷишӣ"},
        }
        for gi, group in enumerate(lesson["grammar"])
        for ei, example in enumerate(group["examples"])
        if example.get("translation") == {"uz": "", "ru": "", "tj": ""}
    ]
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": relative, "source_git_blob_sha1": _git_blob_sha1(raw),
        "translations": translations,
    }


class LocalGrammarOverlayTests(unittest.TestCase):
    def test_three_local_first_overlay_files_include_checked_mirrors(self):
        original = (ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "seeds"
            src.mkdir()
            draft = private_fixture()
            (src / "source.json").write_text(json.dumps(draft))
            dest = base / "overlays"
            report = build_local_grammar_previews(
                src, dest, root=ROOT, require_complete=False,
            )
            self.assertEqual(report["private_locale_packs"], 3)
            self.assertEqual(report["main_display_maps"], 6)
            self.assertEqual(report["mirrored_display_maps"], 6)
            self.assertEqual(report["locale_values"], 36)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            self.assertFalse(report["client_runtime_integrated"])
            self.assertFalse(report["ready_to_ship"])
            for locale in ("uz", "ru", "tj"):
                path = dest / locale / "nhsk2_lesson_16.json"
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                payload = json.loads(path.read_text())
                self.assertEqual(payload["source_git_blob_sha1"],
                                 draft["source_git_blob_sha1"])
                self.assertEqual(len(payload["texts"]), 12)
                self.assertEqual(payload["locale"], locale)
                self.assertTrue(all(
                    key.startswith("/grammar/") or key.startswith("/sections/")
                    for key in payload["texts"]
                ))
                for forbidden in ('"zh"', '"pinyin"', '"correct_index"',
                                  '"requires_pro"', '"answer_tokens"', '"options"'):
                    self.assertNotIn(forbidden, path.read_text())
        self.assertEqual(
            (ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json").read_bytes(),
            original,
        )

    def test_requires_complete_136_contexts_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "seeds"
            src.mkdir()
            (src / "draft.json").write_text(json.dumps(private_fixture()))
            output = root / "out"
            with self.assertRaisesRegex(ValueError, "complete candidate coverage"):
                build_local_grammar_previews(src, output, root=ROOT)
            self.assertFalse(output.exists())

    def test_stale_sha_and_gender_placeholders_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "seed"
            src.mkdir()
            draft = private_fixture()
            draft["source_git_blob_sha1"] = "0" * 40
            file = src / "draft.json"
            file.write_text(json.dumps(draft))
            with self.assertRaises(ValueError):
                build_local_grammar_previews(src, base / "stale", root=ROOT,
                                             require_complete=False)
            self.assertFalse((base / "stale").exists())
            draft = private_fixture()
            draft["translations"][0]["values"]["ru"] = "Читал(а) книгу."
            file.write_text(json.dumps(draft, ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, "russian_gender_placeholder"):
                build_local_grammar_previews(src, base / "invalid", root=ROOT,
                                             require_complete=False)
            self.assertFalse((base / "invalid").exists())

    def test_never_outputs_inside_git_or_input_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "seed"
            src.mkdir()
            (src / "draft.json").write_text(json.dumps(private_fixture()))
            for output in (src / "child", ROOT / "localization" / "oops"):
                with self.assertRaises(ValueError):
                    build_local_grammar_previews(src, output, root=ROOT,
                                                 require_complete=False)


if __name__ == "__main__":
    unittest.main()
