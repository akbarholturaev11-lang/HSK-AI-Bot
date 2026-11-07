"""The download page must say what it offers before any script runs.

Everything the page shows about versions and links is fetched and written into
the DOM by its JavaScript. Search and AI crawlers run none of that, so the page
as delivered read "Versiya tekshirilmoqda…" and said nothing about what exists
or where to get it.

So the same facts are rendered server-side, as plain markup and as JSON-LD.
What is pinned here is that they are actually in the bytes that leave the
server, and that nothing is claimed about a platform that is not published.
"""

import json
import re
import unittest
from types import SimpleNamespace

from app.public_site.app_downloads_render import (
    downloads_section,
    format_size,
    structured_data,
)


ORIGIN = "https://hsk.example"


def _status(**overrides):
    platforms = {
        "macos": {
            "available": True,
            "version": "1.4.2",
            "download": "/downloads/macos",
            "file": "HSK-AI_1.4.2.dmg",
            "size": None,
        },
        "windows": {
            "available": True,
            "version": "1.4.2",
            "download": "/downloads/windows",
            "file": "HSK-AI_1.4.2-setup.exe",
            "size": None,
        },
        "android": {
            "available": True,
            "version": "1.1.1 (3)",
            "download": "/downloads/android",
            "file": "hsk-ai-1.1.1-3-direct-release.apk",
            "size": 3_850_356,
        },
    }
    platforms.update(overrides)
    return {"ok": True, "platforms": platforms, "any": True}


class SizeTests(unittest.TestCase):
    def test_sizes_read_the_way_a_person_reads_them(self):
        self.assertEqual(format_size(3_850_356), "3.7 MB")
        self.assertEqual(format_size(4096), "4 KB")

    def test_a_missing_size_is_simply_absent(self):
        for value in (None, 0, -1, "", "big"):
            with self.subTest(value=value):
                self.assertEqual(format_size(value), "")


class SectionTests(unittest.TestCase):
    def test_every_platform_is_named_with_its_version_and_link(self):
        html = downloads_section(_status(), origin=ORIGIN, language="uz")

        for label in ("macOS", "Windows", "Android"):
            self.assertIn(label, html)
        self.assertIn("/downloads/android", html)
        self.assertIn("1.1.1 (3)", html)
        self.assertIn("3.7 MB", html)

    def test_an_unpublished_platform_is_shown_as_unavailable_not_linked(self):
        html = downloads_section(
            _status(android={"available": False, "version": None, "download": None,
                             "file": None, "size": None}),
            origin=ORIGIN,
            language="uz",
        )

        self.assertIn("Android", html)
        self.assertNotIn("/downloads/android", html)
        self.assertIn("hali chiqarilmagan", html)

    def test_it_speaks_the_readers_language(self):
        for language, heading in (
            ("uz", "Barcha yuklamalar"),
            ("ru", "Все загрузки"),
            ("tj", "Ҳамаи боргириҳо"),
        ):
            with self.subTest(language=language):
                self.assertIn(heading, downloads_section(_status(), origin=ORIGIN, language=language))


class StructuredDataTests(unittest.TestCase):
    def _graph(self, status):
        raw = structured_data(status, origin=ORIGIN, page_url="/download")
        body = re.sub(r"^<script[^>]*>|</script>$", "", raw)
        return json.loads(body.replace("\\u003c", "<"))["@graph"]

    def test_each_published_platform_is_described(self):
        graph = self._graph(_status())

        self.assertEqual(len(graph), 3)
        systems = sorted(node["operatingSystem"] for node in graph)
        self.assertEqual(systems, ["Android", "Windows", "macOS"])

    def test_the_android_entry_carries_what_an_assistant_would_quote(self):
        android = next(n for n in self._graph(_status()) if n["operatingSystem"] == "Android")

        self.assertEqual(android["softwareVersion"], "1.1.1 (3)")
        self.assertEqual(android["downloadUrl"], ORIGIN + "/downloads/android")
        self.assertEqual(android["fileSize"], "3.7 MB")
        self.assertEqual(android["offers"]["price"], "0")

    def test_an_unpublished_platform_is_never_described(self):
        """The claim an assistant would repeat to somebody who cannot find it."""

        graph = self._graph(
            _status(android={"available": False, "version": None, "download": None,
                             "file": None, "size": None})
        )

        self.assertEqual(len(graph), 2)
        self.assertNotIn("Android", [node["operatingSystem"] for node in graph])

    def test_nothing_published_means_no_block_at_all(self):
        empty = {
            name: {"available": False, "version": None, "download": None,
                   "file": None, "size": None}
            for name in ("macos", "windows", "android")
        }
        self.assertEqual(structured_data({"platforms": empty}, origin=ORIGIN, page_url="/download"), "")

    def test_a_closing_script_tag_cannot_escape_the_block(self):
        graph = structured_data(
            _status(android={"available": True, "version": "</script><b>x", "download": "/downloads/android",
                             "file": "a.apk", "size": 10}),
            origin=ORIGIN,
            page_url="/download",
        )
        self.assertNotIn("</script><b>", graph)


class PageMarkerTests(unittest.TestCase):
    def test_the_page_still_carries_the_marker_the_server_fills(self):
        from pathlib import Path

        html = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        self.assertIn("<!--APP-DOWNLOADS-->", html)


if __name__ == "__main__":
    unittest.main()
