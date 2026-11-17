"""Shaxsiy takror routerlari: egalik faqat transportdan, qat'iy body, xavfsiz nosozlik."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import course_adaptive as api
from app.db.base import Base
from app.db.models.user import User
from app.services.course_adaptive_lesson_service import AdaptiveRequestError
from app.services.desktop_auth_service import DesktopAuthError


def learner() -> User:
    return User(
        id=1, telegram_id=777, full_name="Learner", language="uz", level="hsk1",
        learning_mode="course", voice_mode="none", status="free", payment_status="none",
        question_limit=5, questions_used=0, bonus_questions=0, bonus_questions_used=0,
        discount_referral_count=0, discount_eligible=False, discount_used=False,
        daily_practice_streak=0, created_at=datetime.now(timezone.utc),
    )


class FakeService:
    def __init__(self):
        self.plan = AsyncMock(return_value={"ok": True, "enabled": True, "plan": {"id": 1, "items": []}})
        self.answer = AsyncMock(return_value={"ok": True, "item_id": "a1:1:meaning_choice", "correct": True})


class AdaptiveApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add(learner())
            await session.commit()
        self.service = FakeService()
        self.settings = SimpleNamespace(BOT_TOKEN="test-token")
        app = FastAPI()
        app.include_router(api.create_course_adaptive_router(
            session_factory=self.sessions, settings_obj=self.settings,
            service_factory=lambda session: self.service,
        ))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def telegram(self, verified=777):
        return patch.object(api, "extract_verified_webapp_user_id", return_value=verified)

    PLAN = {"level": "hsk1", "lesson_order": 3, "formats": ["meaning_choice"], "language": "uz"}
    ANSWER = {"plan_id": 1, "item_id": "a1:1:meaning_choice", "selected_index": 0}

    async def test_telegram_requires_signed_init_data(self):
        with self.telegram(None):
            response = await self.client.post("/api/v3/adaptive/plan", json=self.PLAN)
        self.assertEqual((response.status_code, response.json()["error"]), (401, "invalid_telegram_init_data"))
        self.service.plan.assert_not_awaited()

    async def test_telegram_owner_comes_from_init_data_only(self):
        with self.telegram():
            response = await self.client.post(
                "/api/v3/adaptive/plan", json=self.PLAN, headers={"X-Telegram-Init-Data": "signed"}
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        user = self.service.plan.await_args.args[0]
        self.assertEqual(user.id, 1)
        self.assertEqual(self.service.plan.await_args.kwargs["analytics_client"], "telegram")

    async def test_body_cannot_name_an_owner_or_extra_fields(self):
        with self.telegram():
            for body in ({**self.PLAN, "user_id": 2}, {**self.PLAN, "lesson_order": 0}, {"level": "hsk1"}):
                response = await self.client.post("/api/v3/adaptive/plan", json=body)
                self.assertEqual(response.status_code, 422, body)
            response = await self.client.post("/api/v3/adaptive/plan?user_id=2", json=self.PLAN)
            self.assertEqual(response.status_code, 422)
            response = await self.client.post(
                "/api/v3/adaptive/answer", json={**self.ANSWER, "selected_tokens": ["你"]}
            )
            self.assertEqual(response.status_code, 422)
            response = await self.client.post(
                "/api/v3/adaptive/answer", content=b"{}", headers={"Content-Type": "text/plain"}
            )
            self.assertEqual(response.status_code, 415)
        self.service.plan.assert_not_awaited()
        self.service.answer.assert_not_awaited()

    async def test_ambiguous_transport_is_rejected(self):
        with self.telegram():
            response = await self.client.post(
                "/api/v3/adaptive/plan", json=self.PLAN, headers={"Authorization": "Bearer x"}
            )
        self.assertEqual(response.status_code, 401)
        response = await self.client.post(
            "/api/v3/android/adaptive/plan", json=self.PLAN, headers={"X-Telegram-Init-Data": "signed"}
        )
        self.assertEqual(response.status_code, 401)

    async def test_pwa_requires_same_origin(self):
        self.settings.PWA_ENABLED = True
        response = await self.client.post("/api/v3/pwa/adaptive/plan", json=self.PLAN)
        self.assertEqual(response.status_code, 403)
        self.service.plan.assert_not_awaited()

    async def test_android_requires_a_valid_token(self):
        failing = AsyncMock(side_effect=DesktopAuthError("desktop_session_revoked", status_code=401))
        with patch.object(api.DesktopAuthService, "authenticate", failing):
            response = await self.client.post("/api/v3/android/adaptive/answer", json=self.ANSWER)
        self.assertEqual((response.status_code, response.json()["error"]), (401, "desktop_session_revoked"))
        self.service.answer.assert_not_awaited()

    async def test_android_passes_tokens_answer(self):
        async with self.sessions() as session:
            user = await session.get(User, 1)
        context = SimpleNamespace(user=user)
        with patch.object(api.DesktopAuthService, "authenticate", AsyncMock(return_value=context)):
            response = await self.client.post(
                "/api/v3/android/adaptive/answer",
                json={"plan_id": 1, "item_id": "a1:1:sentence_builder", "selected_tokens": ["我", "是"]},
                headers={"Authorization": "Bearer token"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        kwargs = self.service.answer.await_args.kwargs
        self.assertEqual((kwargs["answer"], kwargs["analytics_client"]), (["我", "是"], "android"))

    async def test_plan_failure_never_blocks_the_lesson(self):
        self.service.plan.side_effect = RuntimeError("db down")
        with self.telegram():
            response = await self.client.post("/api/v3/adaptive/plan", json=self.PLAN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "enabled": False, "plan": None})

    async def test_service_errors_keep_their_status(self):
        self.service.answer.side_effect = AdaptiveRequestError("adaptive_plan_not_found", status_code=404)
        with self.telegram():
            response = await self.client.post("/api/v3/adaptive/answer", json=self.ANSWER)
        self.assertEqual((response.status_code, response.json()), (404, {"ok": False, "error": "adaptive_plan_not_found"}))
        self.service.answer.side_effect = RuntimeError("db down")
        with self.telegram():
            response = await self.client.post("/api/v3/adaptive/answer", json=self.ANSWER)
        self.assertEqual((response.status_code, response.json()["error"]), (503, "adaptive_unavailable"))


if __name__ == "__main__":
    unittest.main()
