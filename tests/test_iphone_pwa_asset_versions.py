"""The learner PWA worker serves `?v=` assets Cache First.

A PWA asset whose bytes change while its `?v=` token stays the same would be
served stale from the worker cache indefinitely. Every reference to an
`iphone-pwa-*` asset must therefore carry its own content hash.
Run: python -m unittest tests.test_iphone_pwa_asset_versions
"""
import re
import unittest
from pathlib import Path

from scripts.i18n_baseline_guard import git_blob_sha1

STATIC = Path("app/static")


class IphonePwaAssetVersionTests(unittest.TestCase):
    def test_every_pwa_asset_reference_is_content_addressed(self):
        assets = sorted(p for p in (STATIC / "course_v3_data").glob("iphone-pwa-*")
                        if p.suffix in {".js", ".css"})
        self.assertTrue(assets)
        pages = {page: page.read_text(encoding="utf-8") for page in STATIC.rglob("*.html")}
        for asset in assets:
            rel = asset.relative_to(STATIC).as_posix()
            digest = git_blob_sha1(asset.read_bytes())[:12]
            pattern = re.compile(r'["\']/?' + re.escape(rel) + r'(\?v=[A-Za-z0-9_.\-]+)?["\']')
            for page, text in pages.items():
                for match in pattern.finditer(text):
                    with self.subTest(asset=rel, page=page.name):
                        token = match.group(1) or ""
                        self.assertTrue(token.endswith("-" + digest),
                                        f"{rel} changed: refresh ?v= to <date>-{digest}")

    def test_every_pwa_asset_is_served_by_the_app_route(self):
        # Regression: /course_v3_data/{filename} serves an allowlist only, so a
        # new iphone-pwa-* file that is not listed 404s in production.
        main = Path("app/main.py").read_text(encoding="utf-8")
        for asset in sorted((STATIC / "course_v3_data").glob("iphone-pwa-*")):
            if asset.suffix in {".js", ".css"}:
                with self.subTest(asset=asset.name):
                    self.assertIn(f'"{asset.name}":', main)

    def test_ios_launch_images_exist_for_every_declared_size(self):
        login = (STATIC / "iphone-pwa-login.html").read_text(encoding="utf-8")
        refs = re.findall(r'apple-touch-startup-image" media="[^"]+" href="/assets/startup/([^"]+)"', login)
        self.assertEqual(len(refs), 11)
        for name in refs:
            with self.subTest(image=name):
                self.assertTrue((STATIC / "assets/startup" / name).is_file())
                self.assertRegex(name, r"^hsk-startup-[0-9]{3,4}x[0-9]{4}\.png$")

    def test_worker_caches_only_versioned_same_origin_assets(self):
        worker = (STATIC / "iphone-pwa-sw.js").read_text(encoding="utf-8")
        self.assertIn('url.searchParams.has("v")', worker)
        self.assertIn("url.origin === self.location.origin", worker)
        self.assertIn('url.pathname.indexOf("/api/") !== 0', worker)
        self.assertIn('url.pathname.indexOf("/iphone-pwa") !== 0', worker)
        self.assertIn("return fetch(request);", worker)


if __name__ == "__main__":
    unittest.main()
