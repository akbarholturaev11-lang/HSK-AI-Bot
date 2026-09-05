"""Uchdan-uchgacha: mashq xatosi haqiqiy bazaga tushishi.

Adapter testlari servisni mock qiladi, servis testlari bazani mock qiladi.
Bu test esa oraliqni yopadi: HAQIQIY imzolangan Telegram initData bilan
HAQIQIY bazaga so'rov yuboradi va `course_mistakes` da qator paydo
bo'lganini tekshiradi.

Aynan shu zanjir buzilsa Daily Plan zaiflikni ko'rmay qoladi, shuning uchun
u alohida qoplanadi.
"""

import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import urlencode

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.miniapp_practice import create_miniapp_practice_router
from app.db.base import Base
from app.db.models.course_mistake import CourseMistake
from app.db.models.user import User


BOT_TOKEN = "123456:test-token"
TELEGRAM_ID = 998877


def signed_init_data(telegram_id: int = TELEGRAM_ID) -> str:
    params = {
        "auth_date": "1757030000",
        "query_id": "AAA",
        "user": json.dumps({"id": telegram_id}, separators=(",", ":")),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


def learner(user_id: int = 1) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=TELEGRAM_ID,
        full_name="Test Learner",
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
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class DrillReportIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.session_factory() as session:
            session.add(learner())
            await session.commit()

        app = FastAPI()
        app.include_router(
            create_miniapp_practice_router(
                session_factory=self.session_factory,
                settings_obj=SimpleNamespace(BOT_TOKEN=BOT_TOKEN),
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _mistakes(self) -> list[CourseMistake]:
        async with self.session_factory() as session:
            result = await session.execute(select(CourseMistake))
            return list(result.scalars().all())

    async def _report(self, mistakes, feature="recognition", level="hsk1"):
        return await self.client.post(
            "/api/v3/practice/report",
            json={
                "feature": feature,
                "level": level,
                "language": "uz",
                "mistakes": mistakes,
                "initData": signed_init_data(),
            },
        )

    async def test_a_wrong_character_becomes_a_stored_mistake(self):
        response = await self._report([{"hanzi": "你", "selected": "好"}])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recorded"], 1)

        stored = await self._mistakes()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].correct_answer, "你")
        self.assertEqual(stored[0].user_answer, "好")
        self.assertEqual(stored[0].category, "character")
        self.assertEqual(stored[0].source, "recognition")
        self.assertEqual(stored[0].level, "hsk1")
        self.assertIn("nǐ", stored[0].prompt)

    async def test_repeating_the_same_mistake_raises_its_weight(self):
        # Bir xil xato ikki marta -> yangi qator emas, og'irlik oshadi.
        # Reja aynan shu og'irlikka qarab zaiflikni tanlaydi.
        await self._report([{"hanzi": "你", "selected": "好"}])
        await self._report([{"hanzi": "你", "selected": "您"}])

        stored = await self._mistakes()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].wrong_count, 2)

    async def test_memorize_mistakes_land_under_their_own_source(self):
        await self._report([{"hanzi": "好"}], feature="memorize")

        stored = await self._mistakes()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].source, "memorize")
        self.assertEqual(stored[0].category, "character")

    async def test_a_forged_character_is_never_stored(self):
        response = await self._report([{"hanzi": "ZZZ"}, {"hanzi": "🙂"}])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recorded"], 0)
        self.assertEqual(await self._mistakes(), [])

    async def test_a_tampered_signature_stores_nothing(self):
        response = await self.client.post(
            "/api/v3/practice/report",
            json={
                "feature": "recognition",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你"}],
                "initData": signed_init_data()[:-4] + "0000",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(await self._mistakes(), [])

    async def test_a_user_who_never_started_the_bot_stores_nothing(self):
        async with self.session_factory() as session:
            found = await session.execute(select(User).where(User.telegram_id == TELEGRAM_ID))
            await session.delete(found.scalar_one())
            await session.commit()

        response = await self._report([{"hanzi": "你"}])

        self.assertEqual(response.status_code, 403)
        self.assertEqual(await self._mistakes(), [])


if __name__ == "__main__":
    unittest.main()
