"""Regression tests for Edge MP3 and Gemini TTS WAV failover."""
from __future__ import annotations

import asyncio
import base64
from io import BytesIO
import os
from pathlib import Path
import tempfile
import time
import unittest

import httpx
from unittest.mock import AsyncMock, patch
import wave

from app.services import tts_service as tts

FAKE_MP3 = b"ID3" + bytes(256)
FAKE_PCM = b"\x00\x01" * 400


class FakeGeminiResponse:
    def __init__(self, pcm=FAKE_PCM, mime="audio/L16;codec=pcm;rate=24000"):
        self.pcm = pcm
        self.mime = mime

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "inlineData": {
                            "mimeType": self.mime,
                            "data": base64.b64encode(self.pcm).decode("ascii"),
                        }
                    }]
                }
            }]
        }


class FakeHttpClient:
    def __init__(self, response=None):
        self.response = response or FakeGeminiResponse()
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, *, headers, json):
        self.calls.append((url, headers, json))
        return self.response


class TTSServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.variables = patch.dict(
            os.environ, {"HSK_TTS_CACHE_DIR": self.directory.name}, clear=False
        )
        self.variables.start()
        self.addCleanup(self.variables.stop)
        tts._locks.clear()
        tts._paid_times.clear()
        tts._edge_retry_at = 0
        tts._gemini_retry_at = 0

    async def test_rejects_non_chinese_and_oversized_text(self):
        for text in ("hello", "", "你" * 241):
            with self.subTest(text_length=len(text)):
                with self.assertRaises(ValueError):
                    await tts.synthesize_chinese_mp3(text)

    async def test_edge_success_is_cached_as_mp3_without_gemini(self):
        async def edge(text, rate, path):
            Path(path).write_bytes(FAKE_MP3)

        with patch.object(tts, "_edge", new=AsyncMock(side_effect=edge)) as generate, \
             patch.object(tts, "_fallback", new=AsyncMock()) as gemini:
            first = await tts.synthesize_chinese_mp3("你好")
            second = await tts.synthesize_chinese_mp3("你好")
            self.assertEqual(".mp3", first.suffix)
            self.assertEqual(first, second)
            self.assertEqual(FAKE_MP3, first.read_bytes())
            generate.assert_awaited_once()
            gemini.assert_not_awaited()

    async def test_edge_403_falls_back_to_gemini_wav_and_caches_it(self):
        valid_wav = tts._wav_from_pcm(FAKE_PCM)
        with patch.object(tts, "_edge", new=AsyncMock(side_effect=RuntimeError("403"))), \
             patch.object(tts, "_fallback", new=AsyncMock(return_value=valid_wav)) as gemini:
            first = await tts.synthesize_chinese_mp3("老师，再见！")
            second = await tts.synthesize_chinese_mp3("老师，再见！")
            self.assertEqual(".wav", first.suffix)
            self.assertEqual(first, second)
            self.assertTrue(first.read_bytes().startswith(b"RIFF"))
            gemini.assert_awaited_once_with("老师，再见！", "-10%")

    async def test_concurrent_same_phrase_has_only_one_paid_fallback(self):
        wav = tts._wav_from_pcm(FAKE_PCM)

        async def delayed_gemini(text, rate):
            await asyncio.sleep(0.02)
            return wav

        with patch.object(tts, "_edge", new=AsyncMock(side_effect=RuntimeError("403"))), \
             patch.object(tts, "_fallback", new=AsyncMock(side_effect=delayed_gemini)) as gemini:
            files = await asyncio.gather(
                tts.synthesize_chinese_mp3("同学们，请听。"),
                tts.synthesize_chinese_mp3("同学们，请听。"),
            )
            self.assertEqual(files[0], files[1])
            gemini.assert_awaited_once()

    async def test_edge_403_opens_circuit_for_other_phrases(self):
        class Edge403(Exception):
            status = 403

        class RefusedEdge:
            async def save(self, path):
                raise Edge403("403 Forbidden")

        with patch("edge_tts.Communicate", return_value=RefusedEdge()) as factory, \
             patch.object(tts, "_fallback", new=AsyncMock(
                 return_value=tts._wav_from_pcm(FAKE_PCM)
             )):
            await tts.synthesize_chinese_mp3("你好")
            self.assertGreater(tts._edge_retry_at, time.monotonic())
            await tts.synthesize_chinese_mp3("下课了！")
            factory.assert_called_once()

    async def test_missing_two_providers_never_caches_an_error(self):
        with patch.object(tts, "_edge", new=AsyncMock(side_effect=RuntimeError("403"))), \
             patch.object(tts, "_fallback", new=AsyncMock(
                 side_effect=tts.TTSUnavailable("gemini_no_key")
             )):
            with self.assertRaises(tts.TTSUnavailable):
                await tts.synthesize_chinese_mp3("谢谢你！")
            self.assertEqual([], list(Path(self.directory.name).glob("*.wav")))
            self.assertEqual([], list(Path(self.directory.name).glob("*.mp3")))

    async def test_gemini_uses_its_own_api_key_and_returns_playable_wav(self):
        fake = FakeHttpClient()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test-token"}), \
             patch.object(tts.httpx, "AsyncClient", return_value=fake):
            wav_bytes = await tts._fallback("你好", "-10%")

        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        with wave.open(BytesIO(wav_bytes), "rb") as wav:
            self.assertEqual(1, wav.getnchannels())
            self.assertEqual(2, wav.getsampwidth())
            self.assertEqual(24000, wav.getframerate())
            self.assertEqual(FAKE_PCM, wav.readframes(wav.getnframes()))
        self.assertEqual(1, len(fake.calls))
        url, headers, body = fake.calls[0]
        self.assertIn("gemini-2.5-flash-preview-tts", url)
        self.assertEqual("gemini-test-token", headers["x-goog-api-key"])
        self.assertEqual(["AUDIO"], body["generationConfig"]["responseModalities"])
        self.assertEqual("Kore", body["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
        self.assertNotIn("Authorization", headers)

    async def test_gemini_http_budget_is_enforced_before_second_request(self):
        fake = FakeHttpClient()
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-key",
            "HSK_TTS_GEMINI_MAX_HOURLY": "1",
        }), patch.object(tts.httpx, "AsyncClient", return_value=fake):
            self.assertTrue((await tts._fallback("你好", "-10%")).startswith(b"RIFF"))
            with self.assertRaises(tts.TTSUnavailable):
                await tts._fallback("再见", "-10%")
        self.assertEqual(1, len(fake.calls))

    async def test_old_mp3_cache_key_remains_usable_after_migration(self):
        old = Path(self.directory.name) / (tts._cache_key("谢谢你！", "-10%") + ".mp3")
        old.write_bytes(FAKE_MP3)
        with patch.object(tts, "_edge", new=AsyncMock()) as edge, \
             patch.object(tts, "_fallback", new=AsyncMock()) as gemini:
            self.assertEqual(old, await tts.synthesize_chinese_mp3("谢谢你！"))
            edge.assert_not_awaited()
            gemini.assert_not_awaited()

    async def test_bundled_word_is_instant_and_never_calls_external_tts(self):
        # This is the word visible on the learner's first-card screenshot.
        with patch.object(tts, "_edge", new=AsyncMock()) as edge, \
             patch.object(tts, "_fallback", new=AsyncMock()) as gemini:
            path = await tts.synthesize_chinese_mp3("谢谢")
            self.assertTrue(path.is_file())
            self.assertEqual(".mp3", path.suffix)
            self.assertGreater(path.stat().st_size, 128)
            self.assertIn("android/app/src/main/assets/audio/words", path.as_posix())
            edge.assert_not_awaited()
            gemini.assert_not_awaited()

    async def test_nondefault_rate_does_not_reuse_bundled_default_audio(self):
        self.assertIsNone(tts._bundled_word_audio("谢谢", "+10%"))

    async def test_gemini_invalid_audio_is_rejected(self):
        fake = FakeHttpClient(FakeGeminiResponse(pcm=b"broken", mime="audio/L16;rate=24000"))
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
             patch.object(tts.httpx, "AsyncClient", return_value=fake):
            with self.assertRaises(tts.TTSUnavailable):
                await tts._fallback("你好", "-10%")

    async def test_gemini_429_opens_circuit_and_skips_repeated_paid_requests(self):
        response = httpx.Response(
            429,
            headers={"Retry-After": "120"},
            request=httpx.Request("POST", "https://example.test/tts"),
        )
        fake = FakeHttpClient(response=response)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
             patch.object(tts.httpx, "AsyncClient", return_value=fake):
            with self.assertRaises(httpx.HTTPStatusError):
                await tts._fallback("请坐", "-10%")
            self.assertGreaterEqual(tts._gemini_retry_at - time.monotonic(), 110)
            with self.assertRaisesRegex(tts.TTSUnavailable, "gemini_cooling_down"):
                await tts._fallback("再见", "-10%")
        self.assertEqual(1, len(fake.calls))

    async def test_gemini_503_trips_circuit_but_other_errors_do_not(self):
        for status in (503, 400):
            with self.subTest(status=status):
                tts._gemini_retry_at = 0
                response = httpx.Response(
                    status,
                    request=httpx.Request("POST", "https://example.test/tts"),
                )
                fake = FakeHttpClient(response=response)
                with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
                     patch.object(tts.httpx, "AsyncClient", return_value=fake):
                    with self.assertRaises(httpx.HTTPStatusError):
                        await tts._fallback("请坐", "-10%")
                self.assertEqual(status == 503, tts._gemini_retry_at > time.monotonic())

    def test_retry_after_is_bounded_and_invalid_values_are_safe(self):
        for raw, low, high in (("1", 29, 31), ("999999", 119, 121),
                               ("600", 599, 601), ("broken", 119, 121)):
            with self.subTest(retry_after=raw):
                response = httpx.Response(429, headers={"Retry-After": raw})
                delay = tts._gemini_retry_delay(response)
                self.assertGreaterEqual(delay, low)
                self.assertLessEqual(delay, high)

    async def test_cached_audio_remains_available_while_gemini_is_cooling_down(self):
        phrase = "谢谢你！"
        cached = Path(self.directory.name) / (tts._cache_key(phrase, "-10%") + ".mp3")
        cached.write_bytes(FAKE_MP3)
        tts._gemini_retry_at = time.monotonic() + 500
        with patch.object(tts, "_edge", new=AsyncMock()) as edge, \
             patch.object(tts, "_fallback", new=AsyncMock()) as gemini:
            self.assertEqual(cached, await tts.synthesize_chinese_mp3(phrase))
            edge.assert_not_awaited()
            gemini.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
