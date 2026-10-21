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

    def test_unlocked_account_lookup_cannot_replace_serialized_start(self):
        exact = "get_by_telegram_id_for_update(telegram_id)"
        self.assertIn(exact, self.api)
        changed = self.api.replace(exact, "get_by_telegram_id(telegram_id)", 1)
        regressions = {row["check"] for row in audit_source(changed, self.client)["regressions"]}
        self.assertIn("server.uses_verified_account_lookup", regressions)
        self.assertIn("server.locks_account_before_progress_and_quota", regressions)

    def test_locking_a_different_identity_cannot_authorize_start(self):
        exact = "get_by_telegram_id_for_update(telegram_id)"
        self.assertIn(exact, self.api)
        changed = self.api.replace(exact, "get_by_telegram_id_for_update(user_id)", 1)
        regressions = {row["check"] for row in audit_source(changed, self.client)["regressions"]}
        self.assertIn("server.uses_verified_account_lookup", regressions)

    def test_progress_lookup_before_account_lock_is_detected(self):
        exact = "            user = await UserRepository(session).get_by_telegram_id_for_update(telegram_id)"
        self.assertIn(exact, self.api)
        changed = self.api.replace(
            exact,
            "            await CourseProgressRepository(session).get_by_user_id(700, for_update=True)\n" + exact,
            1,
        )
        regressions = {row["check"] for row in audit_source(changed, self.client)["regressions"]}
        self.assertIn("server.locks_account_before_progress_and_quota", regressions)

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

    def test_reintroducing_skip_test_sequence_rejection_is_detected(self):
        skip_test = self.api.index("async def v3_course_lesson_skip_test(")
        gate = "            access = await LessonAccessService(session).status("
        self.assertIn(gate, self.api[skip_test:])
        changed = self.api[:skip_test] + self.api[skip_test:].replace(
            gate,
            "            if lesson_order > completed + 1:\n"
            "                return _private_content_response({}, status_code=403)\n" + gate,
            1,
        )
        result = audit_source(changed, self.client)
        self.assertIn(
            "server.skip_test_allows_locked_lesson_projection",
            {row["check"] for row in result["regressions"]},
        )

    def test_skip_test_projection_security_and_side_effect_guards_are_required(self):
        skip_test = self.api.index("async def v3_course_lesson_skip_test(")
        prefix, handler = self.api[:skip_test], self.api[skip_test:]
        cases = (
            ("await _authenticated(request)", "await _unverified(request)",
             "skip_test_uses_authenticated_identity_helper"),
            ("get_by_telegram_id(telegram_id)", "get_by_id(telegram_id)",
             "skip_test_uses_verified_account_lookup"),
            ("if level != user_level:", "if False:", "skip_test_checks_selected_level"),
            ("lesson_order > total:", "lesson_order > total + 999:",
             "skip_test_enforces_numbered_lesson_bounds"),
            ("_foundation_is_blocked(session, user, level)", "_no_foundation_check(session, user, level)",
             "skip_test_checks_required_foundation"),
            ("completed=completed, consume=False", "completed=completed, consume=True",
             "skip_test_checks_non_consuming_entitlement"),
            ('if not access.get("allowed"):', "if False:",
             "skip_test_access_denial_precedes_source_read"),
            ('"questions": questions', '"questions": lesson',
             "skip_test_returns_bounded_projection_only"),
            ("            lesson = _read_course_lesson(level, lesson_order)",
             "            await session.commit()\n            lesson = _read_course_lesson(level, lesson_order)",
             "skip_test_does_not_commit_or_unlock_progress"),
            ("            lesson = _read_course_lesson(level, lesson_order)",
             "            progress.completed_lessons_count = lesson_order\n"
             "            lesson = _read_course_lesson(level, lesson_order)",
             "skip_test_does_not_commit_or_unlock_progress"),
        )
        for before, after, check in cases:
            with self.subTest(check=check, mutation=after):
                self.assertIn(before, handler)
                changed = prefix + handler.replace(before, after, 1)
                result = audit_source(changed, self.client)
                self.assertIn("server." + check, {row["check"] for row in result["regressions"]})

    def test_skip_test_question_cap_and_private_cache_headers_are_required(self):
        for before, after, check in (
            ("min(6, len(candidates))", "len(candidates)",
             "skip_test_returns_bounded_projection_only"),
            ('"Cache-Control": "no-store"', '"Cache-Control": "public"',
             "skip_test_uses_no_store_response"),
        ):
            with self.subTest(check=check):
                self.assertIn(before, self.api)
                result = audit_source(self.api.replace(before, after, 1), self.client)
                self.assertIn("server." + check, {row["check"] for row in result["regressions"]})

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
