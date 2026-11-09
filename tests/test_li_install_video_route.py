"""Serve the real approved Safari MP4 with HTTP Range support.

The display guide's disabled/missing-media fallback is covered by the browser
E2E suite; this exercises the actual FastAPI route and the committed bytes.
"""
import hashlib
import unittest
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import app

MP4 = Path("app/static/assets/onboarding/iphone-home-screen.mp4")
SHA256 = "3e099a0c0489d9f0dc3e358490f5d87f2682462204eac7668b557c918874d15e"


class SafariInstallVideoRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_supplied_focus_hero_is_served_from_fixed_public_path(self):
        image = Path("app/static/assets/onboarding/iphone-install-home-focus.jpg")
        self.assertTrue(image.is_file())
        data = image.read_bytes()
        self.assertEqual(len(data), 164899)
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            "17848fda4d9cbdf9655cd407c10efa0e5b6ae7fcf6b59132f47314134c553428",
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://hsk.test"
        ) as client:
            response = await client.get(
                "/assets/onboarding/iphone-install-home-focus.jpg"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.content, data)

    async def test_real_video_metadata_and_partial_content_on_slow_connections(self):
        self.assertTrue(MP4.is_file(), "Approved install video must exist on this branch")
        video = MP4.read_bytes()
        self.assertEqual(hashlib.sha256(video).hexdigest(), SHA256)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://hsk.test",
        ) as client:
            for start, end in ((0, 127), (1024, 2047), (len(video) - 512, len(video) - 1)):
                with self.subTest(start=start):
                    response = await client.get(
                        "/assets/onboarding/iphone-home-screen.mp4",
                        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "gzip"},
                    )
                    self.assertEqual(response.status_code, 206, response.text[:200])
                    self.assertTrue(response.headers["content-type"].startswith("video/mp4"))
                    self.assertEqual(response.headers["accept-ranges"], "bytes")
                    # Starlette's global gzip middleware must not transform
                    # compressed MP4 range bytes, even for gzip-capable peers.
                    self.assertEqual(response.headers.get("content-encoding"), "identity")
                    self.assertIn("no-transform", response.headers["cache-control"])
                    self.assertEqual(
                        response.headers["content-range"],
                        f"bytes {start}-{end}/{len(video)}",
                    )
                    self.assertEqual(response.content, video[start:end + 1])
            entire = await client.get("/assets/onboarding/iphone-home-screen.mp4", headers={"Accept-Encoding":"gzip"})
            self.assertEqual(entire.status_code, 200)
            self.assertEqual(len(entire.content), 574244)
            self.assertEqual(entire.content, video)
            self.assertEqual(entire.headers.get("x-content-type-options"), "nosniff")
            self.assertEqual(entire.headers.get("content-encoding"), "identity")
