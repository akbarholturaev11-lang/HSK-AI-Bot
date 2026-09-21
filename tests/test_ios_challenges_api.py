import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.api.ios_challenges import create_ios_challenge_router

class IOSChallengeTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_uses_shared_service(self):
        user=SimpleNamespace(telegram_id=123)
        context=SimpleNamespace(user=SimpleNamespace(telegram_id=123))
        service=SimpleNamespace(list_for_user=AsyncMock(return_value={"ok":True,"items":[]}))
        session=SimpleNamespace(commit=AsyncMock())
        @asynccontextmanager
        async def sf(): yield session
        app=FastAPI()
        app.include_router(create_ios_challenge_router(session_factory=sf,settings_obj=SimpleNamespace(),bot=SimpleNamespace(),challenge_service_factory=lambda *_:service))
        with (patch("app.api.ios_challenges.DesktopAuthService.authenticate",new=AsyncMock(return_value=context)),
              patch("app.api.ios_challenges.UserRepository.get_by_telegram_id",new=AsyncMock(return_value=user))):
            async with AsyncClient(transport=ASGITransport(app=app),base_url="https://test") as client:
                response=await client.get("/api/v3/ios/challenges",headers={"Authorization":"Bearer token"})
        self.assertEqual(200,response.status_code)
        service.list_for_user.assert_awaited_once_with(123)

    async def test_respond_delegates_action(self):
        user=SimpleNamespace(telegram_id=123)
        context=SimpleNamespace(user=SimpleNamespace(telegram_id=123))
        service=SimpleNamespace(respond=AsyncMock(return_value={"ok":True}))
        session=SimpleNamespace(commit=AsyncMock())
        @asynccontextmanager
        async def sf(): yield session
        app=FastAPI()
        app.include_router(create_ios_challenge_router(session_factory=sf,settings_obj=SimpleNamespace(),bot=SimpleNamespace(),challenge_service_factory=lambda *_:service))
        with (patch("app.api.ios_challenges.DesktopAuthService.authenticate",new=AsyncMock(return_value=context)),
              patch("app.api.ios_challenges.UserRepository.get_by_telegram_id",new=AsyncMock(return_value=user))):
            async with AsyncClient(transport=ASGITransport(app=app),base_url="https://test") as client:
                response=await client.post("/api/v3/ios/challenges/9/respond",headers={"Authorization":"Bearer token"},json={"action":"accept"})
        self.assertEqual(200,response.status_code)
        service.respond.assert_awaited_once()
        self.assertEqual("accept",service.respond.await_args.args[2])

if __name__=="__main__": unittest.main()
