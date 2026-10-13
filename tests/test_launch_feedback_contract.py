"""Cold-launch Golden Logo sound/haptic parity for Telegram and native Android."""

import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
ANDROID = ROOT / "android" / "app"
MINI = (STATIC / "course-v3.html").read_text(encoding="utf-8")
BRAND = (ANDROID / "src/main/java/com/pomp/hskai/core/design/components/HskBrandLoader.kt").read_text(encoding="utf-8")
FEEDBACK = (ANDROID / "src/main/java/com/pomp/hskai/core/design/components/HskLaunchFeedback.kt").read_text(encoding="utf-8")
EXPECTED_AUDIO_HASH = "293d88755db6c5ae78cb2f10bf22b25eeb603e5995a9a6252439a414fab4edd8"


class LaunchFeedbackContractTests(unittest.TestCase):
    def test_same_real_golden_logo_audio_is_bundled_on_both_platforms(self):
        mini = (STATIC / "assets/hsk-launch-gold.mp3").read_bytes()
        android = (ANDROID / "src/main/res/raw/hsk_launch_gold.mp3").read_bytes()
        self.assertEqual(mini, android)
        self.assertTrue(mini.startswith(b"ID3"))
        self.assertEqual(hashlib.sha256(mini).hexdigest(), EXPECTED_AUDIO_HASH)

    def test_mini_only_plays_on_actual_cold_launch(self):
        self.assertIn("if(returning){root.classList.add", MINI)
        self.assertIn('launchAudio=new Audio("/assets/hsk-launch-gold.mp3?v=20261013")', MINI)
        self.assertIn('!motionReduced&&document.visibilityState!=="hidden"', MINI)
        self.assertIn('playRequest.catch(function(){})', MINI)
        self.assertIn("if(INIT_DATA&&tg&&tg.platform)try{", MINI)
        self.assertIn('function stopLaunchEffects()', MINI)
        self.assertIn('launchAudio.pause()', MINI)
        self.assertRegex(MINI, r'launchPulse\("light"\)\},570\)')
        self.assertRegex(MINI, r'launchPulse\("medium"\)\},1910\)')

    def test_android_startup_only_and_respects_device_controls(self):
        activity = (ANDROID / "src/main/java/com/pomp/hskai/MainActivity.kt").read_text(encoding="utf-8")
        manifest = (ANDROID / "src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        self.assertIn("SplashScreen(onLaunchSplashAnimationFinished)", activity)
        self.assertIn("LaunchedEffect(launch)", BRAND)
        self.assertIn("if (!launch) return@LaunchedEffect", BRAND)
        self.assertIn("feedback.play()", BRAND)
        self.assertIn("delay(570)", BRAND)
        self.assertIn("delay(1340)", BRAND)
        self.assertIn("feedback.release()", BRAND)
        self.assertIn("R.raw.hsk_launch_gold", FEEDBACK)
        self.assertIn("AudioManager.RINGER_MODE_NORMAL", FEEDBACK)
        self.assertIn("Settings.System.HAPTIC_FEEDBACK_ENABLED", FEEDBACK)
        self.assertIn('android.permission.VIBRATE', manifest)

    def test_android_release_version_advances_for_updated_apk(self):
        gradle = (ANDROID / "build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('val appVersionName = "1.7.12"', gradle)
        self.assertIn("val appVersionCode = 43", gradle)


if __name__ == "__main__":
    unittest.main()
