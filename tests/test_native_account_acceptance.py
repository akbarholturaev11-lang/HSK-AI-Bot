"""Backend acceptance contracts; provider verification is mocked, not live OAuth."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import func, select

from app.api.android_course import create_android_course_router
from app.api.desktop_course import create_desktop_course_router
from app.api.desktop_rating import create_desktop_rating_router
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.desktop import DesktopLinkRequest, DesktopSession
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.identity_link_service import IdentityLinkService
from app.services.native_oauth_service import NativeOAuthService
from app.services.study_miniapp_service import StudyMiniAppService
from tests.test_native_oauth_api import _Base, _verified


class NativeAccountAcceptanceTests(_Base):
    settings_overrides = {
        "APPLE_OAUTH_ENABLED": True, "APPLE_SERVICE_ID": "acceptance-service",
        "APPLE_TEAM_ID": "test-team", "APPLE_KEY_ID": "test-key",
        "APPLE_PRIVATE_KEY": "test-only-not-a-private-key",
    }

    async def _signin(self, provider, *, platform="android", key="a", subject="legacy"):
        browser = platform != "android" or provider == "apple"
        started_response = await self.client.post("/api/v3/native-auth/oauth/start", json=self._start_body(
            provider=provider, platform=platform,
            mode="browser_redirect" if browser else "native_id_token",
            installation_key=key * 48,
        ))
        self.assertEqual(started_response.status_code, 200, started_response.text)
        started = started_response.json()
        identity = _verified(provider=provider, subject=subject)
        if not browser:
            with patch("app.services.google_auth.verify_android_id_token", return_value=identity):
                response = await self.client.post("/api/v3/native-auth/oauth/assert", json={
                    "link_request_id": started["link_request_id"], "polling_secret": started["polling_secret"],
                    "provider": provider, "id_token": "t" * 64,
                })
        else:
            async with self.sessions() as session:
                state = NativeOAuthService(session, self.settings).state(started["link_request_id"])
            adapter = "google_auth" if provider == "google" else "apple_auth"
            verifier = "verify_desktop_id_token" if provider == "google" else "verify_id_token_for_service"
            with patch(f"app.services.{adapter}.exchange_code", return_value="test-id-token"), \
                 patch(f"app.services.{adapter}.{verifier}", return_value=identity):
                path = f"/api/v3/native-auth/oauth/callback/{provider}"
                if provider == "apple":
                    response = await self.client.post(path, data={"state": state, "code": "test-code"})
                else:
                    response = await self.client.get(path, params={"state": state, "code": "test-code"})
        return started, response

    async def _bind_existing_providers(self):
        async with self.sessions() as session:
            for provider in ("google", "apple"):
                await IdentityLinkService(session, self.settings).link_to_user(
                    _verified(provider=provider, subject="legacy"), user_id=1)
            await session.commit()

    async def test_google_and_apple_cannot_sign_in_to_blocked_existing_identity(self):
        await self._bind_existing_providers()
        async with self.sessions() as session:
            (await session.get(User, 1)).status = "blocked"
            await session.commit()
        for provider in ("google", "apple"):
            with self.subTest(provider=provider):
                started, response = await self._signin(provider, key=provider[0])
                self.assertIn("user_blocked", response.text)
                async with self.sessions() as session:
                    row = await session.get(DesktopLinkRequest, started["link_request_id"])
                    self.assertEqual((row.status, row.link_failure_code), ("failed", "user_blocked"))
                    self.assertEqual(await session.scalar(select(func.count(User.id))), 2)
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 0)

    async def test_block_between_provider_approval_and_poll_prevents_token_minting(self):
        await self._bind_existing_providers()
        for provider in ("google", "apple"):
            with self.subTest(provider=provider):
                async with self.sessions() as session:
                    (await session.get(User, 1)).status = "free"
                    await session.commit()
                started, response = await self._signin(provider, key=provider[0])
                async with self.sessions() as session:
                    row = await session.get(DesktopLinkRequest, started["link_request_id"])
                    self.assertEqual(row.status, "approved", response.text)
                    self.assertIsNotNone(row.approved_identity_id)
                    (await session.get(User, 1)).status = "blocked"
                    await session.commit()
                    with self.assertRaises(DesktopAuthError) as rejected:
                        await DesktopAuthService(session, self.settings).poll_link(
                            link_request_id=started["link_request_id"], polling_secret=started["polling_secret"])
                    self.assertEqual(rejected.exception.code, "user_blocked")
                    self.assertEqual(await session.scalar(select(func.count(DesktopSession.id))), 0)

    async def test_legacy_paid_learner_keeps_payment_and_shared_progress_after_provider_signin(self):
        app = self.client._transport.app
        app.include_router(create_android_course_router(session_factory=self.sessions, settings_obj=self.settings))
        app.include_router(create_desktop_course_router(session_factory=self.sessions, settings_obj=self.settings))
        app.include_router(create_desktop_rating_router(session_factory=self.sessions, settings_obj=self.settings))
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status, user.payment_status = "active", "approved"
            user.start_date, user.end_date = now - timedelta(days=2), now + timedelta(days=28)
            session.add(CourseMiniAppProfile(user_id=1, xp_total=60))
            payment = Payment(user_telegram_id=1001, plan_type="1_month", amount=95,
                currency="somoni", payment_status="approved", reviewed_at=now)
            session.add(payment)
            await session.commit()
            before = (user.status, user.payment_status, user.start_date.replace(tzinfo=None),
                      user.end_date.replace(tzinfo=None), payment.id, payment.amount)
        await self._bind_existing_providers()
        headers = {}
        for provider, platform, key in (("google", "android", "G"), ("google", "windows", "W"), ("apple", "macos", "A")):
            started, response = await self._signin(provider, platform=platform, key=key)
            async with self.sessions() as session:
                tokens = await DesktopAuthService(session, self.settings).poll_link(
                    link_request_id=started["link_request_id"], polling_secret=started["polling_secret"])
                actor = await DesktopAuthService(session, self.settings).authenticate(tokens["access_token"])
                self.assertEqual((actor.user.id, actor.user.telegram_id), (1, 1001), response.text)
            headers[platform] = {"Authorization": "Bearer " + tokens["access_token"]}
        completed = await self.client.post("/api/v3/android/course/complete", headers=headers["android"],
            json={"lesson_order": 1, "event_id": "acceptance-legacy-android-lesson", "mistakes": []})
        self.assertEqual(completed.status_code, 200, completed.text)
        for platform in ("windows", "macos"):
            course = await self.client.get("/api/v3/desktop/course/map", headers=headers[platform])
            self.assertEqual(course.status_code, 200, course.text)
            payload = course.json()
            self.assertTrue(payload["user"]["is_paid"])
            self.assertEqual(payload["progress"]["completed"], 1)
            self.assertGreater(payload["progress"]["xp"], 60)
        rating = await self.client.get("/api/v3/desktop/rating/leaderboard", headers=headers["windows"])
        self.assertEqual(rating.status_code, 200, rating.text)
        async with self.sessions() as session:
            miniapp = await StudyMiniAppService(session).get_profile_payload(1001)
            self.assertTrue(miniapp["subscription"]["is_paid"])
            self.assertEqual(miniapp["stats"]["completed_lessons"], 1)
            self.assertEqual(miniapp["stats"]["xp"], payload["progress"]["xp"])
            self.assertEqual(rating.json()["xp"], miniapp["stats"]["xp"])
            user, payment = await session.get(User, 1), await session.get(Payment, before[4])
            after = (user.status, user.payment_status, user.start_date.replace(tzinfo=None),
                     user.end_date.replace(tzinfo=None), payment.id, payment.amount)
            self.assertEqual(after, before)
            self.assertEqual(payment.payment_status, "approved")
            self.assertEqual(await session.scalar(select(func.count(User.id))), 2)
            self.assertEqual(await session.scalar(select(func.count(Payment.id))), 1)
