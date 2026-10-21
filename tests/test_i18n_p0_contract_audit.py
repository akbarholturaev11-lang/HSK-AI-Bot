"""P0 compatibility and static lesson inspection: structural, read-only guards."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_p0_contract_audit import (
    assessment_shape_candidates, lesson_route_contract, locale_contract,
    run_audit, structural_answer_fields,
)


def sample_manifest():
    return {
        "schema_version": 1, "status": "preparation_only_no_runtime_switch",
        "default_locale": "uz",
        "locales": [
            {"id": "uz", "tag": "uz"}, {"id": "ru", "tag": "ru"},
            {"id": "tj", "tag": "tg"},
        ],
        "backend_compatibility_aliases": {"tg": "tj", "tg-TJ": "tj"},
    }


def sample_registry():
    return {"schema_version": 1, "runtime_changes_authorized": True,
            "existing_languages": ["uz", "ru", "tj"]}


class P0ContractAuditTests(unittest.TestCase):
    def test_current_locale_alias_contract(self):
        result = locale_contract(sample_manifest(), sample_registry())
        self.assertEqual(result["display_tags"]["tj"], "tg")
        self.assertEqual(result["backend_codes"], ["ru", "tj", "uz"])

    def test_existing_locale_adoption_status_does_not_authorize_new_languages(self):
        for status in ("local_first_runtime_adoption_in_progress",
                       "local_first_existing_locale_source_complete"):
            manifest = {**sample_manifest(), "status": status}
            self.assertEqual(locale_contract(manifest, sample_registry())["backend_codes"],
                             ["ru", "tj", "uz"])
            manifest["locales"].append({"id": "en", "tag": "en"})
            with self.assertRaisesRegex(ValueError, "locale mapping"):
                locale_contract(manifest, sample_registry())
        with self.assertRaisesRegex(ValueError, "Unknown localization phase"):
            locale_contract({**sample_manifest(), "status": "release_all_languages"}, sample_registry())

    def test_rejects_new_locale_activation_tajik_rename_or_unauthorized_runtime(self):
        m = sample_manifest()
        m["locales"].append({"id": "en", "tag": "en"})
        with self.assertRaisesRegex(ValueError, "locale mapping"):
            locale_contract(m, sample_registry())
        m = sample_manifest()
        m["backend_compatibility_aliases"]["tg"] = "tg"
        with self.assertRaisesRegex(ValueError, "Tajik"):
            locale_contract(m, sample_registry())
        with self.assertRaisesRegex(ValueError, "runtime implementation is not authorized"):
            locale_contract(sample_manifest(), {
                **sample_registry(), "runtime_changes_authorized": False
            })

    def test_route_requires_security_review_without_inventing_verdict(self):
        source = '''
@app.get("/course_v3_data/{level}/{filename}")
async def course_v3_lesson_file(level, filename):
    return static_json_response(f"app/static/course_v3_data/{level}/{filename}")
'''
        route = lesson_route_contract(source)
        self.assertFalse(route["explicit_dependency_in_handler_or_decorator"])
        self.assertEqual(route["global_middleware_and_upstream_auth"], "not_evaluated")
        with self.assertRaisesRegex(ValueError, "missing or duplicated"):
            lesson_route_contract("def other(): pass")

    def test_only_structural_keys_no_sensitive_values(self):
        fields = structural_answer_fields({"sections": [
            {"cards": [{"answer": "SENSITIVE", "correct_answer": 2,
                        "translation": {"tj": "Салом"}}]}
        ]})
        self.assertEqual(fields["$.sections[].cards[].answer"], 1)
        self.assertEqual(fields["$.sections[].cards[].correct_answer"], 1)
        self.assertNotIn("SENSITIVE", json.dumps(fields))

    def test_assessment_shape_check_only_emits_paths_not_answers(self):
        data = {"sections": [{"cards": [
            {"type": "choice", "options": ["SECRET_A", "SECRET_B"],
             "correct_index": 1},
            {"type": "choice", "options": ["SECRET_X"],
             "correct_index": 2},
            {"type": "choice", "options": {"uz": ["A"], "ru": [],
                                         "tj": ["B"]}, "correct_index": 0},
        ]}]}
        findings = assessment_shape_candidates(data)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(item["issue"] == "correct_index_out_of_bounds"
                            for item in findings))
        self.assertNotIn("SECRET", json.dumps(findings))

    def test_unreviewed_dynamic_shapes_are_candidates_not_silent_passes(self):
        result = assessment_shape_candidates({"correct_index": True,
                                               "options": ["a", "b"]})
        self.assertEqual(result[0]["issue"], "invalid_correct_index_type")
        result = assessment_shape_candidates({"correct_index": 0,
                                               "options": {"dynamic": "value"}})
        self.assertEqual(result[0]["issue"], "unclassified_options_mapping")

    def test_seven_track_fixture_and_no_content_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            localization = root / "localization"
            localization.mkdir()
            (localization / "manifest.json").write_text(json.dumps(sample_manifest()))
            (localization / "surface_registry.json").write_text(json.dumps(sample_registry()))
            app = root / "app"
            app.mkdir()
            (app / "main.py").write_text('''
@app.get("/course_v3_data/{level}/{filename}")
async def course_v3_lesson_file(level, filename):
    return None
''')
            for level in ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"):
                directory = app / "static/course_v3_data" / level
                directory.mkdir(parents=True)
                (directory / "lesson_01.json").write_text(
                    json.dumps({"sections": [{"cards": [{"correct": "SECRET"}]}]})
                )
            report = run_audit(root)
            self.assertEqual(report["scanned_lesson_files"], 7)
            self.assertEqual(report["answer_like_field_occurrences"], 7)
            self.assertNotIn("SECRET", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
