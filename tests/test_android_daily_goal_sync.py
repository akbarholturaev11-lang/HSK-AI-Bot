"""One account, one daily goal.

A learner picked 40 XP in the Mini App and the Android app showed 50 at the
same moment. The server had owned `daily_goal_xp` since it stopped being a JS
variable, and the Mini App read and wrote it — but the Android contract never
carried it. Android kept its own copy in device storage, so neither side could
ever see the other's number.

What is pinned here is the contract: Android may send the goal, the server
bounds it the way it bounds the Mini App's, and it reaches the one setter both
clients share.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.android_course import (
    AndroidStudyPreferencesRequest,
    create_android_course_router,
)


class RequestContractTests(unittest.TestCase):
    def test_the_goal_alone_is_a_complete_request(self):
        # Changing only the goal is the normal case from the profile screen.
        self.assertEqual(AndroidStudyPreferencesRequest(daily_goal_xp=40).daily_goal_xp, 40)

    def test_it_is_bounded_exactly_as_the_mini_app_is(self):
        # miniapp_preferences.py: ge=10, le=500
        self.assertEqual(AndroidStudyPreferencesRequest(daily_goal_xp=10).daily_goal_xp, 10)
        self.assertEqual(AndroidStudyPreferencesRequest(daily_goal_xp=500).daily_goal_xp, 500)
        for value in (9, 501, 0, -40):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    AndroidStudyPreferencesRequest(daily_goal_xp=value)

    def test_an_empty_request_is_still_refused(self):
        with self.assertRaises(ValidationError):
            AndroidStudyPreferencesRequest()

    def test_the_other_preferences_still_work_on_their_own(self):
        self.assertEqual(AndroidStudyPreferencesRequest(daily_minutes=10).daily_minutes, 10)
        self.assertIsNone(AndroidStudyPreferencesRequest(daily_minutes=10).daily_goal_xp)


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = SimpleNamespace(
            set_study_preferences=AsyncMock(return_value={"ok": True, "study_setup": {}})
        )

        class _Session:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *exc):
                return False

        app = FastAPI()
        app.include_router(
            create_android_course_router(
                session_factory=_Session,
                settings_obj=SimpleNamespace(),
                service_factory=lambda session, settings: self.service,
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="https://testserver"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_the_goal_reaches_the_service(self):
        response = await self.client.post(
            "/api/v3/android/preferences/study",
            json={"daily_goal_xp": 40},
            headers={"Authorization": "Bearer t", "Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.set_study_preferences.await_args.kwargs["daily_goal_xp"], 40
        )

    async def test_a_goal_outside_the_bounds_never_reaches_it(self):
        response = await self.client.post(
            "/api/v3/android/preferences/study",
            json={"daily_goal_xp": 5000},
            headers={"Authorization": "Bearer t", "Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 422)
        self.service.set_study_preferences.assert_not_awaited()

    async def test_the_other_preferences_send_no_goal(self):
        await self.client.post(
            "/api/v3/android/preferences/study",
            json={"daily_minutes": 10},
            headers={"Authorization": "Bearer t", "Content-Type": "application/json"},
        )

        self.assertIsNone(
            self.service.set_study_preferences.await_args.kwargs["daily_goal_xp"]
        )


if __name__ == "__main__":
    unittest.main()
