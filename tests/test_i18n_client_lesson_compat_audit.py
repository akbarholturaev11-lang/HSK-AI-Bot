"""Guard public Mini App lesson compatibility and native authenticated transport."""
import unittest

from scripts.i18n_client_lesson_compat_audit import FILES, audit, contract


class ClientLessonTransportTests(unittest.TestCase):
    def test_current_client_transport_contracts(self):
        report = audit()
        self.assertEqual(report["status"], "SOURCE_CONTRACT_OK_AUTHENTICATED_MINIAPP_REVIEW")
        self.assertEqual(report["failures"], [])
        self.assertTrue(all(all(v for v in checks.values())
                            for checks in report["checks"].values()))
        self.assertEqual(report["migration_priority"],
                         "miniapp_authenticated_lesson_api_runtime_verification")

    def test_miniapp_auth_and_legacy_route_guards_fail_closed(self):
        from pathlib import Path
        from scripts.i18n_client_lesson_compat_audit import ROOT
        sources = {
            key: (ROOT / path).read_text(encoding="utf-8")
            for key, path in FILES.items()
        }
        broken = dict(sources)
        broken["miniapp"] = broken["miniapp"].replace(
            '"X-Telegram-Init-Data":INIT_DATA', '"Content-Type":"application/json"',
        )
        report = contract(broken)
        self.assertTrue(any(row["platform"] == "miniapp"
                            and row["check"] == "fetches_with_signed_identity_and_no_store"
                            for row in report["failures"]))

        broken = dict(sources)
        main = sources["backend_main"]
        legacy_start = main.index("async def course_v3_lesson_file(")
        legacy_end = main.index("@app.get(", legacy_start)
        broken["backend_main"] = (
            main[:legacy_start]
            + main[legacy_start:legacy_end].replace(
                'status_code=404,\n        content={"ok": False, "error": "lesson_content_not_found"}',
                'status_code=200,\n        content={"ok": True}',
            )
            + main[legacy_end:]
        )
        report = contract(broken)
        self.assertTrue(any(row["platform"] == "legacy_public_route"
                            and row["check"] == "old_lesson_json_route_returns_404"
                            for row in report["failures"]))

        broken = dict(sources)
        backend = sources["backend_miniapp_content"]
        skip_start = backend.index("async def v3_course_lesson_skip_test(")
        broken["backend_miniapp_content"] = (
            backend[:skip_start]
            + backend[skip_start:].replace(
                "lesson_order > completed + 1", "lesson_order > completed + 999", 1,
            )
        )
        report = contract(broken)
        self.assertTrue(any(row["platform"] == "miniapp_server"
                            and row["check"] == "skip_test_sequence_is_checked"
                            for row in report["failures"]))

    def test_missing_credential_or_cache_rule_requires_manual_review(self):
        from pathlib import Path
        from scripts.i18n_client_lesson_compat_audit import ROOT
        sources = {
            key: (ROOT / path).read_text(encoding="utf-8")
            for key, path in FILES.items()
        }
        broken = dict(sources)
        broken["android_repository"] = broken["android_repository"].replace(
            'api.lesson("Bearer $token", lessonOrder, accessRef)',
            'api.lesson("ANONYMOUS", lessonOrder, accessRef)',
        )
        missing_auth = contract(broken)
        self.assertEqual(missing_auth["status"], "REGRESSION")
        self.assertIn({"platform": "android", "check": "repository_sends_bearer",
                       "issue": "source_contract_missing"}, missing_auth["failures"])

        broken = dict(sources)
        broken["desktop_rust"] = broken["desktop_rust"].replace(
            '/api/v3/desktop/course/lesson/{lesson_order}',
            '/course_v3_data/hsk1/lesson_01.json',
        )
        missing_private_endpoint = contract(broken)
        self.assertTrue(any(row["platform"] == "desktop"
                            and row["check"] == "rust_private_lesson_endpoint"
                            for row in missing_private_endpoint["failures"]))

        broken = dict(sources)
        broken["android_repository"] = broken["android_repository"].replace(
            'error !is ApiError.Offline && error !is ApiError.Timeout',
            'error is ApiError.Unauthorized',
        )
        missing_fallback_guard = contract(broken)
        self.assertTrue(any(row["check"] == "offline_cache_limited_to_transport_failures"
                            for row in missing_fallback_guard["failures"]))

        broken = dict(sources)
        activity = sources["android_main_activity"]
        sign_out_start = activity.index("val signOut: (Boolean) -> Unit")
        first_part, sign_out = activity[:sign_out_start], activity[sign_out_start:]
        self.assertIn("app.clearLocalData()", sign_out)
        broken["android_main_activity"] = first_part + sign_out.replace(
            "app.clearLocalData()", "// deliberately removed cache clearing", 1,
        )
        self.assertNotEqual(broken["android_main_activity"], activity)
        missing_logout_cleanup = contract(broken)
        self.assertTrue(any(row["check"] == "sign_out_invokes_cache_cleanup"
                            for row in missing_logout_cleanup["failures"]))

        broken = dict(sources)
        broken["android_app"] = broken["android_app"].replace(
            'courseRepository.clearCache()', '// no local course cache wipe',
        )
        missing_app_cleanup = contract(broken)
        self.assertTrue(any(row["check"] == "app_session_cleanup_calls_repository_clear"
                            for row in missing_app_cleanup["failures"]))

    def test_source_inventory_fail_closed_on_missing_file(self):
        sources = {key: "" for key in FILES}
        sources.pop("desktop_rust")
        with self.assertRaisesRegex(ValueError, "Client source list changed"):
            contract(sources)


if __name__ == "__main__":
    unittest.main()
