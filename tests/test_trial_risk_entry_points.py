"""HTTP-level regression for Pro-trial shadow telemetry on both clients."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.android_features import create_android_features_router
from app.api.miniapp_entitlements import create_miniapp_entitlements_router
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.trial_risk_event import TrialRiskEvent
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService


SECRET = "trial-entry-test-secret-" + "x" * 40
REMOTE_IP = "203.0.113.17"


def _user(user_id: int, telegram_id: int) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=f"Trial API {user_id}",
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        created_at=now - timedelta(days=3),
        last_active_at=now,
    )


class TrialRiskEntryPointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([_user(1, 1001), _user(2, 2002)])
            await session.commit()

        self.settings = SimpleNamespace(
            BOT_TOKEN="test-bot-token",
            DESKTOP_AUTH_SIGNING_SECRET=SECRET,
        )
        app = FastAPI()
        app.include_router(
            create_miniapp_entitlements_router(
                session_factory=self.sessions,
                settings_obj=self.settings,
            )
        )
        app.include_router(
            create_android_features_router(
                session_factory=self.sessions,
                settings_obj=self.settings,
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://trial.test",
        )
        self.funnel_patch = patch(
            "app.services.conversion_funnel_service.async_session_maker",
            self.sessions,
        )
        self.funnel_patch.start()

    async def asyncTearDown(self):
        self.funnel_patch.stop()
        await self.client.aclose()
        await self.db.dispose()

    async def test_miniapp_then_android_records_cross_client_shadow_history(self):
        with patch(
            "app.api.miniapp_entitlements.extract_verified_webapp_user_id",
            return_value=1001,
        ):
            mini = await self.client.post(
                "/api/v3/trial/start",
                headers={
                    "X-Telegram-Init-Data": "signed-test-data",
                    "X-Real-IP": REMOTE_IP,
                },
                json={},
            )

        self.assertEqual(200, mini.status_code)
        self.assertTrue(mini.json()["ok"])
        self.assertNotIn("risk", mini.json())

        device_hash = "a" * 64
        android_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=2002),
            device=SimpleNamespace(installation_key_hash=device_hash),
        )
        with patch.object(
            DesktopAuthService,
            "authenticate",
            AsyncMock(return_value=android_context),
        ):
            android = await self.client.post(
                "/api/v3/android/trial/start",
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Real-IP": REMOTE_IP,
                },
            )

        self.assertEqual(200, android.status_code)
        self.assertTrue(android.json()["ok"])
        self.assertNotIn("risk", android.json())

        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(TrialRiskEvent).order_by(TrialRiskEvent.telegram_id)
                )
            ).scalars().all()

        self.assertEqual([1001, 2002], [row.telegram_id for row in rows])
        self.assertIsNone(rows[0].installation_key_hash)
        self.assertEqual(device_hash, rows[1].installation_key_hash)
        self.assertEqual(0, rows[0].prior_ip_trial_users_24h)
        self.assertEqual(1, rows[1].prior_ip_trial_users_24h)
        self.assertNotEqual(REMOTE_IP, rows[0].ip_hash)
        self.assertEqual(rows[0].ip_hash, rows[1].ip_hash)


if __name__ == "__main__":
    unittest.main()
