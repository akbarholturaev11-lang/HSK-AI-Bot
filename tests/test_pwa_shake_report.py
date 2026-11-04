"""Authenticated PWA shake bug-report transport regression (no live Telegram)."""
import base64
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.admin_pwa_native_reports import (
    NativeReportAdmission, NativeReportRateLimited,
)
from tests.test_pwa_browser_auth import PwaBrowserAuthTests, ORIGIN


class PwaShakeReportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reuse the canonical browser OAuth/CSRF and SQLite model fixture,
        # not a synthetic authenticated Telegram or Android bearer token.
        await PwaBrowserAuthTests.asyncSetUp(self)
        self.settings.ADMIN_PWA_ENABLED = True
        self.receipt_bot.send_message = AsyncMock()
        self.receipt_bot.send_photo = AsyncMock()

    async def asyncTearDown(self):
        await PwaBrowserAuthTests.asyncTearDown(self)

    async def sign_in(self):
        state = await PwaBrowserAuthTests.begin(self)
        callback = await PwaBrowserAuthTests.callback(self, state)
        self.assertEqual(callback.status_code, 303, callback.text)
        session = await self.client.get("/api/v3/pwa-auth/session")
        self.assertEqual(session.status_code, 200, session.text)
        return session.json()["csrf"]

    def report(self, screenshot=""):
        return {
            "description": "Lessons do not open",
            "screen": "course",
            "app_version": "iphone-pwa",
            "screenshot_data_url": screenshot,
        }

    async def test_requires_cookie_csrf_and_origin(self):
        no_auth = await self.client.post(
            "/api/v3/pwa/bug-report", headers={"Origin": ORIGIN},
            json=self.report(),
        )
        self.assertIn(no_auth.status_code, (401, 403))
        csrf = await self.sign_in()
        missing_csrf = await self.client.post(
            "/api/v3/pwa/bug-report", headers={"Origin": ORIGIN},
            json=self.report(),
        )
        self.assertIn(missing_csrf.status_code, (401, 403))
        wrong_origin = await self.client.post(
            "/api/v3/pwa/bug-report",
            headers={"Origin": "https://evil.example", "X-HSK-PWA-CSRF": csrf},
            json=self.report(),
        )
        self.assertIn(wrong_origin.status_code, (401, 403))

    async def test_valid_user_report_reuses_private_inbox_and_bot_notification(self):
        csrf = await self.sign_in()
        image = b"\xff\xd8\xfftest-jpeg"
        data_url = "data:image/jpeg;base64," + base64.b64encode(image).decode()
        admission = NativeReportAdmission(report_id=9, already_sent=False)
        with patch(
            "app.services.admin_pwa_native_reports.reserve_native_report",
            new_callable=AsyncMock, return_value=admission,
        ) as reserve, patch(
            "app.services.admin_pwa_native_reports.finish_native_report",
            new_callable=AsyncMock,
        ) as finish, patch(
            "app.services.admin_notify_service.AdminNotifyService._feedback_recipient_ids",
            return_value=[987654],
        ):
            response = await self.client.post(
                "/api/v3/pwa/bug-report",
                headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                json=self.report(data_url),
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(reserve.await_args.kwargs["user_id"], 1)
        self.assertEqual(reserve.await_args.kwargs["screenshot"], image)
        self.assertEqual(reserve.await_args.kwargs["screen"], "course")
        self.receipt_bot.send_message.assert_awaited_once()
        self.receipt_bot.send_photo.assert_awaited_once()
        self.assertEqual(finish.await_args.kwargs["delivered"], True)

    async def test_rejects_invalid_image_and_no_notification_on_bad_request(self):
        csrf = await self.sign_in()
        for bad in (
            "data:image/png;base64," + base64.b64encode(b"\x89PNG").decode(),
            "data:image/jpeg;base64,not-base64",
            "data:image/jpeg;base64," + base64.b64encode(b"not-a-jpeg").decode(),
        ):
            with self.subTest(image=bad[:26]):
                response = await self.client.post(
                    "/api/v3/pwa/bug-report",
                    headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                    json=self.report(bad),
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.receipt_bot.send_message.assert_not_awaited()

    async def test_rate_limit_does_not_forge_success(self):
        csrf = await self.sign_in()
        with patch(
            "app.services.admin_pwa_native_reports.reserve_native_report",
            new_callable=AsyncMock, side_effect=NativeReportRateLimited(),
        ):
            result = await self.client.post(
                "/api/v3/pwa/bug-report",
                headers={"Origin": ORIGIN, "X-HSK-PWA-CSRF": csrf},
                json=self.report(),
            )
        self.assertEqual(result.status_code, 429, result.text)
        self.assertEqual(result.json()["error"], "pwa_report_rate_limited")
        self.receipt_bot.send_message.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
