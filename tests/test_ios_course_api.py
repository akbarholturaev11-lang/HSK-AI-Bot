import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.ios_course import create_ios_course_router


class IOSCourseTransportTests(unittest.IsolatedAsyncioTestCase):
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
            course_map=AsyncMock(return_value={
                "ok": True, "level": "hsk3", "units": [],
                "progress": {}, "user": {}, "notify": {"enabled": True},
            })
        )
        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/map?tz=480",
                headers={"Authorization": "Bearer access-token"},
            )
        self.assertEqual(200, response.status_code)
        service.course_map.assert_awaited_once_with(
            "access-token", timezone_offset_minutes=480
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
        service = SimpleNamespace(onboarding_status=AsyncMock(return_value={
            "ok": True, "completed": False, "level": "hsk2",
            "profile": {
                "goal": "hsk_exam", "daily_minutes": 10,
                "start_mode": "lesson_1", "timezone_offset_minutes": 0,
            },
        }))
        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/onboarding",
                headers={"Authorization": "Bearer access-token"},
            )
        self.assertEqual(200, response.status_code)
        service.onboarding_status.assert_awaited_once_with("access-token")

    async def test_complete_onboarding_passes_validated_answers(self):
        service = SimpleNamespace(complete_onboarding=AsyncMock(return_value={
            "ok": True, "level": "hsk3", "tab": "course",
            "placement": False, "review_only": False,
            "foundation_required": False,
        }))
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
        service.complete_onboarding.assert_awaited_once()

    async def test_foundation_load_uses_shared_foundation_service(self):
        service = SimpleNamespace(foundation=AsyncMock(return_value={
            "ok": True,
            "foundation": {"id": "starter0_hsk1", "version": 1, "cards": []},
            "status": {"required": True, "completed": False},
        }))
        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/foundation",
                headers={"Authorization": "Bearer access-token"},
            )
        self.assertEqual(200, response.status_code)
        service.foundation.assert_awaited_once_with("access-token")

    async def test_foundation_completion_preserves_event_id(self):
        service = SimpleNamespace(complete_foundation=AsyncMock(return_value={
            "ok": True, "duplicate": False,
            "foundation": {"required": True, "completed": True},
        }))
        async with await self._client(service) as client:
            response = await client.post(
                "/api/v3/ios/course/foundation/complete",
                headers={"Authorization": "Bearer access-token"},
                json={
                    "foundation_id": "starter0_hsk1",
                    "foundation_version": 1,
                    "speaking_bonus": True,
                    "event_id": "ios:foundation:12345678",
                },
            )
        self.assertEqual(200, response.status_code)
        service.complete_foundation.assert_awaited_once_with(
            "access-token",
            foundation_id="starter0_hsk1",
            foundation_version=1,
            speaking_bonus=True,
            event_id="ios:foundation:12345678",
        )


    async def test_dictionary_uses_shared_course_dictionary(self):
        service = SimpleNamespace()
        fake_context = SimpleNamespace(user=SimpleNamespace(telegram_id=123456))
        user = SimpleNamespace(language="uz")

        with (
            patch(
                "app.api.ios_course.DesktopAuthService.authenticate",
                new=AsyncMock(return_value=fake_context),
            ),
            patch(
                "app.api.ios_course.UserRepository.get_by_telegram_id",
                new=AsyncMock(return_value=user),
            ),
            patch(
                "app.api.ios_course.dictionary_version",
                return_value="abc123",
            ),
            patch(
                "app.api.ios_course.dictionary_for_language",
                return_value=[{"h": "你", "p": "nǐ", "m": "sen", "lv": "1"}],
            ) as dictionary,
        ):
            async with await self._client(service) as client:
                response = await client.get(
                    "/api/v3/ios/dictionary",
                    headers={"Authorization": "Bearer access-token"},
                )

        self.assertEqual(200, response.status_code)
        self.assertEqual("abc123", response.json()["version"])
        self.assertEqual("你", response.json()["words"][0]["h"])
        dictionary.assert_called_once_with("uz")

    async def test_lesson_fetch_passes_access_ref(self):
        service = SimpleNamespace(lesson=AsyncMock(return_value={
            "ok": True, "level": "hsk1", "lesson_order": 1, "lesson": {},
        }))
        async with await self._client(service) as client:
            response = await client.get(
                "/api/v3/ios/course/lesson/1?access_ref=ad%3Aabc",
                headers={"Authorization": "Bearer access-token"},
            )
        self.assertEqual(200, response.status_code)
        service.lesson.assert_awaited_once_with(
            "access-token", lesson_order=1, access_ref="ad:abc"
        )

    async def test_lesson_completion_sends_only_client_mistake_selections(self):
        service = SimpleNamespace(complete=AsyncMock(return_value={
            "ok": True, "completed_lesson": 1, "duplicate": False,
        }))
        async with await self._client(service) as client:
            response = await client.post(
                "/api/v3/ios/course/complete",
                headers={"Authorization": "Bearer access-token"},
                json={
                    "lesson_order": 1,
                    "event_id": "ios:lesson:12345678",
                    "access_ref": "",
                    "mistakes": [{
                        "material_ref": "lesson:hsk1:1:section:1:card:3",
                        "selected_index": 1,
                    }],
                },
            )
        self.assertEqual(200, response.status_code)
        service.complete.assert_awaited_once_with(
            "access-token",
            lesson_order=1,
            event_id="ios:lesson:12345678",
            mistakes=[{
                "material_ref": "lesson:hsk1:1:section:1:card:3",
                "selected_index": 1,
            }],
            access_ref="",
        )


if __name__ == "__main__":
    unittest.main()
