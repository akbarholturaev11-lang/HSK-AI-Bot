"""Prevent repository config from silently overriding Railway's Railpack builder.

The production service chooses RAILPACK in its dashboard; source-level
railway.toml overrides dashboard settings during a deployment.
"""
import json
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RailwayBuildConfigTest(unittest.TestCase):
    def test_railway_file_matches_production_builder_and_startup(self):
        config = tomllib.loads((ROOT / "railway.toml").read_text("utf-8"))
        self.assertEqual(config["build"]["builder"].lower(), "railpack")
        self.assertEqual(config["deploy"]["startCommand"], "bash scripts/start.sh")
        self.assertEqual(config["deploy"]["healthcheckPath"], "/health")

    def test_ffmpeg_remains_available_in_final_runtime_image(self):
        config = json.loads((ROOT / "railpack.json").read_text("utf-8"))
        self.assertEqual(config["$schema"], "https://schema.railpack.com")
        packages = config["deploy"]["aptPackages"]
        self.assertIn("...", packages)
        self.assertIn("ffmpeg", packages)


if __name__ == "__main__":
    unittest.main()
