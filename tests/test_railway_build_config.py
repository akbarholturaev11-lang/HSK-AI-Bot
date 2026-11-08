"""Protect production Dockerfile fallback from regressions to broken build drivers."""
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RailwayBuildConfigTest(unittest.TestCase):
    def test_dockerfile_builder_and_startup(self):
        config = tomllib.loads((ROOT / "railway.toml").read_text("utf-8"))
        self.assertEqual(config["build"]["builder"].lower(), "dockerfile")
        self.assertEqual(config["build"]["dockerfilePath"], "Dockerfile")
        self.assertEqual(config["deploy"]["startCommand"], "bash scripts/start.sh")
        self.assertEqual(config["deploy"]["healthcheckPath"], "/health")

    def test_runtime_pins_python312_and_ffmpeg(self):
        docker = (ROOT / "Dockerfile").read_text("utf-8")
        self.assertEqual((ROOT / ".python-version").read_text("utf-8").strip(), "3.12")
        self.assertIn("FROM python:3.12-slim-bookworm", docker)
        self.assertIn("ffmpeg", docker)
        self.assertIn("COPY requirements.txt ./", docker)
        self.assertIn("pip install --no-cache-dir -r requirements.txt", docker)
        self.assertIn('CMD ["bash", "scripts/start.sh"]', docker)


if __name__ == "__main__":
    unittest.main()
