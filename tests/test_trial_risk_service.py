"""Trial anti-abuse V1 records only privacy-safe shadow signals."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.trial_risk_event import TrialRiskEvent
from app.db.models.user import User
from app.services.trial_risk_service import TrialRiskService


SECRET = "trial-risk-test-secret-" + "x" * 40


def _user(user_id: int, telegram_id: int, *, age_minutes: int) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=f"User {user_id}",
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
        created_at=now - timedelta(minutes=age_minutes),
        last_active_at=now,
    )


class TrialRiskServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool
        )
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all(
                [
                    _user(1, 101, age_minutes=10),
                    _user(2, 202, age_minutes=180),
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.db.dispose()

    async def test_same_device_and_ip_become_shadow_signals_for_the_next_user(self):
        device_hash = "a" * 64
        raw_ip = "203.0.113.9"
        settings = SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET=SECRET)

        async with self.sessions() as session:
            first = await session.get(User, 1)
            service = TrialRiskService(session, settings)
            first_snapshot = await service.analyze(
                first,
                client="android",
                source="android_trial",
                installation_key_hash=device_hash,
                remote_ip=raw_ip,
            )
            self.assertEqual(0, first_snapshot.prior_device_trial_users)
            self.assertEqual(0, first_snapshot.prior_ip_trial_users_24h)
            self.assertIn("account_under_1h", first_snapshot.signals)
            self.assertTrue(await service.record_started(first, first_snapshot))
            await session.commit()

        async with self.sessions() as session:
            second = await session.get(User, 2)
            snapshot = await TrialRiskService(session, settings).analyze(
                second,
                client="android",
                source="android_trial",
                installation_key_hash=device_hash,
                remote_ip=raw_ip,
            )

        self.assertEqual(1, snapshot.prior_device_trial_users)
        self.assertEqual(1, snapshot.prior_ip_trial_users_24h)
        self.assertEqual(1, snapshot.prior_ip_trial_users_7d)
        self.assertIn("device_used_for_other_trial", snapshot.signals)
        self.assertIn("shared_ip_24h", snapshot.signals)
        self.assertIn("account_under_24h", snapshot.signals)

        async with self.sessions() as session:
            row = (
                await session.execute(select(TrialRiskEvent).where(TrialRiskEvent.telegram_id == 101))
            ).scalar_one()
        self.assertNotEqual(raw_ip, row.ip_hash)
        self.assertEqual(64, len(row.ip_hash or ""))
        self.assertEqual(device_hash, row.installation_key_hash)
        self.assertNotIn(raw_ip, row.signals_json)

    async def test_invalid_ip_and_missing_secret_are_not_persisted_as_identifiers(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
            service = TrialRiskService(
                session,
                SimpleNamespace(DESKTOP_AUTH_SIGNING_SECRET="short"),
            )
            snapshot = await service.analyze(
                user,
                client="miniapp",
                source="miniapp_trial",
                remote_ip="not-an-ip",
            )

        self.assertIsNone(snapshot.ip_hash)
        self.assertIsNone(snapshot.installation_key_hash)


if __name__ == "__main__":
    unittest.main()
