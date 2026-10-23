"""Exercise public browser assets through the actual HTTP application routes."""
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urljoin, urlsplit

import httpx


ROOT = Path(__file__).resolve().parents[1]


class _CourseAssetReferences(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        value = attrs.get("src") if tag == "script" else (
            attrs.get("href") if tag == "link" and "stylesheet" in attrs.get("rel", "").split() else None
        )
        if not value or urlsplit(value).netloc:
            return
        url = urljoin("/" + self.page, value)
        if urlsplit(url).path.startswith("/course_v3_data/"):
            self.urls.add(url)


class TelegramSdkAssetTests(unittest.IsolatedAsyncioTestCase):
    async def test_liquid_glass_assets_return_exact_same_origin_bytes(self):
        from app.main import app

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for filename in ("html2canvas.min.js", "container.js", "nav-glass.js", "nav-glass.css"):
                with self.subTest(asset=filename):
                    response = await client.get("/assets/liquid-glass/" + filename + "?v=20261022-pilot1")
                    self.assertEqual(response.status_code, 200)
                    media_type = "text/css" if filename.endswith(".css") else "application/javascript"
                    self.assertIn(media_type, response.headers["content-type"])
                    self.assertEqual(response.content, (ROOT / "app/static/assets/liquid-glass" / filename).read_bytes())

    async def test_liquid_glass_allowlist_does_not_expose_other_files(self):
        from app.main import app

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for path in ("unknown.js", "LICENSE", "..%2F..%2Fmain.py", "%2e%2e%2fnotification_templates"):
                with self.subTest(path=path):
                    response = await client.get("/assets/liquid-glass/" + path)
                    self.assertEqual(response.status_code, 404)

    async def test_sdk_is_public_and_returns_the_pinned_official_bytes(self):
        from app.main import app
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/assets/telegram-web-app.js?v=20261019-1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/javascript', response.headers['content-type'])
        self.assertEqual(response.content, Path('app/static/assets/telegram-web-app.js').read_bytes())
        self.assertEqual(hashlib.sha256(response.content).hexdigest(),
                         '124bdff7ba3fe86c8ba5143467afec21e020405e74abdb92cfdda6c0ee3b5908')

    async def test_html_course_scripts_and_stylesheets_are_served_by_real_routes(self):
        from app.main import app

        urls = set()
        for page in (ROOT / "app/static").glob("*.html"):
            parser = _CourseAssetReferences(page.name)
            parser.feed(page.read_text(encoding="utf-8"))
            urls.update(parser.urls)
        paths = {urlsplit(url).path for url in urls}
        self.assertTrue({
            "/course_v3_data/hsk-common-i18n.js",
            "/course_v3_data/hsk-course-i18n.js",
            "/course_v3_data/p3-grammar-reservation.js",
        }.issubset(paths))

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for url in sorted(urls):
                with self.subTest(asset=url):
                    response = await client.get(url)
                    path = urlsplit(url).path
                    self.assertEqual(response.status_code, 200)
                    media_type = "application/javascript" if path.endswith(".js") else "text/css"
                    self.assertIn(media_type, response.headers["content-type"])
                    self.assertEqual(response.content, (ROOT / "app/static" / path.lstrip("/")).read_bytes())

    async def test_public_asset_allowlist_keeps_lesson_exam_and_unknown_files_private(self):
        from app.main import app

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for path in (
                "/course_v3_data/nhsk2/lesson_16.json",
                "/course_v3_data/exams/hsk1.json",
                "/course_v3_data/parts_manifest.json",
                "/course_v3_data/not-allowed.js",
            ):
                with self.subTest(path=path):
                    response = await client.get(path)
                    self.assertEqual(response.status_code, 404)
