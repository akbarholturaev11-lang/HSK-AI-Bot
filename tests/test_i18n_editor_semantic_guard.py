"""Agent-owned P3 known-mistranslation guard never needs user review."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_editor_semantic_guard import (
    audit_private_translation_semantics, RUSSIAN_GENDER_PLACEHOLDER,
    SPECIFIC_WEATHER, SNOW_REQUIRED,
)
from scripts.i18n_lesson_locale_gap_review_queue import _git_blob_sha1

ROOT = Path(__file__).resolve().parents[1]


def real_draft(number):
    rel = f"app/static/course_v3_data/nhsk2/lesson_{number:02d}.json"
    raw = (ROOT / rel).read_bytes()
    source = json.loads(raw)
    entries = []
    for gi, group in enumerate(source["grammar"]):
        for ei, item in enumerate(group["examples"]):
            if item.get("translation") == {"uz": "", "ru": "", "tj": ""}:
                entries.append({
                    "pointer": f"/grammar/{gi}/examples/{ei}/translation",
                    "values": {
                        "uz": "Mazmuni tekshiriladigan taklif",
                        "ru": "Предложение для проверки",
                        "tj": "Пешниҳоди тарҷума",
                    },
                })
    return {
        "schema_version": 1, "kind": "p3_editor_translation_draft",
        "source_file": rel, "source_git_blob_sha1": _git_blob_sha1(raw),
        "translations": entries,
    }


class P3SemanticRegressionTests(unittest.TestCase):
    def test_ambiguous_weather_and_explicit_snow_terms(self):
        self.assertIsNotNone(SPECIFIC_WEATHER["uz"].search("Kecha qor yog‘di."))
        self.assertIsNotNone(SPECIFIC_WEATHER["ru"].search("Вчера шёл снег."))
        self.assertIsNotNone(SPECIFIC_WEATHER["tj"].search("Дирӯз борон борид."))
        self.assertIsNotNone(SNOW_REQUIRED["uz"].search("Qor yog‘moqda."))
        self.assertIsNotNone(SNOW_REQUIRED["ru"].search("Идёт снег."))
        self.assertIsNotNone(SNOW_REQUIRED["tj"].search("Барф меборад."))

    def test_russian_gender_placeholder_guard(self):
        self.assertIsNotNone(
            RUSSIAN_GENDER_PLACEHOLDER.search("Ты возвращался(ась) домой?")
        )
        self.assertIsNotNone(
            RUSSIAN_GENDER_PLACEHOLDER.search("Ты читал(а) книгу?")
        )
        self.assertIsNone(
            RUSSIAN_GENDER_PLACEHOLDER.search("Домой уже год не приезжаешь?")
        )

    def test_private_real_source_pilot_finds_gender_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "drafts"
            folder.mkdir()
            draft = real_draft(16)
            draft["translations"][0]["values"]["ru"] = "Он был(а) в Китае."
            (folder / "lesson.json").write_text(
                json.dumps(draft, ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, "russian_gender_placeholder"):
                audit_private_translation_semantics(
                    folder, root=ROOT, require_complete=False,
                )

    def test_private_source_pilot_safe_for_known_failure_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "drafts"
            folder.mkdir()
            (folder / "lesson.json").write_text(
                json.dumps(real_draft(16), ensure_ascii=False))
            result = audit_private_translation_semantics(
                folder, root=ROOT, require_complete=False,
            )
            self.assertEqual(result["known_semantic_regressions"], 0)
            self.assertGreater(result["unique_contexts_checked"], 0)
            self.assertFalse(result["ready_to_ship"])
            self.assertFalse(result["qualified_human_review_required"])

    def test_default_incomplete_batch_not_mistaken_for_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "drafts"
            folder.mkdir()
            (folder / "lesson.json").write_text(
                json.dumps(real_draft(16), ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, "complete candidate coverage"):
                audit_private_translation_semantics(folder, root=ROOT)

    def test_source_stays_immutable(self):
        source = ROOT / "app/static/course_v3_data/nhsk2/lesson_16.json"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "drafts"
            folder.mkdir()
            (folder / "lesson.json").write_text(
                json.dumps(real_draft(16), ensure_ascii=False))
            audit_private_translation_semantics(
                folder, root=ROOT, require_complete=False,
            )
        self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
