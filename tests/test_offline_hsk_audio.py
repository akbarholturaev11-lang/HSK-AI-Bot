"""Checks that both course tracks can reuse the same offline speech assets."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import build_hsk_offline_audio as offline
from app.services import tts_service


class OfflineAudioBundleTests(unittest.TestCase):
    def test_original_short_mp3_names_remain_compatible(self):
        self.assertEqual(offline.audio_name("你好"), "20320_22909.mp3")
        self.assertEqual(tts_service._offline_audio_name("你好"), "20320_22909.mp3")

    def test_long_sentence_has_same_short_name_as_backend(self):
        sentence = "今天我们在教室里学习新的汉语句子。" * 5
        name = offline.audio_name(sentence)
        self.assertTrue(name.startswith("sha1_"))
        self.assertLessEqual(len(name.encode("utf-8")), 240)
        self.assertEqual(name, tts_service._offline_audio_name(sentence))

    def test_only_speakable_course_fields_extracted(self):
        sample = {
            "subtitle": {"uz": "你好 degan so'z", "tj": "你好"},
            "active_words": [{"zh": "你好"}],
            "dialogues": [{"dialogue": [{"zh": "大家好！"}]}],
            "sections": [{"cards": [{
                "word": {"zh": "妈妈"},
                "phrase": "你好吗？",
                "audio_text": "我很好。",
                "explanation": {"ru": "请喝茶 means drink tea"},
                "prompt": {"uz": "你 so'zini belgilang"},
                "g": {"examples": [{"zh": "我们学习汉语。"}]},
            }]}],
        }
        result = offline.extract_audio_strings(sample)
        self.assertEqual(
            result,
            {"你好", "大家好！", "妈妈", "你好吗？", "我很好。", "我们学习汉语。"},
        )

    def test_generated_public_manifest_does_not_advertise_missing_mp3(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as dirname:
            out = Path(dirname) / "words"
            index = Path(dirname) / "index.js"
            out.mkdir()
            long = "我们一起学习汉语。" * 15
            words = ["你好", "大家好！", long]
            for text in ("你好", long):
                (out / offline.audio_name(text)).write_bytes(b"ID3" + bytes(256))
            with patch.object(offline, "OUT", out), patch.object(offline, "INDEX", index):
                with patch.object(offline, "corpus", return_value=words):
                    self.assertEqual(offline.write_offline_index(), 0)
            generated = index.read_text("utf-8")
            self.assertIn("window.HSK_OFFLINE_AUDIO=new Set(", generated)
            self.assertIn("window.HSK_OFFLINE_LONG_NAMES=", generated)
            self.assertIn("你好", generated)
            self.assertIn("sha1_", generated)
            self.assertNotIn("大家好！", generated)

    def test_miniapp_direct_audio_uses_original_server_only_as_fallback(self):
        html = (offline.ROOT / "app/static/course-v3.html").read_text("utf-8")
        backend = (offline.ROOT / "app/main.py").read_text("utf-8")
        self.assertIn('src="/audio/words/index.js?', html)
        self.assertIn('return "/audio/words/"+filename;', html)
        self.assertIn('return ttsServerUrl(t);', html)
        self.assertIn('if(src===server)throw err;', html)
        self.assertIn('playSource(ttsServerUrl(t));return;', html)
        self.assertIn('@app.get("/audio/words/{filename}")', backend)
        self.assertIn('@app.get("/api/v3/tts")', backend)

    def test_fake_mp3_is_not_valid_and_valid_file_is_not_regenerated(self):
        with tempfile.TemporaryDirectory() as dirname:
            file = Path(dirname) / "audio.mp3"
            file.write_bytes(b"html" * 100)
            self.assertFalse(offline.valid_audio(file))
            file.write_bytes(b"ID3" + bytes(256))
            self.assertTrue(offline.valid_audio(file))


if __name__ == "__main__":
    unittest.main()
