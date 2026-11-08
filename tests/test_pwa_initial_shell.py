"""PWA initial paint must be non-blocking and independent of private map state."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from starlette.requests import Request

from app.api.pwa_auth import (
    _add_pwa_course_initial_shell,
    _pwa_inline_html,
)


def request(path="/iphone-pwa/course", etag=None):
    headers = [] if not etag else [(b"if-none-match", etag.encode("ascii"))]
    return Request({"type": "http", "method": "GET", "path": path,
                    "query_string": b"", "headers": headers})


class PwaInitialShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = Path("app/static/course-v3.html").read_bytes()
        cls.digest = hashlib.sha256(cls.canonical).hexdigest()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(Path("app/static/course-v3.html").read_bytes()).hexdigest() == cls.digest

    def test_only_authenticated_pwa_delivery_gets_shell_and_existing_course_is_unchanged(self):
        adapted = _add_pwa_course_initial_shell(self.canonical)
        self.assertIn(b'hsk-pwa-shell-loading', adapted)
        self.assertIn(b'hsk-pwa-boot-shell', adapted)
        self.assertIn(b'aria-busy="true"', adapted)
        self.assertIn(b'<nav class="nav" id="nav" inert>', adapted)
        self.assertIn('data-i="course">Курс</span>'.encode("utf-8"), adapted)
        self.assertIn(b'class="hsk-pwa-boot-title" aria-label="HSK AI">HSK AI</h1>', adapted)
        self.assertIn(b'html.hsk-pwa-browser #hsk-launch-splash{display:none!important}', adapted)
        self.assertIn(b'@media(prefers-reduced-motion:reduce)', adapted)
        self.assertNotIn(b"hsk-pwa-boot-shell", self.canonical)
        self.assertNotIn(b'"is_paid":true', adapted.lower())
        self.assertNotIn(b'http-equiv="refresh"', adapted.lower())

    def test_pwa_shell_preserves_private_etag_revalidation(self):
        path = "app/static/course-v3.html"
        first = _pwa_inline_html(request(), path, {"X-Frame-Options": "DENY"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["Cache-Control"], "private, no-cache")
        self.assertEqual(first.headers["X-Frame-Options"], "DENY")
        self.assertIn(b"hsk-pwa-boot-shell", first.body)
        self.assertIn(b"iphone-pwa-inline-pro.js", first.body)
        second = _pwa_inline_html(request(etag=first.headers["ETag"]), path, {})
        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.headers["ETag"], first.headers["ETag"])

    def test_other_pwa_pages_do_not_receive_course_shell(self):
        with tempfile.NamedTemporaryFile(suffix=".html") as file:
            Path(file.name).write_text("<html><body>Other screen</body></html>", encoding="utf-8")
            page = _pwa_inline_html(request("/iphone-pwa/practice/test"), file.name, {})
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Other screen", page.body)
            self.assertNotIn(b"hsk-pwa-boot-shell", page.body)

    def test_unexpected_canonical_markup_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "pwa_initial_shell_source_mismatch"):
            _add_pwa_course_initial_shell(b"<html><body>not the course</body></html>")


if __name__ == "__main__":
    unittest.main()
