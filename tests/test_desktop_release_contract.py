import base64
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
WORKFLOW = ROOT / ".github/workflows/desktop-release.yml"


class DesktopReleaseContractTests(unittest.TestCase):
    def test_release_versions_and_updater_key_are_aligned(self):
        package = json.loads((DESKTOP / "package.json").read_text(encoding="utf-8"))
        tauri = json.loads(
            (DESKTOP / "src-tauri/tauri.conf.json").read_text(encoding="utf-8")
        )
        cargo = (DESKTOP / "src-tauri/Cargo.toml").read_text(encoding="utf-8")
        cargo_version = re.search(r'^version\s*=\s*"([^"]+)"', cargo, re.MULTILINE)

        self.assertIsNotNone(cargo_version)
        self.assertEqual(package["version"], "1.1.1")
        self.assertEqual(tauri["version"], package["version"])
        self.assertEqual(cargo_version.group(1), package["version"])

        pubkey = tauri["plugins"]["updater"]["pubkey"]
        decoded = base64.b64decode(pubkey).decode("utf-8")
        self.assertIn("untrusted comment: minisign public key:", decoded)
        self.assertIn("https://telegram-chinese-bot-production.up.railway.app", tauri["plugins"]["updater"]["endpoints"][0])

    def test_release_workflow_uses_v3_signing_and_r2_contract(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertEqual(workflow.count("secrets.TAURI_SIGNING_PRIVATE_KEY_V3"), 2)
        self.assertEqual(
            workflow.count("secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD_V3"), 2
        )
        self.assertNotIn("secrets.TAURI_SIGNING_PRIVATE_KEY }}", workflow)
        self.assertNotIn("secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}", workflow)
        self.assertEqual(workflow.count('readFileSync("./src-tauri/Cargo.toml"'), 2)
        for name in (
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_ACCOUNT_ID",
            "R2_BUCKET",
            "R2_PUBLIC_BASE_URL",
        ):
            self.assertIn(name, workflow)


if __name__ == "__main__":
    unittest.main()
