import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMO_JS = ROOT / "app" / "static" / "course_v3_data" / "desktop-download.js"
PROMO_CSS = ROOT / "app" / "static" / "course_v3_data" / "desktop-download.css"
PROFILE_ART = ROOT / "app" / "static" / "assets" / "hsk-ai-devices.jpg"


def _function_body(source: str, name: str) -> str:
    match = re.search(
        rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{",
        source,
    )
    if not match:
        raise AssertionError(f"function {name} not found")
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    if depth:
        raise AssertionError(f"function {name} is not balanced")
    return source[start : index - 1]


class AndroidContextualAppPromoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = PROMO_JS.read_text(encoding="utf-8")
        cls.css = PROMO_CSS.read_text(encoding="utf-8")

    def test_existing_automatic_placements_and_cooldown_are_unchanged(self):
        self.assertIn(
            'var PROMO_SOURCES = ["home_prompt", "lesson_end_promo", "ad_promo"];',
            self.js,
        )
        self.assertIn("var DEFAULT_PROMO_COOLDOWN_DAYS = 14;", self.js)

    def test_automatic_promos_require_current_client_to_match_target(self):
        gate = _function_body(self.js, "automaticTargetMatchesCurrentClient")
        self.assertIn('target === detectPlatform()', gate)
        self.assertIn("isPlatformTargeted(target)", gate)
        self.assertIn("isPlatformAvailable(target)", gate)

        modal_gate = _function_body(self.js, "shouldShowPromo")
        inline_gate = _function_body(self.js, "shouldShowAdPromoEntry")
        self.assertIn("automaticTargetMatchesCurrentClient()", modal_gate)
        self.assertIn("automaticTargetMatchesCurrentClient()", inline_gate)
        self.assertIn("!state.promoEligible", inline_gate)

    def test_android_context_copy_covers_requested_surfaces(self):
        for context in ("course", "mashq", "voice", "dictionary", "lesson_end"):
            self.assertRegex(
                self.js,
                rf"(?m)^\s{{6}}{context}:\s*\{{",
                msg=f"missing Android promo context: {context}",
            )
        self.assertIn("Xatoni shu zahoti tushuning", self.js)
        self.assertIn("Mashq ichida AI yordamchi", self.js)
        self.assertIn("To‘liq offline lug‘at", self.js)

    def test_android_copy_never_activates_for_ios_or_unknown_target(self):
        chooser = _function_body(self.js, "androidPromoCopy")
        self.assertIn('detectPlatform() !== "android"', chooser)
        self.assertIn('state.autoTargetPlatform !== "android"', chooser)

    def test_profile_card_remains_manual_and_uses_device_art(self):
        self.assertIn('var ENTRY_SOURCES = ["profile"].concat(PROMO_SOURCES);', self.js)
        profile = _function_body(self.js, "renderProfile")
        self.assertIn("buildProfileDeviceVisual()", profile)
        self.assertIn('buildActions("profile")', profile)
        self.assertIn('trackEntrySeen("profile"', profile)
        self.assertIn('seal.src = "/assets/hsk-ai-logo-256.png"', profile)
        self.assertNotIn("pdd-eyebrow", profile)
        self.assertNotIn("copy.cardBody", profile)
        self.assertNotIn("buildBenefits(true)", profile)
        visual = _function_body(self.js, "buildProfileDeviceVisual")
        self.assertIn('var source = "/assets/hsk-ai-devices.jpg"', visual)
        self.assertIn('image.src = source + "?retry=" + Date.now()', visual)
        self.assertIn('image.src = "/assets/hsk-ai-logo-256.png"', visual)
        self.assertIn('image.loading = "eager"', visual)
        self.assertIn('image.decoding = "async"', visual)
        self.assertIn(".pdd-profile-device-visual", self.css)
        self.assertIn("aspect-ratio: 3 / 2", self.css)
        self.assertIn("object-fit: contain", self.css)

    def test_profile_device_photo_has_a_served_jpeg_route(self):
        app_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/assets/hsk-ai-devices.jpg")', app_source)
        self.assertIn('"app/static/assets/hsk-ai-devices.jpg"', app_source)
        self.assertIn('"image/jpeg"', app_source)

    def test_profile_art_is_valid_jpeg(self):
        data = PROFILE_ART.read_bytes()
        self.assertGreater(len(data), 1000)
        self.assertEqual(data[:2], b"\xff\xd8")
        self.assertEqual(data[-2:], b"\xff\xd9")


if __name__ == "__main__":
    unittest.main()
