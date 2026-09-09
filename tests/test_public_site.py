import json
import re
import unittest
from html.parser import HTMLParser
from types import SimpleNamespace
from xml.etree import ElementTree

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.public_site import create_public_site_router, indexnow_payload
from app.api.public_site import GOOGLE_VERIFICATION_FILENAME
from app.public_site.content import HOME_PATHS, PAGES
from app.public_site.render import attribution, public_origin

ORIGIN = "https://learn.example.com"


def settings(**kwargs):
    return SimpleNamespace(**{"PUBLIC_SITE_URL": ORIGIN, "INDEXNOW_KEY": "", **kwargs})


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag, **attrs):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in attrs.items())]


# Robots RFC uses longest matching rule; urllib.robotparser doesn't support $/*.
def allowed(text, agent, path):
    groups = text.split("\n\n")
    group = next(g for g in groups if g.startswith(f"User-agent: {agent}\n"))
    matches = []
    for line in group.splitlines()[1:]:
        action, value = line.split(": ", 1)
        pattern = re.escape(value).replace(r"\*", ".*").replace(r"\$", "$")
        if re.match(pattern, path):
            matches.append((len(value.replace("*", "").replace("$", "")), action == "Allow"))
    return max(matches, default=(0, True))[1]


class PublicSiteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        self.app.include_router(create_public_site_router(settings_obj=settings()))
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url=ORIGIN)

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_all_html_metadata_source_and_schemas(self):
        titles, descriptions = set(), set()
        for path, page in PAGES.items():
            response = await self.client.get(path + "?utm_source=test", headers={"host": "untrusted.example"})
            self.assertEqual(response.status_code, 200, path)
            html = response.text
            parsed = Tags(html)
            self.assertEqual(len(parsed.find("h1")), 1)
            self.assertIn(page["h1"], html)
            self.assertEqual(parsed.find("link", rel="canonical")[0]["href"], ORIGIN + path)
            self.assertEqual(parsed.find("meta", name="description")[0]["content"], page["description"])
            self.assertIn("HSK AI", html)
            self.assertIn("darsi_chini_bot", html)
            self.assertIn("HSK 1", html)
            self.assertNotIn("telegram-web-app.js", html)
            self.assertEqual(parsed.find("html")[0]["lang"], page["lang"])
            for prop in ("og:title", "og:description", "og:type", "og:url", "og:image"):
                self.assertTrue(parsed.find("meta", property=prop))
            self.assertEqual(parsed.find("meta", name="twitter:card")[0]["content"], "summary_large_image")
            expected = HOME_PATHS if path in HOME_PATHS.values() else {page["lang"]: path}
            self.assertEqual({t["hreflang"]: t["href"] for t in parsed.find("link", rel="alternate")},
                             {lang: ORIGIN + p for lang, p in expected.items()})
            graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])["@graph"]
            self.assertTrue({"Organization", "WebSite", "SoftwareApplication", "WebPage"}.issubset({n["@type"] for n in graph}))
            self.assertFalse(any("aggregateRating" in n or "review" in n for n in graph))
            if path == "/tj/hsk/":
                self.assertEqual([n["name"] for n in graph if n["@type"] == "Course"], [f"HSK {i}" for i in range(1, 5)])
                for i in range(1, 5):
                    self.assertTrue(parsed.find("section", id=f"hsk{i}"))
            titles.add(page["title"])
            descriptions.add(page["description"])
        self.assertEqual(len(titles), len(PAGES))
        self.assertEqual(len(descriptions), len(PAGES))

    async def test_sitemap_and_robots_private_boundaries(self):
        response = await self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        urls = ElementTree.fromstring(response.content).findall("{*}url/{*}loc")
        self.assertEqual([u.text for u in urls], [ORIGIN + path for path in PAGES])
        self.assertNotIn("lastmod", response.text)
        robots = await self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn(f"Sitemap: {ORIGIN}/sitemap.xml", robots.text)
        for agent in ("*", "Googlebot", "Bingbot", "OAI-SearchBot"):
            for path in PAGES:
                self.assertTrue(allowed(robots.text, agent, path))
                self.assertTrue(allowed(robots.text, agent, path + "?utm_source=x"))
            for path in ("/admin.html", "/api/v3/map", "/subscription.html", "/payments/x", "/course-v3.html",
                         "/course-v3", "/course_v3_data/hsk1.json", "/uploads/private", "/docs", "/openapi.json",
                         "/go/telegram", "/tj/private", "/future-private"):
                self.assertFalse(allowed(robots.text, agent, path), (agent, path))
            self.assertTrue(allowed(robots.text, agent, "/public-assets/site.css"))

    async def test_attribution_click_and_no_open_redirect(self):
        with self.assertLogs("uvicorn.error.public_analytics", level="INFO") as captured:
            response = await self.client.get("/tj/?utm_source=bing&utm_campaign=hsk&initData=SECRET")
            parsed = Tags(response.text)
            cta = parsed.find("a", **{"class": "cta"})[0]["href"]
            self.assertIn("utm_campaign=hsk", cta)
            nav = parsed.find("a", lang="ru")[0]["href"]
            self.assertIn("utm_source=bing", nav)
            response = await self.client.get(cta + "&url=https://evil.example")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://t.me/darsi_chini_bot")
        self.assertIn("noindex", response.headers["x-robots-tag"])
        logs = " ".join(captured.output)
        self.assertIn("landing_view", logs)
        self.assertIn("telegram_bot_cta_clicked", logs)
        self.assertIn('"utm_source":"bing"', logs)
        self.assertNotIn("SECRET", logs)
        self.assertEqual((await self.client.get("/go/telegram?page=/api/private")).status_code, 400)

    async def test_assets_and_unknown_paths(self):
        for path in ("site.css", "avatar.webp", "social-cover.webp"):
            r = await self.client.get("/public-assets/" + path)
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.content)
        self.assertEqual((await self.client.get("/public-assets/not-real.css")).status_code, 404)
        self.assertEqual((await self.client.get("/tj/not-a-page/")).status_code, 404)
        self.assertEqual((await self.client.get("/tj", follow_redirects=True)).status_code, 200)

    async def test_verification_optional_and_escaped(self):
        self.assertNotIn("google-site-verification", (await self.client.get("/")).text)
        cfg = settings(INDEXNOW_KEY="test-key-12345678", GOOGLE_SITE_VERIFICATION='token"><script>', BING_SITE_VERIFICATION="bing-token")
        app = FastAPI()
        app.include_router(create_public_site_router(settings_obj=cfg))
        async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as client:
            html = (await client.get("/")).text
            self.assertNotIn('token"><script>', html)
            self.assertEqual(Tags(html).find("meta", name="msvalidate.01")[0]["content"], "bing-token")
            self.assertEqual((await client.get("/test-key-12345678.txt")).text, cfg.INDEXNOW_KEY)
            robots = (await client.get("/robots.txt")).text
            self.assertTrue(allowed(robots, "Bingbot", "/test-key-12345678.txt"))
        payload = indexnow_payload(cfg)
        self.assertEqual(payload["urlList"], [ORIGIN + p for p in PAGES])
        self.assertEqual(payload["keyLocation"], ORIGIN + "/test-key-12345678.txt")
        with self.assertRaises(ValueError):
            indexnow_payload(settings())
        with self.assertRaises(ValueError):
            create_public_site_router(settings_obj=settings(INDEXNOW_KEY="../../evil"))

    async def test_google_search_console_file_is_exact_public_root_file(self):
        response = await self.client.get("/" + GOOGLE_VERIFICATION_FILENAME)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"google-site-verification: google4575dc78c69e5824.html")
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
        self.assertNotIn("noindex", response.headers.get("x-robots-tag", "").lower())
        self.assertNotIn("authorization", response.headers)

    def test_config_and_attribution_safety(self):
        for bad in ("http://example.com", "https://user:pass@example.com", "https://example.com/a", "https://example.com/?x=1"):
            with self.assertRaises(ValueError):
                public_origin(settings(PUBLIC_SITE_URL=bad))
        self.assertEqual(public_origin(settings(PUBLIC_SITE_URL="", MINI_APP_BASE_URL=ORIGIN + "/course-v3.html")), ORIGIN)
        self.assertEqual(attribution({"token": "secret", "utm_source": "x" * 1000}), {"utm_source": "x" * 80})
        self.assertNotIn("\n", attribution({"source": "bad\nlog"})["source"])

    def test_main_wires_router_without_changing_health(self):
        from pathlib import Path
        import ast
        tree = ast.parse(Path("app/main.py").read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertEqual(sum(isinstance(n.func, ast.Name) and n.func.id == "create_public_site_router" for n in calls), 1)


class IndexNowSubmissionTests(unittest.TestCase):
    def test_dry_run_never_creates_network_client_or_prints_key(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        from scripts.submit_indexnow import main
        output = StringIO()
        cfg = settings(INDEXNOW_KEY="test-key-12345678")
        with patch("scripts.submit_indexnow.Settings", return_value=cfg), patch("sys.argv", ["submit_indexnow"]), \
                patch("scripts.submit_indexnow.httpx.Client") as client, redirect_stdout(output):
            main()
        client.assert_not_called()
        self.assertNotIn(cfg.INDEXNOW_KEY, output.getvalue())
        self.assertIn(ORIGIN + "/tj/", output.getvalue())

    def test_submission_checks_ownership_and_posts_only_inventory(self):
        from unittest.mock import patch
        from scripts.submit_indexnow import main
        cfg = settings(INDEXNOW_KEY="test-key-12345678")
        with patch("scripts.submit_indexnow.Settings", return_value=cfg), patch("sys.argv", ["submit_indexnow", "--submit"]), \
                patch("scripts.submit_indexnow.httpx.Client") as factory:
            client = factory.return_value.__enter__.return_value
            client.get.return_value.status_code = 200
            client.get.return_value.text = "wrong-key"
            with self.assertRaises(ValueError):
                main()
            client.post.assert_not_called()
            client.get.return_value.text = cfg.INDEXNOW_KEY
            client.post.return_value.status_code = 202
            main()
            factory.assert_called_with(timeout=15, follow_redirects=False)
            client.post.assert_called_once_with("https://api.indexnow.org/indexnow", json=indexnow_payload(cfg))
