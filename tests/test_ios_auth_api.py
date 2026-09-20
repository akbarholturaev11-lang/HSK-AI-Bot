import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.ios_auth import IOSLinkStartRequest, create_ios_auth_router


class IOSAuthTransportTests(unittest.IsolatedAsyncioTestCase):
    def test_ios_start_model_rejects_android(self):
        with self.assertRaises(ValidationError):
            IOSLinkStartRequest(
                platform="android",
                app_version="1.0.0",
                installation_key="k" * 48,
            )

    async def test_start_route_always_uses_ios_platform(self):
        service = SimpleNamespace(
            start_link=AsyncMock(
                return_value={
                    "ok": True,
                    "status": "pending",
                    "link_request_id": "request-id",
                    "display_code": "ABCDEFGH",
                    "polling_secret": "s" * 48,
                    "bot_deep_link": "https://t.me/test?start=ios_link_request-id",
                }
            )
        )

        @asynccontextmanager
        async def session_factory():
            yield object()

        app = FastAPI()
        app.include_router(
            create_ios_auth_router(
                session_factory=session_factory,
                settings_obj=SimpleNamespace(),
                service_factory=lambda *_args: service,
            )
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
        ) as client:
            response = await client.post(
                "/api/v3/ios-auth/link/start",
                json={
                    "platform": "ios",
                    "app_version": "1.0.0",
                    "installation_key": "k" * 48,
                },
            )

        self.assertEqual(200, response.status_code)
        service.start_link.assert_awaited_once_with(
            platform="ios",
            app_version="1.0.0",
            installation_key="k" * 48,
        )


if __name__ == "__main__":
    unittest.main()
