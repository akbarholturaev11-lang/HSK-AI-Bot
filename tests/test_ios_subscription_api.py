import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.ios_subscription import create_ios_subscription_router


class IOSSubscriptionTransportTests(unittest.IsolatedAsyncioTestCase):
    async def _client(self, service):
        @asynccontextmanager
        async def session_factory():
            yield SimpleNamespace(commit=AsyncMock())
        app = FastAPI()
        app.include_router(create_ios_subscription_router(
            session_factory=session_factory,
            settings_obj=SimpleNamespace(),
            bot=SimpleNamespace(),
            service_factory=lambda *_args, **_kwargs: service,
        ))
        return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")

    async def test_overview_delegates_to_shared_service(self):
        service = SimpleNamespace(overview=AsyncMock(return_value={"ok": True, "status": "free"}))
        async with await self._client(service) as client:
            response = await client.get("/api/v3/ios/subscription/overview",
                                        headers={"Authorization": "Bearer token"})
        self.assertEqual(200, response.status_code)
        service.overview.assert_awaited_once_with("token")

    async def test_trial_status_delegates_to_shared_service(self):
        service = SimpleNamespace(trial_status=AsyncMock(return_value={"ok": True, "available": True}))
        async with await self._client(service) as client:
            response = await client.get("/api/v3/ios/subscription/trial",
                                        headers={"Authorization": "Bearer token"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["available"])
        service.trial_status.assert_awaited_once_with("token")


if __name__ == "__main__":
    unittest.main()
