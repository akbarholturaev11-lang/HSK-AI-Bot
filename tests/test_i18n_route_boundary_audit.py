"""Contract tests for public lesson JSON route and private exams, AST only."""
import json
from pathlib import Path
import unittest

from scripts.i18n_route_boundary_audit import audit, middleware_boundary, routes

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = '''
@app.get("/course_v3_data/{filename}")
async def course_v3_data_file(filename: str):
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
    return static_json_response(filename)
'''
GUARD = 'GUARDED_PATH_PREFIX = "/api/"'


class RouteBoundaryContractTests(unittest.TestCase):
    def test_private_exam_remains_server_only(self):
        result = audit(SAMPLE, GUARD)
        self.assertTrue(result["exam"]["explicit_404_return"])
        self.assertFalse(result["exam"]["serves_file"])
        self.assertTrue(result["lesson"]["serves_file"])
        self.assertFalse(result["lesson"]["handler_dependency"])
        self.assertTrue(result["lesson"]["has_level_and_filename_pattern_validation"])
        self.assertFalse(result["middleware"]["guard_applies_to_course_json"])
        self.assertIn("source_level_public_lesson_file_exposure",
                      {row["issue"] for row in result["findings"]})

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

    def test_middleware_scope_change_is_not_guessed(self):
        result = middleware_boundary('GUARDED_PATH_PREFIX = "/course_v3_data/"')
        self.assertTrue(result["guard_applies_to_course_json"])
        with self.assertRaisesRegex(ValueError, "prefix"):
            middleware_boundary("other_setting = '/api/'")

    def test_duplicate_or_missing_route_requires_manual_audit(self):
        with self.assertRaisesRegex(ValueError, "contract changed"):
            routes(SAMPLE.replace('@app.get("/course_v3_data/exams/{filename}")',
                                  '@app.get("/not-exam")'))

    def test_real_source_route_security_state_without_app_import(self):
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        guard = (ROOT / "app/services/blocked_user_guard.py").read_text(encoding="utf-8")
        result = audit(main, guard)
        self.assertEqual(result["status"], "SOURCE_REVIEW_REQUIRED")
        self.assertTrue(result["exam"]["explicit_404_return"])
        self.assertFalse(result["exam"]["serves_file"])
        self.assertTrue(result["lesson"]["has_level_and_filename_pattern_validation"])
        self.assertEqual(result["middleware"]["guarded_prefix"], "/api/")
        self.assertIn("source_level_public_lesson_file_exposure",
                      {row["issue"] for row in result["findings"]})
        self.assertNotIn("private", json.dumps(result["lesson"]))


if __name__ == "__main__":
    unittest.main()
