import base64
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.desktop_subscription import (
    MAX_DESKTOP_SUBSCRIPTION_SUBMIT_BODY_BYTES,
    create_desktop_subscription_router,
)
from app.db.base import Base
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.payment import Payment
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.services.desktop_auth_service import DesktopAuthService


PNG_1X1_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _settings():
    return SimpleNamespace(
        DESKTOP_AUTH_SIGNING_SECRET="desktop-subscription-test-" + "x" * 48,
        DESKTOP_AUTH_LINK_TTL_SECONDS=600,
        DESKTOP_AUTH_ACCESS_TTL_SECONDS=900,
        DESKTOP_AUTH_REFRESH_TTL_DAYS=30,
        BOT_USERNAME="pomp_test_bot",
    )


def _user(user_id: int, telegram_id: int, name: str) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        telegram_id=telegram_id,
        full_name=name,
        language="uz",
        level="hsk1",
        learning_mode="course",
        voice_mode="none",
        status="free",
        payment_status="none",
        question_limit=5,
        questions_used=0,
        bonus_questions=0,
        bonus_questions_used=0,
        discount_referral_count=0,
        discount_eligible=False,
        discount_used=False,
        daily_practice_streak=0,
        created_at=now,
        last_active_at=now,
    )


class _BotStub:
    async def get_me(self):
        return SimpleNamespace(username="pomp_test_bot")


class DesktopSubscriptionApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.settings = _settings()
        self.bot = _BotStub()

        async with self.sessions() as session:
            session.add_all(
                [
                    _user(1, 1001, "Desktop A"),
                    _user(2, 1002, "Desktop B"),
                ]
            )
            await session.commit()
            self.token_a = await self._link(session, 1001, "a" * 48)
            self.token_b = await self._link(session, 1002, "b" * 48)

        # ConversionFunnelService intentionally writes through its own session.
        # Bind that writer to this isolated database for API-level assertions.
        self.funnel_session_patch = patch(
            "app.services.conversion_funnel_service.async_session_maker",
            self.sessions,
        )
        self.funnel_session_patch.start()

        self.app = FastAPI()
        self.app.include_router(
            create_desktop_subscription_router(
                session_factory=self.sessions,
                settings_obj=self.settings,
                bot=self.bot,
            )
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="https://desktop.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        self.funnel_session_patch.stop()
        await self.engine.dispose()

    async def _link(self, session, telegram_id: int, installation_key: str) -> str:
        auth = DesktopAuthService(session, self.settings)
        started = await auth.start_link(
            platform="macos",
            app_version="1.0.0",
            installation_key=installation_key,
        )
        await auth.approve_link(
            display_code=started["display_code"],
            telegram_id=telegram_id,
        )
        linked = await auth.poll_link(
            link_request_id=started["link_request_id"],
            polling_secret=started["polling_secret"],
        )
        return linked["access_token"]

    @staticmethod
    def _headers(token: str):
        return {"Authorization": f"Bearer {token}"}

    async def test_overview_requires_bearer_and_rejects_identity_query(self):
        missing = await self.client.get(
            "/api/v3/desktop/subscription/overview"
        )
        injected = await self.client.get(
            "/api/v3/desktop/subscription/overview"
            "?telegram_id=1002&amount=1&currency=USD&mode=admin_discount",
            headers=self._headers(self.token_a),
        )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["error"], "desktop_access_invalid")
        self.assertEqual(injected.status_code, 422)
        self.assertEqual(
            injected.json()["error"],
            "desktop_subscription_request_invalid",
        )
        self.assertEqual(missing.headers.get("cache-control"), "no-store")

    async def test_free_overview_returns_server_offer_access_and_fixed_source(self):
        response = await self.client.get(
            "/api/v3/desktop/subscription/overview",
            headers=self._headers(self.token_a),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "desktop_subscription")
        self.assertEqual(payload["mode"], "subscription")
        self.assertEqual(payload["access"]["state"], "free")
        self.assertFalse(payload["access"]["is_paid"])
        self.assertIsNone(payload["access"]["expires_at"])
        self.assertTrue(payload["checkout_allowed"])
        self.assertIsNone(payload["read_only_reason"])
        self.assertTrue(payload["attempt_id"].startswith("desktop-"))
        self.assertIn("3_months", payload["prices"]["visa"])
        self.assertEqual(response.headers.get("cache-control"), "no-store")

        async with self.sessions() as session:
            entry = (
                await session.execute(select(SubscriptionEntryEvent))
            ).scalar_one()
            funnel = (
                await session.execute(
                    select(ConversionFunnelEvent).where(
                        ConversionFunnelEvent.event_name == "checkout_opened"
                    )
                )
            ).scalar_one()
        self.assertEqual(entry.telegram_id, 1001)
        self.assertEqual(entry.source, "desktop_subscription")
        self.assertEqual(entry.mode, "subscription")
        self.assertEqual(funnel.telegram_id, 1001)
        self.assertEqual(funnel.source, "desktop_subscription")

    async def test_quote_uses_server_price_and_forbids_client_owned_fields(self):
        quote = await self.client.post(
            "/api/v3/desktop/subscription/quote",
            headers=self._headers(self.token_a),
            json={
                "plan_type": "1_month",
                "payment_method": "alipay",
                "card_country": None,
            },
        )
        injected = await self.client.post(
            "/api/v3/desktop/subscription/quote",
            headers=self._headers(self.token_a),
            json={
                "plan_type": "1_month",
                "payment_method": "alipay",
                "telegram_id": 1002,
                "amount": 1,
                "currency": "USD",
                "mode": "admin_discount",
            },
        )
        wrong_country = await self.client.post(
            "/api/v3/desktop/subscription/quote",
            headers=self._headers(self.token_a),
            json={
                "plan_type": "1_month",
                "payment_method": "alipay",
                "card_country": "tj",
            },
        )

        self.assertEqual(quote.status_code, 200)
        payload = quote.json()
        self.assertEqual(payload["source"], "desktop_subscription")
        self.assertEqual(payload["quote"]["final_amount"], 66)
        self.assertEqual(payload["quote"]["final_currency"], "¥")
        self.assertTrue(payload["quote"]["qr"]["available"])
        self.assertTrue(
            payload["quote"]["qr"]["image_data_url"].startswith(
                "data:image/jpeg;base64,"
            )
        )
        self.assertEqual(injected.status_code, 422)
        self.assertEqual(wrong_country.status_code, 422)

    async def test_event_requires_attempt_from_authenticated_overview(self):
        overview = await self.client.get(
            "/api/v3/desktop/subscription/overview",
            headers=self._headers(self.token_a),
        )
        attempt_id = overview.json()["attempt_id"]
        event = await self.client.post(
            "/api/v3/desktop/subscription/event",
            headers=self._headers(self.token_a),
            json={
                "attempt_id": attempt_id,
                "stage": "payment_instructions_viewed",
                "plan_type": "1_month",
                "payment_method": "alipay",
            },
        )
        foreign_attempt = await self.client.post(
            "/api/v3/desktop/subscription/event",
            headers=self._headers(self.token_b),
            json={
                "attempt_id": attempt_id,
                "stage": "payment_instructions_viewed",
                "plan_type": "1_month",
                "payment_method": "alipay",
            },
        )

        self.assertEqual(event.status_code, 200)
        self.assertTrue(event.json()["ok"])
        self.assertEqual(event.json()["source"], "desktop_subscription")
        self.assertEqual(foreign_attempt.status_code, 409)
        self.assertEqual(
            foreign_attempt.json()["error"],
            "checkout_attempt_not_opened",
        )

    async def test_submit_creates_one_pending_payment_for_authenticated_user(self):
        overview = await self.client.get(
            "/api/v3/desktop/subscription/overview",
            headers=self._headers(self.token_a),
        )
        request = {
            "plan_type": "1_month",
            "payment_method": "alipay",
            "card_country": None,
            "screenshot_data_url": PNG_1X1_DATA_URL,
            "attempt_id": overview.json()["attempt_id"],
        }
        notify = AsyncMock(return_value="telegram-file-id")
        with patch(
            "app.services.subscription_miniapp_service."
            "AdminNotifyService.notify_payment_review",
            notify,
        ):
            first = await self.client.post(
                "/api/v3/desktop/subscription/submit",
                headers=self._headers(self.token_a),
                json=request,
            )
            replay = await self.client.post(
                "/api/v3/desktop/subscription/submit",
                headers=self._headers(self.token_a),
                json=request,
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "pending")
        self.assertEqual(first.json()["source"], "desktop_subscription")
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["already_pending"])
        notify.assert_awaited_once()

        async with self.sessions() as session:
            payments = list(
                (await session.execute(select(Payment))).scalars().all()
            )
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].user_telegram_id, 1001)
        self.assertEqual(payments[0].payment_status, "pending")
        self.assertEqual(payments[0].amount, 66)
        self.assertEqual(payments[0].currency, "¥")
        self.assertEqual(payments[0].screenshot_file_id, "telegram-file-id")

    async def test_admin_delivery_failure_rolls_back_payment(self):
        notify = AsyncMock(side_effect=RuntimeError("telegram unavailable"))
        with patch(
            "app.services.subscription_miniapp_service."
            "AdminNotifyService.notify_payment_review",
            notify,
        ):
            response = await self.client.post(
                "/api/v3/desktop/subscription/submit",
                headers=self._headers(self.token_b),
                json={
                    "plan_type": "1_month",
                    "payment_method": "alipay",
                    "card_country": None,
                    "screenshot_data_url": PNG_1X1_DATA_URL,
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "admin_notification_failed")
        async with self.sessions() as session:
            payments = list(
                (await session.execute(select(Payment))).scalars().all()
            )
        self.assertEqual(payments, [])

    async def test_active_paid_account_is_read_only_and_keeps_expiry(self):
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        async with self.sessions() as session:
            user = await session.get(User, 1)
            user.status = "active"
            user.payment_status = "approved"
            user.end_date = expires_at
            await session.commit()

        overview = await self.client.get(
            "/api/v3/desktop/subscription/overview",
            headers=self._headers(self.token_a),
        )
        quote = await self.client.post(
            "/api/v3/desktop/subscription/quote",
            headers=self._headers(self.token_a),
            json={
                "plan_type": "1_month",
                "payment_method": "alipay",
                "card_country": None,
            },
        )
        submit = await self.client.post(
            "/api/v3/desktop/subscription/submit",
            headers=self._headers(self.token_a),
            json={
                "plan_type": "1_month",
                "payment_method": "alipay",
                "card_country": None,
                "screenshot_data_url": PNG_1X1_DATA_URL,
            },
        )

        self.assertEqual(overview.status_code, 200)
        payload = overview.json()
        self.assertEqual(payload["access"]["state"], "paid")
        self.assertTrue(payload["access"]["is_paid"])
        self.assertTrue(payload["access"]["expires_at"].endswith("Z"))
        self.assertFalse(payload["checkout_allowed"])
        self.assertEqual(
            payload["read_only_reason"],
            "desktop_subscription_active",
        )
        self.assertEqual(payload["prices"], {})
        self.assertIsNone(payload["attempt_id"])
        self.assertEqual(quote.status_code, 409)
        self.assertEqual(quote.json()["error"], "desktop_subscription_active")
        self.assertEqual(submit.status_code, 409)
        self.assertEqual(submit.json()["error"], "desktop_subscription_active")
        async with self.sessions() as session:
            self.assertIsNone(
                (await session.execute(select(Payment.id))).scalar_one_or_none()
            )

    async def test_receipt_mime_signature_and_body_size_are_enforced(self):
        jpeg_bytes = b"\xff\xd8\xff" + b"not-a-png"
        wrong_signature = "data:image/png;base64," + base64.b64encode(
            jpeg_bytes
        ).decode("ascii")
        invalid = await self.client.post(
            "/api/v3/desktop/subscription/submit",
            headers=self._headers(self.token_a),
            json={
                "plan_type": "1_month",
                "payment_method": "alipay",
                "card_country": None,
                "screenshot_data_url": wrong_signature,
            },
        )
        oversized = await self.client.post(
            "/api/v3/desktop/subscription/submit",
            headers={
                **self._headers(self.token_a),
                "Content-Type": "application/json",
                "Content-Length": str(
                    MAX_DESKTOP_SUBSCRIPTION_SUBMIT_BODY_BYTES + 1
                ),
            },
            content=b"{}",
        )
        wrong_content_type = await self.client.post(
            "/api/v3/desktop/subscription/quote",
            headers=self._headers(self.token_a),
            content=b"{}",
        )

        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["error"], "invalid_screenshot")
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(
            oversized.json()["error"],
            "desktop_subscription_request_too_large",
        )
        self.assertEqual(wrong_content_type.status_code, 415)


if __name__ == "__main__":
    unittest.main()
