"""Test WAV and MP3 tour narration and reject path traversal."""
import unittest

from app.services.tour_audio import resolve_tour_audio


class TourAudioContractTests(unittest.TestCase):
    def test_all_three_languages_have_WAV_files(self):
        for lang in ("uz", "ru", "tj"):
            for n in ("f01.wav", "f03.wav", "f10.wav"):
                with self.subTest(lang=lang, filename=n):
                    result = resolve_tour_audio(lang, n)
                    self.assertIsNotNone(result)
                    path, mime = result
                    self.assertTrue(path.is_file())
                    self.assertEqual(mime, "audio/wav")

    def test_mp3_unchanged(self):
        path, mime = resolve_tour_audio("ru", "b1.mp3")
        self.assertTrue(path.is_file())
        self.assertEqual(mime, "audio/mpeg")

    def test_rejects_unsupported_paths(self):
        for lang, name in [
            ("../ru", "f03.wav"),
            ("en", "f03.wav"),
            ("ru", "../secret.wav"),
            ("ru", "%2e%2e%2fsecret.wav"),
            ("ru", "f03.exe"),
            ("ru", "missing.wav"),
            ("ru", ".env"),
            ("ru", "f03.mp3"),
        ]:
            with self.subTest(lang=lang, name=name):
                self.assertIsNone(resolve_tour_audio(lang, name))

    def test_server_uses_typed_resolver(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
        self.assertIn('@app.get("/audio/tour/{lang}/{filename}")', source)
        self.assertIn("resolve_tour_audio(lang, filename)", source)


if __name__ == "__main__":
    unittest.main()
