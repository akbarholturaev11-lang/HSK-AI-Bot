"""Regression: one canonical static PWA first paint, never a second injected shell.

The authenticated /iphone-pwa/course route owns the cookie gate. This test
covers the pure HTML renderer; browser-level identity checks live elsewhere.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path

from starlette.requests import Request
from app.api.pwa_auth import _pwa_inline_html


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

    def test_canonical_shell_is_static_and_does_not_claim_access(self):
        source = self.canonical
        self.assertIn(b'class="pwa-initial-shell"', source)
        self.assertIn(b'class="pwa-first-logo"', source)
        self.assertIn(b'fetchpriority="high"', source)
        self.assertIn(b'PWA_PREBOOT_TAB', source)
        self.assertIn(b'/assets/telegram-web-app.js', source)
        self.assertIn(b'var tg=PWA_COURSE_HOST?null:window.Telegram', source)
        self.assertNotIn(b'hsk-pwa-boot-shell', source)
        shell = source.split(b'<div class="scr on" id="s-course">', 1)[1].split(
            b'<div class="scr" id="s-mashq">', 1
        )[0]
        for private in (b'"is_paid":true', b"localStorage", b"data-lesson", b'"user_id"'):
            self.assertNotIn(private, shell)

    def test_pwa_document_preserves_one_shell_and_private_etag(self):
        path = "app/static/course-v3.html"
        first = _pwa_inline_html(request(), path, {"X-Frame-Options": "DENY"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["Cache-Control"], "private, no-cache")
        self.assertEqual(first.headers["X-Frame-Options"], "DENY")
        self.assertEqual(first.body.count(b'class="pwa-initial-shell"'),
                         self.canonical.count(b'class="pwa-initial-shell"'))
        self.assertNotIn(b"hsk-pwa-boot-shell", first.body)
        self.assertEqual(first.body.count(b'id="hsk-pwa-progressive-sections"'), 1)
        self.assertIn(b".hsk-pwa-section-loading", first.body)
        self.assertIn(b".hsk-pwa-profile-accuracy-loading", first.body)
        self.assertIn(b"prefers-reduced-motion:reduce", first.body)
        self.assertNotIn(b'<script src="/assets/telegram-web-app.js?v=20261019-1"></script>', first.body)
        self.assertIn(b"iphone-pwa-inline-pro.js", first.body)
        second = _pwa_inline_html(request(etag=first.headers["ETag"]), path, {})
        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.headers["ETag"], first.headers["ETag"])

    def test_other_pages_do_not_receive_course_shell(self):
        with tempfile.NamedTemporaryFile(suffix=".html") as file:
            Path(file.name).write_text("<html><body>Other screen</body></html>", encoding="utf-8")
            page = _pwa_inline_html(request("/iphone-pwa/practice/test"), file.name, {})
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Other screen", page.body)
            self.assertNotIn(b"pwa-initial-shell", page.body)
            self.assertNotIn(b"hsk-pwa-progressive-sections", page.body)

    def test_inline_response_never_modifies_shared_file(self):
        _pwa_inline_html(request(), "app/static/course-v3.html", {})
        self.assertEqual(Path("app/static/course-v3.html").read_bytes(), self.canonical)


if __name__ == "__main__":
    unittest.main()
