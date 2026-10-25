"""Cached private aggregates recheck live authority after external IO."""
from datetime import datetime, timedelta, timezone
import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_feedback_analytics import create_admin_pwa_feedback_analytics_router
from app.admin_api.pwa_read import create_admin_pwa_read_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.admin_pwa import AdminPwaSession
from app.db.models.user import User
from tests import test_admin_pwa_payment_review as fixtures


class AggregateAuthorityTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def test_json_and_files_reject_authority_or_rollout_changed_during_cache_io(self):
        for base in ("statistics", "feedback/categories"):
            for export in (False, True):
                for change in ("revoked", "expired", "blocked", "allowlist", "disabled", "origin"):
                    with self.subTest(base=base, export=export, change=change):
                        self.settings.ADMIN_PWA_ENABLED = True
                        self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://hskai.app"
                        self.settings.admin_id_list = [9001]
                        async with self.sessions() as db:
                            session = await db.get(AdminPwaSession, self.session_id)
                            session.revoked_at = None
                            session.expires_at = datetime.now(timezone.utc)+timedelta(hours=1)
                            (await db.get(User, 101)).status = "active"
                            await db.commit()

                        async def reader(query):
                            if change == "disabled":
                                self.settings.ADMIN_PWA_ENABLED = False
                            elif change == "origin":
                                self.settings.ADMIN_PWA_PUBLIC_ORIGIN = "https://other.invalid"
                            elif change == "allowlist":
                                self.settings.admin_id_list = []
                            else:
                                async with self.sessions() as db:
                                    session = await db.get(AdminPwaSession, self.session_id)
                                    now = datetime.now(timezone.utc)
                                    if change == "revoked":
                                        session.revoked_at = now
                                    elif change == "expired":
                                        session.expires_at = now-timedelta(seconds=1)
                                    else:
                                        (await db.get(User, 101)).status = "blocked"
                                    await db.commit()
                            return {"private_marker": "MUST_NOT_LEAK"}

                        app = FastAPI()
                        kwargs = {"settings_obj": self.settings, "session_factory": self.sessions}
                        if base == "statistics":
                            app.include_router(create_admin_pwa_read_router(**kwargs, statistics_reader=reader))
                        else:
                            app.include_router(create_admin_pwa_feedback_analytics_router(**kwargs, reader=reader))
                        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://hskai.app",
                                headers={"origin": "https://hskai.app"},
                                cookies={ADMIN_PWA_COOKIE_NAME: fixtures.COOKIE}) as client:
                            response = await client.post("/api/admin/v1/"+base+("/export" if export else ""),
                                json={"format": "json"} if export else {})
                        expected = 404 if change == "disabled" else 403 if change == "origin" else 401
                        self.assertEqual(response.status_code, expected,
                                         response.text)
                        self.assertEqual(response.headers["cache-control"], "no-store")
                        self.assertNotIn("MUST_NOT_LEAK", response.text)
