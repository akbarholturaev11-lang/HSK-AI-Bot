"""Guard public Mini App lesson compatibility and native authenticated transport."""
import unittest

from scripts.i18n_client_lesson_compat_audit import FILES, audit, contract


class ClientLessonTransportTests(unittest.TestCase):
    def test_current_client_transport_contracts(self):
        report = audit()
        self.assertEqual(report["status"], "SOURCE_CONTRACT_OK_LEGACY_MINIAPP_REVIEW")
        self.assertEqual(report["failures"], [])
        self.assertTrue(all(all(v for v in checks.values())
                            for checks in report["checks"].values()))
        self.assertEqual(report["migration_priority"],
                         "miniapp_legacy_public_lesson_fetch")

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
