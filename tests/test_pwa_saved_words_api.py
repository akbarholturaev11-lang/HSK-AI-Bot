"""PWA dictionary saved words: per-user isolation, idempotence, strict inputs."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.pwa_saved_words import SavedWordSet, create_pwa_saved_words_router
from app.db.base import Base
from app.db.models.course_saved_word import CourseSavedWord


ORIGIN = "https://app.example.test"


class SavedWordsApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as db:
            await db.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        app = FastAPI()
        app.include_router(create_pwa_saved_words_router(
            session_factory=sessions, settings_obj=SimpleNamespace()
        ))
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN)
        self.current_actor = SimpleNamespace(id=101, status="free")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def action(self, route, payload):
        async def actor(_cookie, _csrf):
            return self.current_actor, None
        with (
            patch("app.api.pwa_saved_words.require_same_origin"),
            patch("app.api.pwa_saved_words.PwaAuthService", return_value=SimpleNamespace(mutation_actor=actor)),
        ):
            return await self.client.post(
                route, json=payload, headers={"Origin": ORIGIN,"X-HSK-PWA-CSRF":"test"}
            )

    async def test_save_remove_persist_and_other_account_sees_nothing(self):
        route="/api/v3/pwa/dictionary/saved/"
        self.assertEqual((await self.action(route+"list", {})).json()["words"], [])
        first=await self.action(route+"set", {"hanzi":"坚持","saved":True})
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json()["saved"],True)
        await self.action(route+"set", {"hanzi":"坚持","saved":True})
        self.assertEqual((await self.action(route+"list", {})).json()["words"], ["坚持"])
        self.current_actor=SimpleNamespace(id=102,status="free")
        self.assertEqual((await self.action(route+"list", {})).json()["words"], [])
        await self.action(route+"set", {"hanzi":"结果","saved":True})
        self.current_actor=SimpleNamespace(id=101,status="free")
        self.assertEqual((await self.action(route+"list", {})).json()["words"], ["坚持"])
        await self.action(route+"set", {"hanzi":"坚持","saved":False})
        self.assertEqual((await self.action(route+"list", {})).json()["words"], [])

    async def test_invalid_payload_rejected_before_database_write(self):
        route="/api/v3/pwa/dictionary/saved/set"
        for invalid in (
            {"hanzi":"not-a-Chinese-word","saved":True},
            {"hanzi":"结果","saved":"yes"},
            {"hanzi":"你好","saved":True,"user_id":102},
            {"hanzi":"","saved":True},
        ):
            result=await self.action(route,invalid)
            self.assertEqual(result.status_code,422)

    async def test_cross_origin_rejected(self):
        route="/api/v3/pwa/dictionary/saved/set"
        with patch("app.api.pwa_saved_words.require_same_origin", side_effect=__import__(
                "app.services.pwa_auth_service",fromlist=["PwaAuthError"]).PwaAuthError("pwa_origin_invalid",status_code=403)):
            result=await self.client.post(route,json={"hanzi":"学习","saved":True},headers={"Origin":"https://evil.invalid"})
        self.assertEqual(result.status_code,403)
        self.assertEqual(result.json()["ok"],False)


if __name__ == "__main__":
    unittest.main()
