"""Protect the authenticated start gate without touching legacy lesson delivery."""
import json
from pathlib import Path
import unittest

from scripts.i18n_miniapp_reservation_boundary_audit import (
    ROOT, API, MINIAPP, audit, audit_source,
)


class MiniAppReservationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = (ROOT / API).read_text(encoding="utf-8")
        cls.client = (ROOT / MINIAPP).read_text(encoding="utf-8")

    def test_reservation_and_authenticated_content_contract(self):
        result = audit(ROOT)
        self.assertEqual(result["status"], "SOURCE_AUTHENTICATED_CONTENT_GATE_PRESENT")
        self.assertEqual(result["regressions"], [])
        self.assertTrue(all(result["server"].values()))
        self.assertTrue(all(result["miniapp"].values()))
        self.assertEqual(result["review_findings"], [])
        self.assertNotIn("correct_index", json.dumps(result))
        self.assertNotIn("BOT_TOKEN", json.dumps(result))

    def test_removing_server_401_guard_is_detected(self):
        exact = 'return JSONResponse(status_code=401, content={"ok": False, "error": "invalid_telegram_init_data"})'
        self.assertIn(exact, self.api)
        changed = self.api.replace(exact, exact.replace("401", "200"), 1)
        result = audit_source(changed, self.client)
        self.assertIn(
            "server.rejects_missing_identity_401",
            {row["check"] for row in result["regressions"]},
        )

    def test_dropping_quota_consumption_is_detected(self):
        self.assertIn("consume=True", self.api)
        changed = self.api.replace("consume=True", "consume=False", 1)
        result = audit_source(changed, self.client)
        self.assertIn(
            "server.uses_lesson_access_consume_true",
            {row["check"] for row in result["regressions"]},
        )

    def test_unlock_sequence_guard_change_is_detected(self):
        self.assertIn("order > completed + 1", self.api)
        changed = self.api.replace("order > completed + 1",
                                   "order > completed + 999", 1)
        result = audit_source(changed, self.client)
        self.assertIn(
            "server.content_rejects_out_of_sequence_lesson",
            {row["check"] for row in result["regressions"]},
        )

    def test_start_reservation_sequence_guard_change_is_detected(self):
        start = self.api.index("async def v3_course_lesson_start(")
        changed = self.api[:start] + self.api[start:].replace(
            "order > completed + 1", "order > completed + 999", 1,
        )
        result = audit_source(changed, self.client)
        self.assertIn(
            "server.rejects_out_of_sequence_lesson",
            {row["check"] for row in result["regressions"]},
        )

    def test_skip_test_sequence_guard_change_is_detected(self):
        skip_test = self.api.index("async def v3_course_lesson_skip_test(")
        changed = self.api[:skip_test] + self.api[skip_test:].replace(
            "lesson_order > completed + 1", "lesson_order > completed + 999", 1,
        )
        result = audit_source(changed, self.client)
        self.assertIn(
            "server.skip_test_rejects_out_of_sequence_lesson",
            {row["check"] for row in result["regressions"]},
        )

    def test_client_reservation_before_fetch_is_required(self):
        exact = "reserveLessonStart(l).then(function(){return loadLessonData(lv,l.n)}"
        self.assertIn(exact, self.client)
        changed = self.client.replace(exact, "loadLessonData(lv,l.n)", 1)
        result = audit_source(self.api, changed)
        self.assertIn(
            "miniapp.reserves_before_interactive_json_read",
            {row["check"] for row in result["regressions"]},
        )

    def test_moving_shared_lesson_fetch_requires_contract_review(self):
        exact = "fetch(lessonDataUrl(lv,n),"
        self.assertIn(exact, self.client)
        changed = self.client.replace(exact, "fetch('/api/lesson/new',", 1)
        result = audit_source(self.api, changed)
        self.assertIn(
            "miniapp.uses_direct_legacy_static_json_fetch",
            {row["check"] for row in result["regressions"]},
        )

    def test_missing_handler_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "handler identity changed"):
            audit_source(self.api.replace("async def v3_course_lesson_start(",
                                          "async def deprecated_lesson_start(", 1),
                         self.client)


if __name__ == "__main__":
    unittest.main()
