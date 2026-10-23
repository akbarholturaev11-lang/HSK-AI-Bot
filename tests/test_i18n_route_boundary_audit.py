"""Contract tests for public lesson JSON route and private exams, AST only."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i18n_route_boundary_audit import (
    MAP_TRACKS, audit, curriculum_map_shapes, middleware_boundary, routes,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = '''
COURSE_V3_PUBLIC_MAP_FILES = frozenset({"hsk1.json", "hsk2.json", "hsk3.json", "hsk4.json", "nhsk1.json", "nhsk2.json", "nhsk3.json"})
@app.get("/course_v3_data/{filename}")
async def course_v3_data_file(filename: str):
    if filename not in COURSE_V3_PUBLIC_MAP_FILES:
        return JSONResponse(status_code=404, content={})
    return static_json_response(filename)
@app.get("/course_v3_data/exams/{filename}")
async def course_v3_exam_file(filename: str):
    return JSONResponse(status_code=404, content={"error":"private"})
@app.get("/course_v3_data/{level}/{filename}")
async def course_v3_lesson_file(level: str, filename: str):
    if not re.fullmatch(r"(?:hsk[1-4]|nhsk[1-3])", level):
        return JSONResponse(status_code=404, content={})
    if not re.fullmatch(r"lesson_\\d+\\.json", filename):
        return JSONResponse(status_code=404, content={})
    return JSONResponse(status_code=404, content={})
'''
GUARD = 'GUARDED_PATH_PREFIX = "/api/"'


class RouteBoundaryContractTests(unittest.TestCase):
    def test_private_exam_remains_server_only(self):
        result = audit(SAMPLE, GUARD)
        self.assertEqual(result["status"], "SOURCE_CHECK_NO_FINDINGS")
        self.assertTrue(result["exam"]["explicit_404_return"])
        self.assertFalse(result["exam"]["serves_file"])
        self.assertFalse(result["lesson"]["serves_file"])
        self.assertFalse(result["lesson"]["handler_dependency"])
        self.assertTrue(result["lesson"]["explicit_404_return"])
        self.assertTrue(result["lesson"]["has_level_and_filename_pattern_validation"])
        self.assertFalse(result["middleware"]["guard_applies_to_course_json"])
        self.assertTrue(result["map"]["fixed_public_map_allowlist"])

    def test_exam_file_response_or_200_is_a_release_blocker(self):
        changed = SAMPLE.replace(
            'return JSONResponse(status_code=404, content={"error":"private"})',
            'return static_json_response("secret_exam.json")',
        )
        result = audit(changed, GUARD)
        self.assertIn("private_exam_route_no_longer_returns_explicit_404",
                      {row["issue"] for row in result["findings"]})
        self.assertTrue(any(row["severity"] == "stop_the_release"
                            for row in result["findings"]))

    def test_route_validation_drift_is_release_blocker(self):
        changed = SAMPLE.replace('r"lesson_\\d+\\.json"', 'r".+\\.json"')
        result = audit(changed, GUARD)
        self.assertIn("lesson_level_or_filename_validation_changed",
                      {row["issue"] for row in result["findings"]})

    def test_generic_root_json_response_requires_fixed_map_allowlist(self):
        changed = SAMPLE.replace(
            'if filename not in COURSE_V3_PUBLIC_MAP_FILES:',
            'if not filename.endswith(".json"):',
        )
        result = audit(changed, GUARD)
        self.assertIn("public_course_json_route_missing_fixed_allowlist",
                      {row["issue"] for row in result["findings"]})

    def test_middleware_scope_change_is_not_guessed(self):
        result = middleware_boundary('GUARDED_PATH_PREFIX = "/course_v3_data/"')
        self.assertTrue(result["guard_applies_to_course_json"])
        with self.assertRaisesRegex(ValueError, "prefix"):
            middleware_boundary("other_setting = '/api/'")

    def test_duplicate_or_missing_route_requires_manual_audit(self):
        with self.assertRaisesRegex(ValueError, "contract changed"):
            routes(SAMPLE.replace('@app.get("/course_v3_data/exams/{filename}")',
                                  '@app.get("/not-exam")'))

    def test_public_curriculum_map_shape_and_private_answer_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "app/static/course_v3_data"
            folder.mkdir(parents=True)
            for track in MAP_TRACKS:
                (folder / (track + ".json")).write_text(json.dumps({
                    "level": track,
                    "units": [{"lessons": [{"n": 1, "title": "SENSITIVE_LESSON_NAME"}]}],
                }), encoding="utf-8")
            result = curriculum_map_shapes(root)
            self.assertEqual(result["maps_checked"], 7)
            self.assertEqual(result["lesson_navigation_entries"], 7)
            self.assertEqual(result["private_assessment_key_occurrences"], 0)
            self.assertNotIn("SENSITIVE_LESSON_NAME", json.dumps(result))
            exposed = folder / "hsk1.json"
            exposed.write_text(json.dumps({
                "units": [{"lessons": [{"n": 1, "correct_index": 0,
                                         "answer_key": "SECRET_ANSWER",
                                         "correctIndex": 2,
                                         "answer-key": "SECRET_ANSWER"}]}],
            }), encoding="utf-8")
            finding = curriculum_map_shapes(root)
            self.assertEqual(finding["private_assessment_key_occurrences"], 4)
            self.assertNotIn("SECRET_ANSWER", json.dumps(finding))
            self.assertEqual(
                finding["maps"][0]["private_assessment_key_paths"],
                ["$.units[].lessons[].correct_index", "$.units[].lessons[].answer_key",
                 "$.units[].lessons[].correctIndex", "$.units[].lessons[].answer-key"]
            )

    def test_existing_seven_curriculum_maps_contain_navigation_not_grading_keys(self):
        result = curriculum_map_shapes(ROOT)
        self.assertEqual(result["maps_checked"], 7)
        self.assertEqual(result["lesson_navigation_entries"], 746)
        self.assertEqual(result["private_assessment_key_occurrences"], 0)
        self.assertTrue(all(row["lesson_navigation_entries"] > 0
                            for row in result["maps"]))

    def test_real_source_route_security_state_without_app_import(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        guard = (ROOT / "app/services/blocked_user_guard.py").read_text(encoding="utf-8")
        result = audit(main, guard)
        self.assertEqual(result["status"], "SOURCE_CHECK_NO_FINDINGS")
        self.assertTrue(result["exam"]["explicit_404_return"])
        self.assertFalse(result["exam"]["serves_file"])
        self.assertTrue(result["lesson"]["has_level_and_filename_pattern_validation"])
        self.assertTrue(result["lesson"]["explicit_404_return"])
        self.assertFalse(result["lesson"]["serves_file"])
        self.assertTrue(result["map"]["fixed_public_map_allowlist"])
        self.assertEqual(result["middleware"]["guarded_prefix"], "/api/")
        self.assertEqual(result["findings"], [])
        self.assertNotIn("private", json.dumps(result["lesson"]))


if __name__ == "__main__":
    unittest.main()
