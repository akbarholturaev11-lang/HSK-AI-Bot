import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.public_site import (
    GOOGLE_VERIFICATION_FILENAME,
    SITEMAP_PATHS,
    create_public_site_router,
    indexnow_payload,
)
from app.public_site.content import DOWNLOAD_PATH, GOOGLE_SIGNIN_PRIVACY_PAGES, HOME_PATHS, PAGE_TRANSLATIONS, PAGES
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

    async def test_railway_host_moves_only_public_html_to_official_domain(self):
        from app.api.public_site import (
            LEGACY_RAILWAY_PUBLIC_HOST, legacy_public_site_redirect,
        )
        from fastapi import Request
        from starlette.requests import Request as StarletteRequest

        assert Request is StarletteRequest
        official = "https://hskai.app"
        old = "https://" + LEGACY_RAILWAY_PUBLIC_HOST
        app = FastAPI()
        app.include_router(create_public_site_router(
            settings_obj=settings(PUBLIC_SITE_URL=official)
        ))
        @app.get("/api/private-probe")
        async def private_probe():
            return {"safe": True}

        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url=official, follow_redirects=False) as client:
            # Every existing language/guide page, public privacy and legal page
            # gets an exact-path 301; no unexpected home-page catch-all.
            paths = tuple(PAGES) + tuple(GOOGLE_SIGNIN_PRIVACY_PAGES) + (
                "/privacy", "/terms", "/account-deletion",
            )
            for path in paths:
                moved = await client.get(old + path)
                self.assertEqual(moved.status_code, 301, path)
                self.assertEqual(moved.headers["location"], official + path)
                self.assertEqual(moved.headers["cache-control"], "public, max-age=300")
                original = await client.get(official + path)
                self.assertEqual(original.status_code, 200, path)

            # Critical service endpoints, ownership checks and crawler discovery
            # must stay on the old host; never redirect the whole Railway domain.
            for path in (
                "/robots.txt", "/sitemap.xml", "/llms.txt",
                "/google4575dc78c69e5824.html", "/public-assets/logo.png",
            ):
                response = await client.get(old + path)
                self.assertEqual(response.status_code, 200, path)
                self.assertNotIn("location", response.headers)
            self.assertEqual((await client.get(old + "/api/private-probe")).json(),
                             {"safe": True})
            self.assertEqual((await client.get(old + "/unknown-private-path")).status_code, 404)
            self.assertEqual((await client.get(official + "/ru/")).status_code, 200)
            # Referral campaign tag remains, arbitrary auth token does not.
            forwarded = await client.get(old + "/ru/?utm_source=organic&token=secret")
            self.assertEqual(forwarded.headers["location"],
                             official + "/ru/?utm_source=organic")

        # The download route is owned by main.py, so test the shared pure guard
        # without initializing Telegram polling, OAuth or the database.
        def request_for(path, query=b""):
            return StarletteRequest({
                "type": "http", "method": "GET", "scheme": "https",
                "path": path, "raw_path": path.encode(), "query_string": query,
                "headers": [(b"host", LEGACY_RAILWAY_PUBLIC_HOST.encode())],
                "server": (LEGACY_RAILWAY_PUBLIC_HOST, 443),
                "client": ("127.0.0.1", 9000),
            })
        for path in ("/download", "/apps", "/desktop-download",
                     "/desktop-download.html"):
            redirect = legacy_public_site_redirect(
                request_for(path, b"lang=uz&utm_campaign=seo&token=private"),
                official,
            )
            self.assertEqual(redirect.status_code, 301)
            self.assertEqual(
                redirect.headers["location"],
                official + path + "?utm_campaign=seo&lang=uz",
            )
        for path in ("/api/v3/apps/public-status", "/iphone-pwa",
                     "/api/account-deletion/status", "/webhook"):
            self.assertIsNone(legacy_public_site_redirect(request_for(path), official))
        self.assertIsNone(legacy_public_site_redirect(
            request_for("/"), "https://unrelated.example"
        ))
        self.assertIn(
            "legacy_public_site_redirect(request, public_origin(settings))",
            Path("app/main.py").read_text(encoding="utf-8"),
        )

    async def test_account_deletion_request_is_accessible_outside_app(self):
        page = await self.client.get("/account-deletion")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Request deletion of your HSK AI account", page.text)
        self.assertIn("https://t.me/darsi_chini_bot?start=account_deletion", page.text)
        self.assertIn("Request deletion", page.text)
        self.assertIn('data-provider="google"', page.text)
        self.assertIn('data-provider="apple"', page.text)
        self.assertIn('data-provider="telegram"', page.text)
        self.assertIn("JavaScript is needed for Google or Apple verification", page.text)
        self.assertIn("within 30 days", page.text)
        self.assertIn("Approved payment records", page.text)
        self.assertIn("Pending and rejected payment records", page.text)
        self.assertIn("partner payout evidence, payout details and ledger notes", page.text)
        self.assertIn("Completion status is retained for 30 days after processing", page.text)
        self.assertIn("Check request status", page.text)
        self.assertIn("does not cancel automatic renewal", page.text)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(page.headers["referrer-policy"], "no-referrer")
        self.assertIn("frame-ancestors 'none'", page.headers["content-security-policy"])
        self.assertNotIn("telegram-web-app.js", page.text)
        self.assertIn("/account-deletion", (await self.client.get("/privacy")).text)
        self.assertIn("/account-deletion", SITEMAP_PATHS)

    async def test_account_deletion_script_is_public_without_auth_or_database(self):
        script = await self.client.get("/public-assets/account-deletion.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("javascript", script.headers["content-type"])
        self.assertIn("/api/account-deletion/", script.text)
        self.assertNotIn("localStorage", script.text)
        self.assertNotIn("sessionStorage", script.text)
        self.assertNotIn("Authorization", script.text)
        self.assertNotIn("Bearer", script.text)
        self.assertEqual((await self.client.get("/public-assets/not-public.js")).status_code, 404)

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
            self.assertEqual(parsed.find("meta", name="robots")[0]["content"], "index,follow")
            self.assertIn("HSK AI", html)
            self.assertIn("darsi_chini_bot", html)
            if page.get("translation_group") == "hsk":
                self.assertIn("HSK 1", html)
            self.assertNotIn("telegram-web-app.js", html)
            self.assertEqual(parsed.find("html")[0]["lang"], page["lang"])
            for prop in ("og:title", "og:description", "og:type", "og:url", "og:image"):
                self.assertTrue(parsed.find("meta", property=prop))
            self.assertEqual(parsed.find("meta", name="twitter:card")[0]["content"], "summary_large_image")
            expected = PAGE_TRANSLATIONS.get(
                page.get("translation_group"),
                {page["lang"]: path},
            )
            self.assertEqual(
                {t["hreflang"]: t["href"] for t in parsed.find("link", rel="alternate") if "hreflang" in t},
                {lang: ORIGIN + p for lang, p in expected.items()},
            )
            graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])["@graph"]
            self.assertTrue({"Organization", "WebSite", "SoftwareApplication", "WebPage"}.issubset({n["@type"] for n in graph}))
            website = next(n for n in graph if n["@type"] == "WebSite")
            self.assertEqual(website["name"], "HSK AI")
            self.assertEqual(website["url"], ORIGIN + "/")
            self.assertEqual(
                website["alternateName"],
                ["HSKAI", "HSK-AI", "HSK Ai", "HSK AI App", "hskai.app"],
            )
            org = next(n for n in graph if n["@type"] == "Organization")
            self.assertEqual(org["alternateName"], website["alternateName"])
            application = next(n for n in graph if n["@type"] == "SoftwareApplication")
            self.assertEqual(application["url"], ORIGIN + "/")
            self.assertEqual(
                application["alternateName"],
                ["HSKAI", "HSK-AI", "HSK Ai", "HSK AI App"],
            )
            self.assertTrue(parsed.find("a", **{"class": "footer-brand", "href": "/"}))
            self.assertFalse(any("aggregateRating" in n or "review" in n for n in graph))
            if path == "/tj/hsk/":
                self.assertEqual([n["name"] for n in graph if n["@type"] == "Course"], [f"HSK {i}" for i in range(1, 5)])
                for i in range(1, 5):
                    self.assertTrue(parsed.find("section", id=f"hsk{i}"))
            if path == "/":
                self.assertTrue(parsed.find("a", **{"class": "secondary-cta"}))
                self.assertIn(DOWNLOAD_PATH, html)
            titles.add(page["title"])
            descriptions.add(page["description"])
        self.assertEqual(len(titles), len(PAGES))
        self.assertEqual(len(descriptions), len(PAGES))

    async def test_branded_homepage_is_distinct_and_canonical(self):
        home = await self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertEqual(Tags(home.text).find("html")[0]["lang"], "ru")
        self.assertIn("HSK AI — официальный сайт приложения", home.text)
        self.assertIn("Это самостоятельный образовательный продукт", home.text)
        self.assertIn('rel="canonical" href="' + ORIGIN + '/"', home.text)
        self.assertNotIn("telegram-chinese-bot-production.up.railway.app", home.text)
        site = json.loads(re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            home.text, re.S,
        )[1])["@graph"]
        self.assertEqual(next(x for x in site if x["@type"] == "WebSite")["url"], ORIGIN + "/")

    async def test_product_first_header_language_and_download_contract(self):
        # Content remains crawlable without JavaScript, with one URL per locale.
        for language, url_code in (("tg", "tj"), ("ru", "ru"), ("uz", "uz")):
            response = await self.client.get(HOME_PATHS[language] + "?utm_source=instagram")
            html = response.text
            self.assertIn('class="course-cta"', html)
            self.assertIn('class="product-summary"', html)
            self.assertIn('<details class="language-switch">', html)
            self.assertIn('data-site-nav="features"', html)
            self.assertIn('data-site-nav="download"', html)
            self.assertIn("lang=" + url_code, html)
            self.assertIn("/download?lang=" + url_code, html)
            self.assertIn("utm_source=instagram", html)
            self.assertNotIn('class="example"', html)
            self.assertIn('/public-assets/language.js', html)
        # Shared header is present on the existing installer page as well.
        download = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        self.assertIn('data-site-nav="courses"', download)
        self.assertIn('data-site-nav="features"', download)
        self.assertIn('data-site-selected-lang', download)
        self.assertIn('/public-assets/navigation.css', download)
        self.assertIn('/public-assets/language.js', download)
        script = Path("app/static/desktop-download-page.js").read_text(encoding="utf-8")
        self.assertIn("HSKSiteLanguage.get()", script)
        self.assertIn("HSKSiteLanguage.set(state.language)", script)
        self.assertIn('nextUrl.searchParams.set("lang", language)', script)

    async def test_sitemap_and_robots_private_boundaries(self):
        response = await self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        urls = ElementTree.fromstring(response.content).findall("{*}url/{*}loc")
        self.assertEqual([u.text for u in urls], [ORIGIN + path for path in SITEMAP_PATHS])
        self.assertNotIn("lastmod", response.text)
        robots = await self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn(f"Sitemap: {ORIGIN}/sitemap.xml", robots.text)
        for agent in ("*", "Googlebot", "Bingbot", "OAI-SearchBot"):
            for path in PAGES:
                self.assertTrue(allowed(robots.text, agent, path))
                self.assertTrue(allowed(robots.text, agent, path + "?utm_source=x"))
            for path in GOOGLE_SIGNIN_PRIVACY_PAGES:
                self.assertTrue(allowed(robots.text, agent, path))
                self.assertTrue(allowed(robots.text, agent, path + "?utm_source=x"))
            self.assertTrue(allowed(robots.text, agent, DOWNLOAD_PATH))
            self.assertTrue(allowed(robots.text, agent, DOWNLOAD_PATH + "?lang=uz"))
            for path in ("/admin.html", "/api/v3/map", "/subscription.html", "/payments/x", "/course-v3.html",
                         "/course-v3", "/course_v3_data/hsk1.json", "/uploads/private", "/docs", "/openapi.json",
                         "/go/telegram", "/tj/private", "/future-private"):
                self.assertFalse(allowed(robots.text, agent, path), (agent, path))
            self.assertTrue(allowed(robots.text, agent, "/public-assets/site.css"))
            self.assertTrue(allowed(robots.text, agent, "/desktop-download?lang=uz"))
            self.assertTrue(allowed(robots.text, agent, "/desktop-download.html"))
            self.assertTrue(allowed(robots.text, agent, "/assets/hsk-ai-cover.webp"))
            self.assertTrue(allowed(robots.text, agent, "/google4575dc78c69e5824.html"))
            self.assertTrue(allowed(robots.text, agent, "/account-deletion"))

        verification = await self.client.get("/google4575dc78c69e5824.html")
        self.assertEqual(verification.status_code, 200)
        self.assertEqual(
            verification.text,
            "google-site-verification: google4575dc78c69e5824.html",
        )

    async def test_hsk_ai_brand_identity_and_verified_official_links(self):
        from app.public_site.render import BOT_URL, NEWS_URL, SUPPORT_URL, OFFICIAL_SOCIAL_LINKS

        for path in ("/", "/tj/", "/ru/", "/uz/"):
            page = await self.client.get(path)
            self.assertEqual(page.status_code, 200)
            self.assertTrue(PAGES[path]["title"].startswith("HSK AI"), path)
            self.assertTrue(PAGES[path]["h1"].startswith("HSK AI"), path)
            self.assertIn('name="application-name" content="HSK AI"', page.text)
            self.assertIn('class="official-footer-links"', page.text)
            self.assertIn(SUPPORT_URL, page.text)
            self.assertIn(NEWS_URL, page.text)
            self.assertIn("/iphone-pwa", page.text)
            graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page.text, re.S)[1])["@graph"]
            org = next(node for node in graph if node["@type"] == "Organization")
            self.assertEqual(org["name"], "HSK AI")
            self.assertIn(BOT_URL, org["sameAs"])
            self.assertIn(NEWS_URL, org["sameAs"])
            self.assertEqual({url for _, url in OFFICIAL_SOCIAL_LINKS},
                             set(org["sameAs"]) - {BOT_URL})
            self.assertEqual(org["contactPoint"][0]["url"], SUPPORT_URL)

        for path in ("/tj/guide/faq/", "/ru/guide/faq/", "/uz/guide/faq/"):
            page = await self.client.get(path)
            self.assertIn("HSK AI", page.text)
            self.assertIn(SUPPORT_URL, page.text)
        download_source = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        self.assertIn('class="official-footer-links"', download_source)
        self.assertIn(SUPPORT_URL, download_source)
        self.assertIn(NEWS_URL, download_source)
        self.assertIn("https://facebook.com/1159152280609531", download_source)
        privacy = await self.client.get("/privacy")
        self.assertIn(SUPPORT_URL, privacy.text)
        self.assertNotIn('href="' + BOT_URL + '"', privacy.text)

    async def test_every_legal_and_account_page_is_linked(self):
        legal_paths = ("/privacy", "/privacy#security", "/terms", "/account-deletion")
        google_by_lang = {
            "/": "/privacy/google-sign-in/ru/",
            "/tj/": "/privacy/google-sign-in/tj/",
            "/ru/": "/privacy/google-sign-in/ru/",
            "/uz/": "/privacy/google-sign-in/uz/",
        }
        for path, google in google_by_lang.items():
            response = await self.client.get(path)
            self.assertEqual(response.status_code, 200)
            for expected in (*legal_paths, google):
                with self.subTest(page=path, legal=expected):
                    self.assertIn(f'href="{expected}"', response.text)

        download = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        for expected in (*legal_paths, "/privacy/google-sign-in/"):
            self.assertIn(f'href="{expected}"', download)

        privacy = await self.client.get("/privacy")
        self.assertEqual(privacy.status_code, 200)
        self.assertIn('<h2 id="security">Security</h2>', privacy.text)
        terms = await self.client.get("/terms")
        deletion = await self.client.get("/account-deletion")
        self.assertEqual(terms.status_code, 200)
        self.assertEqual(deletion.status_code, 200)
        for page in (privacy, terms, deletion):
            for expected in ("/privacy", "/privacy#security", "/privacy/google-sign-in/", "https://t.me/hskai_support_bot"):
                with self.subTest(url=page.url.path, link=expected):
                    self.assertIn(f'href="{expected}"', page.text)
        self.assertIn("/terms", SITEMAP_PATHS)
        sitemap = await self.client.get("/sitemap.xml")
        self.assertIn(f"<loc>{ORIGIN}/terms</loc>", sitemap.text)

    async def test_russian_first_visit_and_ai_readable_public_inventory(self):
        default = await self.client.get("/")
        self.assertEqual(default.status_code, 200)
        self.assertEqual(default.headers["content-language"], "ru")
        self.assertEqual(Tags(default.text).find("html")[0]["lang"], "ru")
        self.assertIn("HSK AI — официальный сайт приложения", default.text)
        self.assertIn('<link rel="canonical" href="' + ORIGIN + '/">', default.text)
        self.assertIn('href="/llms.txt"', default.text)
        self.assertIn("Удаление аккаунта", default.text)
        self.assertIn("Конфиденциальность", default.text)

        for path, lang in (("/tj/", "tg"), ("/ru/", "ru"), ("/uz/", "uz")):
            response = await self.client.get(path)
            self.assertEqual(response.headers["content-language"], lang)
            self.assertIn("<h1>", response.text)
            self.assertIn('<nav class="official-footer-links"', response.text)

        policy = await self.client.get("/privacy/google-sign-in/")
        self.assertEqual(policy.headers["content-language"], "ru")
        self.assertIn("Вход через Google", policy.text)
        uz_policy = await self.client.get("/privacy/google-sign-in/uz/")
        self.assertEqual(uz_policy.headers["content-language"], "uz")
        self.assertIn("Google bilan kirish", uz_policy.text)

        inventory = await self.client.get("/llms.txt")
        self.assertEqual(inventory.status_code, 200)
        self.assertTrue(inventory.headers["content-type"].startswith("text/plain"))
        for expected in ("/ru/", "/tj/", "/uz/", "/download", "/privacy",
                         "/account-deletion", "/terms", "/privacy/google-sign-in/",
                         "https://t.me/hskai_support_bot"):
            self.assertIn(expected, inventory.text)
        for denied in ("telegram_user_id", "BOT_TOKEN", "/api/admin/"):
            self.assertNotIn(denied, inventory.text)
        robots = (await self.client.get("/robots.txt")).text
        self.assertTrue(allowed(robots, "OAI-SearchBot", "/llms.txt"))
        self.assertFalse(allowed(robots, "OAI-SearchBot", "/course-v3.html"))

        download_source = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ru">', download_source)
        self.assertIn('href="/download?lang=ru"', download_source)
        self.assertIn("Скачать HSK AI", download_source)
        self.assertIn('href="/llms.txt"', download_source)
        shared = Path("app/static/public-site-language.js").read_text(encoding="utf-8")
        self.assertIn('updateLinks(current || read() || "ru")', shared)
        installer = Path("app/static/desktop-download-page.js").read_text(encoding="utf-8")
        self.assertIn('return "ru";', installer)

    def test_public_download_has_absolute_russian_hreflang(self):
        # Test the pure metadata helper without importing app.main or touching
        # Telegram, the database, Railway or an application startup hook.
        import ast

        main_source = Path("app/main.py").read_text(encoding="utf-8")
        helper = next(
            item for item in ast.parse(main_source).body
            if isinstance(item, ast.FunctionDef)
            and item.name == "_absolute_download_seo_urls"
        )
        namespace = {}
        exec(compile(ast.Module(body=[helper], type_ignores=[]),
                     "app/main.py", "exec"), namespace)

        html = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="alternate" hreflang="ru" href="/download">', html)
        rendered = namespace["_absolute_download_seo_urls"](html, "https://hskai.app")
        for metadata in (
            '<link rel="canonical" href="https://hskai.app/download">',
            '<link rel="alternate" hreflang="ru" href="https://hskai.app/download">',
            '<meta property="og:url" content="https://hskai.app/download">',
        ):
            self.assertIn(metadata, rendered)
        self.assertNotIn('hreflang="uz" href="/download"', rendered)

    async def test_r2_confirmed_standard_prices_and_limits_are_public(self):
        # R2 hsk-ai-support-kb/knowledge/subscriptions.json, owner-verified
        # 2026-11-07. Publish standard data, not a guaranteed user checkout quote.
        standard_prices = (
            "3.15", "7.49", "19.44", "¥19", "¥49", "¥149",
            "7.90", "19.00", "34.90", "64.90",
        )
        for lang in ("ru", "tj", "uz"):
            with self.subTest(language=lang):
                guide = await self.client.get(f"/{lang}/guide/subscription/")
                faq = await self.client.get(f"/{lang}/guide/faq/")
                self.assertEqual(guide.status_code, 200)
                self.assertEqual(faq.status_code, 200)
                for html in (guide.text, faq.text):
                    for price in standard_prices:
                        self.assertIn(price, html)
                    self.assertIn("1.50", html)
                    self.assertIn("2026", html)
                    self.assertIn("5", html)
                    self.assertIn("20", html)
                    self.assertIn("Google Play", html)
                # The FAQ's standard prices are real source data, not placeholders.
                self.assertNotIn("Не используйте цену с этой страницы", faq.text)
                self.assertNotIn("не считайте их безлимитными", guide.text)
                self.assertNotIn("avtomatik tarzda cheksiz hisoblanmaydi", guide.text)
                self.assertNotIn("худкор бемаҳдуд нестанд", guide.text)
                self.assertNotIn("Bu sahifadagi matnni joriy narx deb qabul qilmang", faq.text)
                self.assertNotIn("Нархи дар ин саҳифа навишташуда ҳисобида нашавад", faq.text)

        index = await self.client.get("/llms.txt")
        self.assertEqual(index.status_code, 200)
        self.assertIn("## Стандартные цены Pro", index.text)
        self.assertIn("Основное название бренда: HSK AI", index.text)
        for spelling in ("HSKAI", "HSK-AI", "HSK Ai", "HSK AI App", "hskai.app"):
            self.assertIn(spelling, index.text)
        self.assertIn("## Стандартные лимиты Free", index.text)
        self.assertIn("## Pro Trial и ограничения", index.text)
        self.assertIn("USD 1.50", index.text)
        self.assertIn("все прочие квоты действий Trial безлимитны", index.text)
        for price in standard_prices:
            self.assertIn(price, index.text)

    async def test_play_pro_help_prefers_browser_pwa_without_reinstall(self):
        # The user-facing guidance and the AI-readable source must agree.
        cases = {
            "tg": ("/tj/guide/subscription/", "/tj/guide/faq/",
                   "Обуна дар браузер (PWA)", "насб кардан"),
            "ru": ("/ru/guide/subscription/", "/ru/guide/faq/",
                   "Оформить Pro в браузере (PWA)", "устанавливать APK"),
            "uz": ("/uz/guide/subscription/", "/uz/guide/faq/",
                   "Brauzerda Pro olish (PWA)", "APK o‘rnatish"),
        }
        for lang, (guide_path, faq_path, label, no_install) in cases.items():
            with self.subTest(locale=lang):
                guide = await self.client.get(guide_path)
                faq = await self.client.get(faq_path)
                self.assertEqual(guide.status_code, 200)
                self.assertEqual(faq.status_code, 200)
                for html in (guide.text, faq.text):
                    self.assertIn("https://hskai.app/iphone-pwa", html)
                    self.assertIn("Google Play", html)
                    self.assertIn(no_install, html)
                self.assertIn(
                    f'<a class="pwa-subscription-link" href="/iphone-pwa">{label}</a>',
                    guide.text,
                )
                self.assertEqual(
                    len(Tags(guide.text).find("a", **{"class": "pwa-subscription-link"})), 1
                )

        ai_index = await self.client.get("/llms.txt")
        self.assertEqual(ai_index.status_code, 200)
        self.assertIn("## Как купить Pro, если в Google Play закончился лимит", ai_index.text)
        self.assertIn("https://hskai.app/iphone-pwa", ai_index.text.replace(ORIGIN, "https://hskai.app"))
        self.assertIn("добавлять PWA на главный экран не нужно", ai_index.text)
        self.assertIn("Удалять приложение из Google Play", ai_index.text)

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
        for path in ("site.css", "navigation.css", "language.js", "avatar.webp", "logo.png", "social-cover.webp"):
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
        self.assertEqual(payload["urlList"], [ORIGIN + p for p in SITEMAP_PATHS])
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

    async def test_google_signin_privacy_pages_are_public_and_descriptive(self):
        for path, page in GOOGLE_SIGNIN_PRIVACY_PAGES.items():
            response = await self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            parsed = Tags(response.text)
            self.assertEqual(parsed.find("html")[0]["lang"], page["lang"])
            self.assertEqual(parsed.find("link", rel="canonical")[0]["href"], ORIGIN + path)
            self.assertIn(page["h1"], response.text)
            self.assertIn("Google", response.text)
            self.assertNotIn("telegram-web-app.js", response.text)
            self.assertEqual(response.headers["content-language"], page["lang"])

    async def test_android_privacy_policy_is_public_and_review_ready(self):
        response = await self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/html"))
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertNotIn("noindex", response.headers.get("x-robots-tag", "").lower())
        self.assertNotIn("authorization", response.headers)
        self.assertIn("HSK AI Privacy Policy", response.text)
        self.assertIn("Pomp HSK AI", response.text)
        self.assertIn("hskaiapp@gmail.com", response.text)
        for section in (
            "Information we collect and use",
            "Microphone, photos and notifications",
            "Service providers and sharing",
            "Security",
            "Retention and deletion",
            "Your choices and questions",
        ):
            self.assertIn(section, response.text)
        for disclosure in (
            "Google or Apple can create an account without Telegram",
            "Learning activity",
            "AI, images and speech",
            "Firebase Cloud Messaging",
            "30 days",
            "Approved payment and accounting records",
            'href="/account-deletion"',
        ):
            self.assertIn(disclosure, response.text)
        self.assertNotIn("telegram-web-app.js", response.text)
        self.assertIn("/privacy", SITEMAP_PATHS)

    async def test_account_and_purchase_guides_cover_provider_only_accounts(self):
        for locale in ("uz", "ru", "tj"):
            response = await self.client.get(f"/{locale}/guide/subscription/")
            self.assertEqual(response.status_code, 200)
            for name in ("Google", "Apple", "HSK 3.0", "Google Play", "Android", "desktop"):
                self.assertIn(name, response.text)
        policy = (await self.client.get("/privacy")).text
        terms = (await self.client.get("/terms")).text
        self.assertIn("Google or Apple can create an account without Telegram", policy)
        self.assertIn("Payments and invitations", policy)
        self.assertIn("while another remains available", policy)
        self.assertIn("independently of its sign-in method", terms)
        self.assertIn("current Google Play app has no purchase flow", terms)

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
