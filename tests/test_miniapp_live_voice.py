"""Real Telegram signatures and database ownership at the Mini App Live boundary."""
import asyncio
import hashlib
import hmac
import json
import time
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tempfile import TemporaryDirectory

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.api.android_live_voice import create_android_live_voice_router
from app.services.voice_practice_service import VoicePracticeError, VoicePracticeService


BOT_TOKEN = "test-only-miniapp-bot"


def signed_data(user_id=4242, *, age=0):
    params = {"auth_date": str(int(time.time()) - age), "user": json.dumps({"id": user_id})}
    check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


class MiniappLiveVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="hsk-miniapp-live-")
        self.engine = create_async_engine("sqlite+aiosqlite:///" + self.temp.name + "/test.db")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        asyncio.run(self.seed())
        self.settings = SimpleNamespace(
            BOT_TOKEN=BOT_TOKEN, GEMINI_API_KEY="test-only", GEMINI_BILLING_TIER="paid",
            ANDROID_VOICE_LIVE_ENABLED=True, ANDROID_VOICE_LIVE_ALLOWED_USERS="4242,4243",
            ANDROID_VOICE_LIVE_MODEL="gemini-3.8-live", ANDROID_VOICE_LIVE_MAX_SECONDS=180,
            ANDROID_VOICE_LIVE_SESSION_BUDGET_USD=0.15,
        )
        self.connected = []
        self.sent = []

        @asynccontextmanager
        async def connector(settings, item):
            self.connected.append(item.id)
            async def receive():
                await asyncio.Event().wait()
                yield  # An async iterator that stays connected until stop.
            yield SimpleNamespace(receive=receive, send_realtime_input=self.send_audio)

        app = FastAPI()
        app.include_router(create_android_live_voice_router(
            session_factory=self.sessions, settings_obj=self.settings, provider_connector=connector,
        ))
        self.client = TestClient(app)

    async def seed(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as session:
            session.add_all([
                User(id=1, telegram_id=4242, full_name="Learner", language="uz", level="hsk1"),
                User(id=2, telegram_id=4243, full_name="Other learner", language="uz", level="hsk1"),
                VoicePracticeSession(id="miniapp-live-session", user_telegram_id=4242, mode="live",
                    role="friend", level="hsk1", language="uz", voice="female", status="active",
                    live_started_at=datetime.now(timezone.utc), turn_count=1),
                VoicePracticeSession(id="miniapp-turn-session", user_telegram_id=4242, mode="turn",
                    role="friend", level="hsk1", language="uz", voice="female", status="active",
                    turn_count=2, history=[{"user": "你好", "assistant": "你好吗？"}]),
            ])
            await session.commit()

    def tearDown(self):
        asyncio.run(self.engine.dispose())
        self.temp.cleanup()

    async def send_audio(self, **kwargs):
        self.sent.append(kwargs)

    def socket(self, *, origin="http://testserver"):
        return self.client.websocket_connect("/api/voice-practice/live", headers={"origin": origin})

    def test_signed_first_frame_streams_pcm_without_an_android_token_and_releases_lease(self):
        with self.client, self.socket() as socket:
            socket.send_json({"type": "auth", "initData": signed_data(), "session_id": "miniapp-live-session"})
            ready = socket.receive_json()
            self.assertEqual(ready["type"], "ready", ready)
            self.assertEqual(ready["max_dialogs"], 0)
            socket.send_bytes(b"\x00\x00" * 320)
            socket.send_json({"type": "ping"})
            self.assertEqual(socket.receive_json()["type"], "pong")
            socket.send_json({"type": "stop"})
            self.assertEqual(socket.receive()["type"], "websocket.close")
        self.assertEqual(self.connected, ["miniapp-live-session"])
        self.assertEqual(self.sent[0]["audio"].mime_type, "audio/pcm;rate=16000")
        asyncio.run(self.assert_lease_released())

    async def assert_lease_released(self):
        async with self.sessions() as session:
            item = await session.get(VoicePracticeSession, "miniapp-live-session")
            self.assertIsNone(item.live_connection_token)

    def test_invalid_stale_future_and_cross_origin_auth_never_open_the_provider(self):
        for data, origin in [("user=4242", "http://testserver"),
                             (signed_data(age=86410), "http://testserver"),
                             (signed_data(age=-300), "http://testserver"),
                             (signed_data(), "https://untrusted.example")]:
            with self.subTest(origin=origin), self.client, self.socket(origin=origin) as socket:
                if origin == "http://testserver":
                    socket.send_json({"type": "auth", "initData": data, "session_id": "miniapp-live-session"})
                self.assertEqual(socket.receive_json()["code"], "INVALID_INIT_DATA")
                self.assertEqual(socket.receive()["code"], 1008)
        self.assertFalse(self.connected)

    def test_other_user_and_turn_mode_cannot_claim_a_live_session(self):
        for user_id, session_id in [(4243, "miniapp-live-session"), (4242, "miniapp-turn-session")]:
            with self.subTest(user_id=user_id), self.client, self.socket() as socket:
                socket.send_json({"type": "auth", "initData": signed_data(user_id), "session_id": session_id})
                self.assertIn(socket.receive_json()["code"], {"SESSION_NOT_FOUND", "SESSION_MODE_MISMATCH"})
                self.assertEqual(socket.receive()["code"], 1008)
        self.assertFalse(self.connected)

    def test_mode_fallback_preserves_history_count_clock_and_daily_allowance(self):
        with self.client:
            body = {"initData": signed_data(), "session_id": "miniapp-turn-session"}
            for mode in ["live", "turn", "live", "turn"]:
                result = self.client.post("/api/voice-practice/session/mode", json={**body, "mode": mode})
                self.assertEqual(result.status_code, 200, result.text)
        asyncio.run(self.assert_preserved())

    async def assert_preserved(self):
        async with self.sessions() as session:
            item = await session.get(VoicePracticeSession, "miniapp-turn-session")
            self.assertEqual(item.mode, "turn")
            self.assertEqual(item.turn_count, 2)
            self.assertEqual(item.history, [{"user": "你好", "assistant": "你好吗？"}])
            self.assertIsNotNone(item.live_started_at)

    def test_mode_endpoint_checks_signature_owner_and_feature_gate(self):
        with self.client:
            for data, code in [("bad", 401), (signed_data(4243), 404)]:
                response = self.client.post("/api/voice-practice/session/mode", json={
                    "initData": data, "session_id": "miniapp-turn-session", "mode": "live",
                })
                self.assertEqual(response.status_code, code)
            self.settings.ANDROID_VOICE_LIVE_ENABLED = False
            response = self.client.post("/api/voice-practice/session/mode", json={
                "initData": signed_data(), "session_id": "miniapp-turn-session", "mode": "live",
            })
            self.assertEqual(response.status_code, 403)

    def test_live_lease_cannot_be_downgraded_while_streaming(self):
        with self.client, self.socket() as socket:
            socket.send_json({"type": "auth", "initData": signed_data(), "session_id": "miniapp-live-session"})
            self.assertEqual(socket.receive_json()["type"], "ready")
            response = self.client.post("/api/voice-practice/session/mode", json={
                "initData": signed_data(), "session_id": "miniapp-live-session", "mode": "turn",
            })
            self.assertEqual(response.status_code, 409)
            socket.send_json({"type": "stop"})
            self.assertEqual(socket.receive()["type"], "websocket.close")

    def test_mode_switch_cannot_renew_time_or_budget(self):
        async def exhaust(field, value):
            async with self.sessions() as session:
                item = await session.get(VoicePracticeSession, "miniapp-turn-session")
                setattr(item, field, value)
                await session.commit()
        for field, value, code in [
            ("live_started_at", datetime.now(timezone.utc) - timedelta(seconds=181), "live_session_expired"),
            ("live_cost_usd", 10, "budget_limit"),
        ]:
            asyncio.run(exhaust("live_started_at", None))
            asyncio.run(exhaust(field, value))
            with self.client:
                response = self.client.post("/api/voice-practice/session/mode", json={
                    "initData": signed_data(), "session_id": "miniapp-turn-session", "mode": "live",
                })
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["code"], code)

    def test_binary_auth_frame_is_rejected_before_provider_connection(self):
        with self.client, self.socket() as socket:
            socket.send_bytes(b"not an auth frame")
            self.assertEqual(socket.receive_json()["code"], "INVALID_INIT_DATA")
            self.assertEqual(socket.receive()["code"], 1008)
        self.assertFalse(self.connected)

    def test_exhausted_daily_allowance_cannot_open_an_unspoken_live_session(self):
        async def make_unspoken():
            async with self.sessions() as session:
                item = await session.get(VoicePracticeSession, "miniapp-live-session")
                item.turn_count = 0
                await session.commit()
        asyncio.run(make_unspoken())
        with self.client, self.socket() as socket:
            socket.send_json({"type": "auth", "initData": signed_data(), "session_id": "miniapp-live-session"})
            self.assertEqual(socket.receive_json()["code"], "LIMIT_EXCEEDED")
            self.assertEqual(socket.receive()["code"], 1008)
        self.assertFalse(self.connected)

    def test_blocked_and_budget_exhausted_users_cannot_upgrade(self):
        async def set_user(status, payment):
            async with self.sessions() as session:
                user = await session.get(User, 1)
                user.status = status
                user.payment_status = payment
                user.end_date = datetime.now(timezone.utc) + timedelta(days=7)
                await session.commit()
        body = {"initData": signed_data(), "session_id": "miniapp-turn-session", "mode": "live"}
        asyncio.run(set_user("blocked", "none"))
        with self.client:
            response = self.client.post("/api/voice-practice/session/mode", json=body)
            self.assertEqual(response.json()["code"], "access_blocked")
        asyncio.run(set_user("active", "approved"))
        with patch.object(VoicePracticeService, "_ensure_budget_available", AsyncMock(
            side_effect=VoicePracticeError("ai_budget_exhausted", "Budget exhausted.", 403),
        )), self.client:
            response = self.client.post("/api/voice-practice/session/mode", json=body)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "ai_budget_exhausted")
