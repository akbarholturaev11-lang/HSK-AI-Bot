"""Exercise the WebSocket relay with the pinned SDK's real per-turn iterator."""
import asyncio
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.genai.live import AsyncSession

from app.api.android_live_voice import create_android_live_voice_router


class _Provider:
    # Use the SDK implementation: receive() breaks on turn_complete.
    receive = AsyncSession.receive

    def __init__(self, turns):
        self.messages = []
        self.sent_audio = []
        for index in range(turns):
            self.messages.append(SimpleNamespace(
                session_resumption_update=None,
                usage_metadata=SimpleNamespace(prompt_token_count=10, response_token_count=10),
                server_content=SimpleNamespace(
                    input_transcription=SimpleNamespace(text=f"你好{index}"),
                    output_transcription=SimpleNamespace(text="你好吗？"),
                    interrupted=False, turn_complete=True,
                    model_turn=SimpleNamespace(parts=[SimpleNamespace(
                        inline_data=SimpleNamespace(data=b"\x00\x00" * 10),
                    )]),
                ),
            ))

    async def _receive(self):
        await asyncio.sleep(0)
        if self.messages:
            return self.messages.pop(0)
        await asyncio.Event().wait()

    async def send_realtime_input(self, **kwargs):
        self.sent_audio.append(kwargs)


class AndroidLiveVoiceRelayTests(unittest.TestCase):
    def _client(self, *, turns=8, cost_per_turn=0.001, started_seconds_ago=0):
        settings = SimpleNamespace(
            ANDROID_VOICE_LIVE_ENABLED=True,
            ANDROID_VOICE_LIVE_ALLOWED_USERS="4242",
            ANDROID_VOICE_LIVE_MODEL="gemini-3.8-live",
            ANDROID_VOICE_LIVE_SESSION_BUDGET_USD=0.15,
            ANDROID_VOICE_LIVE_MAX_SECONDS=180,
            GEMINI_API_KEY="test-only", GEMINI_BILLING_TIER="paid",
        )
        item = SimpleNamespace(
            id="session-live", user_telegram_id=4242, mode="live", role="friend",
            level="hsk1", language="uz", voice="female", target_words=[],
            plan_json={}, history=[], live_resumption_handle=None,
            live_started_at=datetime.now(timezone.utc) - timedelta(seconds=started_seconds_ago),
        )
        db = SimpleNamespace(commit=AsyncMock(), execute=AsyncMock(return_value=SimpleNamespace(
            rowcount=1, scalar_one_or_none=lambda: item,
        )))

        @asynccontextmanager
        async def session_factory():
            yield db

        provider = _Provider(turns)

        @asynccontextmanager
        async def connector(settings_obj, live_item):
            yield provider

        recorded = []

        async def save_turn(telegram_id, **kwargs):
            recorded.append(kwargs)
            return {
                "turn_count": len(recorded), "max_dialogs": 0,
                "session_should_end": False,
                "session_cost_usd": len(recorded) * cost_per_turn,
                "transcription": kwargs["transcription"],
                "chinese_reply": kwargs["assistant_text"],
            }

        app = FastAPI()
        app.include_router(create_android_live_voice_router(
            session_factory=session_factory, settings_obj=settings,
            voice_service_factory=lambda session: SimpleNamespace(process_live_turn=save_turn),
            provider_connector=connector,
        ))
        return TestClient(app), recorded

    def _authenticate(self):
        return patch("app.api.android_live_voice.DesktopAuthService.authenticate", AsyncMock(
            return_value=SimpleNamespace(user=SimpleNamespace(telegram_id=4242)),
        ))

    def test_one_connection_streams_and_saves_eight_turns_then_accepts_stop(self):
        client, recorded = self._client()
        with self._authenticate(), client, client.websocket_connect(
            "/api/v3/android/voice/live?session_id=session-live",
            headers={"Authorization": "Bearer test-token"},
        ) as socket:
            ready = socket.receive_json()
            self.assertEqual(ready["max_dialogs"], 0)
            self.assertGreater(ready["max_seconds"], 0)
            self.assertLessEqual(ready["max_seconds"], 180)
            for count in range(1, 9):
                self.assertEqual(socket.receive_json()["type"], "audio")
                turn = socket.receive_json()
                self.assertEqual(turn["type"], "turn_complete")
                self.assertEqual(turn["turn_count"], count)
                self.assertFalse(turn["session_should_end"])
            socket.send_json({"type": "stop"})
            self.assertEqual(socket.receive()["type"], "websocket.close")
        self.assertEqual(len(recorded), 8)
        self.assertTrue(all(turn["provider_usage"] is not None for turn in recorded))

    def test_session_budget_still_closes_the_connection(self):
        client, recorded = self._client(cost_per_turn=0.08)
        with self._authenticate(), client, client.websocket_connect(
            "/api/v3/android/voice/live?session_id=session-live",
            headers={"Authorization": "Bearer test-token"},
        ) as socket:
            self.assertEqual(socket.receive_json()["type"], "ready")
            for _ in range(2):
                self.assertEqual(socket.receive_json()["type"], "audio")
                self.assertEqual(socket.receive_json()["type"], "turn_complete")
            self.assertEqual(socket.receive_json()["type"], "budget_limit")
            self.assertEqual(socket.receive()["type"], "websocket.close")
        self.assertEqual(len(recorded), 2)

    def test_elapsed_session_time_still_closes_a_quiet_connection(self):
        client, recorded = self._client(turns=0, started_seconds_ago=177)
        with self._authenticate(), client, client.websocket_connect(
            "/api/v3/android/voice/live?session_id=session-live",
            headers={"Authorization": "Bearer test-token"},
        ) as socket:
            ready = socket.receive_json()
            self.assertGreater(ready["max_seconds"], 0)
            self.assertLessEqual(ready["max_seconds"], 3)
            self.assertEqual(socket.receive_json()["type"], "time_limit")
            self.assertEqual(socket.receive()["type"], "websocket.close")
        self.assertFalse(recorded)
