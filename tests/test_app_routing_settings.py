"""Google Play destination: only our own listing, one stored form."""
import json
import unittest

from app.services.desktop_app_promo_settings_service import (
    ANDROID_PLAY_URL,
    DesktopAppPromoSettings,
    normalize_android_play_url,
)


class AndroidPlayUrlTests(unittest.TestCase):
    def test_official_listing_is_canonicalised(self):
        for value in (
            ANDROID_PLAY_URL,
            "  " + ANDROID_PLAY_URL + "  ",
            ANDROID_PLAY_URL + "&hl=ru&pli=1",
            "https://play.google.com/store/apps/details?hl=uz&id=com.pomp.hskai",
        ):
            self.assertEqual(normalize_android_play_url(value), ANDROID_PLAY_URL, value)

    def test_empty_means_not_configured(self):
        for value in (None, "", "   "):
            self.assertEqual(normalize_android_play_url(value), "")

    def test_everything_else_is_refused(self):
        for value in (
            "http://play.google.com/store/apps/details?id=com.pomp.hskai",
            "https://play.google.com/store/apps/details?id=com.other.app",
            "https://play.google.com/store/apps/details",
            "https://play.google.com/store/apps/details?id=com.pomp.hskai&id=com.other",
            "https://play.google.com/store/apps/details/?id=com.pomp.hskai",
            "https://play.google.com/store/apps/dev?id=com.pomp.hskai",
            "https://play.google.com.evil.example/store/apps/details?id=com.pomp.hskai",
            "https://evil.example/store/apps/details?id=com.pomp.hskai",
            "https://user:pw@play.google.com/store/apps/details?id=com.pomp.hskai",
            "https://play.google.com:8443/store/apps/details?id=com.pomp.hskai",
            "https://play.google.com/store/apps/details?id=com.pomp.hskai#x",
            "https://play.google.com/store/apps/details?id=com.pomp.hskai\nx",
            "https://play.google.com/store/apps/details?id=com.pomp.hskai x",
            "market://details?id=com.pomp.hskai",
            "javascript:alert(1)",
            "https://play.google.com:bad/store/apps/details?id=com.pomp.hskai",
            ANDROID_PLAY_URL + "&x=" + "a" * 600,
            123,
        ):
            self.assertIsNone(normalize_android_play_url(value), value)

    def test_default_and_legacy_rows_have_no_play_destination(self):
        self.assertEqual(DesktopAppPromoSettings.default().android_play_url, "")
        legacy = json.dumps({"enabled": True, "platforms": {"android": True}})
        self.assertEqual(DesktopAppPromoSettings.from_raw(legacy).android_play_url, "")
        # Existing Android/iPhone defaults are not touched by this field.
        self.assertTrue(DesktopAppPromoSettings.from_raw(legacy).platforms["android"])
        self.assertFalse(DesktopAppPromoSettings.default().platforms["ios"])

    def test_corrupt_stored_value_reads_as_not_configured(self):
        raw = json.dumps({"android_play_url": "https://evil.example/app"})
        self.assertEqual(DesktopAppPromoSettings.from_raw(raw).android_play_url, "")

    def test_partial_legacy_write_keeps_the_destination(self):
        current = DesktopAppPromoSettings.from_payload({"android_play_url": ANDROID_PLAY_URL})
        self.assertEqual(current.android_play_url, ANDROID_PLAY_URL)
        kept = DesktopAppPromoSettings.from_payload(
            {"media_type": None, "media_path": None}, previous=current)
        self.assertEqual(kept.android_play_url, ANDROID_PLAY_URL)
        toggled = DesktopAppPromoSettings.from_payload({"enabled": False}, previous=current)
        self.assertEqual(toggled.android_play_url, ANDROID_PLAY_URL)
        cleared = DesktopAppPromoSettings.from_payload({"android_play_url": ""}, previous=current)
        self.assertEqual(cleared.android_play_url, "")
        refused = DesktopAppPromoSettings.from_payload(
            {"android_play_url": "https://evil.example"}, previous=current)
        self.assertEqual(refused.android_play_url, "")

    def test_round_trip_and_public_payload(self):
        settings = DesktopAppPromoSettings.from_payload({"android_play_url": ANDROID_PLAY_URL})
        again = DesktopAppPromoSettings.from_raw(settings.storage_value())
        self.assertEqual(again.android_play_url, ANDROID_PLAY_URL)
        self.assertEqual(again.payload()["android_play_url"], ANDROID_PLAY_URL)


if __name__ == "__main__":
    unittest.main()
