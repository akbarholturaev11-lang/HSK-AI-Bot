"""Cookie/CSRF/HTTPS and real payment adapter HTTP contracts (no live services)."""
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_payment_review_transport import create_admin_pwa_payment_review_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.db.models.payment import Payment
from app.db.models.user import User
from sqlalchemy import select, func
from app.db.models.admin_pwa_payment_review import AdminPwaPaymentOutbox, AdminPwaPaymentReview
from tests import test_admin_pwa_payment_review as payment_tests
from tests.test_admin_pwa_payment_review import COOKIE

# Use the SQL fixture, without inheriting and re-running its test methods.
from tests.test_admin_pwa_payment_review import PaymentFixtures
import unittest


class AdminPwaPaymentHttpTests(PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = payment_tests.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = payment_tests.AdminPwaPaymentReviewTests.asyncTearDown

    def app(self, *, dispatch=None):
        app = FastAPI()
        app.include_router(create_admin_pwa_payment_review_router(
            settings_obj=self.settings, session_factory=self.sessions, dispatch=dispatch))
        return app

    async def client(self, *, base_url="https://hskai.app", headers=None, cookie=COOKIE, dispatch=None):
        client = AsyncClient(transport=ASGITransport(app=self.app(dispatch=dispatch)), base_url=base_url,
            headers={"origin": "https://hskai.app", **(headers or {})})
        if cookie is not None:
            client.cookies.set(ADMIN_PWA_COOKIE_NAME, cookie)
        return client

    async def test_read_only_inspection_then_explicit_rejection_never_approves(self):
        async with await self.client() as client:
            inspected = await client.post("/api/admin/v1/payments/inspect-review",
                                          json={"payment_id": self.payment_id})
            self.assertEqual(inspected.status_code, 200, inspected.text)
            preview = inspected.json()
            self.assertEqual(preview["payment_id"], self.payment_id)
            self.assertEqual(preview["expected"]["amount"], 100)
            self.assertNotIn("decision", preview)
            self.assertNotIn("action", preview)
            self.assertNotIn("payload", preview)
            prepared = await client.post("/api/admin/v1/payments/prepare-review", json={
                "payment_id": self.payment_id, "decision": "reject", "reason": "invalid receipt"})
            self.assertEqual(prepared.status_code, 200, prepared.text)
            operation = prepared.json()
            self.assertEqual(operation["payload"]["decision"], "reject")
            self.assertEqual(operation["payload"]["expected"], preview["expected"])
            from app.admin_api.pwa_payment_review import PaymentReviewCommand
            command = PaymentReviewCommand.model_validate(operation["payload"])
            proof = await self.receipt(command, signed=True)
            committed = await client.post("/api/admin/v1/payments/review", json={
                **operation["payload"], "step_up_id": proof})
            self.assertEqual(committed.status_code, 200, committed.text)
            self.assertEqual(committed.json()["status"], "rejected")
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "rejected")
            self.assertIsNone((await db.get(User, 1)).end_date)
            audit = await db.scalar(select(AdminPwaPaymentReview))
            self.assertEqual(audit.decision, "reject")
            self.assertEqual(await db.scalar(select(func.count()).select_from(AdminPwaPaymentReview)), 1)

    async def test_real_http_prepare_signed_operation_and_review(self):
        async with await self.client() as client:
            prepared = await client.post("/api/admin/v1/payments/prepare-review", json={
                "payment_id": self.payment_id, "decision": "approve", "reason": None})
            self.assertEqual(prepared.status_code, 200, prepared.text)
            self.assertEqual(prepared.headers["cache-control"], "no-store")
            operation = prepared.json()
            self.assertEqual(operation["action"], "payments.review")
            from app.admin_api.pwa_payment_review import PaymentReviewCommand
            command = PaymentReviewCommand.model_validate(operation["payload"])
            receipt = await self.receipt(command, signed=True)
            result = await client.post("/api/admin/v1/payments/review", json={
                **operation["payload"], "step_up_id": receipt})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["status"], "approved")
            again = await client.post("/api/admin/v1/payments/review", json={
                **operation["payload"], "step_up_id": receipt})
            self.assertEqual(again.status_code, 403)

    async def test_flag_off_legacy_headers_or_foreign_origin_never_authorize(self):
        request={"payment_id": self.payment_id, "decision": "approve", "reason": None}
        for path in ("/api/admin/v1/payments/inspect-review", "/api/admin/v1/payments/prepare-review", "/api/admin/v1/payments/review"):
            self.settings.ADMIN_PWA_ENABLED=False
            async with await self.client() as client:
                self.assertEqual((await client.post(path, json=request)).status_code, 404)
            self.settings.ADMIN_PWA_ENABLED=True
            async with await self.client(cookie=None, headers={"X-Telegram-Init-Data": "ignored"}) as client:
                self.assertEqual((await client.post(path, json=request)).status_code, 401)
            async with await self.client(headers={"origin": "https://evil.example"}) as client:
                response=await client.post(path, json=request)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.headers["cache-control"], "no-store")
            async with await self.client(base_url="http://hskai.app") as client:
                self.assertEqual((await client.post(path, json=request)).status_code, 403)
            async with await self.client(headers={"sec-fetch-site": "cross-site"}) as client:
                self.assertEqual((await client.post(path, json=request)).status_code, 403)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "pending")

    async def test_strict_bounded_json_and_no_client_digest_shortcut(self):
        path="/api/admin/v1/payments/prepare-review"
        bodies=['{"payment_id":1,"payment_id":2,"decision":"approve","reason":null}',
                '{"payment_id":true,"decision":"approve","reason":null}',
                '{"payment_id":1,"decision":"approve","reason":null,"digest":"fake"}',
                '{"payment_id":1,"decision":"approve","reason":null,"extra":"'+'x'*4096+'"}',
                'null', '[]', '{']
        async with await self.client() as client:
            for body in bodies:
                with self.subTest(body=body[:80]):
                    response=await client.post(path, content=body, headers={"content-type":"application/json"})
                    self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual((await client.post(path, content="{}", headers={"content-type":"text/plain"})).status_code, 415)
            self.assertEqual((await client.post(path, json={}, headers=[("origin", "https://hskai.app"),
                                                                      ("origin", "https://hskai.app")])).status_code, 403)

    async def test_delivery_failure_after_commit_does_not_report_financial_failure(self):
        command=await self.command()
        receipt=await self.receipt(command)
        dispatch=AsyncMock(side_effect=RuntimeError("delivery unavailable"))
        async with await self.client(dispatch=dispatch) as client:
            response=await client.post("/api/admin/v1/payments/review", json={**command.model_dump(), "step_up_id":receipt})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "approved")
        dispatch.assert_awaited_once()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Payment, self.payment_id)).payment_status, "approved")
            self.assertEqual((await db.get(AdminPwaPaymentOutbox, response.json()["review_id"])).status, "pending")

    async def test_routes_mounted_and_legacy_telegram_guard_unchanged(self):
        from tests.test_main_imports import MainModuleImportTests
        main = MainModuleImportTests._import_main()
        paths=MainModuleImportTests._paths(main.app.routes)
        self.assertIn("/api/admin/v1/payments/review", paths)
        self.assertIn("/api/admin/v1/payments/prepare-review", paths)
        self.assertIn("/api/admin/v1/payments/inspect-review", paths)
        async with AsyncClient(transport=ASGITransport(app=main.app), base_url="https://hskai.app",
                               cookies={ADMIN_PWA_COOKIE_NAME: COOKIE}) as client:
            response=await client.post("/api/admin-miniapp/payments/review", json={"payment_id":1,"action":"approve"})
        self.assertEqual(response.status_code, 401)

    async def test_partial_delivery_reports_durable_uncertain_state(self):
        from app.admin_api.pwa_payment_outbox import dispatch_payment_review
        command = await self.command()
        receipt = await self.receipt(command)
        emitter = AsyncMock(side_effect=RuntimeError("timeout after partial send"))
        async def dispatch(review_id):
            return await dispatch_payment_review(review_id=review_id, session_factory=self.sessions,
                                                  settings_obj=self.settings, emit=emitter)
        async with await self.client(dispatch=dispatch) as client:
            response = await client.post("/api/admin/v1/payments/review", json={
                **command.model_dump(), "step_up_id": receipt})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "approved")
        self.assertEqual(response.json()["delivery_status"], "uncertain")
        emitter.assert_awaited_once()
