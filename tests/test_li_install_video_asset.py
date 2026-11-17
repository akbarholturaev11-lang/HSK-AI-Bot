"""Validate the optional iPhone Safari tutorial MP4 when it is actually present.

The repository keeps a canonical accessible textual guide until this optional
asset is published. A missing video is intentional, not an empty user screen.
"""
from pathlib import Path
import hashlib
import unittest

PATH = Path("app/static/assets/onboarding/iphone-home-screen.mp4")
SHA256 = "3e099a0c0489d9f0dc3e358490f5d87f2682462204eac7668b557c918874d15e"


class PwaInstallVideoAssetTests(unittest.TestCase):
    def test_published_video_is_small_safari_faststart_and_exact_approved_asset(self):
        if not PATH.exists():
            self.skipTest("Optimized user video not yet committed; in-app text fallback is active")
        data = PATH.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), SHA256)
        self.assertLess(len(data), 1_000_000, "Video should remain below 1 MB")
        self.assertEqual(data[4:8], b"ftyp")
        moov = data.find(b"moov")
        mdat = data.find(b"mdat")
        self.assertGreater(moov, 0)
        self.assertGreater(mdat, moov, "faststart required: moov before mdat")
