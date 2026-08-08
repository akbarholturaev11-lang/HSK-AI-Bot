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
        self.assertRegex(package["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(tauri["version"], package["version"])
        self.assertEqual(cargo_version.group(1), package["version"])

        pubkey = tauri["plugins"]["updater"]["pubkey"]
        decoded = base64.b64decode(pubkey, validate=True).decode("utf-8")
        public_key_lines = decoded.splitlines()
        self.assertEqual(len(public_key_lines), 2)
        self.assertRegex(
            public_key_lines[0],
            r"^untrusted comment: minisign public key: [0-9A-F]+$",
        )
        public_key_packet = base64.b64decode(
            public_key_lines[1],
            validate=True,
        )
        self.assertEqual(len(public_key_packet), 42)
        self.assertEqual(public_key_packet[:2], b"Ed")
        self.assertTrue(tauri["bundle"]["createUpdaterArtifacts"])
        self.assertEqual(
            tauri["plugins"]["updater"]["endpoints"],
            [
                "https://telegram-chinese-bot-production.up.railway.app/"
                "api/v3/desktop/update/{{target}}/{{arch}}/{{current_version}}"
            ],
        )

    def test_release_workflow_uses_v4_signing_and_r2_contract(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertEqual(workflow.count("secrets.TAURI_SIGNING_PRIVATE_KEY_V4"), 2)
        self.assertEqual(
            workflow.count("secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD_V4"), 2
        )
        self.assertNotIn("secrets.TAURI_SIGNING_PRIVATE_KEY }}", workflow)
        self.assertNotIn("secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}", workflow)
        self.assertEqual(workflow.count('readFileSync("./src-tauri/Cargo.toml"'), 2)
        self.assertEqual(workflow.count('minisign -Vm "release/$'), 2)
        self.assertIn("base64 --decode < \"release/$mac_update.sig\"", workflow)
        self.assertIn("base64 --decode < \"release/$win_exe.sig\"", workflow)
        for name in (
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_ACCOUNT_ID",
            "R2_BUCKET",
            "R2_PUBLIC_BASE_URL",
        ):
            self.assertIn(name, workflow)

    def test_tag_release_publishes_versioned_artifacts_and_stable_aliases(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn('tags:\n      - "desktop-v*"', workflow)
        self.assertIn(
            'test "${GITHUB_REF_NAME}" = "desktop-v${package_version}"',
            workflow,
        )
        self.assertIn(
            'git merge-base --is-ancestor "$GITHUB_SHA" origin/main',
            workflow,
        )
        self.assertNotIn("inputs.version", workflow)
        self.assertEqual(
            workflow.count(
                "name: Pomp-HSK-AI_${{ needs.prepare.outputs.version }}_"
            ),
            3,
        )
        self.assertNotIn("name: Pomp-HSK-AI_${{ inputs.version }}_", workflow)
        self.assertIn("desktop/latest/Pomp-HSK-AI-universal.dmg", workflow)
        self.assertIn("desktop/latest/Pomp-HSK-AI-x64-setup.exe", workflow)
        self.assertIn("desktop/latest.json", workflow)

    def test_publish_is_serialized_immutable_and_manifest_is_last(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("needs: [prepare, macos, windows]", workflow)
        self.assertIn("group: desktop-release-publish", workflow)
        self.assertIn("Release ${process.argv[1]} must not be older", workflow)
        self.assertIn(
            "Published version has a different immutable artifact fingerprint",
            workflow,
        )
        self.assertIn(
            "Retrying an already published release with the same artifact fingerprint",
            workflow,
        )
        self.assertIn("aws s3api head-object", workflow)
        self.assertIn('--key "desktop/latest.json"', workflow)
        self.assertIn(
            'aws s3 cp "s3://${R2_BUCKET}/desktop/latest.json"',
            workflow,
        )
        self.assertIn("value.split(\".\").map(BigInt)", workflow)
        self.assertIn(
            "Immutable release key exists with different content",
            workflow,
        )
        self.assertIn("--arg mac_download \"$base/$mac_dmg\"", workflow)
        self.assertIn("--arg windows_download \"$base/$win_exe\"", workflow)
        self.assertIn("--retry-all-errors", workflow)
        self.assertEqual(workflow.count("aws s3 cp latest.json"), 1)

        ordered_steps = (
            "- name: Verify checksums and updater signatures",
            "- name: Block downgrade and immutable-key overwrite",
            "- name: Create and validate release metadata locally",
            "- name: Publish installers and updater artifacts",
            "- name: Verify public artifacts and publish manifest last",
        )
        positions = [workflow.index(step) for step in ordered_steps]
        self.assertEqual(positions, sorted(positions))
        public_verification = workflow.index(
            "for public_url in",
            positions[-1],
        )
        manifest_upload = workflow.index("aws s3 cp latest.json")
        self.assertLess(public_verification, manifest_upload)

    def test_manifest_schema_and_public_url_are_validated_before_upload(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        validation_markers = (
            'parsed.protocol !== "https:" || !parsed.hostname',
            'keys == ["macos", "notes", "published_at", "schema_version", "version", "windows"]',
            'endswith(".app.tar.gz")',
            'test("^[0-9a-f]{64}$")',
            'test("^[A-Za-z0-9+/=_-]+$")',
        )
        local_validation = workflow.index(
            "- name: Create and validate release metadata locally"
        )
        artifact_upload = workflow.index(
            "- name: Publish installers and updater artifacts"
        )
        for marker in validation_markers:
            self.assertIn(marker, workflow)
            self.assertLess(workflow.index(marker), artifact_upload)
        self.assertLess(local_validation, artifact_upload)

    def test_cross_platform_checksum_files_are_linux_check_compatible(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("[System.IO.File]::WriteAllText(", workflow)
        self.assertIn('$checksumLine = "$hash  $releaseName`n"', workflow)
        self.assertIn("[System.Text.UTF8Encoding]::new($false)", workflow)
        self.assertNotIn(
            '"$hash  $releaseName" | Set-Content '
            '"$releaseDir/SHA256SUMS-windows.txt"',
            workflow,
        )
        self.assertIn("sha256sum --check SHA256SUMS-windows.txt", workflow)

    def test_release_actions_use_node24_generations(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        for action in (
            "actions/checkout@v6",
            "actions/setup-node@v6",
            "actions/upload-artifact@v6",
            "actions/download-artifact@v8",
        ):
            self.assertIn(action, workflow)
        for old_action in (
            "actions/checkout@v4",
            "actions/setup-node@v4",
            "actions/upload-artifact@v4",
            "actions/download-artifact@v4",
        ):
            self.assertNotIn(old_action, workflow)


if __name__ == "__main__":
    unittest.main()
