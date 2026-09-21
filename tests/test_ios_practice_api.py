import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.ios_practice import create_ios_practice_router


class IOSPracticeTransportTests(unittest.IsolatedAsyncioTestCase):
    async def _client(self, service):
        @asynccontextmanager
        async def session_factory():
            yield object()

        app = FastAPI()
        app.include_router(
            create_ios_practice_router(
                session_factory=session_factory,
                settings_obj=SimpleNamespace(),
                service_factory=lambda *_args, **_kwargs: service,
            )
        )
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
        )

    async def test_start_delegates_to_shared_practice_service(self):
        service = SimpleNamespace(
            start=AsyncMock(
                return_value={
                    "ok": True,
                    "session": {
                        "id": "session-123",
                        "mode": "placement",
                        "skill": "",
                        "level": "hsk3",
                        "questions": [],
                    },
                }
            )
        )
        fake_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=123456)
        )

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service) as client:
                response = await client.post(
                    "/api/v3/ios/practice/start",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "mode": "placement",
                        "level": "hsk3",
                        "language": "uz",
                        "skill": "",
                        "access_ref": "",
                        "ad_supported": False,
                    },
                )

        self.assertEqual(200, response.status_code)
        service.start.assert_awaited_once_with(
            123456,
            mode="placement",
            level="hsk3",
            lang="uz",
            skill="",
            access_ref="",
            ad_supported=False,
        )

    async def test_complete_maps_selected_answers_to_server_shape(self):
        service = SimpleNamespace(
            complete=AsyncMock(
                return_value={
                    "ok": True,
                    "score": 1,
                    "total": 1,
                    "percent": 100,
                    "recommendation": "",
                    "wrong_items": [],
                }
            )
        )
        fake_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=123456)
        )

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service) as client:
                response = await client.post(
                    "/api/v3/ios/practice/complete",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "mode": "training",
                        "level": "hsk2",
                        "language": "ru",
                        "skill": "listening",
                        "session_id": "session-123",
                        "answers": [
                            {"question_id": "q1", "selected": 2}
                        ],
                        "access_ref": "",
                        "ad_supported": False,
                    },
                )

        self.assertEqual(200, response.status_code)
        service.complete.assert_awaited_once_with(
            123456,
            session_id="session-123",
            mode="training",
            level="hsk2",
            lang="ru",
            skill="listening",
            answers=[
                {"question_id": "q1", "selected_index": 2}
            ],
            access_ref="",
            ad_supported=False,
        )

    async def test_training_rejects_unknown_skill_before_service(self):
        service = SimpleNamespace(start=AsyncMock())
        fake_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=123456)
        )

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service) as client:
                response = await client.post(
                    "/api/v3/ios/practice/start",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "mode": "training",
                        "level": "hsk2",
                        "language": "tj",
                        "skill": "unknown",
                    },
                )

        self.assertEqual(422, response.status_code)
        service.start.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
