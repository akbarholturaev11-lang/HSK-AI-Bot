"""Regression coverage for lesson MP3 generation during Edge TTS outages."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.services import tts_service as tts

FAKE_MP3 = b"ID3" + bytes(256)


class TTSServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.variables = patch.dict(os.environ, {"HSK_TTS_CACHE_DIR": self.directory.name}, clear=False)
        self.variables.start()
        self.addCleanup(self.variables.stop)
        tts._locks.clear()
        tts._paid_times.clear()
        tts._edge_retry_at = 0

    async def test_rejects_untrusted_text_without_calling_providers(self):
        for text in ("hello", "", "你" * 241):
            with self.subTest(text_length=len(text)):
                with self.assertRaises(ValueError):
                    await tts.synthesize_chinese_mp3(text)

    async def test_edge_success_is_cached_with_no_second_synthesis(self):
        async def edge(text, rate, path):
            Path(path).write_bytes(FAKE_MP3)

        with patch.object(tts, "_edge", new=AsyncMock(side_effect=edge)) as generate:
            first = await tts.synthesize_chinese_mp3("你好")
            second = await tts.synthesize_chinese_mp3("你好")
            self.assertEqual(first, second)
            self.assertEqual(FAKE_MP3, first.read_bytes())
            generate.assert_awaited_once()

    async def test_edge_403_falls_back_to_server_mp3_and_stores_cache(self):
        with patch.object(tts, "_edge", new=AsyncMock(side_effect=RuntimeError("403"))), \
             patch.object(tts, "_fallback", new=AsyncMock(return_value=FAKE_MP3)) as fallback:
            path = await tts.synthesize_chinese_mp3("老师，再见！")
            self.assertEqual(FAKE_MP3, path.read_bytes())
            self.assertTrue(path.name.endswith(".mp3"))
            fallback.assert_awaited_once_with("老师，再见！", "-10%")

    async def test_concurrent_same_phrase_is_only_generated_once(self):
        async def edge(text, rate, path):
            await asyncio.sleep(0.02)
            Path(path).write_bytes(FAKE_MP3)

        with patch.object(tts, "_edge", new=AsyncMock(side_effect=edge)) as generate:
            files = await asyncio.gather(
                tts.synthesize_chinese_mp3("同学"),
                tts.synthesize_chinese_mp3("同学"),
            )
            self.assertEqual(files[0], files[1])
            generate.assert_awaited_once()

    async def test_edge_403_opens_circuit_for_subsequent_requests(self):
        class Edge403(Exception):
            status = 403

        class RefusedEdge:
            async def save(self, path):
                raise Edge403("403 Forbidden")

        with patch("edge_tts.Communicate", return_value=RefusedEdge()) as factory, \
             patch.object(tts, "_fallback", new=AsyncMock(return_value=FAKE_MP3)):
            await tts.synthesize_chinese_mp3("你好")
            self.assertGreater(tts._edge_retry_at, time.monotonic())
            await tts.synthesize_chinese_mp3("再见")
            factory.assert_called_once()

    async def test_unavailable_providers_raise_instead_of_caching_error(self):
        with patch.object(tts, "_edge", new=AsyncMock(side_effect=RuntimeError("403"))), \
             patch.object(tts, "_fallback", new=AsyncMock(side_effect=tts.TTSUnavailable("no-key"))):
            with self.assertRaises(tts.TTSUnavailable):
                await tts.synthesize_chinese_mp3("谢谢")
            self.assertEqual([], list(Path(self.directory.name).glob("*.mp3")))

    async def test_paid_fallback_has_hourly_request_limit(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "HSK_TTS_OPENAI_MAX_HOURLY": "1"}):
            fake = SimpleNamespace(content=FAKE_MP3)
            class Client:
                def __init__(self):
                    self.audio = SimpleNamespace(speech=SimpleNamespace(create=AsyncMock(return_value=fake)))
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return False

            with patch.object(tts, "AsyncOpenAI", return_value=Client()):
                self.assertEqual(FAKE_MP3, await tts._fallback("你好", "-10%"))
                with self.assertRaises(tts.TTSUnavailable):
                    await tts._fallback("再见", "-10%")


if __name__ == "__main__":
    unittest.main()
