"""Regressions for real Android 1.7.10 Voice request contracts.

HSK 3.0 level codes must cross the strict FastAPI/Pydantic boundary unchanged.
Authentication, quotas and billing remain enforced by the existing services.
"""
import base64
from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.android_features import create_android_features_router
from app.services.desktop_auth_service import DesktopAuthService


@asynccontextmanager
async def fake_sessions():
    yield object()


class AndroidHsk30VoiceContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        calls = self.calls

        class FakeVoiceService:
            def __init__(self, session):
                self.session = session

            async def start_session(self, telegram_id, **kwargs):
                calls.append(("start", telegram_id, kwargs))
                return {"session_id": "voice-session-1", "mode": "turn"}

            async def score_pronunciation(self, telegram_id, **kwargs):
                calls.append(("pronounce", telegram_id, kwargs))
                return {"ok": True, "score": 90, "passed": True}

        app = FastAPI()
        app.include_router(create_android_features_router(
            session_factory=fake_sessions,
            settings_obj=SimpleNamespace(),
            voice_service_factory=FakeVoiceService,
        ))
        self.auth = patch.object(
            DesktopAuthService, "authenticate",
            AsyncMock(return_value=SimpleNamespace(
                user=SimpleNamespace(telegram_id=4242),
            )),
        )
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://android.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    @staticmethod
    def headers():
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def test_android_voice_session_accepts_all_supported_levels(self):
        for level in ("hsk1", "hsk2", "hsk3", "hsk4", "nhsk1", "nhsk2", "nhsk3"):
            with self.subTest(level=level):
                response = await self.client.post(
                    "/api/v3/android/voice/session/start",
                    headers=self.headers(),
                    json={
                        "role": "friend", "level": level, "language": "ru",
                        "voice": "female", "mode": "turn",
                    },
                )
                self.assertEqual(200, response.status_code, response.text)
                self.assertEqual(level, self.calls[-1][2]["level"])

    async def test_android_pronunciation_accepts_hsk30_without_lowering_level(self):
        # The APK's MediaRecorder generates MP4; the backend must keep that
        # signature validation while accepting the new HSK level code.
        audio = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00"
        encoded = "data:audio/mp4;base64," + base64.b64encode(audio).decode("ascii")
        for level in ("nhsk1", "nhsk2", "nhsk3", "hsk3"):
            with self.subTest(level=level):
                response = await self.client.post(
                    "/api/v3/android/voice/pronounce",
                    headers=self.headers(),
                    json={
                        "target": "你好", "target_pinyin": "nǐ hǎo",
                        "level": level, "language": "ru",
                        "audio_data_url": encoded,
                    },
                )
                self.assertEqual(200, response.status_code, response.text)
                self.assertEqual("pronounce", self.calls[-1][0])
                self.assertEqual(level, self.calls[-1][2]["level"])
                self.assertEqual(audio, self.calls[-1][2]["audio_bytes"])
                self.assertEqual("voice.mp4", self.calls[-1][2]["filename"])

    async def test_unsupported_levels_are_rejected_before_service(self):
        for endpoint, request in (
            ("/api/v3/android/voice/session/start",
             {"role": "friend", "level": "nhsk4", "language": "ru"}),
            ("/api/v3/android/voice/pronounce",
             {"target": "你好", "level": "nhsk4", "language": "ru",
              "audio_data_url": "data:audio/mp4;base64," + "A" * 64}),
        ):
            with self.subTest(endpoint=endpoint):
                before = len(self.calls)
                response = await self.client.post(endpoint, headers=self.headers(), json=request)
                self.assertEqual(422, response.status_code)
                self.assertEqual(before, len(self.calls))


if __name__ == "__main__":
    unittest.main()
