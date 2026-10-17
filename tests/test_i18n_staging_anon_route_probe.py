"""Ensure the staging-only probe is opt-in and never captures lesson bodies."""
import unittest

from scripts.i18n_staging_anon_route_probe import (
    TRACKS, cases, probe, staging_origin,
)


class _Response:
    def __init__(self, code):
        self.status = code
        self.closed = False
        self.body_reads = 0

    def read(self, *args):
        self.body_reads += 1
        raise AssertionError("Never read private lesson response bytes")

    def close(self):
        self.closed = True


class StagingAnonymousProbeTests(unittest.TestCase):
    def test_default_is_strictly_offline(self):
        def cannot_open(request, timeout):
            self.fail("Dry-run must not perform network requests")
        result = probe(open_request=cannot_open)
        self.assertEqual(result["status"], "NOT_EXECUTED_STAGING_TARGET_REQUIRED")
        self.assertEqual(result["performed_requests"], 0)
        self.assertEqual(result["planned_requests"], 2 * len(TRACKS) + 3)
        self.assertEqual(result["findings"], [])
        self.assertFalse(any(c["http_status"] is not None for c in result["cases"]))

    def test_production_and_mismatched_hosts_rejected(self):
        for url, hostname in [
            ("https://telegram-chinese-bot-production.up.railway.app", "telegram-chinese-bot-production.up.railway.app"),
            ("https://www.qa.example.test", "www.qa.example.test"),
            ("https://qa.example.test", "staging.example.test"),
            ("http://qa.example.test", "qa.example.test"),
            ("https://qa.example.test/path", "qa.example.test"),
            ("https://qa.example.test?token=secret", "qa.example.test"),
            ("https://user:pass@qa.example.test", "qa.example.test"),
            ("https://qa.example.test:8080", "qa.example.test"),
        ]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    staging_origin(url, hostname)
        self.assertEqual(staging_origin("https://staging.example.test/", "staging.example.test"),
                         "https://staging.example.test")

    def test_status_only_probe_no_auth_no_body(self):
        responses = []
        requests = []
        def fake_open(request, timeout):
            self.assertEqual(timeout, 5)
            requests.append(request)
            code = (404 if "exams/" in request.full_url else
                    401 if "/api/v3/" in request.full_url else 200)
            result = _Response(code)
            responses.append(result)
            return result
        result = probe(execute=True, base_url="https://qa.example.test",
                       confirmed_host="qa.example.test", open_request=fake_open)
        self.assertEqual(result["performed_requests"], 17)
        self.assertTrue(result["exam_404_verified"])
        self.assertEqual(result["anonymous_lesson_success_count"], 7)
        self.assertEqual(result["native_api_denied_without_bearer_count"], 2)
        self.assertEqual(len(responses), 17)
        self.assertTrue(all(r.closed and r.body_reads == 0 for r in responses))
        self.assertEqual(len(result["findings"]), 7)
        for req in requests:
            self.assertEqual(req.get_method(), "GET")
            self.assertNotIn("authorization", {k.lower() for k in req.headers})
            self.assertNotIn("x-telegram-init-data", {k.lower() for k in req.headers})

    def test_non_404_exam_never_counts_as_protected(self):
        result = probe(execute=True, base_url="https://staging.example.test",
                       confirmed_host="staging.example.test",
                       open_request=lambda req, timeout: _Response(200))
        self.assertFalse(result["exam_404_verified"])
        self.assertTrue(any(f["issue"] == "staging_exam_404_not_verified"
                            for f in result["findings"]))
        self.assertTrue(any(f["issue"] == "native_anonymous_auth_denial_not_confirmed"
                            for f in result["findings"]))

    def test_transport_failure_not_claimed_to_be_secure(self):
        from urllib.error import URLError
        def no_service(req, timeout):
            raise URLError("unreachable")
        result = probe(execute=True, base_url="https://qa.example.test",
                       confirmed_host="qa.example.test", open_request=no_service)
        self.assertFalse(result["exam_404_verified"])
        self.assertTrue(all(item["error"] == "transport_error" for item in result["cases"]))
        self.assertEqual(result["anonymous_lesson_success_count"], 0)


if __name__ == "__main__":
    unittest.main()
