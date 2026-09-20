import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.ios_course import create_ios_course_router


class IOSCourseOnboardingTransportTests(unittest.IsolatedAsyncioTestCase):
    async def _client(self, service):
        @asynccontextmanager
        async def session_factory():
            yield object()

        app = FastAPI()
        app.include_router(
            create_ios_course_router(
                session_factory=session_factory,
                settings_obj=SimpleNamespace(),
                service_factory=lambda *_args: service,
            )
        )
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
        )

    async def test_course_map_delegates_timezone_to_shared_service(self):
        service = SimpleNamespace(
            course_map=AsyncMock(
                return_value={
                    "ok": True,
                    "level": "hsk3",
                    "units": [],
                    "progress": {},
                    "user": {},
                    "notify": {"enabled": True},
                }
            )
        )

        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/map?tz=480",
                headers={"Authorization": "Bearer access-token"},
            )

        self.assertEqual(200, response.status_code)
        service.course_map.assert_awaited_once_with(
            "access-token",
            timezone_offset_minutes=480,
        )

    async def test_course_map_rejects_out_of_range_timezone(self):
        service = SimpleNamespace(course_map=AsyncMock())

        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/map?tz=9999",
                headers={"Authorization": "Bearer access-token"},
            )

        self.assertEqual(422, response.status_code)
        service.course_map.assert_not_awaited()

    async def test_status_delegates_to_shared_native_course_service(self):
        service = SimpleNamespace(
            onboarding_status=AsyncMock(
                return_value={
                    "ok": True,
                    "completed": False,
                    "level": "hsk2",
                    "profile": {
                        "goal": "hsk_exam",
                        "daily_minutes": 10,
                        "start_mode": "lesson_1",
                        "timezone_offset_minutes": 0,
                    },
                }
            )
        )

        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/onboarding",
                headers={"Authorization": "Bearer access-token"},
            )

        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["completed"])
        service.onboarding_status.assert_awaited_once_with("access-token")

    async def test_complete_passes_validated_ios_answers(self):
        service = SimpleNamespace(
            complete_onboarding=AsyncMock(
                return_value={
                    "ok": True,
                    "level": "hsk3",
                    "tab": "course",
                    "placement": False,
                    "review_only": False,
                    "foundation_required": False,
                }
            )
        )

        async with await self._client(service) as client:
            response = await client.post(
                "/api/v3/ios/course/onboarding",
                headers={"Authorization": "Bearer access-token"},
                json={
                    "level": "hsk3",
                    "goal": "study_china",
                    "daily_minutes": 10,
                    "start_mode": "lesson_1",
                    "language": "uz",
                    "timezone_offset_minutes": 480,
                    "activation_variant": "direct_start_v1",
                },
            )

        self.assertEqual(200, response.status_code)
        service.complete_onboarding.assert_awaited_once_with(
            "access-token",
            level="hsk3",
            goal="study_china",
            daily_minutes=10,
            start_mode="lesson_1",
            language="uz",
            timezone_offset_minutes=480,
            activation_variant="direct_start_v1",
        )


if __name__ == "__main__":
    unittest.main()
