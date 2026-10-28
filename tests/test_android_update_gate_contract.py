"""No channel drift for mandatory Android policy and install handoff."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ROOT / "android/app/src/direct/java/com/pomp/hskai/feature/update"
PLAY = ROOT / "android/app/src/play/java/com/pomp/hskai/feature/update"


class AndroidUpdateGateContractTests(unittest.TestCase):
    def test_both_channels_refresh_policy_when_app_returns_to_foreground(self):
        for folder, channel in ((DIRECT, "direct"), (PLAY, "play")):
            with self.subTest(channel=channel):
                content = (folder / "MandatoryUpdateGate.kt").read_text()
                self.assertIn("Lifecycle.Event.ON_RESUME", content)
                self.assertIn("UpdatePolicyClient.minimumSupportedVersion(context, \""+channel+"\")", content)
                self.assertIn("AndroidUpdateThreshold", content) if channel == "play" else self.assertIn("AppUpdate.isMandatoryUpdate", content)

    def test_only_direct_has_sideload_installer_and_play_stays_market_only(self):
        direct = (DIRECT / "MandatoryUpdateGate.kt").read_text()
        play = (PLAY / "MandatoryUpdateGate.kt").read_text()
        self.assertIn("UpdateInstallCoordinator.beginUpdateRequest", direct)
        self.assertNotIn("REQUEST_INSTALL_PACKAGES", play)
        self.assertNotIn("ACTION_INSTALL_PACKAGE", play)
        self.assertIn("AppUpdateManagerFactory", play)
        self.assertIn("AppUpdateType.IMMEDIATE", play)
        self.assertIn("market://details", play)


if __name__ == "__main__":
    unittest.main()
